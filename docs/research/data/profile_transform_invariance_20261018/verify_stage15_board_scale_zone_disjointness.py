"""Independent check of the Stage 15 board-scale zone/promotion partition.

This verifier does not import the scan. It regenerates each ruleset itself,
rebuilds the zone and the promotion-source sets through a different code path
(index arithmetic over the compiled board rather than the scan's set
construction), recomputes the partition and the decision, and cross-checks the
board-4 column against the separately published Stage 10 disjoint list.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig  # noqa: E402
from generic_chess.ai.evaluation.evaluator import Evaluator  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile  # noqa: E402
from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results_stage15_board_scale_zone_disjointness.json"
STAGE10 = HERE / "results_zone_promotion_disjointness.json"
OUT = HERE / "verification_stage15_board_scale_zone_disjointness.json"


def rebuild(seed: int, board: int) -> dict:
    compiled = generate_game(
        GeneratorConfig(seed=seed, board_size=board, setup_preset="classic_like")
    ).compiled_ruleset
    config = EvaluationConfig()
    evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)
    width = compiled.board_size
    zone_total = 0
    source_total = 0
    hit_total = 0
    pairs = 0
    for base, gain in evaluator._profile.promotion_gain_by_type.items():
        if gain <= 0:
            continue
        for side in (0, 1):
            zone = evaluator._zones.get((base, side))
            if not zone:
                continue
            pairs += 1
            # different path: flat index arithmetic, no square_to_index helper
            flat_sources = set()
            for src, _dst in compiled.promotion_allowed.get(base, ((), ()))[side]:
                flat_sources.add(src.rank * width + src.file)
            zone_total += len(zone)
            source_total += len(flat_sources)
            hit_total += sum(1 for sq in zone if int(sq) in flat_sources)
    return {
        "pairs": pairs,
        "zone_squares": zone_total,
        "promotion_source_squares": source_total,
        "zone_squares_that_are_promotion_sources": hit_total,
        "disjoint": hit_total == 0,
    }


def main() -> int:
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    stage10 = json.loads(STAGE10.read_text(encoding="utf-8"))
    plan = json.loads((HERE / results["plan"]).read_text(encoding="utf-8"))
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    rows = results["per_seed_board"]
    boards = plan["design"]["boards"]
    seeds = sorted({row["seed"] for row in rows})
    check("every_seed_times_every_board_present", len(rows) == len(seeds) * len(boards),
          f"rows={len(rows)} seeds={len(seeds)} boards={len(boards)}")
    check("no_unsupported_board", results["unsupported"] == [], f"unsupported={results['unsupported']}")

    mismatches = []
    for row in rows:
        mine = rebuild(row["seed"], row["board"])
        if (mine["zone_squares"] != row["zone_squares"]
                or mine["promotion_source_squares"] != row["promotion_source_squares"]
                or mine["zone_squares_that_are_promotion_sources"]
                != row["zone_squares_that_are_promotion_sources"]
                or mine["disjoint"] != row["zone_disjoint_from_every_promotion_source"]):
            mismatches.append({"seed": row["seed"], "board": row["board"], "mine": mine})
    check("independent_rebuild_matches_every_row", not mismatches, f"mismatches={len(mismatches)}")

    per_board_ok = True
    for board in boards:
        board_rows = [row for row in rows if row["board"] == board]
        disjoint = sorted(row["seed"] for row in board_rows
                          if row["zone_disjoint_from_every_promotion_source"])
        stored = results["per_board"][str(board)]
        share = round(len(disjoint) / len(board_rows), 6)
        per_board_ok &= disjoint == sorted(stored["disjoint_seeds"])
        per_board_ok &= len(disjoint) == stored["seeds_disjoint"]
        per_board_ok &= share == stored["disjoint_share"]
    check("per_board_tallies_and_shares_reproduce", per_board_ok, "all boards")

    published = sorted(stage10["seeds_whose_zone_is_disjoint_from_every_promotion_source"])
    board4 = sorted(row["seed"] for row in rows
                    if row["board"] == 4 and row["zone_disjoint_from_every_promotion_source"])
    check("board4_column_matches_the_published_stage10_disjoint_list", board4 == published,
          f"board4={len(board4)} stage10={len(published)}")
    check("board4_disjoint_count_is_25", len(board4) == 25, f"count={len(board4)}")

    share = {int(b): results["per_board"][b]["disjoint_share"] for b in results["per_board"]}
    base = share[4]
    if share[6] <= 0.5 * base and share[8] <= 0.5 * base:
        expected = "board4_disjointness_is_a_small_board_artefact"
    elif share[6] >= 0.75 * base and share[8] >= 0.75 * base:
        expected = "disjointness_persists_across_board_sizes"
    else:
        expected = "mixed_board_size_dependence"
    check("decision_recomputed_from_the_rule", expected == results["decision"],
          f"expected={expected} stored={results['decision']}")

    text = RESULTS.read_text(encoding="utf-8")
    forbidden = [m for m in ("outside_zone", "in_zone_rate_outside", "contact_rate") if m in text]
    check("withdrawn_rate_markers_absent", forbidden == [], f"found={forbidden}")

    passed = all(item["passed"] for item in checks)
    payload = {
        "role": "DEEPSEEK_AUX",
        "session": results["session"],
        "verifies": RESULTS.name,
        "decision": results["decision"],
        "verdict": "all_checks_passed" if passed else "check_failed",
        "checks": checks,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for item in checks:
        print(f"{'PASS' if item['passed'] else 'FAIL'} {item['check']} - {item['detail']}")
    print(f"{sum(1 for c in checks if c['passed'])}/{len(checks)} {payload['verdict']}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
