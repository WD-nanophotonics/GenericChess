"""Is the zone/promotion-source disjointness specific to one setup preset?

Stage 10, 14 and 15 all measure ``setup_preset classic_like``; Stage 15 held the
preset fixed and varied the board. This stage holds the board at 4 and varies
the preset over ``classic_like``, ``bilateral_random`` and ``free_random`` with
the same 36 seeds, so the comparison is controlled by seed in both directions.

Structural only: ``generic_chess/core/movegen.py`` builds a promotion variant
only when ``(from_square, to_square) in compiled.promotion_allowed``, so a zone
square that is not a promotion source cannot carry a promotion action at all.
No search, no game replay, no evaluator change, no new games. No contact count
and no contact rate is produced; the withdrawn 0-versus-53 contrast stays out.
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
PLAN = HERE / "plan_stage16_preset_dependence_zone_disjointness.json"
OUT = HERE / "results_stage16_preset_dependence_zone_disjointness.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage8_seeds() -> list[int]:
    stage8 = json.loads(STAGE8.read_text(encoding="utf-8"))
    seen: dict[int, None] = {}
    for game in stage8["per_game"]:
        seen.setdefault(game["seed"], None)
    return sorted(seen)


def geometry(seed: int, board: int, preset: str) -> dict:
    compiled = generate_game(
        GeneratorConfig(seed=seed, board_size=board, setup_preset=preset)
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
        "preset": preset,
        "board": board,
        "base_type_side_pairs_with_a_zone": pairs_with_zone,
        "zone_squares": zones,
        "promotion_source_squares": sources,
        "zone_squares_that_are_promotion_sources": intersection,
        "zone_square_share_that_are_promotion_sources": (
            round(intersection / zones, 6) if zones else None
        ),
        "zone_disjoint_from_every_promotion_source": intersection == 0,
    }


def decide(per_preset: dict[str, dict], available: list[str], reference: str) -> str:
    """Apply the pre-written rule literally."""
    if reference not in per_preset or len(available) < 2:
        return "insufficient_supported_presets"
    base = per_preset[reference]["disjoint_share"]
    others = [p for p in available if p != reference]
    if not others:
        return "insufficient_supported_presets"
    if all(per_preset[p]["disjoint_share"] >= 0.75 * base for p in others):
        return "disjointness_is_generic_across_presets"
    if any(per_preset[p]["disjoint_share"] <= 0.5 * base for p in others):
        return "classic_like_specific_disjointness"
    return "mixed_preset_dependence"


def main() -> int:
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    seeds = stage8_seeds()
    board = plan["design"]["board"]
    presets = plan["design"]["presets"]
    reference = plan["decision_rule_written_before_the_run"]["reference_preset"]
    rows: list[dict] = []
    unsupported: list[dict] = []
    for preset in presets:
        for seed in seeds:
            try:
                rows.append(geometry(seed, board, preset))
            except Exception as exc:  # recorded, never fabricated
                unsupported.append(
                    {"preset": preset, "seed": seed, "error": f"{type(exc).__name__}: {exc}"}
                )
    per_preset: dict[str, dict] = {}
    available: list[str] = []
    for preset in presets:
        preset_rows = [row for row in rows if row["preset"] == preset]
        if len(preset_rows) * 2 < len(seeds):
            per_preset[preset] = {
                "seeds_examined": len(preset_rows),
                "insufficient": True,
                "reason": f"fewer than half of the {len(seeds)} seeds could be built",
            }
            continue
        disjoint = sorted(
            row["seed"] for row in preset_rows
            if row["zone_disjoint_from_every_promotion_source"]
        )
        shares = [
            row["zone_square_share_that_are_promotion_sources"]
            for row in preset_rows
            if row["zone_square_share_that_are_promotion_sources"] is not None
        ]
        per_preset[preset] = {
            "seeds_examined": len(preset_rows),
            "insufficient": False,
            "seeds_disjoint": len(disjoint),
            "disjoint_seeds": disjoint,
            "disjoint_share": round(len(disjoint) / len(preset_rows), 6),
            "median_zone_square_share_that_are_promotion_sources": (
                round(statistics.median(shares), 6) if shares else None
            ),
            "seeds_with_no_zone": sum(1 for row in preset_rows if row["zone_squares"] == 0),
        }
        available.append(preset)
    disjoint_sets = {
        preset: set(per_preset[preset]["disjoint_seeds"]) for preset in available
    }
    disjoint_everywhere = sorted(set.intersection(*disjoint_sets.values())) if disjoint_sets else []
    decision = decide(per_preset, available, reference)
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
        "defect_corrections": [
            {
                "defect": (
                    "the first run read the reference preset from the plan's prose field "
                    "'reference' ('classic_like disjoint_share, the preset every earlier "
                    "stage used') instead of a preset key, so the lookup always failed and "
                    "the decision fell through to insufficient_supported_presets"
                ),
                "observed": (
                    "the decision string contradicted the three fully built preset summaries "
                    "printed alongside it in the same run"
                ),
                "correction": (
                    "the plan now carries an explicit reference_preset field with the same "
                    "preset the prose described, and the scan reads that key; the thresholds "
                    "(0.75 for generic, 0.5 for classic_like-specific) are unchanged"
                ),
                "how_detected": (
                    "the run printed three supported presets with complete shares and still "
                    "returned insufficient_supported_presets"
                ),
                "measurements_changed": False,
                "decision_string_changed": True,
                "wrong_output_published": False,
            }
        ],
        "supported_presets": available,
        "per_preset": per_preset,
        "seeds_disjoint_under_every_supported_preset": disjoint_everywhere,
        "seed_count_disjoint_under_every_supported_preset": len(disjoint_everywhere),
        "unsupported": unsupported,
        "per_seed_preset": rows,
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

    for preset in presets:
        row = per_preset[preset]
        print(
            f"{preset} examined={row['seeds_examined']} disjoint={row.get('seeds_disjoint')} "
            f"share={row.get('disjoint_share')} "
            f"median_share={row.get('median_zone_square_share_that_are_promotion_sources')}"
        )
    print(f"disjoint_everywhere={len(disjoint_everywhere)} unsupported={len(unsupported)}")
    print(decision)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
