"""Audit effective decision orbits in the historical F23G V4 corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))

from scripts import build_f23c_evaluator_corpus_r2 as f23c
from scripts import build_f23g_preference_corpus_r2 as f23g
from scripts.exact_generic_preference_solver import decision_subtree_fingerprint


V4 = ROOT / "tests" / "fixtures" / "evaluator_v2_corpus_v4.json"


def audit() -> dict:
    fixture = json.loads(V4.read_text(encoding="utf-8"))
    entries = [entry for entry in fixture["generic_exact"] if entry["id"].startswith("generic-deep-")]
    m = f23c._imports()
    by_orbit: dict[str, list[dict]] = defaultdict(list)
    for entry in entries:
        variant = int(entry["ruleset_id"].rsplit("-", 1)[-1])
        compiled, _pieces = f23g._semantic_variant(m, variant)
        state_spec = entry["state"]
        state = m["make_state"](compiled, state_spec["rows"], side_to_move=state_spec["side_to_move"], hands=state_spec["hands"])
        behavior = decision_subtree_fingerprint(compiled, state, max_nodes=30000, max_depth=6)
        orbit_key = f"{entry['ruleset_id']}:{behavior}"
        by_orbit[orbit_key].append(entry)

    split_orbits = {split: {key for key, rows in by_orbit.items() if any(row["split"] == split for row in rows)} for split in ("DEVELOPMENT", "HOLDOUT")}
    leakage = sorted(split_orbits["DEVELOPMENT"] & split_orbits["HOLDOUT"])
    effective_rows = [rows[0] for rows in by_orbit.values()]
    class_counts = Counter(row["preference_authority"]["proof_depth_class"] for row in effective_rows)
    return {
        "physical_corpus_rows": len(entries),
        "canonical_state_identity_count": len({entry["state_identity_sha256"] for entry in entries}),
        "effective_decision_orbit_count": len(by_orbit),
        "effective_development_orbits_before_leakage_exclusion": len(split_orbits["DEVELOPMENT"]),
        "effective_holdout_orbits_before_leakage_exclusion": len(split_orbits["HOLDOUT"]),
        "decision_orbit_split_leakage_count": len(leakage),
        "eligible_development_orbits_after_leakage_exclusion": len(split_orbits["DEVELOPMENT"] - set(leakage)),
        "eligible_holdout_orbits_after_leakage_exclusion": len(split_orbits["HOLDOUT"] - set(leakage)),
        "effective_ruleset_group_counts": Counter(row["ruleset_id"] for row in effective_rows),
        "effective_proof_depth_class_counts": class_counts,
        "effective_max_ply_dependent_count": sum(row["preference_authority"]["max_ply_dependence"] for row in effective_rows),
        "duplicate_multiplicity_per_orbit": {key: len(rows) for key, rows in sorted(by_orbit.items())},
        "decision_orbit_ids": {key: hashlib.sha256(key.encode("utf-8")).hexdigest() for key in sorted(by_orbit)},
        "corrected_deep_supervision_gate": {
            "passes": False,
            "reason": "five effective orbits, all cross-split leakage; physical and canonical counts are not supervision counts",
        },
        "selected_f23h_boundary": "F23H_REFERENCE_PREFERENCE_CORPUS_R3",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit()
    encoded = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
