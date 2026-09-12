"""Extract and classify fallback telemetry from the frozen F94 R6 evidence.

This module is deliberately read-only.  It never starts an Arena run and it
does not reinterpret the R6 authority classifier.  The output binds every
fallback row to the immutable RESULT SHA and the progress-evidence digest that
the R6 aggregate extractor computes.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any

from generic_chess.learning.arena import _pair_from_dict
from generic_chess.learning.serialization import stable_sha256

try:  # Support both ``python -m scripts...`` and direct script execution.
    from scripts.f94_r6_result_aggregate import (
        EXPECTED_RESULT_SHA256,
        PREP_PATH,
        PROGRESS_PATH,
        RESULT_PATH,
        _progress_directory,
        _sha256,
        aggregate,
    )
except ModuleNotFoundError:  # pragma: no cover - direct CLI compatibility
    from f94_r6_result_aggregate import (
        EXPECTED_RESULT_SHA256,
        PREP_PATH,
        PROGRESS_PATH,
        RESULT_PATH,
        _progress_directory,
        _sha256,
        aggregate,
    )


ROOT = Path(__file__).resolve().parents[1]
FORENSICS_SCHEMA = "generic-chess-f94-r6-fallback-forensics-v1"
EXPECTED_PROGRESS_EVIDENCE_SHA256 = (
    "fc84255ad869240e77e4b0a38a863e86a689e48f646d0fac59300fb19b7408de"
)
MAX_DEPTH = 12
LOW_BUDGET = 256
MATCHUPS = ("1024_vs_256", "4096_vs_1024", "4096_vs_256")


def _budget_pair(matchup: str) -> tuple[int, int]:
    try:
        child, parent = (int(value) for value in matchup.split("_vs_"))
    except (AttributeError, ValueError) as exc:
        raise RuntimeError(f"invalid R6 matchup identity: {matchup}") from exc
    return child, parent


def classify_fallback(
    *,
    engine_role: str,
    nodes_budget: int,
    completed_depth: int,
    termination_reason: str,
    decision_kind: str,
) -> str:
    """Classify one fallback without collapsing budget and operational causes."""

    if decision_kind != "action":
        return "FALLBACK_DECISION_KIND_REQUIRES_REVIEW"
    if completed_depth > 0:
        return "POST_ITERATION_FALLBACK_REQUIRES_REVIEW"
    reason = termination_reason.lower()
    if reason == "node_budget":
        if nodes_budget == LOW_BUDGET:
            return "LOW_BUDGET_PRE_ITERATION_NODE_FALLBACK"
        return "HIGH_BUDGET_PRE_ITERATION_NODE_FALLBACK"
    if reason in {"time_budget", "time_limit", "timeout", "deadline", "cancelled", "canceled", "internal_error"} or "deadline" in reason:
        return "OPERATIONAL_OR_ABORT_FALLBACK"
    return "UNCLASSIFIED_FALLBACK_REQUIRES_REVIEW"


def _validate_metric(
    metric: dict[str, Any],
    *,
    index: int,
    plies: int,
    declaration_id: Any,
    parent_budget: int,
    child_budget: int,
) -> None:
    required = {
        "side_to_move", "engine_role", "nodes_budget", "nodes",
        "completed_depth", "termination_reason", "used_fallback",
        "decision_kind",
    }
    if not required <= metric.keys():
        raise RuntimeError("R6 fallback forensics telemetry row is incomplete")
    role = metric["engine_role"]
    expected_budget = child_budget if role == "child" else parent_budget if role == "parent" else None
    if expected_budget is None or metric["nodes_budget"] != expected_budget:
        raise RuntimeError("R6 fallback forensics telemetry role/budget mismatch")
    if not isinstance(metric["used_fallback"], bool):
        raise RuntimeError("R6 fallback forensics used_fallback is not boolean")
    if not isinstance(metric["completed_depth"], int) or metric["completed_depth"] < 0:
        raise RuntimeError("R6 fallback forensics completed_depth is invalid")
    if not isinstance(metric["nodes"], int) or not 0 <= metric["nodes"] <= expected_budget:
        raise RuntimeError("R6 fallback forensics nodes are invalid")
    kind = metric["decision_kind"]
    expected_kind = "declaration" if declaration_id is not None and index == plies else "action"
    if kind != expected_kind:
        raise RuntimeError("R6 fallback forensics decision index/kind mismatch")


def _response_matrix(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for control_name in sorted(result["controls"]):
        by_matchup = {
            row["name"]: row for row in result["controls"][control_name]["matchups"]
        }
        for seed in (9801, 9802, 9803):
            tapes = {
                name: next(tape for tape in by_matchup[name]["tape_results"] if int(tape["tape_seed"]) == seed)
                for name in MATCHUPS
            }
            for pair_index in range(6):
                matchups: dict[str, Any] = {}
                for name in MATCHUPS:
                    pair = tapes[name]["pairs"][pair_index]
                    matchups[name] = {
                        "pair_score": float(pair["pair_score"]),
                        "status": str(pair["status"]),
                    }
                rows.append({
                    "control": control_name,
                    "tape_seed": seed,
                    "pair_index": pair_index,
                    "matchups": matchups,
                })
    return rows


def _source_audit() -> dict[str, Any]:
    return {
        "arena_telemetry": {
            "producer": "generic_chess/learning/arena.py:_play_one_game",
            "metric_alignment": "search_metrics is appended once per search decision; action index equals ply and a terminal declaration, when present, is the final index.",
            "fallback_field": "used_fallback is copied from the native semantic search result as a boolean.",
            "integrity_guard": "_validate_game_telemetry requires one metric per ply plus an optional declaration and validates role budgets.",
        },
        "semantic_search": {
            "producer": "generic_chess/_native/native_module.c:semantic_engine_search",
            "first_iteration_gate": "completed_iteration is set only after a full iterative negamax iteration returns with no control interruption; fallback is entered only when no full iteration completed.",
            "fallback_order": [
                "declaration win",
                "neutral declaration",
                "deterministic minimum legal action",
            ],
            "termination_mapping": {
                "1": "node_budget",
                "2": "time_budget",
                "3": "cancelled",
                "4": "internal_error",
            },
            "interpretation": "node_budget with completed_depth=0 is a legal pre-first-iteration root fallback; time/cancel/internal outcomes remain operational or abort evidence and are not merged with it.",
        },
        "authority_boundary": "This artifact is descriptive evidence only. It does not alter the frozen R6 classifier or promote any prospective R7 rule.",
    }


def extract(
    result_path: Path = RESULT_PATH,
    progress_root: Path = PROGRESS_PATH,
    *,
    expected_result_sha256: str = EXPECTED_RESULT_SHA256,
    expected_progress_evidence_sha256: str = EXPECTED_PROGRESS_EVIDENCE_SHA256,
) -> dict[str, Any]:
    result_path = Path(result_path)
    progress_root = Path(progress_root)
    result_sha256 = _sha256(result_path)
    if expected_result_sha256 and result_sha256 != expected_result_sha256:
        raise RuntimeError(f"R6 fallback forensics source SHA mismatch: {result_sha256} != {expected_result_sha256}")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    aggregate_payload = aggregate(result_path, progress_root, expected_result_sha256=expected_result_sha256)
    evidence_sha256 = aggregate_payload["progress_evidence_sha256"]
    if expected_progress_evidence_sha256 and evidence_sha256 != expected_progress_evidence_sha256:
        raise RuntimeError(
            "R6 fallback forensics progress evidence SHA mismatch: "
            f"{evidence_sha256} != {expected_progress_evidence_sha256}"
        )

    records: list[dict[str, Any]] = []
    invocation_counts: Counter[str] = Counter()
    prep = json.loads(Path(PREP_PATH).read_text(encoding="utf-8"))
    for control_name in sorted(result["controls"]):
        control = result["controls"][control_name]
        prep_control = next(row for row in prep["controls"] if row["name"] == control_name)
        for matchup_row in control["matchups"]:
            matchup = matchup_row["name"]
            child_budget, parent_budget = _budget_pair(matchup)
            for tape in matchup_row["tape_results"]:
                seed = int(tape["tape_seed"])
                directory = _progress_directory(
                    progress_root, control_name, matchup, seed,
                    experiment=result["experiment"],
                    protocol_source_sha=result["protocol_source_sha"],
                    prep_fingerprint=result["prep_fingerprint"],
                )
                manifest_path = directory / "manifest.json"
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest_sha256 = _sha256(manifest_path)
                prep_openings = next(
                    row for row in prep_control["opening_corpora"] if int(row["tape_seed"]) == seed
                )
                if len(tape.get("pairs", ())) != 6 or len(prep_openings["openings"]) != 6:
                    raise RuntimeError("R6 fallback forensics requires six aligned pairs")
                for pair_index in range(6):
                    pair_path = directory / f"pair-{pair_index:06d}.json"
                    payload = json.loads(pair_path.read_text(encoding="utf-8"))
                    try:
                        pair = _pair_from_dict(payload, identity_sha256=manifest["identity_sha256"])
                    except (KeyError, TypeError, ValueError) as exc:
                        raise RuntimeError(f"R6 fallback forensics pair schema/identity mismatch: {pair_path}") from exc
                    pair_sha256 = _sha256(pair_path)
                    for owner in (0, 1):
                        game = payload[f"game_child_owner{owner}"]
                        game_obj = pair.game_child_owner0 if owner == 0 else pair.game_child_owner1
                        metrics = game.get("search_metrics")
                        if not isinstance(metrics, list) or len(metrics) != int(game["plies"]) + int(game.get("declaration_id") is not None):
                            raise RuntimeError(f"R6 fallback forensics telemetry count mismatch: {pair_path}")
                        for decision_index, metric in enumerate(metrics):
                            _validate_metric(
                                metric,
                                index=decision_index,
                                plies=int(game["plies"]),
                                declaration_id=game.get("declaration_id"),
                                parent_budget=parent_budget,
                                child_budget=child_budget,
                            )
                            if not metric["used_fallback"]:
                                continue
                            category = classify_fallback(
                                engine_role=str(metric["engine_role"]),
                                nodes_budget=int(metric["nodes_budget"]),
                                completed_depth=int(metric["completed_depth"]),
                                termination_reason=str(metric["termination_reason"]),
                                decision_kind=str(metric["decision_kind"]),
                            )
                            record = {
                                "control": control_name,
                                "matchup": matchup,
                                "tape_seed": seed,
                                "pair_index": pair_index,
                                "child_owner": owner,
                                "decision_index": decision_index,
                                "ply": decision_index if metric["decision_kind"] == "action" else None,
                                "engine_role": str(metric["engine_role"]),
                                "nodes_budget": int(metric["nodes_budget"]),
                                "nodes": int(metric["nodes"]),
                                "completed_depth": int(metric["completed_depth"]),
                                "termination_reason": str(metric["termination_reason"]),
                                "decision_kind": str(metric["decision_kind"]),
                                "used_fallback": True,
                                "classification": category,
                                "source_result_sha256": result_sha256,
                                "source_result_path": aggregate_payload["source_result_path"],
                                "progress_evidence_sha256": evidence_sha256,
                                "invocation_identity_sha256": manifest["identity_sha256"],
                                "progress_manifest_sha256": manifest_sha256,
                                "pair_checkpoint_sha256": pair_sha256,
                            }
                            records.append(record)
                            invocation_counts[directory.name] += 1

    records.sort(key=lambda row: (
        row["control"], row["matchup"], row["tape_seed"], row["pair_index"],
        row["child_owner"], row["decision_index"],
    ))
    category_counts = dict(sorted(Counter(row["classification"] for row in records).items()))
    role_counts = dict(sorted(Counter(row["engine_role"] for row in records).items()))
    by_matchup = dict(sorted(Counter(row["matchup"] for row in records).items()))
    blocking = [row for row in records if row["classification"] in {
        "HIGH_BUDGET_PRE_ITERATION_NODE_FALLBACK", "OPERATIONAL_OR_ABORT_FALLBACK",
        "POST_ITERATION_FALLBACK_REQUIRES_REVIEW", "FALLBACK_DECISION_KIND_REQUIRES_REVIEW",
        "UNCLASSIFIED_FALLBACK_REQUIRES_REVIEW",
    }]

    western_matrix = [
        row for row in _response_matrix(result)
        if row["control"] == "western_chess_qualification_control_v1"
    ]
    western_4096_vs_1024 = [row["matchups"]["4096_vs_1024"]["pair_score"] for row in western_matrix]
    low_rows = [score for score in western_4096_vs_1024 if score <= 0.5]
    negative_rows = [score for score in western_4096_vs_1024 if score < 0.5]
    western_response_summary = {
        "matchup": "4096_vs_1024",
        "rows": len(western_4096_vs_1024),
        "scores_le_half": len(low_rows),
        "strict_negative_scores": len(negative_rows),
        "score_le_half_pair_indices": sorted({row["pair_index"] for row in western_matrix if row["matchups"]["4096_vs_1024"]["pair_score"] <= 0.5}),
        "strict_negative_tape_seeds": sorted({row["tape_seed"] for row in western_matrix if row["matchups"]["4096_vs_1024"]["pair_score"] < 0.5}),
        "interpretation": "mixed-or-lower outcomes span all six opening indices across the three tapes; strict negative outcomes are limited to two openings on tape 9803.",
    }

    return {
        "schema": FORENSICS_SCHEMA,
        "source_result_sha256": result_sha256,
        "source_result_path": aggregate_payload["source_result_path"],
        "progress_evidence_sha256": evidence_sha256,
        "prep_artifact_sha256": aggregate_payload["prep_artifact_sha256"],
        "experiment": aggregate_payload["experiment"],
        "fallback_count": len(records),
        "fallback_category_counts": category_counts,
        "fallback_role_counts": role_counts,
        "fallback_matchup_counts": by_matchup,
        "blocking_or_review_count": len(blocking),
        "all_observed_fallbacks_are_low_budget_pre_iteration": not blocking and all(
            row["classification"] == "LOW_BUDGET_PRE_ITERATION_NODE_FALLBACK" for row in records
        ),
        "invocation_counts": dict(sorted(invocation_counts.items())),
        "fallback_records": records,
        "response_matrix": _response_matrix(result),
        "western_response_summary": western_response_summary,
        "source_audit": _source_audit(),
        "authority": "descriptive_only",
        "r6_classifier_unchanged": True,
        "prospective_r7_rule": "not_selected",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, default=RESULT_PATH)
    parser.add_argument("--progress-root", type=Path, default=PROGRESS_PATH)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = extract(args.result, args.progress_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
