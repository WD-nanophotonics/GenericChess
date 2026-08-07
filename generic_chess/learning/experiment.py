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
from .openings import ArenaOpeningCorpus, generate_arena_openings
from .selfplay import SelfPlayConfig, collect_self_play
from .tdleaf import TDLeafConfig, tdleaf_update
from .serialization import canonical_json, stable_sha256


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
    openings=None,
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
    (out_dir / "pre_calibration_config.json").write_text(
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
        opening_seed=config["arena_opening_seed"],
        opening_count=config["arena_opening_count"],
        min_plies=config["arena_min_plies"],
        max_plies=config["arena_max_plies"],
    )
    td_cfg = TDLeafConfig(
        gamma=config["gamma"],
        lambd=config["lambda"],
        alpha=config.get("alpha"),
    )
    if openings is None:
        openings = generate_arena_openings(
            compiled,
            count=config["arena_opening_count"] or config["arena_pairs"],
            seed=config["arena_opening_seed"],
            min_plies=config["arena_min_plies"],
            max_plies=config["arena_max_plies"],
        )
    openings.validate(compiled)

    training_rows: list[dict] = []
    arena_game_rows: list[dict] = []
    arena_pair_rows: list[dict] = []
    parent = gen0

    # ---- calibration phase (rule pre-registered; alpha derived) ----
    target_fraction = config.get("alpha_target_l2_fraction", 0.10)
    max_multiplier = config.get("alpha_max_multiplier", 200.0)
    cal_t0 = time.perf_counter()
    calibration_trajectories = collect_self_play(
        compiled, native_rules, parent, selfplay_cfg
    )
    nominal = tdleaf_update(calibration_trajectories, parent, td_cfg)
    median = parent.reference_median
    nominal_alpha = td_cfg.alpha or 0.01 * max(median, 1.0)
    target_l2 = target_fraction * median
    measured_l2 = max(nominal.weight_l2_delta, 1e-9)
    calibrated_alpha = min(
        nominal_alpha * (target_l2 / measured_l2),
        nominal_alpha * max_multiplier,
    )
    calibrated_alpha = max(calibrated_alpha, nominal_alpha)
    calibration_wall = time.perf_counter() - cal_t0
    clamped = calibrated_alpha >= nominal_alpha * max_multiplier - 1e-9
    calibration_artifact = {
        "trajectory_ids": [t.trajectory_id for t in calibration_trajectories],
        "number_of_trajectories": len(calibration_trajectories),
        "positions": nominal.positions_seen,
        "reference_median": median,
        "nominal_alpha": nominal_alpha,
        "measured_nominal_l2": measured_l2,
        "target_l2": target_l2,
        "target_fraction": target_fraction,
        "max_multiplier": max_multiplier,
        "calibrated_alpha": calibrated_alpha,
        "multiplier_clamped": clamped,
        "calibration_wall_seconds": calibration_wall,
    }
    calibration_hash = stable_sha256(calibration_artifact)
    calibration_artifact["calibration_artifact_hash"] = calibration_hash
    (out_dir / "calibration.json").write_text(
        canonical_json(calibration_artifact) + "\n", encoding="utf-8"
    )

    final_config = dict(config)
    final_config.update(
        {
            "calibrated_alpha": calibrated_alpha,
            "alpha_nominal": nominal_alpha,
            "calibration_artifact_hash": calibration_hash,
            "opening_corpus_id": openings.corpus_id,
        }
    )
    training_config_hash = stable_sha256(final_config)
    final_config["training_config_hash"] = training_config_hash
    (out_dir / "final_config.json").write_text(
        canonical_json(final_config) + "\n", encoding="utf-8"
    )
    (out_dir / "config.json").write_text(
        canonical_json(final_config) + "\n", encoding="utf-8"
    )
    calibrated_cfg = TDLeafConfig(
        gamma=config["gamma"],
        lambd=config["lambda"],
        alpha=calibrated_alpha,
    )

    used_trajectories = calibration_trajectories
    for generation in range(1, config["generations"] + 1):
        t0 = time.perf_counter()
        trajectories = used_trajectories
        update = tdleaf_update(trajectories, parent, calibrated_cfg)
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
        arena = run_arena(
            compiled, native_rules, parent, child, arena_cfg, openings=openings
        )
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
                "calibrated_alpha": calibrated_alpha,
                "pair_mean": arena.mean_pair_score,
                "bootstrap_low": arena.bootstrap_low,
                "bootstrap_high": arena.bootstrap_high,
                "better_pairs": arena.child_better_pairs,
                "tied_pairs": arena.tied_pairs,
                "worse_pairs": arena.child_worse_pairs,
                "game_wins": arena.game_wins,
                "game_draws": arena.game_draws,
                "game_losses": arena.game_losses,
                "game_score_rate": arena.game_score_rate,
            }
        )
        for pair in arena.pairs:
            for game in (pair.game_child_owner0, pair.game_child_owner1):
                arena_game_rows.append(
                    {
                        "generation": generation,
                        "training_seed": config["training_seed"],
                        "pair": pair.pair_index,
                        "opening_id": pair.opening_id,
                        "child_owner": game.child_owner,
                        "winner": game.winner,
                        "result": game.result,
                        "child_points": game.child_points,
                        "plies": game.plies,
                        "final_position_key": game.final_position_key,
                    }
                )
            arena_pair_rows.append(
                {
                    "generation": generation,
                    "training_seed": config["training_seed"],
                    "pair": pair.pair_index,
                    "opening_id": pair.opening_id,
                    "game_a_points": pair.game_child_owner0.child_points,
                    "game_b_points": pair.game_child_owner1.child_points,
                    "pair_score": pair.child_pair_score,
                }
            )
        gen_file = out_dir / f"generation_{generation:03d}.json"
        gen_file.write_text(
            json.dumps(
                {
                    "parent": parent.to_dict(),
                    "child": child.to_dict(),
                    "training": training_rows[-1],
                    "arena_pairs": arena_pair_rows[-len(arena.pairs):],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        parent = child
        used_trajectories = None
        if generation < config["generations"]:
            used_trajectories = collect_self_play(
                compiled, native_rules, parent, selfplay_cfg
            )

    (out_dir / "training.csv").write_text(
        _csv(training_rows), encoding="utf-8"
    )
    (out_dir / "arena_games.csv").write_text(
        _csv(arena_game_rows), encoding="utf-8"
    )
    (out_dir / "arena_pairs.csv").write_text(
        _csv(arena_pair_rows), encoding="utf-8"
    )
    curve = [
        {
            "generation": r["generation"],
            "training_games_seen": r["games"],
            "training_wall_seconds": r["training_wall_seconds"],
            "parent_score": 1.0 - r["pair_mean"],
            "child_score": r["pair_mean"],
            "weight_l2_delta": r["weight_l2_delta"],
        }
        for r in training_rows
    ]
    (out_dir / "learning_curve.csv").write_text(_csv(curve), encoding="utf-8")
    summary = {
        "ruleset_label": label,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "generations": len(training_rows),
        "opening_corpus_id": openings.corpus_id,
        "gen1_pair_mean": (
            training_rows[0]["pair_mean"] if training_rows else None
        ),
        "final_pair_mean": (
            training_rows[-1]["pair_mean"] if training_rows else None
        ),
        "final_config_hash": training_config_hash,
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
    parser.add_argument("--arena-opening-seed", type=int, default=314159)
    parser.add_argument("--arena-opening-count", type=int, default=0)
    parser.add_argument("--arena-min-plies", type=int, default=2)
    parser.add_argument("--arena-max-plies", type=int, default=6)
    parser.add_argument("--openings-path", default=None)
    parser.add_argument("--alpha", type=float, default=None)
    parser.add_argument("--alpha-target-fraction", type=float, default=0.10)
    parser.add_argument("--alpha-max-multiplier", type=float, default=200.0)
    parser.add_argument("--lambda", dest="lambd", type=float, default=0.7)
    parser.add_argument("--max-depth", type=int, default=12)
    parser.add_argument("--epsilon", type=float, default=0.10)
    parser.add_argument("--tt-mb", type=int, default=8)
    parser.add_argument("--output", default=None)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--proof", action="store_true")
    parser.add_argument("--gen0-gate", action="store_true")
    args = parser.parse_args(argv)

    params = {
        "training_seed": args.seed,
        "generations": args.generations,
        "selfplay_games": args.selfplay_games,
        "selfplay_nodes": args.selfplay_nodes,
        "arena_pairs": args.arena_pairs,
        "arena_nodes": args.arena_nodes,
        "arena_opening_seed": args.arena_opening_seed,
        "arena_opening_count": args.arena_opening_count,
        "arena_min_plies": args.arena_min_plies,
        "arena_max_plies": args.arena_max_plies,
        "alpha": args.alpha,
        "alpha_target_l2_fraction": args.alpha_target_fraction,
        "alpha_max_multiplier": args.alpha_max_multiplier,
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
        if args.gen0_gate:
            from ..ai.evaluation.config import EvaluationConfig as _EC
            from ..ai.evaluation.profile import build_ruleset_profile as _BRP

            profile = _BRP(compiled, _EC())
            gen0 = LearnableMaterialCheckpoint.from_profile(
                compiled, profile, training_seed=args.seed
            )
            native_rules = compile_native_rules(compiled)
            openings = generate_arena_openings(
                compiled,
                count=params["arena_opening_count"] or params["arena_pairs"],
                seed=params["arena_opening_seed"],
                min_plies=params["arena_min_plies"],
                max_plies=params["arena_max_plies"],
            )
            if args.openings_path:
                path = Path(args.openings_path) / f"{label}_openings.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    canonical_json(openings.to_dict()) + "\n", encoding="utf-8"
                )
            gate_cfg = ArenaConfig(
                pairs=params["arena_pairs"],
                nodes_per_move=params["arena_nodes"],
                max_depth=params["max_depth"],
                tt_megabytes=params["tt_mb"],
            )
            summary = run_arena(
                compiled, native_rules, gen0, gen0, gate_cfg, openings=openings
            )
            bad = [s for s in summary.pair_scores if s != 0.5]
            print(
                f"{label} Gen0-vs-Gen0: pairs={summary.pair_count} "
                f"mean={summary.mean_pair_score:.3f} non_half={len(bad)}"
            )
            if bad:
                print("MEASUREMENT_INVALID: not all pair scores are 0.5")
                return 1
            print("Gen0-vs-Gen0 gate PASSED")
            continue
        openings = None
        if args.openings_path:
            path = Path(args.openings_path) / f"{label}_openings.json"
            if path.exists():
                openings = ArenaOpeningCorpus.from_dict(
                    json.loads(path.read_text(encoding="utf-8"))
                )
                openings.validate(compiled)
            else:
                openings = generate_arena_openings(
                    compiled,
                    count=params["arena_opening_count"] or params["arena_pairs"],
                    seed=params["arena_opening_seed"],
                    min_plies=params["arena_min_plies"],
                    max_plies=params["arena_max_plies"],
                )
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    canonical_json(openings.to_dict()) + "\n", encoding="utf-8"
                )
        experiment_id = f"{label}_seed{args.seed}"
        out_dir = root / experiment_id
        if not args.smoke and not args.proof and out_dir.exists():
            out_dir = root / f"{experiment_id}_{int(time.time())}"
        print(f"running {label} -> {out_dir}")
        summaries.append(
            _run_experiment(label, spec, compiled, params, out_dir, openings)
        )
    for s in summaries:
        print(
            f"{s['ruleset_label']}: gen1 pair mean "
            f"{s['gen1_pair_mean']:.3f} | final pair mean "
            f"{s['final_pair_mean']:.3f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
