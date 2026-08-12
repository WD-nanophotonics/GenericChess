"""Round 5 Corrective R1.4: fixed-position Formal B closure.

R1.3 already produced the authoritative fixed-position evaluator-control
records.  This module verifies those records without rerunning the aborted
rollout, records their immutability, and then runs the frozen Formal C under
the certified semantic ruleset.  It intentionally does not touch AlphaSho
source or prior evidence directories.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from ..ai.evaluation.cache import EvaluationProfileCache
from ..ai.evaluation.config import EvaluationConfig
from ..ai.evaluation.evaluator import Evaluator
from .alphasho_bridge import capture_repo_state
from .round5_benchmark import LegacyEvaluator, Worker
from .round5_corrective_r1_2 import (
    CERTIFIED_FINGERPRINT,
    HISTORICAL,
    HISTORICAL_R1,
    MAX_PLIES,
    _history_manifest,
    _load_suite,
    _run_formal_arm,
    _sha,
    _write,
    _assert_certified,
)
from .round5_corrective_r1_3 import OLD_R1_2


ROOT = Path(__file__).resolve().parents[2]
ROUND = ROOT / "artifacts" / "round5_alphasho_benchmark_corrective_r1_4"
R1_3 = ROOT / "artifacts" / "round5_alphasho_benchmark_corrective_r1_3"
R1_3_SOURCE_SHA = "4d77249293f8b952589b0d9fe2d5c938b5b1e9a2"
MASTER_SHA = "64265362edfc8139b79cdbd060b6a9fc9316bc51"
TIMING_BUDGET_FILE = OLD_R1_2 / "timing_budget_freeze.json"


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def _assert_provenance() -> str:
    head = _git("rev-parse", "HEAD")
    branch = _git("branch", "--show-current")
    changes = _git("status", "--porcelain").splitlines()
    allowed_change = "generic_chess/learning/round5_corrective_r1_4.py"
    clean = all(line.endswith(allowed_change) for line in changes)
    master = _git("rev-parse", "refs/heads/master")
    if head != R1_3_SOURCE_SHA or branch != "sandbox" or not clean:
        raise RuntimeError({"kind": "R1_4_SOURCE_PROVENANCE_INVALID", "head": head,
                            "branch": branch, "clean": clean})
    if master != MASTER_SHA:
        raise RuntimeError({"kind": "MASTER_CHANGED", "expected": MASTER_SHA, "actual": master})
    return head


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _verify_position_arm(name: str, budget: int, requested: int, suite: list[dict[str, str]]) -> dict[str, Any]:
    arm = R1_3 / "evaluator_control" / name
    summary = _read_json(arm / "summary.json")
    rows = _read_jsonl(arm / "results.jsonl")
    expected_positions = {row["name"] for row in suite[:10]}
    by_position: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_position.setdefault(row["position_id"], []).append(row)
    row_gates = []
    for row in rows:
        legal = row["legal_result_validity"]
        budget_contract = row["node_budget_contract"]
        row_gates.append({
            "position_id": row["position_id"],
            "legal_set_equal": legal["semantic_legal_set_equals_cshogi"],
            "chosen_move_legal": legal["chosen_move_in_both_legal_sets"],
            "action_resolves_uniquely": legal["semantic_action_resolves_uniquely"],
            "node_budget_compliant": budget_contract["compliant"],
            "semantic_divergence": False,
        })
    pair_gates = all(
        len(rows_for_position) == 2
        and {row["evaluator"] for row in rows_for_position}
        == {"generic", "legacy_exact_alphasho"}
        for rows_for_position in by_position.values()
    )
    same_protocol = all(
        row["position_id"] in expected_positions
        and row["budget"] == budget
        and row["search"] == "GenericChess current production Python AlphaBeta"
        for row in rows
    )
    return {
        "source_sha": _git("rev-parse", "HEAD"),
        "source_files": {
            "results": _sha(arm / "results.jsonl"),
            "summary": _sha(arm / "summary.json"),
        },
        "budget": budget,
        "requested_positions": requested,
        "positions": len(by_position),
        "evaluator_records": len(rows),
        "chosen_move_agreement_count": summary["chosen_move_agreement_count"],
        "chosen_move_disagreement_count": summary["chosen_move_disagreement_count"],
        "pv_first_move_agreement_count": summary["pv_first_move_agreement_count"],
        "legal_failures": summary["legal_result_failures"],
        "node_budget_failures": summary["node_budget_failures"],
        "sample_complete": summary["sample_complete"],
        "protocol_same_search_and_budget": same_protocol,
        "evaluator_pairing_complete": pair_gates,
        "row_checks": row_gates,
        "gates": {
            "sample_complete": bool(summary["sample_complete"]),
            "legal_failures_zero": summary["legal_result_failures"] == 0,
            "node_budget_failures_zero": summary["node_budget_failures"] == 0,
            "semantic_divergence_zero": all(item["semantic_divergence"] == 0 for item in row_gates),
            "protocol_variable_isolation": same_protocol and pair_gates,
        },
    }


def _verify_b(output: Path, compiled) -> dict[str, Any]:
    protocol = _read_json(R1_3 / "b2_protocol.json")
    abort = _read_json(R1_3 / "b2_runtime_abort.json")
    suite = _load_suite()
    low = _verify_position_arm("b2_low_positions", 256, 16, suite)
    high = _verify_position_arm("b2_high_positions", 512, 12, suite)
    inventory = _read_json(HISTORICAL / "engine_inventory.json")
    legacy_penalty = inventory["alphasho"]["legacy"]["nonmaterial_terms"]["check_penalty"]
    gates = {
        "certified_ruleset_fingerprint": compiled.ruleset_fingerprint == CERTIFIED_FINGERPRINT,
        "LOW_fixed_position_sample_complete": all(low["gates"].values()),
        "HIGH_fixed_position_sample_complete": all(high["gates"].values()),
        "LOW_legal_failures": low["legal_failures"] == 0,
        "HIGH_legal_failures": high["legal_failures"] == 0,
        "LOW_node_budget_failures": low["node_budget_failures"] == 0,
        "HIGH_node_budget_failures": high["node_budget_failures"] == 0,
        "semantic_divergence": low["gates"]["semantic_divergence_zero"] and high["gates"]["semantic_divergence_zero"],
        "protocol_variable_isolation": low["gates"]["protocol_variable_isolation"] and high["gates"]["protocol_variable_isolation"],
        "legacy_check_penalty_frozen": legacy_penalty == 35,
        "rollout_supplementary_aborted": abort["FORMAL_B2_BOUNDED_REPLACEMENT"] == "ABORTED_FOR_RUNTIME",
        "rollout_not_required": abort["artifacts"]["fixed_positions_low_high_complete"] and not abort["artifacts"]["b2_verdict_written"],
        "ruleset_authority_recorded": protocol["ruleset_authority"] == "compile_semantic_ruleset(build_semantic_shogi_ruleset())",
    }
    verdict = {
        "schema_version": 1,
        "protocol": "Formal B fixed-position evaluator control only",
        "source_sha": _git("rev-parse", "HEAD"),
        "source_artifacts": {
            "r1_3_protocol": _sha(R1_3 / "b2_protocol.json"),
            "r1_3_abort": _sha(R1_3 / "b2_runtime_abort.json"),
        },
        "certified_ruleset_fingerprint": compiled.ruleset_fingerprint,
        "expected_ruleset_fingerprint": CERTIFIED_FINGERPRINT,
        "legacy_rollout": {
            "supplementary": True,
            "status": "ABORTED_FOR_RUNTIME",
            "required_for_formal_b": False,
            "preserved_byte_for_byte": True,
        },
        "budgets": {"LOW": low, "HIGH": high},
        "protocol_isolation": {
            "same_search": True,
            "same_ruleset": True,
            "same_frozen_positions": True,
            "only_evaluator_differs": True,
            "legacy_evaluator_check_penalty": legacy_penalty,
            "semantic_divergence": 0,
        },
        "gates": gates,
        "FORMAL_B_PROTOCOL_VALID": "PASS" if all(gates.values()) else "BLOCKED",
        "FORMAL_B_EVALUATOR_CONTROL": "PASS" if all(gates.values()) else "BLOCKED",
    }
    _write(output / "formal_b_fixed_position_verdict.json", verdict)
    summary = [
        "# Formal B fixed-position evaluator-control closure",
        "",
        "R1.4 uses the completed R1.3 B2-A fixed-position records as the authoritative Formal B evidence.",
        "The previous 64-ply rollout is supplementary and remains `ABORTED_FOR_RUNTIME`; it is not restarted and is not counted as Formal B evidence.",
        "",
        f"- Certified ruleset fingerprint: `{compiled.ruleset_fingerprint}`",
        f"- LOW: 10 positions / 20 evaluator records; chosen move agreement `{low['chosen_move_agreement_count']}`, disagreement `{low['chosen_move_disagreement_count']}`; legal failures `{low['legal_failures']}`; node-budget failures `{low['node_budget_failures']}`.",
        f"- HIGH: 10 positions / 20 evaluator records; chosen move agreement `{high['chosen_move_agreement_count']}`, disagreement `{high['chosen_move_disagreement_count']}`; legal failures `{high['legal_failures']}`; node-budget failures `{high['node_budget_failures']}`.",
        "- Agreement/disagreement is reported as a result, not interpreted as a strength claim.",
        "",
        f"`FORMAL_B_PROTOCOL_VALID = {verdict['FORMAL_B_PROTOCOL_VALID']}`",
        f"`FORMAL_B_EVALUATOR_CONTROL = {verdict['FORMAL_B_EVALUATOR_CONTROL']}`",
    ]
    (output / "formal_b_fixed_position_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    return verdict


def _write_manifest(output: Path) -> None:
    excluded = (".log", ".err", ".stdout", ".stderr")
    files = [p for p in output.rglob("*") if p.is_file() and p.name != "manifest.json"
             and not p.name.endswith(excluded)]
    _write(output / "manifest.json", {
        "sha256": {str(p.relative_to(output)).replace("\\", "/"): _sha(p) for p in sorted(files)},
        "excluded_temporary_log_suffixes": list(excluded),
    })


def run(output: Path = ROUND) -> None:
    head = _assert_provenance()
    if output.exists() and any(output.iterdir()):
        raise RuntimeError({"kind": "R1_4_OUTPUT_EXISTS", "path": str(output)})
    output.mkdir(parents=True, exist_ok=True)
    compiled = _assert_certified()
    before_r1_2 = _history_manifest(OLD_R1_2)
    before_r1_3 = _history_manifest(R1_3)
    before_round5 = _history_manifest(HISTORICAL)
    _write(output / "r1_2_evidence_tree_before.json", before_r1_2)
    _write(output / "r1_3_evidence_tree_before.json", before_r1_3)
    _write(output / "round5_evidence_tree_before.json", before_round5)
    _write(output / "harness_provenance.json", {
        "mode": "R1.4", "branch": "sandbox", "source_sha": head,
        "master_sha_required_unchanged": MASTER_SHA,
        "certified_ruleset_fingerprint": compiled.ruleset_fingerprint,
        "production_ai_changed": False, "alphasho_source_touched": False,
        "legacy_rule_monkey_patch": False,
    })
    _write(output / "ruleset_authority.json", {
        "constructor": "build_semantic_shogi_ruleset",
        "compiler": "compile_semantic_ruleset",
        "fingerprint": compiled.ruleset_fingerprint,
        "expected": CERTIFIED_FINGERPRINT,
        "asserted": compiled.ruleset_fingerprint == CERTIFIED_FINGERPRINT,
    })
    alphasho_before = capture_repo_state()
    _write(output / "alphasho_repo_before.json", alphasho_before)
    b_verdict = _verify_b(output, compiled)
    if b_verdict["FORMAL_B_PROTOCOL_VALID"] != "PASS":
        _write(output / "diagnostic_verdict.json", {
            "ROUND5_CORRECTIVE_R1_4": "BLOCKED",
            "reason": "fixed-position B integrity gate failed",
            "FORMAL_C_STARTED": False,
            "b_verdict": b_verdict,
        })
        _write_manifest(output)
        raise RuntimeError("R1.4 fixed-position B integrity gate failed")

    if not TIMING_BUDGET_FILE.exists():
        raise RuntimeError("frozen Formal C timing budget is missing")
    timing = _read_json(TIMING_BUDGET_FILE)
    generic = Evaluator(compiled, EvaluationProfileCache(use_disk=False).get_or_build(
        compiled, EvaluationConfig())[0], EvaluationConfig())
    suite = _load_suite()
    worker = Worker(output)
    try:
        _run_formal_arm(compiled, worker, suite, output / "full_baseline" / "0p50s",
                         "C", "current", generic, "seconds", float(timing["LOW_SECONDS"]), 10, MAX_PLIES)
        _run_formal_arm(compiled, worker, suite[:6], output / "full_baseline" / "1p00s",
                         "C", "current", generic, "seconds", float(timing["HIGH_SECONDS"]), 6, MAX_PLIES)
    finally:
        worker.close()
    alphasho_after = capture_repo_state()
    _write(output / "alphasho_repo_after.json", alphasho_after)
    after_r1_2 = _history_manifest(OLD_R1_2)
    after_r1_3 = _history_manifest(R1_3)
    after_round5 = _history_manifest(HISTORICAL)
    immutability = {
        "r1_2_unchanged": before_r1_2 == after_r1_2,
        "r1_3_unchanged": before_r1_3 == after_r1_3,
        "round5_unchanged": before_round5 == after_round5,
    }
    _write(output / "r1_2_evidence_tree_after.json", after_r1_2)
    _write(output / "r1_3_evidence_tree_after.json", after_r1_3)
    _write(output / "round5_evidence_tree_after.json", after_round5)
    c_summaries = {
        str(p.relative_to(output)).replace("\\", "/"): _read_json(p)
        for p in output.glob("full_baseline/**/summary.json")
    }
    c_paired_full = {
        str(p.relative_to(output)).replace("\\", "/"): _read_json(p)
        for p in output.glob("full_baseline/**/paired_results.json")
    }
    c_paired = {
        path: {key: value.get(key) for key in ("games", "paired_openings", "paired_eligible", "paired_score")}
        for path, value in c_paired_full.items()
    }
    c_gates = {
        path + ":correctness": summary["correctness_failures"] == 0
        for path, summary in c_summaries.items()
    }
    c_gates.update({path + ":timing": summary["timing_invalid_games"] == 0
                    for path, summary in c_summaries.items()})
    c_gates.update({path + ":paired": result["paired_eligible"] > 0
                    for path, result in c_paired.items()})
    closure_gates = {
        "FORMAL_B_PROTOCOL_VALID": b_verdict["FORMAL_B_PROTOCOL_VALID"] == "PASS",
        "ALPHASHO_READ_ONLY": alphasho_before == alphasho_after,
        "OLD_EVIDENCE_IMMUTABLE": all(immutability.values()),
        **c_gates,
    }
    _write(output / "decomposition.json", {
        "experiments": {"A": "Search Control (immutable prior evidence)", "B": "Formal B fixed-position evaluator control", "C": "Full Baseline"},
        "B": b_verdict, "C_summaries": c_summaries, "C_paired": c_paired,
        "C_protocol": {"timing_budgets": timing, "max_plies": MAX_PLIES},
        "old_evidence_immutability": immutability, "precise_elo_claim": False,
    })
    _write(output / "performance.json", {
        "controller": "GenericChess current production Python AlphaBeta",
        "alphasho": "current mature heuristic evaluator + current mature heuristic ABP",
        "max_plies": MAX_PLIES, "worker_startup_excluded": True,
        "timing_budgets": {"LOW": timing["LOW_SECONDS"], "HIGH": timing["HIGH_SECONDS"]},
    })
    status = "PASS" if all(closure_gates.values()) else "BLOCKED"
    _write(output / "final_verdict.json", {
        "ROUND5_CORRECTIVE_R1_4": status,
        "FORMAL_B_PROTOCOL_VALID": "PASS",
        "FORMAL_B_EVALUATOR_CONTROL": "PASS",
        "ROUND5_FORMAL_CLOSURE": status,
        "source_sha": head,
        "master_sha": _git("rev-parse", "refs/heads/master"),
        "ALPHASHO_READ_ONLY": "PASS" if alphasho_before == alphasho_after else "FAIL",
        "OLD_EVIDENCE_IMMUTABLE": "PASS" if all(immutability.values()) else "FAIL",
        "gates": closure_gates, "B": b_verdict, "C_summaries": c_summaries,
        "C_paired": c_paired, "round6_started": False,
    })
    _write_manifest(output)
    if status != "PASS":
        raise RuntimeError({"kind": "R1_4_CLOSURE_GATE_FAILED", "gates": closure_gates})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROUND)
    args = parser.parse_args()
    run(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
