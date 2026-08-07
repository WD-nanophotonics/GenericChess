"""Pre-registered proof-of-learning experiments (CLI).

Usage::

    python -m generic_chess.learning.experiment --smoke
    python -m generic_chess.learning.experiment --proof
    python -m generic_chess.learning.experiment --ruleset classic --seed 7 \
        --generations 2 --selfplay-games 4 --arena-pairs 3 --output out/
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from ..ai.evaluation.config import EvaluationConfig
from ..ai.evaluation.profile import build_ruleset_profile
from ..native.compiler import compile_native_rules
from .arena import ArenaConfig, ArenaSummary, run_arena
from .material import LearnableMaterialCheckpoint
from .selfplay import SelfPlayConfig, collect_self_play
from .tdleaf import TDLeafConfig, tdleaf_update
from .serialization import canonical_json


def _commit_hash() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return out.stdout.strip()
    except Exception:
        return "unknown"


def _rulesets():
    from ..ai.benchmark.audit_suite import standard_ruleset_specs
    from ..generation.config import GeneratorConfig
    from ..generation.generator import generate_game
    from ..core.movement import LeapAtom, RayAtom
    from ..core.pieces import Piece, PieceType

    from tests.native_test_helpers import simple_ruleset

    out = []
    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    for fid, label in (
        ("gen_classic_like_4_101", "R1_classic_like"),
        ("gen_free_random_4_102", "R2_weird_generic"),
    ):
        from ..ai.benchmark.audit_suite import build_compiled

        out.append((label, specs[fid], build_compiled(specs[fid])))
    # R3: promotion + drop hybrid, clearly not traditional chess.
    n = 6
    king = PieceType("K", "K", (), is_anchor=True)
    pawn = PieceType(
        "P", "P", (LeapAtom((0, 1)), LeapAtom((0, -1))),
        is_promotable=True, promotion_target_ids=("G", "Q"),
    )
    g = PieceType("G", "G", (LeapAtom((0, 1)), LeapAtom((0, -1))))
    queen = PieceType(
        "Q", "Q", tuple(
            RayAtom((df, dr)) for df in (-1, 0, 1) for dr in (-1, 0, 1)
            if (df, dr) != (0, 0)
        ),
    )
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[n - 1][n - 1] = Piece(1, "K", "K", False)
    rows[1][0] = Piece(0, "P", "P", False)
    rows[1][1] = Piece(1, "P", "P", False)
    compiled = simple_ruleset(
        (king, pawn, g, queen), rows, drop_types=("P", "G", "Q"),
        drop_mask_all=True,
        promotion_allowed={"P": ((), ())},
        promotion_forced={"P": ((), ())},
        board_size=n,
    )
    out.append(("R3_promo_drop_hybrid", None, compiled))
    return out


def _run_experiment(
    label: str,
    spec,
    compiled,
    params: dict,
    out_dir: Path,
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    config = dict(params)
    config.update(
        {
            "commit": _commit_hash(),
            "ruleset_label": label,
            "ruleset_fingerprint": compiled.ruleset_fingerprint,
        }
    )
    (out_dir / "config.json").write_text(
        canonical_json(config) + "\n", encoding="utf-8"
    )

    eval_config = EvaluationConfig()
    profile = build_ruleset_profile(compiled, eval_config)
    native_rules = compile_native_rules(compiled)
    gen0 = LearnableMaterialCheckpoint.from_profile(
        compiled, profile, training_seed=config["training_seed"]
    )
    (out_dir / "generation_000.json").write_text(
        json.dumps(gen0.to_dict(), sort_keys=True) + "\n", encoding="utf-8"
    )

    selfplay_cfg = SelfPlayConfig(
        games=config["selfplay_games"],
        nodes_per_move=config["selfplay_nodes"],
        max_depth=config["max_depth"],
        seed=config["training_seed"],
        epsilon=config["epsilon"],
        tt_megabytes=config["tt_mb"],
    )
    arena_cfg = ArenaConfig(
        pairs=config["arena_pairs"],
        nodes_per_move=config["arena_nodes"],
        max_depth=config["max_depth"],
        tt_megabytes=config["tt_mb"],
        seed=config["training_seed"],
    )
    td_cfg = TDLeafConfig(
        gamma=config["gamma"],
        lambd=config["lambda"],
        alpha=config.get("alpha"),
    )
    training_config_hash = canonical_json(config)

    training_rows: list[dict] = []
    arena_rows: list[dict] = []
    parent = gen0
    for generation in range(1, config["generations"] + 1):
        t0 = time.perf_counter()
        trajectories = collect_self_play(
            compiled, native_rules, parent, selfplay_cfg
        )
        update = tdleaf_update(trajectories, parent, td_cfg)
        child = parent.child_checkpoint(
            board_weights=update.board_weights,
            hand_weights=update.hand_weights,
            games_seen_delta=len(trajectories),
            positions_seen_delta=update.positions_seen,
            training_updates_delta=1,
            training_config_hash=training_config_hash,
            training_seed=config["training_seed"],
        )
        wall = time.perf_counter() - t0
        arena = run_arena(compiled, native_rules, parent, child, arena_cfg)
        training_rows.append(
            {
                "generation": generation,
                "parent": parent.checkpoint_id,
                "child": child.checkpoint_id,
                "games": len(trajectories),
                "positions": update.positions_seen,
                "mean_td_error": update.mean_td_error,
                "mean_abs_td_error": update.mean_abs_td_error,
                "max_abs_td_error": update.max_abs_td_error,
                "weight_l2_delta": update.weight_l2_delta,
                "weight_max_delta": update.weight_max_delta,
                "normalization_factor": update.normalization_factor,
                "training_wall_seconds": wall,
                "arena_wins": arena.wins,
                "arena_draws": arena.draws,
                "arena_losses": arena.losses,
                "arena_score_rate": arena.score_rate,
                "arena_wilson_low": arena.wilson_low,
                "arena_wilson_high": arena.wilson_high,
            }
        )
        for game in arena.games:
            arena_rows.append(
                {
                    "generation": generation,
                    "pair": game.pair,
                    "child_owner": game.child_owner,
                    "winner": game.winner,
                    "result": game.result,
                    "child_points": game.child_points,
                    "plies": game.plies,
                }
            )
        gen_file = out_dir / f"generation_{generation:03d}.json"
        gen_file.write_text(
            json.dumps(
                {
                    "parent": parent.to_dict(),
                    "child": child.to_dict(),
                    "training": training_rows[-1],
                    "arena": arena_rows[-len(arena.games):],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        parent = child

    (out_dir / "training.csv").write_text(
        _csv(training_rows), encoding="utf-8"
    )
    (out_dir / "arena.csv").write_text(_csv(arena_rows), encoding="utf-8")
    curve = [
        {
            "generation": r["generation"],
            "training_games_seen": r["games"],
            "training_wall_seconds": r["training_wall_seconds"],
            "parent_score": 1.0 - r["arena_score_rate"],
            "child_score": r["arena_score_rate"],
            "weight_l2_delta": r["weight_l2_delta"],
        }
        for r in training_rows
    ]
    (out_dir / "learning_curve.csv").write_text(_csv(curve), encoding="utf-8")
    best = max(training_rows, key=lambda r: r["arena_score_rate"])
    summary = {
        "ruleset_label": label,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "generations": len(training_rows),
        "best_generation": best["generation"],
        "best_child_score": best["arena_score_rate"],
        "final_child_score": training_rows[-1]["arena_score_rate"],
        "config": config,
    }
    (out_dir / "summary.json").write_text(
        json.dumps(summary, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def _csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    keys = list(rows[0].keys())
    lines = [",".join(keys)]
    for row in rows:
        lines.append(
            ",".join(str(row.get(k, "")) for k in keys)
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="generic_chess.learning.experiment")
    parser.add_argument("--ruleset", default=None,
                        help="R1_classic_like | R2_weird_generic | "
                             "R3_promo_drop_hybrid")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--generations", type=int, default=3)
    parser.add_argument("--selfplay-games", type=int, default=6)
    parser.add_argument("--selfplay-nodes", type=int, default=2000)
    parser.add_argument("--arena-pairs", type=int, default=6)
    parser.add_argument("--arena-nodes", type=int, default=4000)
    parser.add_argument("--alpha", type=float, default=None)
    parser.add_argument("--lambda", dest="lambd", type=float, default=0.7)
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--epsilon", type=float, default=0.10)
    parser.add_argument("--tt-mb", type=int, default=8)
    parser.add_argument("--output", default=None)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--proof", action="store_true")
    args = parser.parse_args(argv)

    params = {
        "training_seed": args.seed,
        "generations": args.generations,
        "selfplay_games": args.selfplay_games,
        "selfplay_nodes": args.selfplay_nodes,
        "arena_pairs": args.arena_pairs,
        "arena_nodes": args.arena_nodes,
        "alpha": args.alpha,
        "lambda": args.lambd,
        "gamma": 1.0,
        "max_depth": args.max_depth,
        "epsilon": args.epsilon,
        "tt_mb": args.tt_mb,
    }
    if args.smoke:
        params.update(
            {
                "generations": 1,
                "selfplay_games": 2,
                "selfplay_nodes": 300,
                "arena_pairs": 2,
                "arena_nodes": 300,
                "max_depth": 6,
            }
        )
    root = Path(args.output) if args.output else (
        Path.cwd() / "artifacts" / "learning_phase1"
    )
    rulesets = _rulesets()
    selected = rulesets
    if args.ruleset:
        selected = [r for r in rulesets if r[0] == args.ruleset]
        if not selected:
            print(f"unknown ruleset {args.ruleset!r}", file=sys.stderr)
            return 2
    summaries = []
    for label, spec, compiled in selected:
        experiment_id = f"{label}_seed{args.seed}"
        out_dir = root / experiment_id
        if not args.smoke and not args.proof and out_dir.exists():
            out_dir = root / f"{experiment_id}_{int(time.time())}"
        print(f"running {label} -> {out_dir}")
        summaries.append(
            _run_experiment(label, spec, compiled, params, out_dir)
        )
    for s in summaries:
        print(
            f"{s['ruleset_label']}: best child score "
            f"{s['best_child_score']:.3f} at gen {s['best_generation']}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
