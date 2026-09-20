"""F136: diagnose corrected-Shogi coverage and active-subspace identifiability."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import (
        COUNTS, FrozenBasis, _action_ranking, _collect_fresh_roots, _json_sha, _scalar_metrics,
    )
    from scripts.f123_reverse_benchmark_identifiability_optimizer_diagnosis import (
        _material_dependency_report, _matched_ridge, _minimum_norm, _prepare, _predict, _proxy_fit, _scalar_summary,
    )
    from scripts.f135_corrected_shogi_oracle_schema_rebaseline import (
        CORPUS_SHA, CORPUS_SEED, CorrectedShogiFrozenBasisV2, FAMILY, _collect_states, _materialize, _ranking_summary,
    )
    from scripts.f127_shogi_t1_scalar_compression_expanded_control import _pcg_tight
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import COUNTS, FrozenBasis, _action_ranking, _collect_fresh_roots, _json_sha, _scalar_metrics
    from f123_reverse_benchmark_identifiability_optimizer_diagnosis import _material_dependency_report, _matched_ridge, _minimum_norm, _prepare, _predict, _proxy_fit, _scalar_summary
    from f135_corrected_shogi_oracle_schema_rebaseline import CORPUS_SHA, CORPUS_SEED, CorrectedShogiFrozenBasisV2, FAMILY, _collect_states, _materialize, _ranking_summary
    from f127_shogi_t1_scalar_compression_expanded_control import _pcg_tight

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


BASELINE = "f63eaaffa4c143342fa3d11c05447e8766974a4a"
CORRECTED_ORACLE_SHA = "fdd6405ffa3f92de05f401dbd12d00a16191ac10c2ba2383fe5332694c9e7aa6"
FEATURE_NAME_SHA = "6accfab1039a546071a23c885d582a2c10792e5db49f69bfa9556c131d516942"
F135_HOLDOUT = {
    "rmse_oracle_units": 211.189237270397,
    "normalized_rmse": 0.15595845351232307,
    "r2": 0.9756769607780446,
    "pearson": 0.9878499297805251,
}
F135_ACTION = {
    "top1_agreement": 0.97265625,
    "pairwise_ordering_agreement": 0.9851308467506316,
    "mean_regret_normalized": 0.0024239891704051506,
}
FAMILY_ORDER = (
    "material", "occupancy/PST", "hand", "mobility", "king escape",
    "king-zone pressure", "current check", "promotion potential",
    "legal-drop counts", "mean legal-drop mobility",
)


def _corr(left: np.ndarray, right: np.ndarray) -> float:
    left = np.asarray(left, dtype=np.float64)
    right = np.asarray(right, dtype=np.float64)
    a = left - left.mean(); b = right - right.mean()
    denominator = float(np.sqrt(np.sum(a * a) * np.sum(b * b)))
    return float(np.sum(a * b) / denominator) if denominator else 0.0


def _gate(metrics: dict) -> bool:
    return bool(metrics["normalized_rmse"] <= 0.05 and metrics["r2"] >= 0.99 and metrics["pearson"] >= 0.995)


def _prediction_metrics(pack: dict, predictions: dict[str, np.ndarray]) -> dict:
    normalizer = float(np.std(pack["oracle"]["holdout"])) or 1.0
    return {
        split: _scalar_metrics(pack["oracle"][split], predictions[split], normalizer)
        for split in ("train", "dev", "holdout")
    }


def _feature_family(name: str) -> str:
    if name.startswith("material_diff:"): return "material"
    if name.startswith("occupancy_diff:"): return "occupancy/PST"
    if name.startswith("hand_diff:"): return "hand"
    if name == "mobility_diff": return "mobility"
    if name == "king_escape_diff": return "king escape"
    if name == "king_zone_pressure_diff": return "king-zone pressure"
    if name == "current_check_diff": return "current check"
    if name == "promotion_potential_diff": return "promotion potential"
    if name.startswith("legal_drop_count_diff:"): return "legal-drop counts"
    if name == "mean_legal_drop_mobility_diff": return "mean legal-drop mobility"
    raise AssertionError(f"unknown corrected feature family: {name}")


def _matrix_report(pack: dict, basis: CorrectedShogiFrozenBasisV2) -> dict:
    singular = pack["singular_values"]; retained = pack["retained"]
    spectrum = singular[retained]
    return {
        "raw_feature_count": len(basis.names),
        "active_feature_count": int(pack["active"].sum()),
        "train_constant_feature_count": len(pack["constant_feature_names"]),
        "active_feature_names": [name for name, keep in zip(basis.names, pack["active"]) if keep],
        "train_constant_feature_names": list(pack["constant_feature_names"]),
        "design_dimensions_including_intercept": list(pack["design"]["train"].shape),
        "numerical_rank": int(retained.sum()),
        "nullity": int(len(singular) - retained.sum()),
        "retained_spectrum_condition_number": float(spectrum[0] / spectrum[-1]) if len(spectrum) else None,
        "effective_ranks": {str(threshold): int(np.sum(singular > threshold * singular[0])) for threshold in (1e-6, 1e-8, 1e-10)},
        "rank_tolerance": float(pack["rank_tol"]),
    }


def _constant_audit(pack: dict, basis: CorrectedShogiFrozenBasisV2) -> tuple[dict, dict]:
    train = pack["raw"]["train"]
    entries: dict[str, dict] = {}
    contributions: dict[str, np.ndarray] = {}
    family_vectors: dict[str, dict[str, list[np.ndarray]]] = {
        family: {split: [] for split in ("dev", "holdout")} for family in FAMILY_ORDER
    }
    for name in pack["constant_feature_names"]:
        index = basis.names.index(name); value = float(train[0, index]); weight = float(basis.weights[index])
        entry = {"feature_name": name, "semantic_family": _feature_family(name), "oracle_coefficient": weight, "train_constant_value": value}
        for split in ("dev", "holdout"):
            delta = pack["raw"][split][:, index] - value; contribution = weight * delta
            entry[split] = {
                "remains_constant": bool(np.allclose(delta, 0.0, atol=1e-12, rtol=0.0)),
                "variance": float(np.var(pack["raw"][split][:, index])),
                "nonzero_state_count": int(np.count_nonzero(np.abs(delta) > 1e-12)),
                "contribution_rms": float(np.sqrt(np.mean(contribution * contribution))),
                "max_abs_contribution": float(np.max(np.abs(contribution))),
            }
            family = _feature_family(name)
            family_vectors[family][split].append(contribution)
            contributions.setdefault(split, []).append(contribution)
        entries[name] = entry
    aggregate = {}
    for split in ("dev", "holdout"):
        matrix = np.column_stack(contributions[split]) if contributions.get(split) else np.zeros((len(pack["raw"][split]), 0))
        total = matrix.sum(axis=1) if matrix.shape[1] else np.zeros(len(pack["raw"][split]))
        aggregate[split] = {
            "train_constant_features_becoming_variable": int(sum(not row[split]["remains_constant"] for row in entries.values())),
            "oracle_contribution_rms": float(np.sqrt(np.mean(total * total))),
            "oracle_contribution_max_abs": float(np.max(np.abs(total))) if len(total) else 0.0,
            "oracle_contribution_rms_over_holdout_target_std": float(np.sqrt(np.mean(total * total)) / (float(np.std(pack["oracle"]["holdout"])) or 1.0)),
        }
    family_totals = {}
    for family in FAMILY_ORDER:
        family_totals[family] = {}
        for split in ("dev", "holdout"):
            total = np.sum(np.column_stack(family_vectors[family][split]), axis=1) if family_vectors[family][split] else np.zeros(len(pack["raw"][split]))
            family_totals[family][split] = {"signed_contribution_rms": float(np.sqrt(np.mean(total * total))), "max_abs_contribution": float(np.max(np.abs(total))) if len(total) else 0.0}
    ranked = sorted(entries.values(), key=lambda row: row["holdout"]["contribution_rms"], reverse=True)
    return {"features": entries, "aggregate": aggregate, "by_family": family_totals, "top_30_by_holdout_contribution_rms": ranked[:30]}, {split: np.sum(np.column_stack(contributions[split]), axis=1) if contributions.get(split) else np.zeros(len(pack["raw"][split])) for split in ("dev", "holdout")}


def _counterfactual(pack: dict, matched: np.ndarray, c_const: dict) -> dict:
    predictions = {split: _predict(matched, pack, split) + (c_const[split] if split in c_const else 0.0) for split in ("train", "dev", "holdout")}
    metrics = _prediction_metrics(pack, predictions)
    return {"scalar_metrics": metrics, "a1_gate_pass": _gate(metrics["holdout"])}


def _ridge_bias(pack: dict, matched: np.ndarray, minimum_norm: np.ndarray) -> dict:
    result = {}
    for split in ("train", "dev", "holdout"):
        delta = pack["target_std"] * (pack["design"][split] @ (matched - minimum_norm))
        result[split] = {
            "rmse_oracle_units": float(np.sqrt(np.mean(delta * delta))),
            "normalized_rmse": float(np.sqrt(np.mean(delta * delta)) / (float(np.std(pack["oracle"]["holdout"])) or 1.0)),
            "max_abs_oracle_units": float(np.max(np.abs(delta))),
        }
    return result


def _active_oracle_decomposition(pack: dict, basis: CorrectedShogiFrozenBasisV2, residual_after_constant_correction: np.ndarray | None = None) -> dict:
    active_indices = np.flatnonzero(pack["active"]); constant_indices = np.flatnonzero(~pack["active"])
    train_raw = pack["raw"]["train"]
    train_constant = float(np.dot(pack["feature_scale"][constant_indices] * 0.0 + train_raw[0, constant_indices], np.asarray(basis.weights)[constant_indices])) if len(constant_indices) else 0.0
    theta = np.zeros(pack["design"]["train"].shape[1], dtype=np.float64)
    theta[:-1] = np.asarray(basis.weights)[active_indices] * pack["feature_scale"][active_indices] / pack["target_std"]
    theta[-1] = (float(np.dot(np.asarray(basis.weights)[active_indices], pack["feature_mean"][active_indices])) + train_constant - pack["target_mean"]) / pack["target_std"]
    vt = pack["vt"]; retained = pack["retained"]
    row = vt[retained].T @ (vt[retained] @ theta) if np.any(retained) else np.zeros_like(theta)
    null = theta - row
    total_norm_sq = float(np.dot(theta, theta))
    result = {
        "theta_oracle_active_norm": float(np.linalg.norm(theta)),
        "row_component_norm": float(np.linalg.norm(row)),
        "null_component_norm": float(np.linalg.norm(null)),
        "null_fraction_of_squared_exact_parameter_norm": float(np.dot(null, null) / total_norm_sq) if total_norm_sq else 0.0,
        "theta_oracle_active": theta.tolist(),
    }
    normalizer = float(np.std(pack["oracle"]["holdout"])) or 1.0
    null_predictions = {}
    for split in ("train", "dev", "holdout"):
        contribution = pack["target_std"] * (pack["design"][split] @ null)
        null_predictions[split] = {"rmse_oracle_units": float(np.sqrt(np.mean(contribution * contribution))), "normalized_rmse": float(np.sqrt(np.mean(contribution * contribution)) / normalizer), "max_abs_oracle_units": float(np.max(np.abs(contribution)))}
        if split == "holdout" and residual_after_constant_correction is not None:
            null_predictions[split]["pearson_with_f135_residual_after_exact_constant_correction"] = _corr(contribution, residual_after_constant_correction)
        result.setdefault("null_prediction_contribution", {})[split] = null_predictions[split]
    return result, null_predictions["holdout"]


def _coverage_candidates(pack: dict, basis: CorrectedShogiFrozenBasisV2, rows: list[dict]) -> list[dict]:
    train = pack["raw"]["train"]
    candidates = []
    for name in pack["constant_feature_names"]:
        index = basis.names.index(name); value = train[0, index]; holdout_delta = pack["raw"]["holdout"][:, index] - value; dev_delta = pack["raw"]["dev"][:, index] - value
        differing = np.flatnonzero(np.abs(np.r_[dev_delta, holdout_delta]) > 1e-12)
        if len(differing) and abs(basis.weights[index]) > 0.0:
            global_index = COUNTS["train"] + int(differing[0]) if differing[0] < COUNTS["dev"] else COUNTS["train"] + COUNTS["dev"] + int(differing[0] - COUNTS["dev"])
            candidates.append({"feature_name": name, "semantic_family": _feature_family(name), "dev_or_holdout_differing_state_count": int(len(differing)), "first_frozen_corpus_identity_exhibiting_difference": rows[global_index]["identity"], "oracle_contribution_rms": float(np.sqrt(np.mean((basis.weights[index] * holdout_delta) ** 2)))} )
    return sorted(candidates, key=lambda row: row["oracle_contribution_rms"], reverse=True)


def _run(output: Path) -> dict:
    started = time.time(); compiled = compile_semantic_ruleset(build_standard_shogi_ruleset()); legacy = FrozenBasis(FAMILY, compiled); basis = CorrectedShogiFrozenBasisV2(FAMILY, compiled)
    if basis.oracle_weight_sha256 != CORRECTED_ORACLE_SHA or _json_sha(basis.names) != FEATURE_NAME_SHA: raise RuntimeError("F136_CORRECTED_SCHEMA_HASH_MISMATCH")
    states = _collect_states(compiled); rows = _materialize(states, basis)
    if _json_sha([row["identity"] for row in states]) != CORPUS_SHA: raise RuntimeError("F136_FROZEN_CORPUS_IDENTITY_MISMATCH")
    pack = _prepare(rows, basis); matched = _matched_ridge(pack); pcg, pcg_trace = _pcg_tight(pack); minimum_norm = _minimum_norm(pack)
    matched_metrics = _scalar_summary(matched, pack); f135_metrics = _scalar_summary(pcg, pack)
    if any(abs(f135_metrics["holdout"][key] - value) > 1e-9 for key, value in F135_HOLDOUT.items()): raise RuntimeError("F136_F135_REPRODUCTION_FAILURE")
    roots = _collect_fresh_roots(FAMILY, compiled, basis, 1220221, {row["identity"] for row in states}, 256)
    ranking_fit = _proxy_fit(pcg, pack); ranking_fit["pcg_model"] = ranking_fit.pop("adam_model")
    ranking = _ranking_summary(_action_ranking(roots, basis, ranking_fit, "pcg"), float(np.std(pack["oracle"]["holdout"])) or 1.0)
    if any(abs(ranking[key] - F135_ACTION[key]) > 1e-9 for key in F135_ACTION): raise RuntimeError("F136_F135_ACTION_REPRODUCTION_FAILURE")
    exact_sanity = {}
    for split, split_rows in (("train", rows[:COUNTS["train"]]), ("dev", rows[COUNTS["train"]:COUNTS["train"] + COUNTS["dev"]]), ("holdout", rows[-COUNTS["holdout"]:])):
        errors = np.asarray([basis.oracle(np.asarray(row["features"], dtype=np.float64)) - row["oracle"] for row in split_rows])
        exact_sanity[split] = {"max_abs_stored_oracle_error": float(np.max(np.abs(errors))), "self_prediction_max_abs_error": float(np.max(np.abs(errors))), "zero_self_prediction_error": bool(np.max(np.abs(errors)) <= 1e-12)}
    matrix = _matrix_report(pack, basis); constant_audit, c_const = _constant_audit(pack, basis)
    f135_predictions = {split: _predict(matched, pack, split) for split in ("train", "dev", "holdout")}
    residual_diagnostics = {}; holdout_residual = pack["oracle"]["holdout"] - f135_predictions["holdout"]
    for split in ("dev", "holdout"):
        residual = pack["oracle"][split] - f135_predictions[split]; correction = c_const[split]
        residual_diagnostics[split] = {"c_const_rms": float(np.sqrt(np.mean(correction * correction))), "c_const_normalized_rms": float(np.sqrt(np.mean(correction * correction)) / (float(np.std(pack["oracle"]["holdout"])) or 1.0)), "c_const_mae": float(np.mean(np.abs(correction))), "c_const_max_abs": float(np.max(np.abs(correction))), "pearson_with_f135_prediction_residual": _corr(correction, residual), "pearson_with_absolute_f135_residual": _corr(correction, np.abs(residual)), "fraction_f135_squared_error_explained_by_c_const": float(1.0 - np.sum((residual - correction) ** 2) / np.sum(residual * residual)) if np.sum(residual * residual) else 0.0}
    matched_plus = _counterfactual(pack, matched, c_const); min_predictions = {split: _predict(minimum_norm, pack, split) for split in ("train", "dev", "holdout")}; min_metrics = _prediction_metrics(pack, min_predictions); min_plus = _counterfactual(pack, minimum_norm, c_const)
    corrected_holdout_residual = pack["oracle"]["holdout"] - f135_predictions["holdout"] - c_const["holdout"]
    null_decomp, null_holdout = _active_oracle_decomposition(pack, basis, corrected_holdout_residual)
    material_dependencies = _material_dependency_report(pack, basis)
    classification = "CORRECTED_A1_FAILURE_NOT_EXPLAINED_BY_LINEAR_IDENTIFIABILITY"
    const_norm = constant_audit["aggregate"]["holdout"]["oracle_contribution_rms_over_holdout_target_std"]; null_norm = null_holdout["normalized_rmse"]
    if matched_plus["a1_gate_pass"]: classification = "CORRECTED_A1_FAILURE_TRAIN_CONSTANT_COVERAGE_SUPPORTED"
    elif min_plus["a1_gate_pass"]: classification = "CORRECTED_A1_FAILURE_REGULARIZATION_BIAS_SUPPORTED"
    elif const_norm >= 0.05 and null_norm >= 0.05: classification = "CORRECTED_A1_FAILURE_MIXED_IDENTIFIABILITY_SUPPORTED"
    elif null_norm >= 0.05: classification = "CORRECTED_A1_FAILURE_ACTIVE_SUBSPACE_NONIDENTIFIABILITY_SUPPORTED"
    return {"schema": "F136_CORRECTED_SHOGI_COVERAGE_IDENTIFIABILITY_V1", "baseline": BASELINE, "corrected_oracle_sha256": basis.oracle_weight_sha256, "feature_name_sha256": _json_sha(basis.names), "corpus": {"counts": COUNTS, "seed": CORPUS_SEED, "identity_sha256": CORPUS_SHA}, "f135_reproduction": {"matched_ridge_scalar_metrics": matched_metrics, "pcg_scalar_metrics": f135_metrics, "pcg_solver": pcg_trace, "action_ranking": ranking, "expected_holdout": F135_HOLDOUT, "expected_action": F135_ACTION, "pass": True}, "exact_oracle_sanity": exact_sanity, "train_design_report": matrix, "train_constant_coverage_audit": constant_audit, "exact_omitted_coverage_signal": residual_diagnostics, "counterfactual_coverage_correction": {"matched_plus_const": matched_plus, "active_minnorm_plus_const": min_plus}, "active_minnorm": {"scalar_metrics": min_metrics, "a1_gate_pass": _gate(min_metrics["holdout"])}, "ridge_bias_diagnostic": _ridge_bias(pack, matched, minimum_norm), "active_row_space_identifiability": null_decomp, "material_pst_dependency": material_dependencies, "secondary_coverage_targets": _coverage_candidates(pack, basis, rows), "classification": classification, "runtime_seconds": time.time() - started}


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args(); result = _run(args.output); args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"); print(json.dumps({"classification": result["classification"], "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))


if __name__ == "__main__": main()
