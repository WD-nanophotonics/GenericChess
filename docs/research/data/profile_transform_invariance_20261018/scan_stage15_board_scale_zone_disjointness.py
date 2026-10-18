"""Does the zone/promotion-source disjointness of this study depend on board size?

Every measurement in this report is board 4 with ``setup_preset classic_like``.
This script asks whether the structural exclusion closed in Stage 10 and Stage 14
is a small-board artefact by regenerating the *same* seeds at board sizes 6 and
8 and recomputing the same geometric partition.

Structural only: ``generic_chess/core/movegen.py`` builds a promotion variant
only when ``(from_square, to_square) in compiled.promotion_allowed``, so a zone
square that is not a promotion source cannot carry a promotion action at all.
No search, no game replay, no evaluator change, no new games - ruleset
regeneration and set arithmetic only. No contact count and no contact rate is
produced here; the withdrawn 0-versus-53 contrast stays excluded.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.core.coordinates import square_to_index  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402

HERE = Path(__file__).resolve().parent
STAGE8 = HERE / "results_bind_reachability_to_decisions.json"
PLAN = HERE / "plan_stage15_board_scale_zone_disjointness.json"
OUT = HERE / "results_stage15_board_scale_zone_disjointness.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage8_seeds() -> list[int]:
    """The seed list already examined by this study, in first-appearance order."""
    stage8 = json.loads(STAGE8.read_text(encoding="utf-8"))
    seen: dict[int, None] = {}
    for game in stage8["per_game"]:
        seen.setdefault(game["seed"], None)
    return sorted(seen)


def geometry(seed: int, board: int) -> dict:
    compiled = generate_game(
        GeneratorConfig(seed=seed, board_size=board, setup_preset="classic_like")
    ).compiled_ruleset
    config = EvaluationConfig()
    evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)
    zones = 0
    sources = 0
    intersection = 0
    pairs_with_zone = 0
    for base, gain in evaluator._profile.promotion_gain_by_type.items():
        if gain <= 0:
            continue
        for side in (0, 1):
            zone = evaluator._zones.get((base, side))
            if not zone:
                continue
            pairs_with_zone += 1
            allowed = compiled.promotion_allowed.get(base, ((), ()))[side]
            source_set = {square_to_index(src, compiled.board_size) for src, _dst in allowed}
            zones += len(zone)
            sources += len(source_set)
            intersection += len(zone & source_set)
    return {
        "seed": seed,
        "board": board,
        "compiled_board_size": compiled.board_size,
        "base_type_side_pairs_with_a_zone": pairs_with_zone,
        "zone_squares": zones,
        "promotion_source_squares": sources,
        "zone_squares_that_are_promotion_sources": intersection,
        "zone_square_share_that_are_promotion_sources": (
            round(intersection / zones, 6) if zones else None
        ),
        "zone_disjoint_from_every_promotion_source": intersection == 0,
    }


def decide(summary: dict[int, dict], rule: dict) -> str:
    """Apply the pre-written decision rule literally, no judgement added here."""
    share = {board: row["disjoint_share"] for board, row in summary.items()}
    if 4 not in share:
        return "board4_reference_unavailable"
    base = share[4]
    if 6 not in share or 8 not in share:
        return "insufficient_supported_board_sizes"
    artefact = share[6] <= 0.5 * base and share[8] <= 0.5 * base
    persists = share[6] >= 0.75 * base and share[8] >= 0.75 * base
    if artefact:
        return "board4_disjointness_is_a_small_board_artefact"
    if persists:
        return "disjointness_persists_across_board_sizes"
    return "mixed_board_size_dependence"


def main() -> int:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    seeds = stage8_seeds()
    boards = plan["design"]["boards"]
    rows: list[dict] = []
    unsupported: list[dict] = []
    for board in boards:
        for seed in seeds:
            try:
                rows.append(geometry(seed, board))
            except Exception as exc:  # recorded, never fabricated
                unsupported.append(
                    {"board": board, "seed": seed, "error": f"{type(exc).__name__}: {exc}"}
                )
    summary: dict[int, dict] = {}
    for board in boards:
        board_rows = [row for row in rows if row["board"] == board]
        if not board_rows:
            continue
        disjoint = [row["seed"] for row in board_rows if row["zone_disjoint_from_every_promotion_source"]]
        shares = [
            row["zone_square_share_that_are_promotion_sources"]
            for row in board_rows
            if row["zone_square_share_that_are_promotion_sources"] is not None
        ]
        summary[board] = {
            "seeds_examined": len(board_rows),
            "seeds_disjoint": len(disjoint),
            "disjoint_seeds": disjoint,
            "disjoint_share": round(len(disjoint) / len(board_rows), 6),
            "median_zone_square_share_that_are_promotion_sources": (
                round(statistics.median(shares), 6) if shares else None
            ),
            "seeds_with_no_zone": sum(1 for row in board_rows if row["zone_squares"] == 0),
        }
    decision = decide(summary, plan["decision_rule_written_before_the_run"])
    payload = {
        "role": "DEEPSEEK_AUX",
        "session": "3d8dc073-5fcc-456e-933c-a7b6646296e5",
        "question": plan["question"],
        "plan": PLAN.name,
        "source": STAGE8.name,
        "source_sha256": sha256(STAGE8),
        "design": plan["design"],
        "decision_rule": plan["decision_rule_written_before_the_run"],
        "decision": decision,
        "per_board": summary,
        "unsupported": unsupported,
        "per_seed_board": rows,
        "nonclaims": plan["nonclaims"],
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    plan["status"] = "executed"
    plan["execution"] = {
        "at": datetime.now(timezone.utc).isoformat(),
        "script": Path(__file__).name,
        "output": OUT.name,
        "output_sha256": sha256(OUT),
        "seeds": len(seeds),
        "decision": decision,
    }
    PLAN.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    for board, row in summary.items():
        print(
            f"board={board} seeds={row['seeds_examined']} disjoint={row['seeds_disjoint']} "
            f"share={row['disjoint_share']} median_share={row['median_zone_square_share_that_are_promotion_sources']}"
        )
    print(f"unsupported={len(unsupported)}")
    print(decision)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
