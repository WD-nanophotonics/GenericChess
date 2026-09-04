"""F58 offline compact nonlinear generic value self-distillation gate."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from f50_generic_learnable_evaluator import _ruleset  # noqa: E402
from f54_direct_capacity_and_gradient_geometry_diagnosis import (  # noqa: E402
    _agreement, _metrics, _parent, _parallel_search, _record_dict, _session, _static_row,
)
from generic_chess.learning.diagnostics import generate_diagnostic_corpus  # noqa: E402
from generic_chess.learning.features import non_anchor_type_ids  # noqa: E402
from generic_chess.learning.nonlinear import (  # noqa: E402
    bounded_value_domain, fit_compact_residual, semantic_state_features,
)
from generic_chess.learning.openings import generate_arena_openings  # noqa: E402
from generic_chess.learning.serialization import stable_sha256  # noqa: E402
from generic_chess.native.semantic import dynamic_features as native_dynamic_features  # noqa: E402
from generic_chess.native.adapter import pack_semantic_search_position  # noqa: E402


OUT = ROOT / ".generic_chess_flow" / "f58-compact-nonlinear-capacity"
DEV_COUNT = 384
VALIDATION_COUNT = 128
CORPUS_COUNT = DEV_COUNT + VALIDATION_COUNT
OPENING_COUNT = 48
SEEDS = {"A_CANONICAL_WESTERN_CHESS": 580101, "B_CANONICAL_STANDARD_SHOGI": 580201}
TEACHER_BUDGETS = (40000, 80000)
MATE_THRESHOLD = 90_000_000
TRAINING_SEEDS = (58011, 58012, 58013)
MODEL_GRID = ((16, 1e-4), (16, 1e-3), (32, 1e-4), (32, 1e-3))


def _corpus(label, compiled):
    seed = SEEDS[label]
    openings = generate_arena_openings(compiled, count=OPENING_COUNT, seed=seed, min_plies=2, max_plies=6)
    corpus = generate_diagnostic_corpus(compiled, openings, count=CORPUS_COUNT, seed=seed + 1, min_plies=8, max_plies=40)
    payload = corpus.to_dict()
    return payload, {"corpus_id": corpus.corpus_id, "source_opening_corpus_id": openings.corpus_id,
                     "records": [_record_dict(position) for position in corpus.positions]}


def _features(compiled, native, record):
    session = _session(compiled, record)
    packed = pack_semantic_search_position(compiled, native, session)
    dynamic = native_dynamic_features(native, packed)
    return semantic_state_features(session.state.position, compiled, dynamic)


def _mate(row):
    return abs(int(row["native_score"])) > MATE_THRESHOLD


def _bounded_error(pred, target, scale):
    return _metrics(bounded_value_domain(pred, scale), bounded_value_domain(target, scale))


def _run(label, *, emit_models=False):
    compiled, native, _profile = _ruleset(label)
    parent = _parent(label)
    payload, info = _corpus(label, compiled)
    records = info["records"]
    x = np.vstack([_features(compiled, native, record) for record in records])
    static = [_static_row(compiled, native, parent, record) for record in records]
    teacher = {str(nodes): _parallel_search(compiled, native, parent, records, nodes) for nodes in TEACHER_BUDGETS}
    stable = [a["action_key"] == b["action_key"] for a, b in zip(teacher["40000"], teacher["80000"])]
    high = teacher["80000"]
    dev_high, val_high = high[:DEV_COUNT], high[DEV_COUNT:]
    dev_static = np.asarray([row["static_value"] for row in static[:DEV_COUNT]], dtype=float)
    val_static = np.asarray([row["static_value"] for row in static[DEV_COUNT:]], dtype=float)
    dev_target = np.asarray([row["owner0_value"] for row in dev_high], dtype=float)
    val_target = np.asarray([row["owner0_value"] for row in val_high], dtype=float)
    stable_dev = [i for i in range(DEV_COUNT) if stable[i] and not _mate(dev_high[i])]
    stable_val = [i for i in range(VALIDATION_COUNT) if stable[DEV_COUNT + i] and not _mate(val_high[i])]
    if len(stable_dev) < 64 or len(stable_val) < 16:
        raise ValueError(f"{label}: insufficient stable ordinary data")
    split = max(16, int(len(stable_dev) * 0.8))
    fit_idx, select_idx = stable_dev[:split], stable_dev[split:]
    candidates = []
    for width, regularization in MODEL_GRID:
        selection = []
        for seed in TRAINING_SEEDS:
            model = fit_compact_residual(
                x[fit_idx], (dev_target - dev_static)[fit_idx],
                width=width, regularization=regularization, seed=seed,
            )
            prediction = dev_static[select_idx] + model.predict(x[select_idx])
            selection.append({"seed": seed, "metrics": _metrics(prediction, dev_target[select_idx])})
        candidates.append({"width": width, "regularization": regularization, "selection": selection,
                           "mean_selection_mse": float(np.mean([item["metrics"]["mse"] for item in selection]))})
    best = min(candidates, key=lambda item: item["mean_selection_mse"])
    final_models = []
    current_type_ids = tuple(sorted(compiled.support.type_metadata))
    legacy = compiled._legacy_compiled
    base_type_ids = tuple(sorted(piece_type.type_id for piece_type in legacy.piece_types))
    hand_type_indices = tuple(current_type_ids.index(type_id) for type_id in base_type_ids)
    for seed in TRAINING_SEEDS:
        model = fit_compact_residual(
            x[stable_dev], (dev_target - dev_static)[stable_dev],
            width=best["width"], regularization=best["regularization"], seed=seed,
        )
        final_models.append(replace(model, hand_type_indices=hand_type_indices))
    parent_metrics = _metrics(val_static[stable_val], val_target[stable_val])
    parent_bounded = _bounded_error(val_static[stable_val], val_target[stable_val], parent.value_scale)
    child_metrics = []
    for model in final_models:
        prediction = val_static + model.predict(x[DEV_COUNT:])
        child_metrics.append({
            "seed": model.seed,
            "metrics": _metrics(prediction[stable_val], val_target[stable_val]),
            "bounded": _bounded_error(prediction[stable_val], val_target[stable_val], parent.value_scale),
        })
    child_mse = np.asarray([item["metrics"]["mse"] for item in child_metrics], dtype=float)
    improvement = (parent_metrics["mse"] - float(np.mean(child_mse))) / parent_metrics["mse"]
    return {
        "label": label, "parent_checkpoint_id": parent.checkpoint_id,
        "corpus": {"schema_version": payload["schema_version"], "corpus_id": info["corpus_id"],
                    "source_opening_corpus_id": info["source_opening_corpus_id"], "seed": payload["seed"],
                    "count": len(records), "split": {"development": [0, DEV_COUNT], "validation": [DEV_COUNT, CORPUS_COUNT]},
                    "development_position_keys_sha256": stable_sha256([r["position_key"] for r in records[:DEV_COUNT]]),
                    "validation_position_keys_sha256": stable_sha256([r["position_key"] for r in records[DEV_COUNT:]]),
                    "evaluator_invoked_for_selection": False},
        "input_dimension": int(x.shape[1]),
        "teacher_stability": {"40k_vs_80k": _agreement(teacher["40000"], teacher["80000"]),
                              "stable_count": sum(stable), "stable_rate": sum(stable) / len(stable),
                              "stable_development_count": sum(stable[:DEV_COUNT]),
                              "stable_validation_count": sum(stable[DEV_COUNT:])},
        "target_partition": {"mate_threshold": MATE_THRESHOLD,
                              "development_mate_band_count": sum(_mate(row) for row in dev_high),
                              "validation_mate_band_count": sum(_mate(row) for row in val_high),
                              "stable_ordinary_development_count": len(stable_dev),
                              "stable_ordinary_validation_count": len(stable_val)},
        "model_selection": {"grid": [list(item) for item in MODEL_GRID], "seeds": list(TRAINING_SEEDS),
                             "fixed_development_fit_count": len(fit_idx), "fixed_development_selection_count": len(select_idx),
                             "selected_width": best["width"], "selected_regularization": best["regularization"],
                             "selection_by_seed": best["selection"],
                             "selected_mean_selection_mse": best["mean_selection_mse"],
                             "final_validation_mse_mean": float(np.mean(child_mse)),
                             "final_validation_mse_std": float(np.std(child_mse))},
        "value_capacity": {"parent": parent_metrics, "parent_bounded": parent_bounded,
                           "children": child_metrics, "mean_improvement_fraction": improvement,
                           "capacity_supported": bool(improvement >= 0.10 and all(item["metrics"]["mse"] < parent_metrics["mse"] for item in child_metrics))},
        "native_integration_entered": False, "classification": "PENDING_REVIEW",
        **({"compact_models": [model.to_dict() for model in final_models]} if emit_models else {}),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ruleset", choices=tuple(SEEDS), default=None)
    parser.add_argument("--emit-models", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    labels = (args.ruleset,) if args.ruleset else tuple(SEEDS)
    results = [_run(label, emit_models=args.emit_models) for label in labels]
    by_ruleset = {result["label"]: ("COMPACT_NONLINEAR_VALUE_CAPACITY_SUPPORTED" if result["value_capacity"]["capacity_supported"] else "COMPACT_NONLINEAR_VALUE_CAPACITY_NOT_SUPPORTED") for result in results}
    distinct = set(by_ruleset.values())
    overall = next(iter(distinct)) if len(distinct) == 1 else "MIXED_RULESET_OUTCOME"
    for result in results:
        result["classification"] = by_ruleset[result["label"]]
    output = {"work_order": "GENERICCHESS-F58-COMPACT-NONLINEAR-GENERIC-VALUE-SELF-DISTILLATION",
              "classification": overall, "classification_by_ruleset": by_ruleset,
              "corpus_count": CORPUS_COUNT, "split": {"development": DEV_COUNT, "validation": VALIDATION_COUNT},
              "teacher_budgets": TEACHER_BUDGETS, "results": results,
              "wall_seconds": time.perf_counter() - started}
    (OUT / "f58_results.json").write_text(json.dumps(output, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"work_order": output["work_order"], "classification": overall,
                      "classification_by_ruleset": by_ruleset, "wall_seconds": output["wall_seconds"],
                      "results": [{"label": r["label"], "corpus_id": r["corpus"]["corpus_id"],
                                   "teacher_stability": r["teacher_stability"], "value_capacity": r["value_capacity"]} for r in results]}, sort_keys=True))


if __name__ == "__main__":
    main()
