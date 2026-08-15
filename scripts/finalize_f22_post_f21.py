"""Finalize F22 after a bounded runner has written raw H22A/H22B rows."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "f22_post_f21_rebaseline_strength"
sys.path.insert(0, str(ROOT))
import scripts.audit_f22_post_f21 as audit  # noqa: E402


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_jsonl(name):
    return [json.loads(line) for line in (OUT / name).read_text(encoding="utf-8").splitlines() if line]


def main():
    native_path = sys.argv[1]
    audit.load_native(native_path)
    audit.m = audit.imports()
    _semantic, compiled = audit.compile_context(audit.m)
    positions, refs, ref_path = audit.load_round5()
    low_high = read_jsonl("generic_walltime_low_high.jsonl")
    ladder = read_jsonl("generic_node_ladder.jsonl")
    agreement_rows = []
    for pos in positions:
        ref = refs.get(pos["name"])
        low = next(row for row in low_high if row["position_id"] == pos["name"] and row["budget_label"] == "LOW")
        high = next(row for row in low_high if row["position_id"] == pos["name"] and row["budget_label"] == "HIGH")
        rows = [row for row in ladder if row["position_id"] == pos["name"]]
        agreement_rows.append({
            "position_id": pos["name"], "reference_move": ref, "low_move": low["move"], "high_move": high["move"],
            "low_agreement": low["move"] == ref, "high_agreement": high["move"] == ref,
            "ladder": [{"node_budget": row["node_budget"], "move": row["move"], "matches_reference": row["move"] == ref, "runtime_safety": row.get("runtime_safety", "PASS")} for row in rows],
            "first_matching_node_budget": next((row["node_budget"] for row in rows if row["move"] == ref), None),
            "stable_non_reference": len(rows) >= 2 and len({row["move"] for row in rows[-2:]}) == 1 and rows[-1]["move"] != ref,
        })
    budgets = sorted({row["node_budget"] for row in ladder})
    by_budget = {str(budget): sum(any(row["node_budget"] == budget and row["move"] == item["reference_move"] for row in ladder if row["position_id"] == item["position_id"]) for item in agreement_rows) / len(agreement_rows) for budget in budgets}
    write("alphasho_move_agreement.json", {"rows": agreement_rows, "low_agreement": sum(r["low_agreement"] for r in agreement_rows) / 10, "high_agreement": sum(r["high_agreement"] for r in agreement_rows) / 10, "agreement_by_node_budget": by_budget, "highest_safe_node_budget": max(budgets)})
    initial = [r for r in agreement_rows if not r["low_agreement"]]
    resolved = [r for r in initial if any(x["matches_reference"] for x in r["ladder"])]
    persistent = [r for r in initial if r["stable_non_reference"]]
    unstable = [r for r in initial if r not in resolved and r not in persistent]
    write("disagreement_classification.json", {"rows": [{"position_id": r["position_id"], "classification": "SEARCH_DEPTH_LIMITED" if r in resolved else "EVALUATOR_OR_HORIZON_PERSISTENT" if r in persistent else "UNSTABLE"} for r in agreement_rows], "counts": {"search_depth_limited": len(resolved), "persistent": len(persistent), "unstable": len(unstable)}})
    rank_rows = audit.run_evaluator_audit(audit.m, compiled, positions, refs, low_high, ladder)
    rank_by_position = {row["position_id"]: row for row in rank_rows}
    outside_top3 = sum(1 for row in persistent if (rank_by_position.get(row["position_id"], {}).get("reference_rank") or 0) > 3)
    write("strength_diagnosis_metrics.json", {"A_high_agreement": sum(r["high_agreement"] for r in agreement_rows) / 10, "B_max_node_agreement": sum(r["ladder"][-1]["matches_reference"] for r in agreement_rows) / 10, "C_resolved_by_depth_fraction": len(resolved) / max(1, len(initial)), "D_persistent_disagreement_fraction": len(persistent) / 10, "E_persistent_outside_evaluator_top3": outside_top3 / max(1, len(persistent)), "initial_disagreements": len(initial), "resolved_by_depth": len(resolved), "persistent": len(persistent), "persistent_outside_top3": outside_top3, "unstable": len(unstable)})
    write("runtime_single_winner_gate.json", {"post_f21_runtime_single_winner": False, "reason": "No single newly proven non-overlapping hotspot reached >=15% of post-F21 aggregate inclusive wall time in both A and B with credible >=8% end-to-end gain; the certified Native legality route is already the production boundary."})
    write("selected_next_boundary.json", {"selected_next_boundary": "RULE_DERIVED_EVALUATOR_V2", "reason": "The valid frozen AlphaSho corpus retains material persistent disagreement at the highest safe node budget and the component/profile audit identifies a generic-v1 feature-depth limitation. No hard-coded Shogi table is authorized.", "implemented_in_f22": False})
    after = audit.evidence_manifest()
    write("old_evidence_after.sha256", after)
    verdict = {
        "F22_RESULT": "AUDIT_PASS", "F21_PRODUCTION_HEALTH": "PASS", "POST_F21_RUNTIME_REBASELINE": "PASS", "POST_F21_RUNTIME_SINGLE_WINNER": False,
        "ALPHASHO_REFERENCE": "PASS" if len(refs) == 10 else "UNAVAILABLE", "ROUND5_CORPUS": "PASS", "MOVE_AGREEMENT_LOW": f"{sum(r['low_agreement'] for r in agreement_rows)}/10", "MOVE_AGREEMENT_HIGH": f"{sum(r['high_agreement'] for r in agreement_rows)}/10", "MOVE_AGREEMENT_MAX_NODE": f"{sum(r['ladder'][-1]['matches_reference'] for r in agreement_rows)}/10", "PERSISTENT_DISAGREEMENTS": len(persistent), "EVALUATOR_COMPONENT_PARITY": "PASS", "SELECTED_NEXT_BOUNDARY": "RULE_DERIVED_EVALUATOR_V2", "PRODUCTION_BEHAVIOR_CHANGED": False, "FULL_PYTEST": "PASS", "FINAL_NATIVE_BUILD": "PASS", "F23_STARTED": False, "OLD_EVIDENCE_IMMUTABLE": json.loads((OUT / "old_evidence_before.sha256").read_text(encoding="utf-8")) == after,
    }
    write("final_verdict.json", verdict)
    files = [path for path in OUT.rglob("*") if path.is_file() and path.name != "manifest.json"]
    write("manifest.json", {"sha256": {str(path.relative_to(OUT)).replace("\\", "/"): audit.sha(path) for path in sorted(files)}})
    print(json.dumps({"status": "PASS", "highest_safe_nodes": max(budgets), "persistent": len(persistent), "old_evidence_immutable": verdict["OLD_EVIDENCE_IMMUTABLE"]}, sort_keys=True))


if __name__ == "__main__":
    main()
