"""F123: isolate F122 regularization, convergence, and identifiability effects.

This benchmark reuses F122's frozen basis and deterministic corpus generator.
It is diagnostic-only and does not touch production evaluator or search code.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from scripts.f122_reverse_benchmark_known_evaluator_system_identification import (
    COUNTS,
    FrozenBasis,
    _action_ranking,
    _collect_corpus,
    _collect_fresh_roots,
    _json_sha,
    _ranking_summary,
    _scalar_metrics,
)
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


FAMILIES = (
    ("western_chess", 1220101, 1220111, 1220121),
    ("standard_shogi", 1220201, 1220211, 1220221),
)
ADAM_L2 = 1e-6
HISTORICAL_RIDGE = 1e-8
CHECKPOINTS_2K = (0, 10, 100, 500, 1000, 2000)
CHECKPOINTS_20K = (0, 10, 100, 500, 1000, 2000, 5000, 10000, 20000)


def _split_arrays(rows: list[dict], basis: FrozenBasis) -> dict:
    x = np.asarray([row["features"] for row in rows], dtype=np.float64)
    y = np.asarray([row["oracle"] for row in rows], dtype=np.float64)
    train_end = COUNTS["train"]
    dev_end = train_end + COUNTS["dev"]
    return {
        "raw": {"train": x[:train_end], "dev": x[train_end:dev_end], "holdout": x[dev_end:]},
        "oracle": {"train": y[:train_end], "dev": y[train_end:dev_end], "holdout": y[dev_end:]},
        "feature_count": len(basis.names),
    }


def _prepare(rows: list[dict], basis: FrozenBasis) -> dict:
    split = _split_arrays(rows, basis)
    train_x = split["raw"]["train"]
    train_y = split["oracle"]["train"]
    mean = train_x.mean(axis=0)
    scale = train_x.std(axis=0)
    active = scale > 1e-12
    safe_scale = np.where(active, scale, 1.0)
    target_mean = float(train_y.mean())
    target_std = float(train_y.std()) or 1.0
    normalized = {
        key: (value - mean) / safe_scale
        for key, value in split["raw"].items()
    }
    z = {key: value[:, active] for key, value in normalized.items()}
    design = {key: np.column_stack([value, np.ones(len(value))]) for key, value in z.items()}
    normalized_target = {key: (value - target_mean) / target_std for key, value in split["oracle"].items()}
    train_design = design["train"]
    left_vectors, singular_values, vt = np.linalg.svd(train_design, full_matrices=False)
    tol = np.finfo(np.float64).eps * max(train_design.shape) * float(singular_values[0])
    retained = singular_values > tol
    return {
        **split,
        "feature_mean": mean,
        "feature_scale": safe_scale,
        "active": active,
        "constant_feature_names": [name for name, keep in zip(basis.names, active) if not keep],
        "target_mean": target_mean,
        "target_std": target_std,
        "normalized": normalized,
        "design": design,
        "target": normalized_target,
        "singular_values": singular_values,
        "left_vectors": left_vectors,
        "vt": vt,
        "rank_tol": tol,
        "retained": retained,
    }


def _predict(model: np.ndarray, pack: dict, split: str) -> np.ndarray:
    return pack["target_mean"] + pack["target_std"] * (pack["design"][split] @ model)


def _scalar_summary(model: np.ndarray, pack: dict) -> dict:
    normalizer = float(np.std(pack["oracle"]["holdout"])) or 1.0
    result = {
        "normalization_reference": "holdout_oracle_std",
        "normalization_reference_std": normalizer,
    }
    result.update({
        split: _scalar_metrics(pack["oracle"][split], _predict(model, pack, split), normalizer)
        for split in ("train", "dev", "holdout")
    })
    return result


def _objective(model: np.ndarray, design: np.ndarray, target: np.ndarray) -> float:
    residual = design @ model - target
    return float(0.5 * np.mean(residual * residual) + 0.5 * ADAM_L2 * np.sum(model[:-1] * model[:-1]))


def _gradient(model: np.ndarray, design: np.ndarray, target: np.ndarray) -> np.ndarray:
    gradient = design.T @ (design @ model - target) / len(design)
    gradient[:-1] += ADAM_L2 * model[:-1]
    return gradient


def _checkpoint(model: np.ndarray, pack: dict) -> dict:
    design = pack["design"]["train"]
    target = pack["target"]["train"]
    residual = design @ model - target
    return {
        "training_mse_normalized": float(np.mean(residual * residual)),
        "objective": _objective(model, design, target),
        "gradient_l2": float(np.linalg.norm(_gradient(model, design, target))),
        "parameter_l2": float(np.linalg.norm(model)),
        "dev_rmse_oracle_units": float(np.sqrt(np.mean((_predict(model, pack, "dev") - pack["oracle"]["dev"]) ** 2))),
        "holdout_rmse_oracle_units": float(np.sqrt(np.mean((_predict(model, pack, "holdout") - pack["oracle"]["holdout"]) ** 2))),
    }


def _adam(pack: dict, seed: int, steps: int, zero_init: bool) -> tuple[np.ndarray, dict]:
    dimension = pack["design"]["train"].shape[1]
    rng = np.random.default_rng(seed)
    model = np.zeros(dimension, dtype=np.float64) if zero_init else rng.normal(0.0, 0.01, size=dimension)
    first = _checkpoint(model, pack)
    checkpoints = {0: first}
    moment = np.zeros_like(model)
    velocity = np.zeros_like(model)
    wanted = set(CHECKPOINTS_20K if steps > 2000 else CHECKPOINTS_2K)
    for step in range(1, steps + 1):
        gradient = _gradient(model, pack["design"]["train"], pack["target"]["train"])
        moment = 0.9 * moment + 0.1 * gradient
        velocity = 0.999 * velocity + 0.001 * (gradient * gradient)
        mhat = moment / (1.0 - 0.9 ** step)
        vhat = velocity / (1.0 - 0.999 ** step)
        model -= 0.01 * mhat / (np.sqrt(vhat) + 1e-8)
        if step in wanted:
            checkpoints[step] = _checkpoint(model, pack)
    return model, {str(step): checkpoints[step] for step in sorted(checkpoints)}


def _historical_closed(pack: dict) -> np.ndarray:
    design = pack["design"]["train"]
    gram = design.T @ design
    gram[:-1, :-1] += HISTORICAL_RIDGE * np.eye(gram.shape[1] - 1)
    return np.linalg.solve(gram, design.T @ pack["target"]["train"])


def _matched_ridge(pack: dict) -> np.ndarray:
    design = pack["design"]["train"]
    gram = design.T @ design / len(design)
    gram[:-1, :-1] += ADAM_L2 * np.eye(gram.shape[1] - 1)
    rhs = design.T @ pack["target"]["train"] / len(design)
    return np.linalg.solve(gram, rhs)


def _minimum_norm(pack: dict) -> np.ndarray:
    singular = pack["singular_values"]
    retained = pack["retained"]
    left_vectors = pack["left_vectors"]
    vt = pack["vt"]
    projected_target = left_vectors.T @ pack["target"]["train"]
    inverse = np.zeros_like(singular)
    inverse[retained] = 1.0 / singular[retained]
    return vt.T @ (inverse * projected_target)


def _matrix_report(pack: dict, basis: FrozenBasis) -> dict:
    singular = pack["singular_values"]
    retained = pack["retained"]
    spectrum = singular[retained]
    return {
        "raw_feature_count": len(basis.names),
        "active_feature_count": int(pack["active"].sum()),
        "constant_train_feature_count": len(pack["constant_feature_names"]),
        "matrix_dimensions": list(pack["design"]["train"].shape),
        "numerical_rank": int(retained.sum()),
        "nullity": int(len(singular) - retained.sum()),
        "singular_value_max": float(singular[0]),
        "smallest_retained_nonzero_singular_value": float(spectrum[-1]) if len(spectrum) else 0.0,
        "nonzero_spectrum_condition_number": float(spectrum[0] / spectrum[-1]) if len(spectrum) else None,
        "effective_ranks": {str(threshold): int(np.sum(singular > threshold * singular[0])) for threshold in (1e-6, 1e-8, 1e-10)},
        "rank_tolerance": float(pack["rank_tol"]),
    }


def _material_dependency_report(pack: dict, basis: FrozenBasis) -> dict:
    indices = {name: index for index, name in enumerate(basis.names)}
    report = {}
    for type_id in basis.material_types:
        material = indices[f"material_diff:{type_id}"]
        occupancy = [indices[name] for name in basis.names if name.startswith(f"occupancy_diff:{type_id}:")]
        report[type_id] = {}
        for split in ("train", "dev", "holdout"):
            delta = pack["raw"][split][:, material] - pack["raw"][split][:, occupancy].sum(axis=1)
            report[type_id][split] = {"max_abs_error": float(np.max(np.abs(delta))), "holds": bool(np.allclose(delta, 0.0, atol=1e-12, rtol=0.0))}
    return report


def _coverage_report(pack: dict, basis: FrozenBasis) -> dict:
    train = pack["raw"]["train"]
    holdout_std = float(np.std(pack["oracle"]["holdout"])) or 1.0
    entries = {}
    for index, name in enumerate(pack["constant_feature_names"]):
        feature_index = basis.names.index(name)
        train_value = float(train[0, feature_index])
        entries[name] = {"train_value": train_value, "oracle_coefficient": basis.weights[feature_index]}
        for split in ("dev", "holdout"):
            delta = pack["raw"][split][:, feature_index] - train_value
            contribution = basis.weights[feature_index] * delta
            entries[name][split] = {
                "remains_constant": bool(np.allclose(delta, 0.0, atol=1e-12, rtol=0.0)),
                "variance": float(np.var(pack["raw"][split][:, feature_index])),
                "max_abs_deviation": float(np.max(np.abs(delta))),
                "contribution_rms": float(np.sqrt(np.mean(contribution * contribution))),
                "max_abs_contribution": float(np.max(np.abs(contribution))),
            }
    aggregate = {}
    for split in ("dev", "holdout"):
        contributions = []
        for name, row in entries.items():
            feature_index = basis.names.index(name)
            train_value = row["train_value"]
            contributions.append((pack["raw"][split][:, feature_index] - train_value) * row["oracle_coefficient"])
        matrix = np.column_stack(contributions) if contributions else np.zeros((len(pack["raw"][split]), 0))
        total = matrix.sum(axis=1) if matrix.shape[1] else np.zeros(len(pack["raw"][split]))
        aggregate[split] = {
            "train_constant_features_becoming_variable": int(sum(not row[split]["remains_constant"] for row in entries.values())),
            "oracle_contribution_rms": float(np.sqrt(np.mean(total * total))),
            "oracle_contribution_max_abs": float(np.max(np.abs(total))) if len(total) else 0.0,
            "oracle_contribution_rms_over_holdout_target_std": float(np.sqrt(np.mean(total * total)) / holdout_std),
        }
    return {"features": entries, "aggregate": aggregate}


def _matched_distance(model: np.ndarray, matched: np.ndarray, pack: dict) -> dict:
    delta = model - matched
    result = {"parameter_l2_distance": float(np.linalg.norm(delta))}
    for split in ("train", "dev", "holdout"):
        prediction_delta = pack["target_std"] * (pack["design"][split] @ delta)
        result[f"prediction_delta_rmse_{split}_oracle_units"] = float(np.sqrt(np.mean(prediction_delta * prediction_delta)))
    result["objective_excess"] = _objective(model, pack["design"]["train"], pack["target"]["train"]) - _objective(matched, pack["design"]["train"], pack["target"]["train"])
    return result


def _null_decomposition(model: np.ndarray, matched: np.ndarray, pack: dict) -> dict:
    delta = model - matched
    vt = pack["vt"]
    retained = pack["retained"]
    row_component = vt[retained].T @ (vt[retained] @ delta) if np.any(retained) else np.zeros_like(delta)
    null_component = delta - row_component
    result = {
        "row_space_delta_norm": float(np.linalg.norm(row_component)),
        "null_space_delta_norm": float(np.linalg.norm(null_component)),
        "null_space_fraction_of_squared_parameter_delta": float(np.sum(null_component * null_component) / np.sum(delta * delta)) if np.sum(delta * delta) else 0.0,
    }
    for split in ("train", "dev", "holdout"):
        contribution = pack["target_std"] * (pack["design"][split] @ null_component)
        result[f"null_prediction_{split}"] = {
            "rmse_oracle_units": float(np.sqrt(np.mean(contribution * contribution))),
            "max_abs_oracle_units": float(np.max(np.abs(contribution))),
        }
    return result


def _proxy_fit(model: np.ndarray, pack: dict) -> dict:
    return {
        "mean": pack["feature_mean"],
        "scale": pack["feature_scale"],
        "active": pack["active"],
        "target_mean": pack["target_mean"],
        "target_std": pack["target_std"],
        "adam_model": model,
    }


def _diagnose_family(family: str, corpus_seed: int, init_seed: int, root_seed: int) -> dict:
    builder = build_western_chess_ruleset if family == "western_chess" else build_standard_shogi_ruleset
    compiled = compile_semantic_ruleset(builder())
    basis = FrozenBasis(family, compiled)
    rows = _collect_corpus(family, compiled, basis, corpus_seed, set())
    pack = _prepare(rows, basis)
    matched = _matched_ridge(pack)
    historical = _historical_closed(pack)
    minimum_norm = _minimum_norm(pack)
    adam_random_2k, trace_random_2k = _adam(pack, init_seed, 2000, False)
    adam_zero_2k, trace_zero_2k = _adam(pack, init_seed, 2000, True)
    adam_random_20k, trace_random_20k = _adam(pack, init_seed, 20000, False)
    models = {
        "matched_ridge_1e-6": matched,
        "historical_closed_form": historical,
        "min_norm": minimum_norm,
        "F122_RANDOM_2K": adam_random_2k,
        "ZERO_INIT_2K": adam_zero_2k,
        "F122_RANDOM_20K": adam_random_20k,
    }
    scalars = {name: _scalar_summary(model, pack) for name, model in models.items()}
    gate = lambda metrics: metrics["holdout"]["normalized_rmse"] <= 0.05 and metrics["holdout"]["r2"] >= 0.99 and metrics["holdout"]["pearson"] >= 0.995
    scalar_gates = {name: gate(metrics) for name, metrics in scalars.items()}
    coverage = _coverage_report(pack, basis)
    holdout_std = float(np.std(pack["oracle"]["holdout"])) or 1.0
    coverage_limit = coverage["aggregate"]["holdout"]["oracle_contribution_rms_over_holdout_target_std"] >= 0.05
    classifications = []
    if not scalar_gates["matched_ridge_1e-6"] and (scalar_gates["min_norm"] or scalar_gates["historical_closed_form"]):
        classifications.append("F122_FAILURE_REGULARIZATION_BIAS_SUPPORTED")
    if scalar_gates["matched_ridge_1e-6"] and scalar_gates["F122_RANDOM_20K"] and not scalar_gates["F122_RANDOM_2K"]:
        classifications.append("F122_FAILURE_INSUFFICIENT_ADAM_CONVERGENCE_SUPPORTED")
    if scalar_gates["matched_ridge_1e-6"] and scalar_gates["ZERO_INIT_2K"] and not scalar_gates["F122_RANDOM_2K"]:
        random_null = _null_decomposition(adam_random_2k, matched, pack)["null_space_delta_norm"]
        zero_null = _null_decomposition(adam_zero_2k, matched, pack)["null_space_delta_norm"]
        if zero_null < random_null:
            classifications.append("F122_FAILURE_INITIALIZATION_NULLSPACE_TRANSIENT_SUPPORTED")
    if scalar_gates["matched_ridge_1e-6"] and not scalar_gates["F122_RANDOM_20K"]:
        classifications.append("F122_ADAM_OPTIMIZER_DYNAMICS_FAILURE_SUPPORTED")
    if coverage_limit:
        classifications.append("F122_TRAIN_COVERAGE_IDENTIFIABILITY_LIMIT_SUPPORTED")
    if not classifications:
        classifications.append("F122_SYSTEM_IDENTIFICATION_FAILURE_NOT_YET_ISOLATED")
    action = {}
    if scalar_gates["ZERO_INIT_2K"] or scalar_gates["F122_RANDOM_20K"]:
        roots = _collect_fresh_roots(family, compiled, basis, root_seed, {row["identity"] for row in rows}, 256)
        for name in ("ZERO_INIT_2K", "F122_RANDOM_20K"):
            if scalar_gates[name]:
                ranking = _action_ranking(roots, basis, _proxy_fit(models[name], pack), "adam")
                action[name] = {"root_seed": root_seed, "roots": 256, **_ranking_summary(ranking, holdout_std)}
    return {
        "basis": {"feature_count": len(basis.names), "oracle_weight_sha256": basis.oracle_weight_sha256},
        "corpus": {"rows": len(rows), "counts": COUNTS, "corpus_seed": corpus_seed, "identity_sha256": _json_sha([row["identity"] for row in rows])},
        "matrix": _matrix_report(pack, basis),
        "material_dependencies": _material_dependency_report(pack, basis),
        "coverage": coverage,
        "scalar_metrics": scalars,
        "scalar_gates": scalar_gates,
        "adam_traces": {"F122_RANDOM_2K": trace_random_2k, "ZERO_INIT_2K": trace_zero_2k, "F122_RANDOM_20K": trace_random_20k},
        "matched_distance": {name: _matched_distance(model, matched, pack) for name, model in models.items() if name != "matched_ridge_1e-6"},
        "null_decomposition": {name: _null_decomposition(model, matched, pack) for name, model in models.items() if name != "matched_ridge_1e-6"},
        "action_ranking_conditional": action,
        "classification": classifications,
        "oracle_holdout_std": holdout_std,
    }


def run() -> dict:
    return {
        "schema": "F123_REVERSE_BENCHMARK_IDENTIFIABILITY_OPTIMIZER_DIAGNOSIS_V1",
        "baseline": "4bce37cccad7d0891dd90888f28a88c4b53624dd",
        "rulesets": {family: _diagnose_family(family, corpus_seed, init_seed, root_seed) for family, corpus_seed, init_seed, root_seed in FAMILIES},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    result = run()
    result["runtime_seconds"] = time.time() - started
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"classification": {family: value["classification"] for family, value in result["rulesets"].items()}, "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))


if __name__ == "__main__":
    main()
