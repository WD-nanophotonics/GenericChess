"""F76-R2 repair of the trusted pointwise-Q candidate's durable identity."""

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
from scripts import f76_parent_retained_pointwise_q_output_delta as f76  # noqa: E402
from scripts import f76_r1_trusted_pointwise_q_corrective as r1  # noqa: E402


WORK_ORDER = "GENERICCHESS-F76-R2-DURABLE-CANDIDATE-IDENTITY-CORRECTIVE"
PARENT_SHA = "0a77db47c59b6f792b035d1e08f5e915e385d208"
LABEL = "B_CANONICAL_STANDARD_SHOGI"
GEN1_ID = "d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4"
R1_ID = "140daa82ba60d5dee82a9212a679834f3c19919c43bf30704feb51c87fd1c324"
R1_ACTUAL_TRAINING_HASH = "ee3d16b950c0f20ac8b49d936dd567116fc4b9383f25ccd4896a6389ed167d43"
R1_DESCRIPTOR = ROOT / "artifacts" / "f76_r1_trusted_pointwise_q" / "candidate.json"
ARTIFACTS = ROOT / "artifacts" / "f76_r2_trusted_pointwise_q"
CANDIDATE_PATH = ARTIFACTS / "candidate.json"
OUT = ROOT / ".generic_chess_flow" / "f76-r2-durable-candidate-identity"
RESULT_PATH = OUT / "f76_r2_results.json"
F62_STAGE_SHA = "e7a93423d6058c68fe7ccbc61302584ca1e8869aa828586254f72f4dfdac2c70"
F62_RECORDS_SHA = "b7a6dc134bf1232fa90d9734ad070c184ecd09f691bc92958686093181d3ff61"


def _atomic_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _trusted_fit_material(compiled, gen1):
    fit_roots = f76._fit_roots()
    trusted_roots, predicates = r1._trusted_roots_with_predicates(fit_roots)
    indices = [root["root_index"] for root in trusted_roots]
    if len(trusted_roots) != 34:
        raise RuntimeError(f"F76-R2 trusted root count mismatch: {len(trusted_roots)}")
    parent_model = CompactNonlinearResidual.from_dict(gen1.compact_nonlinear)
    pointwise = f76._pointwise_rows(trusted_roots, parent_model)
    delta, fit_summary = f76._fit_pointwise_delta(
        pointwise, parent_model.width, parent_model.target_scale, parent_model.regularization
    )
    fit_data_all = [f76._root_rows(root, parent_model) for root in fit_roots]
    high_boundary, high_summary = f76._high_confidence_boundary(fit_data_all, delta, parent_model.target_scale)
    residual_boundary, residual_summary = f76._residual_boundary(fit_data_all, delta, parent_model.target_scale)
    alpha = float(min(1.0, 0.5 * high_boundary, residual_boundary))
    return fit_roots, trusted_roots, predicates, indices, parent_model, delta, fit_summary, high_summary, residual_summary, alpha


def _canonical_identity(gen1, delta, alpha, indices):
    return {
        "work_order": WORK_ORDER,
        "parent_checkpoint_id": gen1.checkpoint_id,
        "f62_stage_sha256": F62_STAGE_SHA,
        "f62_records_sha256": F62_RECORDS_SHA,
        "fit_method": "deterministic_ridge_pointwise_q_output_delta",
        "regularization": 0.001,
        "trusted_root_indices": list(indices),
        "raw_delta": delta.tolist(),
        "alpha": alpha,
    }


def _build_checkpoint(gen1, candidate_model, training_hash):
    return gen1.child_checkpoint(
        board_weights=gen1.board_weights,
        hand_weights=gen1.hand_weights,
        dynamic_weights=gen1.dynamic_weights,
        compact_nonlinear=candidate_model.to_dict(),
        games_seen_delta=0,
        positions_seen_delta=0,
        training_updates_delta=1,
        training_config_hash=training_hash,
        training_seed=None,
    )


def _search_parity(compiled, native, old_checkpoint, new_checkpoint, roots):
    rows = []
    failures = []
    for root in roots:
        old = f76._search_arm(compiled, native, old_checkpoint, root)
        old_repeat = f76._search_arm(compiled, native, old_checkpoint, root)
        new = f76._search_arm(compiled, native, new_checkpoint, root)
        new_repeat = f76._search_arm(compiled, native, new_checkpoint, root)
        exact = old == old_repeat == new == new_repeat
        if not exact:
            failures.append(f"root-{root['root_index']}: R1/R2 search parity mismatch")
        rows.append({
            "root_index": root["root_index"],
            "old_r1": old,
            "old_r1_repeat": old_repeat,
            "new_r2": new,
            "new_r2_repeat": new_repeat,
            "exact": exact,
        })
    return {"root_count": len(rows), "all_exact": not failures, "failures": failures, "rows": rows}


def run() -> dict:
    if not native_available():
        raise RuntimeError("F76-R2 requires the native extension")
    compiled, native, _profile = f59._ruleset(LABEL)
    gen1 = f76._load_gen1(compiled)
    fit_roots, trusted_roots, predicates, indices, parent_model, delta, fit_summary, high_summary, residual_summary, alpha = _trusted_fit_material(compiled, gen1)
    old_descriptor = json.loads(R1_DESCRIPTOR.read_text(encoding="utf-8"))
    old_model = CompactNonlinearResidual.from_dict({
        **gen1.compact_nonlinear,
        "output_weights": old_descriptor["final_output_weights"],
    })
    recomputed_alpha = old_descriptor["alpha"]
    evaluator_failures = []
    if not np.array_equal(delta, np.asarray(old_descriptor["raw_delta"], dtype=np.float64)):
        evaluator_failures.append("R1 raw delta differs from corrected trusted fit")
    if alpha != recomputed_alpha:
        evaluator_failures.append("R1 alpha differs from corrected trusted fit")
    if f76.stable_sha256(old_model.to_dict()) != old_descriptor["candidate_model_sha256"]:
        evaluator_failures.append("R1 evaluator model differs from descriptor")
    old_r1 = _build_checkpoint(gen1, old_model, R1_ACTUAL_TRAINING_HASH)
    if old_r1.checkpoint_id != R1_ID:
        evaluator_failures.append("R1 actual training hash does not reconstruct R1 checkpoint")
    identity = _canonical_identity(gen1, delta, alpha, indices)
    canonical_hash = f76.stable_sha256(identity)
    new_candidate = _build_checkpoint(gen1, old_model, canonical_hash)
    descriptor = {
        "schema": "generic-chess-f76-r2-trusted-pointwise-q-candidate-v1",
        "source_commit": PARENT_SHA,
        "parent_checkpoint_id": gen1.checkpoint_id,
        "child_checkpoint_id": new_candidate.checkpoint_id,
        "canonical_training_identity": identity,
        "canonical_training_config_hash": canonical_hash,
        "candidate_model_sha256": f76.stable_sha256(old_model.to_dict()),
        "final_output_weights": list(old_model.output_weights),
        "r1_candidate_checkpoint_id": R1_ID,
        "r1_actual_training_config_hash": R1_ACTUAL_TRAINING_HASH,
    }
    if CANDIDATE_PATH.is_file():
        if json.loads(CANDIDATE_PATH.read_text(encoding="utf-8")) != descriptor:
            raise RuntimeError("F76-R2 descriptor identity mismatch")
    else:
        _atomic_json(CANDIDATE_PATH, descriptor)
    representation_failures = f76._representation_guard(compiled, gen1, new_candidate, parent_model, old_model)
    parity = f76._native_parity(compiled, native, gen1, new_candidate, old_model, trusted_roots)
    evaluator_equal = old_r1.compact_nonlinear == new_candidate.compact_nonlinear
    if not evaluator_equal:
        evaluator_failures.append("R1 and R2 evaluator payloads differ")
    contract_failures = evaluator_failures + representation_failures + parity["failures"]
    search_parity = None
    if not contract_failures:
        search_parity = _search_parity(compiled, native, old_r1, new_candidate, f76._development_roots())
        contract_failures.extend(search_parity["failures"])
    classification = "POINTWISE_OUTPUT_DELTA_DURABLE_IDENTITY_REPAIRED" if not contract_failures else "HARNESS_MISMATCH"
    result = {
        "schema": "generic-chess-f76-r2-durable-candidate-identity-corrective-v1",
        "work_order": WORK_ORDER,
        "baseline_sha": PARENT_SHA,
        "classification": classification,
        "preserved_r1": {
            "descriptor_path": str(R1_DESCRIPTOR.relative_to(ROOT)),
            "candidate_checkpoint_id": R1_ID,
            "selection_status": "INVALID_FOR_SELECTION_DUE_TO_DURABLE_TRAINING_IDENTITY_MISMATCH",
            "actual_training_config_hash": R1_ACTUAL_TRAINING_HASH,
            "descriptor_training_config_hash": old_descriptor["training_config_hash"],
            "descriptor_hash_differs_from_actual": old_descriptor["training_config_hash"] != R1_ACTUAL_TRAINING_HASH,
        },
        "gen1_checkpoint_id": gen1.checkpoint_id,
        "candidate_checkpoint_id": new_candidate.checkpoint_id,
        "canonical_training_identity": identity,
        "canonical_training_config_hash": canonical_hash,
        "fit_root_count": len(fit_roots),
        "trusted_root_count": len(trusted_roots),
        "trusted_root_indices": indices,
        "trusted_root_predicates": predicates,
        "fit": {
            "action_row_count": sum(len(root) for root in f76._pointwise_rows(trusted_roots, parent_model)),
            "objective_before": fit_summary["objective_before"],
            "objective_after_raw_delta": fit_summary["objective_after"],
            "alpha": alpha,
            "raw_delta_norm": float(np.linalg.norm(delta)),
        },
        "trust_region": {
            "high_confidence_boundary": high_summary.get("first_boundary", {}).get("alpha", float("inf")) if high_summary.get("first_boundary") else float("inf"),
            "residual_cap_boundary": residual_summary.get("first_boundary", {}).get("alpha", float("inf")) if residual_summary.get("first_boundary") else float("inf"),
            "high_confidence_roots_checked": high_summary["selected_root_count"],
            "parent_max_abs_residual": residual_summary["parent_max_abs"],
            "allowed_max_abs_residual": residual_summary["allowed_max_abs"],
        },
        "candidate": {
            "model_sha256": f76.stable_sha256(old_model.to_dict()),
            "evaluator_payload_equal_to_r1": evaluator_equal,
            "descriptor_path": str(CANDIDATE_PATH.relative_to(ROOT)),
        },
        "native_python_parity": parity,
        "search_parity": search_parity,
        "contract_failures": contract_failures,
        "code_provenance": {
            "scripts/f76_r2_durable_candidate_identity_corrective.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "scripts/f76_r1_trusted_pointwise_q_corrective.py": hashlib.sha256((ROOT / "scripts/f76_r1_trusted_pointwise_q_corrective.py").read_bytes()).hexdigest(),
            "generic_chess/native/semantic_engine.py": hashlib.sha256((ROOT / "generic_chess/native/semantic_engine.py").read_bytes()).hexdigest(),
        },
    }
    _atomic_json(RESULT_PATH, result)
    return result


def main() -> None:
    result = run()
    print(json.dumps({
        "classification": result["classification"],
        "candidate_checkpoint_id": result["candidate_checkpoint_id"],
        "canonical_training_config_hash": result["canonical_training_config_hash"],
        "r1_evaluator_candidate_id": result["preserved_r1"]["candidate_checkpoint_id"],
        "trusted_root_count": result["trusted_root_count"],
        "search_parity_all_exact": None if result["search_parity"] is None else result["search_parity"]["all_exact"],
        "contract_failures": result["contract_failures"],
    }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
