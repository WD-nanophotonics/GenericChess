"""Independent check of the Stage 16 preset-dependence partition.

Does not import the scan. Regenerates each ruleset, rebuilds the zone and the
promotion-source sets through `Square.rank`/`Square.file` index arithmetic,
recomputes the partition, the cross-preset intersection and the decision, and
cross-checks the classic_like column against the published Stage 10 list.
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
RESULTS = HERE / "results_stage16_preset_dependence_zone_disjointness.json"
STAGE10 = HERE / "results_zone_promotion_disjointness.json"
OUT = HERE / "verification_stage16_preset_dependence_zone_disjointness.json"


def rebuild(seed: int, board: int, preset: str) -> dict:
    compiled = generate_game(
        GeneratorConfig(seed=seed, board_size=board, setup_preset=preset)
    ).compiled_ruleset
    config = EvaluationConfig()
    evaluator = Evaluator(compiled, build_ruleset_profile(compiled, config), config)
    width = compiled.board_size
    zone_total = 0
    source_total = 0
    hit_total = 0
    for base, gain in evaluator._profile.promotion_gain_by_type.items():
        if gain <= 0:
            continue
        for side in (0, 1):
            zone = evaluator._zones.get((base, side))
            if not zone:
                continue
            flat = {src.rank * width + src.file
                    for src, _dst in compiled.promotion_allowed.get(base, ((), ()))[side]}
            zone_total += len(zone)
            source_total += len(flat)
            hit_total += sum(1 for sq in zone if int(sq) in flat)
    return {
        "zone_squares": zone_total,
        "promotion_source_squares": source_total,
        "zone_squares_that_are_promotion_sources": hit_total,
        "disjoint": hit_total == 0,
    }


def main() -> int:
    results = json.loads(RESULTS.read_text(encoding="utf-8"))
    stage10 = json.loads(STAGE10.read_text(encoding="utf-8"))
    plan = json.loads((HERE / results["plan"]).read_text(encoding="utf-8"))
    presets = plan["design"]["presets"]
    board = plan["design"]["board"]
    rows = results["per_seed_preset"]
    seeds = sorted({row["seed"] for row in rows})
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    check("every_seed_times_every_preset_present", len(rows) == len(seeds) * len(presets),
          f"rows={len(rows)} seeds={len(seeds)} presets={len(presets)}")
    check("no_unsupported_pair", results["unsupported"] == [],
          f"unsupported={results['unsupported']}")

    mismatches = []
    for row in rows:
        mine = rebuild(row["seed"], row["board"], row["preset"])
        if (mine["zone_squares"] != row["zone_squares"]
                or mine["promotion_source_squares"] != row["promotion_source_squares"]
                or mine["zone_squares_that_are_promotion_sources"]
                != row["zone_squares_that_are_promotion_sources"]
                or mine["disjoint"] != row["zone_disjoint_from_every_promotion_source"]):
            mismatches.append({"seed": row["seed"], "preset": row["preset"], "mine": mine})
    check("independent_rebuild_matches_every_row", not mismatches, f"mismatches={len(mismatches)}")

    tallies_ok = True
    disjoint_sets: list[set] = []
    for preset in results["supported_presets"]:
        preset_rows = [row for row in rows if row["preset"] == preset]
        disjoint = sorted(row["seed"] for row in preset_rows
                          if row["zone_disjoint_from_every_promotion_source"])
        stored = results["per_preset"][preset]
        tallies_ok &= disjoint == sorted(stored["disjoint_seeds"])
        tallies_ok &= len(disjoint) == stored["seeds_disjoint"]
        tallies_ok &= round(len(disjoint) / len(preset_rows), 6) == stored["disjoint_share"]
        disjoint_sets.append(set(disjoint))
    check("per_preset_tallies_and_shares_reproduce", tallies_ok, "all presets")

    everywhere = sorted(set.intersection(*disjoint_sets))
    check("cross_preset_intersection_recomputes",
          everywhere == results["seeds_disjoint_under_every_supported_preset"],
          f"count={len(everywhere)}")

    published = sorted(stage10["seeds_whose_zone_is_disjoint_from_every_promotion_source"])
    classic = sorted(row["seed"] for row in rows
                     if row["preset"] == "classic_like"
                     and row["zone_disjoint_from_every_promotion_source"])
    check("classic_like_column_matches_the_published_stage10_disjoint_list",
          classic == published, f"classic_like={len(classic)} stage10={len(published)}")

    shares = {p: results["per_preset"][p]["disjoint_share"] for p in results["supported_presets"]}
    base = shares["classic_like"]
    others = [p for p in results["supported_presets"] if p != "classic_like"]
    if others and all(shares[p] >= 0.75 * base for p in others):
        expected = "disjointness_is_generic_across_presets"
    elif any(shares[p] <= 0.5 * base for p in others):
        expected = "classic_like_specific_disjointness"
    elif not others:
        expected = "insufficient_supported_presets"
    else:
        expected = "mixed_preset_dependence"
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
