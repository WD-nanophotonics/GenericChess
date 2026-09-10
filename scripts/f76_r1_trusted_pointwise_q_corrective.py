"""F76-R1 corrective pointwise-Q fit using only the trusted F62 roots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from generic_chess.learning.nonlinear import CompactNonlinearResidual  # noqa: E402
from generic_chess.native import native_available  # noqa: E402
from scripts import f59_action_spectrum_diagnosis as f59  # noqa: E402
from scripts import f74_parent_retained_output_delta_probe as f74  # noqa: E402
from scripts import f76_parent_retained_pointwise_q_output_delta as f76  # noqa: E402


WORK_ORDER = "GENERICCHESS-F76-R1-TRUSTED-POINTWISE-Q-CORRECTIVE"
PARENT_SHA = "b40792426a4df593efb9febe8b97350cc029d097"
LABEL = "B_CANONICAL_STANDARD_SHOGI"
GEN1_ID = "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
INVALID_F76_ID = "efe6bcf97198a75badae0989720e3a5c05889c0d9f3babbe92c472d686724ffd"
F75_DESCRIPTOR = ROOT / "artifacts" / "f75_parent_retained_arena" / "candidate.json"
ARTIFACTS = ROOT / "artifacts" / "f76_r1_trusted_pointwise_q"
CANDIDATE_PATH = ARTIFACTS / "candidate.json"
OUT = ROOT / ".generic_chess_flow" / "f76-r1-trusted-pointwise-q"
RESULT_PATH = OUT / "f76_r1_results.json"
EXPECTED_TRUSTED_ROOT_COUNT = 34


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{path.stat().st_size if path.exists() else 'new'}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _load_f74_delta() -> np.ndarray:
    payload = json.loads(F75_DESCRIPTOR.read_text(encoding="utf-8"))
    if payload.get("child_checkpoint_id") != "bafabe1a6eeedf30b0ebe34109e5c4efdad87fc434edf8e75e9030e958bca0bb":
        raise RuntimeError("F76-R1 F75 descriptor identity mismatch")
    return np.asarray(payload["raw_delta"], dtype=np.float64)


def _predicate(root: dict) -> dict:
    metadata = root["metadata"]
    deep = metadata["root_80k"]["action_key"]
    return {
        "root_40k_matches_root_80k": metadata["root_40k"]["action_key"] == deep,
        "q10k_matches_q20k": metadata["spectrum_top_10k_action_key"] == metadata["spectrum_top_20k_action_key"],
        "q10k_matches_deep": metadata["spectrum_top_10k_action_key"] == deep,
        "root_80k_not_mate_band": not metadata["root_80k_mate_band"],
        "retained_q20_not_mate_band": not metadata["retained_q20_any_mate_band"],
    }


def _trusted_roots_with_predicates(roots: list[dict]) -> tuple[list[dict], list[dict]]:
    audited = []
    trusted = []
    for root in roots:
        predicate = _predicate(root)
        audited.append({"root_index": root["root_index"], **predicate, "trusted": all(predicate.values())})
        if all(predicate.values()):
            trusted.append(root)
    return trusted, audited


def _descriptor(gen1, candidate, candidate_model, delta, alpha, fit_summary, cosine, invalid_cosine, trusted_indices):
    training_identity = {
        "work_order": WORK_ORDER,
        "parent_checkpoint_id": gen1.checkpoint_id,
        "fit_method": "deterministic_ridge_pointwise_q_output_delta",
        "fit_regularization": gen1.compact_nonlinear["regularization"],
        "trusted_root_indices": trusted_indices,
        "raw_delta": delta.tolist(),
        "alpha": alpha,
    }
    return {
        "schema": "generic-chess-f76-r1-trusted-pointwise-q-candidate-v1",
        "source_commit": PARENT_SHA,
        "parent_checkpoint_id": gen1.checkpoint_id,
        "child_checkpoint_id": candidate.checkpoint_id,
        "alpha": alpha,
        "raw_delta": delta.tolist(),
        "final_output_weights": list(candidate_model.output_weights),
        "training_config_hash": f76.stable_sha256(training_identity),
        "candidate_model_sha256": f76.stable_sha256(candidate_model.to_dict()),
        "trusted_root_indices": trusted_indices,
        "fit_objective_before": fit_summary["objective_before"],
        "fit_objective_after": fit_summary["objective_after"],
        "f74_delta_cosine": cosine,
        "invalid_f76_delta_cosine": invalid_cosine,
    }


def _write_or_verify_descriptor(payload: dict) -> None:
    if CANDIDATE_PATH.is_file():
        if json.loads(CANDIDATE_PATH.read_text(encoding="utf-8")) != payload:
            raise RuntimeError("F76-R1 candidate descriptor identity mismatch")
    else:
        _atomic_json(CANDIDATE_PATH, payload)


def _classify(contract_failures, safety_failures, cosine, development):
    if contract_failures:
        return "HARNESS_MISMATCH"
    if safety_failures:
        return "POINTWISE_OUTPUT_DELTA_UNSAFE"
    if cosine >= 0.995:
        return "POINTWISE_OUTPUT_DELTA_REDUNDANT_WITH_F74"
    if development["decision_changes"] >= 1:
        return "POINTWISE_OUTPUT_DELTA_DEPLOYMENT_VISIBLE"
    return "POINTWISE_OUTPUT_DELTA_NOT_DEPLOYMENT_VISIBLE"


def run() -> dict:
    if not native_available():
        raise RuntimeError("F76-R1 requires the native extension")
    compiled, native, _profile = f59._ruleset(LABEL)
    gen1 = f76._load_gen1(compiled)
    parent_model = CompactNonlinearResidual.from_dict(gen1.compact_nonlinear)
    fit_roots = f76._fit_roots()
    trusted_roots, predicates = _trusted_roots_with_predicates(fit_roots)
    trusted_indices = [root["root_index"] for root in trusted_roots]
    contract_failures = []
    if len(trusted_roots) != EXPECTED_TRUSTED_ROOT_COUNT:
        contract_failures.append(
            f"trusted root count expected {EXPECTED_TRUSTED_ROOT_COUNT}, got {len(trusted_roots)}"
        )
    trusted_rows = [_root for _root in trusted_roots]
    pointwise = f76._pointwise_rows(trusted_rows, parent_model)
    delta, fit_summary = f76._fit_pointwise_delta(
        pointwise, parent_model.width, parent_model.target_scale, parent_model.regularization
    )
    f74_delta = f76._load_f75_delta()
    invalid_delta = np.asarray(json.loads((ROOT / "artifacts" / "f76_parent_retained_pointwise_q" / "candidate.json").read_text(encoding="utf-8"))["raw_delta"], dtype=np.float64)
    cosine = float(delta @ f74_delta / (np.linalg.norm(delta) * np.linalg.norm(f74_delta)))
    invalid_cosine = float(delta @ invalid_delta / (np.linalg.norm(delta) * np.linalg.norm(invalid_delta)))
    fit_data_all = [f76._root_rows(root, parent_model) for root in fit_roots]
    high_boundary, high_summary = f76._high_confidence_boundary(fit_data_all, delta, parent_model.target_scale)
    residual_boundary, residual_summary = f76._residual_boundary(fit_data_all, delta, parent_model.target_scale)
    alpha_star = float(min(1.0, 0.5 * high_boundary, residual_boundary))
    candidate_model, candidate, candidate_summary = f76._make_candidate(gen1, parent_model, delta, alpha_star)
    descriptor = _descriptor(gen1, candidate, candidate_model, delta, alpha_star, fit_summary, cosine, invalid_cosine, trusted_indices)
    _write_or_verify_descriptor(descriptor)
    representation_failures = f76._representation_guard(compiled, gen1, candidate, parent_model, candidate_model)
    parity = f76._native_parity(compiled, native, gen1, candidate, candidate_model, trusted_roots)
    final_fit_data = [f76._root_rows(root, candidate_model) for root in fit_roots]
    final_objective = f76._pointwise_objective(alpha_star * delta, pointwise, parent_model.target_scale, parent_model.regularization)
    parent_max = residual_summary["parent_max_abs"]
    candidate_max = max(float(np.max(np.abs(root["parent_residual"]))) for root in final_fit_data)
    high_indices = {
        root["root_index"] for root, margin in zip(
            fit_data_all,
            [max(root["parent_total"]) - sorted(root["parent_total"])[-2] for root in fit_data_all],
        ) if margin >= high_summary["upper_quartile_threshold"]
    }
    retention_failures = []
    for root in fit_data_all:
        if root["root_index"] not in high_indices:
            continue
        candidate_root = next(item for item in final_fit_data if item["root_index"] == root["root_index"])
        if root["keys"][_top_index(root["parent_total"], root["keys"])] != candidate_root["keys"][_top_index(candidate_root["parent_total"], candidate_root["keys"])]:
            retention_failures.append(f"root-{root['root_index']}: high-confidence top action changed")
    contract_failures.extend(representation_failures + parity["failures"] + retention_failures)
    safety_failures = []
    if not alpha_star > 0.0:
        safety_failures.append("trust-region alpha is not positive")
    if candidate_max > 2.0 * parent_max:
        safety_failures.append("fit residual cap exceeded")
    if not final_objective < fit_summary["objective_before"]:
        safety_failures.append("trusted-training weighted pointwise-Q objective did not improve")
    development = None
    if contract_failures:
        classification = _classify(contract_failures, safety_failures, cosine, development)
    elif safety_failures:
        classification = _classify(contract_failures, safety_failures, cosine, development)
    elif cosine >= 0.995:
        classification = _classify(contract_failures, safety_failures, cosine, development)
    else:
        development_rows = [f76._development_row(compiled, native, gen1, candidate, root) for root in f76._development_roots()]
        development = f76._development_summary(development_rows)
        contract_failures.extend(
            f"root-{row['root_index']}: repeated fresh arm differed" for row in development_rows if not row["deterministic"]
        )
        if not development["root_window_pruning_all_true"]:
            contract_failures.append("development root pruning telemetry was not true")
        classification = _classify(contract_failures, safety_failures, cosine, development)
    result = {
        "schema": "generic-chess-f76-r1-trusted-pointwise-q-corrective-v1",
        "work_order": WORK_ORDER,
        "baseline_sha": PARENT_SHA,
        "classification": classification,
        "invalid_f76_candidate": {"checkpoint_id": INVALID_F76_ID, "selection_status": "INVALID_FOR_SELECTION_DUE_TO_FIT_CORPUS_CONTRACT_MISMATCH"},
        "gen1_checkpoint_id": gen1.checkpoint_id,
        "candidate_checkpoint_id": candidate.checkpoint_id,
        "fit_data_identity": {"stage_sha256": f74.F62_STAGE_SHA, "records_sha256": f74.F62_RECORDS_SHA},
        "fit_root_count": len(fit_roots),
        "trusted_root_count": len(trusted_roots),
        "trusted_root_indices": trusted_indices,
        "trusted_root_predicates": predicates,
        "fit": {
            "objective": "weighted_pointwise_q_trusted_roots",
            "regularization": parent_model.regularization,
            "target_scale": parent_model.target_scale,
            "action_row_count": sum(len(root) for root in pointwise),
            "summary": fit_summary,
            "objective_before": fit_summary["objective_before"],
            "objective_after_raw_delta": fit_summary["objective_after"],
            "objective_after_alpha_star": final_objective,
        },
        "correction": {
            "raw_delta": delta.tolist(),
            "raw_delta_norm": float(np.linalg.norm(delta)),
            "f74_delta_cosine": cosine,
            "invalid_f76_delta_cosine": invalid_cosine,
            "alpha_high_confidence_boundary": high_boundary,
            "alpha_residual_cap_boundary": residual_boundary,
            "alpha_star": alpha_star,
            "high_confidence": high_summary,
            "residual_cap": residual_summary,
            "candidate": candidate_summary,
            "descriptor_path": str(CANDIDATE_PATH.relative_to(ROOT)),
        },
        "retention": {
            "source_fit_root_count": len(fit_roots),
            "upper_quartile_roots_checked": len(high_indices),
            "high_confidence_top_action_retained": not retention_failures,
            "parent_max_abs_residual": parent_max,
            "candidate_max_abs_residual": candidate_max,
            "allowed_max_abs_residual": 2.0 * parent_max,
        },
        "native_python_parity": parity,
        "development": development,
        "contract_failures": contract_failures,
        "safety_failures": safety_failures,
        "code_provenance": {
            **f76._provenance(),
            "scripts/f76_r1_trusted_pointwise_q_corrective.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
    }
    _atomic_json(RESULT_PATH, result)
    return result


def _top_index(scores, keys):
    return min(range(len(scores)), key=lambda index: (-float(scores[index]), keys[index]))


def main() -> None:
    result = run()
    print(json.dumps({
        "classification": result["classification"],
        "candidate_checkpoint_id": result["candidate_checkpoint_id"],
        "fit_root_count": result["fit_root_count"],
        "trusted_root_count": result["trusted_root_count"],
        "trusted_root_indices": result["trusted_root_indices"],
        "raw_delta_norm": result["correction"]["raw_delta_norm"],
        "f74_delta_cosine": result["correction"]["f74_delta_cosine"],
        "invalid_f76_delta_cosine": result["correction"]["invalid_f76_delta_cosine"],
        "alpha_star": result["correction"]["alpha_star"],
        "objective_before": result["fit"]["objective_before"],
        "objective_after_alpha_star": result["fit"]["objective_after_alpha_star"],
        "decision_changes": None if result["development"] is None else result["development"]["decision_changes"],
        "contract_failures": result["contract_failures"],
        "safety_failures": result["safety_failures"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
