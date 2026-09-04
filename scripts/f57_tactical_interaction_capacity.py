"""F57 offline generic tactical-interaction capacity gate.

The interaction representation is deliberately kept out of Native.  This
stage tests whether semantic attacked/defended/hanging counts can improve a
frozen v2 evaluator on fresh, teacher-labelled data before paying another
Native evaluator cost.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from f50_generic_learnable_evaluator import _ruleset  # noqa: E402
from f54_direct_capacity_and_gradient_geometry_diagnosis import (  # noqa: E402
    _agreement,
    _metrics,
    _parent,
    _parallel_search,
    _record_dict,
    _session,
    _static_row,
)
from f55_well_posed_linear_capacity_oracle import (  # noqa: E402
    _conditioning,
    _cv_select_alpha,
    _training_scale,
)
from generic_chess.learning.diagnostics import generate_diagnostic_corpus  # noqa: E402
from generic_chess.learning.features import (  # noqa: E402
    TACTICAL_INTERACTION_FEATURE_NAMES,
    tactical_interaction_features,
)
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402


OUT = ROOT / ".generic_chess_flow" / "f57-tactical-interaction-capacity"
CORPUS_COUNT = 192
TRAIN_COUNT = 128
VALIDATION_COUNT = 64
OPENING_COUNT = 32
CORPUS_MIN_PLIES = 8
CORPUS_MAX_PLIES = 40
CORPUS_SEEDS = {
    "A_CANONICAL_WESTERN_CHESS": 570101,
    "B_CANONICAL_STANDARD_SHOGI": 570201,
}
TEACHER_BUDGETS = (40000, 80000)
MATE_BAND_NATIVE_THRESHOLD = 90_000_000
CV_FOLDS = 4
VALUE_IMPROVEMENT_THRESHOLD = 0.10


def _generate_corpus(label, compiled):
    seed = CORPUS_SEEDS[label]
    openings = generate_arena_openings(
        compiled, count=OPENING_COUNT, seed=seed, min_plies=2, max_plies=6
    )
    corpus = generate_diagnostic_corpus(
        compiled, openings, count=CORPUS_COUNT, seed=seed + 1,
        min_plies=CORPUS_MIN_PLIES, max_plies=CORPUS_MAX_PLIES,
    )
    payload = corpus.to_dict()
    return payload, {
        "corpus_id": corpus.corpus_id,
        "source_opening_corpus_id": openings.corpus_id,
        "records": [_record_dict(position) for position in corpus.positions],
    }


def _is_mate_band(row):
    return abs(int(row["native_score"])) > MATE_BAND_NATIVE_THRESHOLD


def _type_ids(compiled):
    return tuple(sorted(getattr(compiled.support, "type_metadata", {})))


def _interaction_vector(compiled, record, type_ids):
    session = _session(compiled, record)
    values = tactical_interaction_features(session.state.position, compiled, type_ids)
    return np.asarray(
        [values[f"{feature}:{owner}:{type_id}"]
         for feature in TACTICAL_INTERACTION_FEATURE_NAMES
         for owner in (0, 1)
         for type_id in type_ids],
        dtype=float,
    )


def _run_label(label):
    compiled, native, _profile = _ruleset(label)
    parent = _parent(label)
    corpus_payload, corpus_info = _generate_corpus(label, compiled)
    records = corpus_info["records"]
    train_records = records[:TRAIN_COUNT]
    validation_records = records[TRAIN_COUNT:]
    type_ids = _type_ids(compiled)
    x = np.vstack([_interaction_vector(compiled, record, type_ids) for record in records])
    base_rows = [_static_row(compiled, native, parent, record) for record in records]
    teacher = {
        str(nodes): _parallel_search(compiled, native, parent, records, nodes)
        for nodes in TEACHER_BUDGETS
    }
    stable = [a["action_key"] == b["action_key"] for a, b in zip(teacher["40000"], teacher["80000"])]
    teacher_80k = teacher["80000"]
    train_teacher = teacher_80k[:TRAIN_COUNT]
    validation_teacher = teacher_80k[TRAIN_COUNT:]
    stable_train = [i for i in range(TRAIN_COUNT) if stable[i]]
    stable_validation = [i for i in range(VALIDATION_COUNT) if stable[TRAIN_COUNT + i]]
    ordinary_train = [i for i in stable_train if not _is_mate_band(train_teacher[i])]
    ordinary_validation = [i for i in stable_validation if not _is_mate_band(validation_teacher[i])]
    y_train = np.asarray([row["owner0_value"] for row in train_teacher], dtype=float)
    y_validation = np.asarray([row["owner0_value"] for row in validation_teacher], dtype=float)
    current_train = np.asarray([row["static_value"] for row in base_rows[:TRAIN_COUNT]], dtype=float)
    current_validation = np.asarray([row["static_value"] for row in base_rows[TRAIN_COUNT:]], dtype=float)
    fit_x = x[ordinary_train]
    fit_residual = (y_train - current_train)[ordinary_train]
    active, scale, _std = _training_scale(fit_x)
    fit_scaled = fit_x[:, active] / scale
    selected_alpha, cv_scores = _cv_select_alpha(fit_scaled, fit_residual)
    from f55_well_posed_linear_capacity_oracle import _ridge_svd
    theta = _ridge_svd(fit_scaled, fit_residual, selected_alpha)
    beta = np.zeros(x.shape[1], dtype=float)
    beta[active] = theta / scale
    parent_metrics = _metrics(current_validation[ordinary_validation], y_validation[ordinary_validation])
    child_values = current_validation + x[TRAIN_COUNT:] @ beta
    child_metrics = _metrics(child_values[ordinary_validation], y_validation[ordinary_validation])
    improvement = ((parent_metrics["mse"] - child_metrics["mse"]) / parent_metrics["mse"]
                   if parent_metrics["mse"] else 0.0)
    return {
        "label": label,
        "parent_checkpoint_id": parent.checkpoint_id,
        "corpus": {
            "schema_version": corpus_payload["schema_version"],
            "corpus_id": corpus_info["corpus_id"],
            "source_opening_corpus_id": corpus_info["source_opening_corpus_id"],
            "seed": corpus_payload["seed"],
            "count": len(records),
            "split": {"development": [0, TRAIN_COUNT], "validation": [TRAIN_COUNT, CORPUS_COUNT]},
            "development_position_keys_sha256": stable_sha256([r["position_key"] for r in train_records]),
            "validation_position_keys_sha256": stable_sha256([r["position_key"] for r in validation_records]),
            "evaluator_invoked_for_selection": False,
        },
        "teacher_stability": {
            "40k_vs_80k": _agreement(teacher["40000"], teacher["80000"]),
            "stable_count": sum(stable), "stable_rate": sum(stable) / len(stable),
            "stable_development_count": len(stable_train),
            "stable_validation_count": len(stable_validation),
        },
        "target_partition": {
            "native_static_score_band": [-MATE_BAND_NATIVE_THRESHOLD, MATE_BAND_NATIVE_THRESHOLD],
            "development_ordinary_non_mate_count": len([i for i in range(TRAIN_COUNT) if not _is_mate_band(train_teacher[i])]),
            "validation_ordinary_non_mate_count": len([i for i in range(VALIDATION_COUNT) if not _is_mate_band(validation_teacher[i])]),
            "stable_development_ordinary_non_mate_count": len(ordinary_train),
            "stable_validation_ordinary_non_mate_count": len(ordinary_validation),
            "development_mate_band_count": sum(_is_mate_band(row) for row in train_teacher),
            "validation_mate_band_count": sum(_is_mate_band(row) for row in validation_teacher),
        },
        "interaction_parameterization": {
            "feature_order": list(TACTICAL_INTERACTION_FEATURE_NAMES),
            "owner_axis": [0, 1], "type_count": len(type_ids),
            "parameter_count": int(x.shape[1]),
            "active_parameter_count": int(np.count_nonzero(active)),
            "zero_variance_parameter_count": int(np.count_nonzero(~active)),
            "conditioning_before_scaling": _conditioning(fit_x[:, active]),
            "conditioning_after_scaling": _conditioning(fit_scaled),
            "cv_folds": CV_FOLDS, "selected_alpha": selected_alpha,
            "cv_scores": cv_scores,
            "coefficient_l2": float(np.linalg.norm(beta)),
        },
        "value_capacity": {
            "parent": parent_metrics,
            "interaction_child": child_metrics,
            "improvement_fraction": improvement,
            "capacity_supported": improvement >= VALUE_IMPROVEMENT_THRESHOLD,
        },
        "native_support_entered": False,
        "classification": "PENDING_REVIEW",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--unused-validation-nodes", type=int, default=2000)
    parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    results = [_run_label(label) for label in CORPUS_SEEDS]
    by_ruleset = {
        result["label"]: (
            "TACTICAL_INTERACTION_CAPACITY_SUPPORTED"
            if result["value_capacity"]["capacity_supported"]
            else "TACTICAL_INTERACTION_CAPACITY_NOT_SUPPORTED"
        )
        for result in results
    }
    distinct = set(by_ruleset.values())
    classification = next(iter(distinct)) if len(distinct) == 1 else "MIXED_RULESET_OUTCOME"
    for result in results:
        result["classification"] = by_ruleset[result["label"]]
    payload = {
        "work_order": "GENERICCHESS-F57-GENERIC-TACTICAL-INTERACTION-CAPACITY",
        "corpus_count": CORPUS_COUNT, "split": {"development": TRAIN_COUNT, "validation": VALIDATION_COUNT},
        "teacher_budgets": TEACHER_BUDGETS, "classification": classification,
        "classification_by_ruleset": by_ruleset,
        "results": results, "wall_seconds": time.perf_counter() - started,
    }
    (OUT / "f57_results.json").write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "work_order": payload["work_order"], "classification": classification,
        "classification_by_ruleset": by_ruleset,
        "wall_seconds": payload["wall_seconds"],
        "results": [{"label": r["label"], "corpus_id": r["corpus"]["corpus_id"],
                     "teacher_stability": r["teacher_stability"],
                     "value_capacity": r["value_capacity"]} for r in results],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
