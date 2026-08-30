"""Diagnose frozen R9 failures without rewriting V11."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V11 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v11.json"


def _target_piece(candidate, action):
    rows = candidate["rows"]
    n = candidate["board_size"]
    file, rank = action["to"]
    return rows[n - 1 - rank][file]


def strict_witness(record):
    witness = record.get("mechanic_witness")
    if not witness:
        return False, "NO_WITNESS"
    action = witness.get("action", {})
    mechanism = record["mechanic_family"]
    candidate = record["candidate"]
    values = {row["value"] for row in record.get("v3_root_action_values", [])}
    if len(values) < 2 or witness.get("value") not in values:
        return False, "NOT_DISTINGUISHING"
    if mechanism == "drop_hand":
        return action.get("kind") == "drop", "DROP_ACTION_REQUIRED"
    if mechanism == "promotion_choice":
        return action.get("promotion_target_id") is not None, "PROMOTION_TARGET_REQUIRED"
    if mechanism == "capture_recapture":
        target = _target_piece(candidate, action)
        return target != "." and target.islower(), "ACTUAL_CAPTURE_REQUIRED"
    if mechanism == "semantic_guard_aux_state":
        return action.get("kind") == "semantic_board" and not str(action.get("pattern_id", "")).startswith("legacy"), "CUSTOM_SEMANTIC_PATTERN_REQUIRED"
    if mechanism == "interposition_leaper":
        file, rank = action.get("from", [-1, -1])
        n = candidate["board_size"]
        actor = candidate["rows"][n - 1 - rank][file] if 0 <= file < n and 0 <= rank < n else "."
        return actor.upper() == "L", "DESIGNATED_LEAPER_REQUIRED"
    return witness.get("kind") in {"terminal_anchor_action", "terminal_anchor"}, "NATURAL_ANCHOR_TERMINAL_REQUIRED"


def audit(path: Path = V11):
    corpus = json.loads(path.read_text(encoding="utf-8"))
    records = corpus["records"]
    by_family = {}
    for family in sorted({row["construction_family"] for row in records}):
        subset = [row for row in records if row["construction_family"] == family]
        strict = [strict_witness(row) for row in subset]
        by_family[family] = {
            "planned": len(subset),
            "v3_exact": sum(row["v3_exact"] for row in subset),
            "v3_unresolved": sum(not row["v3_exact"] for row in subset),
            "preference_bearing": sum(row.get("preference_bearing", False) for row in subset),
            "all_equal": sum(row.get("status") == "SOLVED_ALL_EQUAL" for row in subset),
            "strict_root_mechanic_witness": sum(ok for ok, _ in strict),
            "strict_witness_failures": dict(sorted(Counter(reason for ok, reason in strict if not ok).items())),
            "abstraction_certified": sum(row.get("abstraction_status") == "MAX_PLY_ABSTRACT_CERTIFIED" for row in subset),
            "abstraction_refused": sum(row.get("abstraction_status") == "ABSTRACTION_REFUSED" for row in subset),
            "abstraction_refusal_causes": dict(sorted(Counter(next(iter(row.get("abstraction_stats", {}).get("unresolved", {})), "NOT_RECORDED") for row in subset if row.get("abstraction_status") == "ABSTRACTION_REFUSED").items())),
            "max_ply_abstract_leaves": sum(row.get("abstraction_stats", {}).get("max_ply_abstract_leaves", 0) for row in subset),
            "node_cycle_refusals": sum(row.get("abstraction_stats", {}).get("unresolved_cap_hits", 0) + row.get("abstraction_stats", {}).get("cycle_refusals", 0) for row in subset),
            "planned_split": dict(sorted(Counter(row["planned_split"] for row in subset).items())),
        }
    sole = next((row for row in records if row["id"] == "f23s-r9-semantic-02"), None)
    sole_result = strict_witness(sole) if sole else (False, "MISSING")
    return {
        "schema_version": 1,
        "source_v11_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "r9_runner_contract_mismatch": {"v3_isolated_8_second_wall": False, "abstraction_ladder_executed": False, "historical_note": "R9 declared both contracts but used direct V3 calls and one max_nodes=100000 abstraction call."},
        "by_family": by_family,
        "strict_reaudit": {"f23s-r9-semantic-02": {"passes": sole_result[0], "reason": sole_result[1]}},
        "historical_v11_effective_count": len(corpus["eligible_preference_representatives"]),
        "production_changed": False,
        "v11_rewritten": False,
    }


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args()
    result = audit(); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"); print(json.dumps({"status": "PASS", "families": len(result["by_family"]), "historical_v11_effective_count": result["historical_v11_effective_count"], "strict_semantic_02": result["strict_reaudit"]["f23s-r9-semantic-02"]}, sort_keys=True))


if __name__ == "__main__":
    main()
