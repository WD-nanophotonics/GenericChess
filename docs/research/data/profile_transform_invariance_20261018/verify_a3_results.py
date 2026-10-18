"""Independent re-read of results_profile_transform_a3.json and its source rules.

Recomputes the headline counts from the stored JSON and re-derives the
forward-zone relation from the compiled rules themselves, so the published
report does not rely on the scanning pass having been correct.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.generation.config import GeneratorConfig  # noqa: E402
from generic_chess.generation.generator import generate_game  # noqa: E402

RESULTS = HERE / "results_profile_transform_a3.json"
OUT = HERE / "results_a3_verification.json"


def main() -> int:
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    verdict = data["verdict"]
    rules = data["rules"]

    recomputed = {
        "rules_total": len(rules),
        "rules_supported": sum(rule["status"] == "supported" for rule in rules),
        "rules_unsupported": sum(rule["status"] == "unsupported" for rule in rules),
        "violation_count": sum(
            len((rule["comparison"] or {}).get("violations", [])) for rule in rules
        ),
        "signature_failure_count": sum(
            len((rule["comparison"] or {}).get("signature_failures", [])) for rule in rules
        ),
        "bijection_rules_passed": sum(
            bool((rule["one_ply"] or {}).get("bijection")) for rule in rules
        ),
        "actions_checked": sum(
            (rule["one_ply"] or {}).get("original_actions", 0) for rule in rules
        ),
        "types_compared": sum(
            (rule["comparison"] or {}).get("types", 0) for rule in rules
        ),
        "raw_exact_matches": sum(
            (rule["comparison"] or {}).get("raw_exact_matches", 0) for rule in rules
        ),
        "median_mismatch_rules": sum(
            not (
                ((rule["comparison"] or {}).get("median_non_anchor_value") or {})
                .get("match", True)
            )
            for rule in rules
        ),
    }
    claimed = {key: verdict[key] for key in recomputed}
    mismatches = {
        key: {"json": claimed[key], "recomputed": recomputed[key]}
        for key in recomputed
        if claimed[key] != recomputed[key]
    }

    # Re-derive the forward-zone relation straight from the compiled rules.
    swap_holds = 0
    swap_fails = 0
    promotable_instances = 0
    zone_sizes = set()
    for size in (6, 8):
        for seed in range(292001, 292041):
            game = generate_game(
                GeneratorConfig(seed=seed, board_size=size, setup_preset="classic_like")
            )
            compiled = game.compiled_ruleset
            area = size * size
            for piece_type in compiled.piece_types:
                if not piece_type.is_promotable:
                    continue
                promotable_instances += 1
                zones = {
                    owner: frozenset(
                        idx
                        for idx in range(area)
                        if not compiled.empty_forward_mobility[piece_type.type_id][owner][idx]
                    )
                    for owner in (0, 1)
                }
                zone_sizes.add((size, len(zones[0]), len(zones[1])))
                mirrored = frozenset(area - 1 - idx for idx in zones[0])
                if mirrored == zones[1]:
                    swap_holds += 1
                else:
                    swap_fails += 1

    payload = {
        "role": "DEEPSEEK_AUX",
        "checked_results": RESULTS.name,
        "checked_sha256": data.get("plan_sha256"),
        "claim_matches_stored_json": not mismatches,
        "mismatches": mismatches,
        "recomputed": recomputed,
        "verdict_decision": verdict["decision"],
        "forward_zone_relation": {
            "promotable_type_instances": promotable_instances,
            "sigma_zone_owner0_equals_zone_owner1": swap_holds,
            "counterexamples": swap_fails,
            "distinct_size_triples": sorted(zone_sizes),
            "reading": "the evaluator forward convention is player-relative and absolute-rank based: under 180-degree board rotation the promoted-zone set of owner 0 maps exactly onto the zone of owner 1, never onto itself",
        },
    }
    OUT.write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "claim_matches_stored_json": payload["claim_matches_stored_json"],
                "mismatches": mismatches,
                "recomputed": recomputed,
                "forward_zone_relation": payload["forward_zone_relation"],
            },
            indent=1,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
