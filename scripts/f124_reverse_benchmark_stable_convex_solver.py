"""F124: deterministic PCG solver for the exact F123 convex objective."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import _search_probe
    from scripts.f123_reverse_benchmark_identifiability_optimizer_diagnosis import (
        COUNTS,
        FAMILIES,
        FrozenBasis,
        _action_ranking,
        _collect_corpus,
        _collect_fresh_roots,
        _json_sha,
        _matched_ridge,
        _proxy_fit,
        _ranking_summary,
        _scalar_summary,
    )
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import _search_probe
    from f123_reverse_benchmark_identifiability_optimizer_diagnosis import (
        COUNTS,
        FAMILIES,
        FrozenBasis,
        _action_ranking,
        _collect_corpus,
        _collect_fresh_roots,
        _json_sha,
        _matched_ridge,
        _proxy_fit,
        _ranking_summary,
        _scalar_summary,
    )

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


L2 = 1e-6
RESIDUAL_TOLERANCE = 1e-10
MAX_ITERATION_MULTIPLIER = 4

# These values are immutable F122 report references. F124 deliberately does
# not rerun Adam or the random baseline.
F122_REFERENCE = {
    "western_chess": {
        "random_baseline": {"holdout_rmse": 15533.7819, "holdout_normalized_rmse": 19.9999, "r2": -398.9978, "pearson": -0.0084},
        "adam_2k": {"holdout_rmse": 54.1045, "holdout_normalized_rmse": 0.0697, "r2": 0.9951, "pearson": 0.9977, "action_top1": 0.9688, "action_pairwise": 0.9838, "action_mean_regret_normalized": 0.0001},
    },
    "standard_shogi": {
        "random_baseline": {"holdout_rmse": 89908.5214, "holdout_normalized_rmse": 20.9805, "r2": -439.1820, "pearson": 0.0522},
        "adam_2k": {"holdout_rmse": 354.7130, "holdout_normalized_rmse": 0.0828, "r2": 0.9931, "pearson": 0.9967, "action_top1": 0.9414, "action_pairwise": 0.9546, "action_mean_regret_normalized": 0.0},
    },
}


def _normal_system(pack: dict) -> tuple[np.ndarray, np.ndarray]:
    design = pack["design"]["train"]
    target = pack["target"]["train"]
    hessian = design.T @ design / len(design)
    hessian[:-1, :-1] += L2 * np.eye(hessian.shape[0] - 1)
    rhs = design.T @ target / len(design)
    return hessian, rhs


def _pcg(pack: dict) -> tuple[np.ndarray, dict]:
    """Solve H theta=b with zero-init Jacobi-preconditioned CG."""
    hessian, rhs = _normal_system(pack)
    diagonal = np.diag(hessian)
    if not np.all(np.isfinite(diagonal)) or not np.all(diagonal > 0.0):
        raise ValueError("PCG_JACOBI_DIAGONAL_NOT_FINITE_POSITIVE")
    inverse_diagonal = 1.0 / diagonal
    parameter_count = len(rhs)
    theta = np.zeros(parameter_count, dtype=np.float64)
    residual = rhs.copy()
    rhs_norm = float(np.linalg.norm(rhs))
    denominator = max(rhs_norm, 1e-30)
    relative_residual = float(np.linalg.norm(residual) / denominator)
    iterations = 0
    preconditioned = inverse_diagonal * residual
    direction = preconditioned.copy()
    rz = float(residual @ preconditioned)
    for iteration in range(1, MAX_ITERATION_MULTIPLIER * parameter_count + 1):
        if relative_residual <= RESIDUAL_TOLERANCE:
            break
        curvature = float(direction @ (hessian @ direction))
        if not np.isfinite(curvature) or curvature <= 0.0:
            raise ValueError("PCG_NON_POSITIVE_CURVATURE")
        step = rz / curvature
        theta += step * direction
        residual -= step * (hessian @ direction)
        iterations = iteration
        relative_residual = float(np.linalg.norm(residual) / denominator)
        if relative_residual <= RESIDUAL_TOLERANCE:
            break
        next_preconditioned = inverse_diagonal * residual
        next_rz = float(residual @ next_preconditioned)
        beta = next_rz / rz
        direction = next_preconditioned + beta * direction
        preconditioned = next_preconditioned
        rz = next_rz
    return theta, {
        "iterations": iterations,
        "maximum_iterations": MAX_ITERATION_MULTIPLIER * parameter_count,
        "relative_residual": relative_residual,
        "diagonal_min": float(np.min(diagonal)),
        "diagonal_max": float(np.max(diagonal)),
    }


def _prediction_difference(model: np.ndarray, reference: np.ndarray, pack: dict) -> dict:
    result = {}
    holdout_std = float(np.std(pack["oracle"]["holdout"])) or 1.0
    for split in ("train", "dev", "holdout"):
        delta = pack["target_std"] * (pack["design"][split] @ (model - reference))
        rmse = float(np.sqrt(np.mean(delta * delta)))
        result[split] = {
            "rmse_oracle_units": rmse,
            "normalized_by_holdout_oracle_std": rmse / holdout_std,
        }
    return result


def _proxy_fit_pcg(model: np.ndarray, pack: dict) -> dict:
    fit = _proxy_fit(model, pack)
    fit["pcg_model"] = fit.pop("adam_model")
    return fit


def _diagnose_family(family: str, corpus_seed: int, root_seed: int) -> dict:
    builder = build_western_chess_ruleset if family == "western_chess" else build_standard_shogi_ruleset
    compiled = compile_semantic_ruleset(builder())
    basis = FrozenBasis(family, compiled)
    rows = _collect_corpus(family, compiled, basis, corpus_seed, set())
    # Importing the F123 preparation helper keeps the exact frozen normalization
    # and active-feature selection without rerunning any optimizer.
    try:
        from scripts.f123_reverse_benchmark_identifiability_optimizer_diagnosis import _prepare
    except ModuleNotFoundError:
        from f123_reverse_benchmark_identifiability_optimizer_diagnosis import _prepare
    pack = _prepare(rows, basis)
    matched = _matched_ridge(pack)
    pcg, trace = _pcg(pack)
    scalar = {
        "F123_matched_ridge_1e-6": _scalar_summary(matched, pack),
        "F124_PCG_DIRECT_LEARNER": _scalar_summary(pcg, pack),
    }
    objective_pcg = float(0.5 * np.mean((pack["design"]["train"] @ pcg - pack["target"]["train"]) ** 2) + 0.5 * L2 * np.sum(pcg[:-1] ** 2))
    objective_matched = float(0.5 * np.mean((pack["design"]["train"] @ matched - pack["target"]["train"]) ** 2) + 0.5 * L2 * np.sum(matched[:-1] ** 2))
    hessian, rhs = _normal_system(pack)
    residual = rhs - hessian @ pcg
    numerical = {
        "finite_parameters": bool(np.all(np.isfinite(pcg))),
        "relative_linear_system_residual": float(np.linalg.norm(residual) / max(np.linalg.norm(rhs), 1e-30)),
        "objective_pcg": objective_pcg,
        "objective_matched": objective_matched,
        "objective_excess": objective_pcg - objective_matched,
        "parameter_l2_distance_to_matched": float(np.linalg.norm(pcg - matched)),
        "prediction_difference_vs_matched": _prediction_difference(pcg, matched, pack),
    }
    numerical["gate_pass"] = bool(
        numerical["finite_parameters"]
        and numerical["relative_linear_system_residual"] <= 1e-10
        and numerical["objective_excess"] <= 1e-10
        and numerical["prediction_difference_vs_matched"]["holdout"]["normalized_by_holdout_oracle_std"] <= 1e-8
    )
    scalar_gate = {
        "holdout_normalized_rmse": scalar["F124_PCG_DIRECT_LEARNER"]["holdout"]["normalized_rmse"] <= 0.05,
        "holdout_r2": scalar["F124_PCG_DIRECT_LEARNER"]["holdout"]["r2"] >= 0.99,
        "holdout_pearson": scalar["F124_PCG_DIRECT_LEARNER"]["holdout"]["pearson"] >= 0.995,
    }
    scalar_gate["pass"] = all(scalar_gate.values())
    roots = _collect_fresh_roots(family, compiled, basis, root_seed, {row["identity"] for row in rows}, 256)
    fit = _proxy_fit_pcg(pcg, pack)
    holdout_std = float(np.std(pack["oracle"]["holdout"])) or 1.0
    ranking = _ranking_summary(_action_ranking(roots, basis, fit, "pcg"), holdout_std)
    action_gate = {
        "top1": ranking["top1_agreement"] >= 0.90,
        "pairwise": ranking["pairwise_ordering_agreement"] >= 0.95,
        "mean_regret": ranking["mean_regret_normalized"] <= 0.05,
    }
    action_gate["pass"] = all(action_gate.values())
    search = _search_probe(roots[:64], basis, fit, "pcg")
    if not numerical["gate_pass"]:
        classification = "KNOWN_EVALUATOR_STABLE_SOLVER_FAILURE"
    elif not (scalar_gate["pass"] and action_gate["pass"]):
        classification = "KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_STILL_FAILS"
    else:
        classification = "KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_PASSES"
    return {
        "basis": {"feature_count": len(basis.names), "oracle_weight_sha256": basis.oracle_weight_sha256},
        "corpus": {"rows": len(rows), "counts": COUNTS, "corpus_seed": corpus_seed, "identity_sha256": _json_sha([row["identity"] for row in rows])},
        "solver": {"name": "PCG_DIRECT_LEARNER", "objective": "mean_squared_normalized_loss_plus_1e-6_weight_l2_excluding_intercept", "initialization": "zero", "preconditioner": "jacobi", **trace},
        "scalar_metrics": scalar,
        "numerical": numerical,
        "scalar_gate": scalar_gate,
        "action_ranking": {"root_seed": root_seed, "roots": 256, "results": ranking, "gate": action_gate},
        "search_recovery": {"roots": 64, "budget_nodes": 2000, "max_depth": 12, "results": search},
        "reference_models": F122_REFERENCE[family],
        "classification": classification,
    }


def run() -> dict:
    result = {
        "schema": "F124_REVERSE_BENCHMARK_STABLE_CONVEX_SOLVER_V1",
        "baseline": "341e1a895c8b57321086819ba9095634ced3b7ea",
        "rulesets": {family: _diagnose_family(family, corpus_seed, root_seed) for family, corpus_seed, _, root_seed in FAMILIES},
    }
    classifications = [value["classification"] for value in result["rulesets"].values()]
    result["classification"] = "KNOWN_EVALUATOR_STABLE_SOLVER_FAILURE" if "KNOWN_EVALUATOR_STABLE_SOLVER_FAILURE" in classifications else ("KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_PASSES" if all(value == "KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_PASSES" for value in classifications) else "KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_STILL_FAILS")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.time()
    result = run()
    result["runtime_seconds"] = time.time() - started
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"classification": result["classification"], "rulesets": {family: value["classification"] for family, value in result["rulesets"].items()}, "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))


if __name__ == "__main__":
    main()
