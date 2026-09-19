"""F129: compress exact one-ply known-oracle Standard-Shogi search."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import (
        FrozenBasis,
        _json_sha,
        _scalar_metrics,
    )
    from scripts.f125_known_oracle_one_ply_search_compression import _sorted_actions
    from scripts.f127_shogi_t1_scalar_compression_expanded_control import (
        eligibility_from_children,
        _fit_metrics_tight,
        _fit_report,
        _numerical_gate,
        _search_representation_gate,
    )
    from scripts.f128_shogi_direct_control_cross_surface_diagnosis import (
        CORPUS_HASH,
        F127_COUNTS,
        ORACLE_HASH,
        _collect_states,
        _eligibility_map,
        _fit_surface,
        _metrics,
        _selected_ordinals,
    )
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import FrozenBasis, _json_sha, _scalar_metrics
    from f125_known_oracle_one_ply_search_compression import _sorted_actions
    from f127_shogi_t1_scalar_compression_expanded_control import eligibility_from_children, _fit_metrics_tight, _fit_report, _numerical_gate, _search_representation_gate
    from f128_shogi_direct_control_cross_surface_diagnosis import CORPUS_HASH, F127_COUNTS, ORACLE_HASH, _collect_states, _eligibility_map, _fit_surface, _metrics, _selected_ordinals

from generic_chess.core.transition import apply_action
from generic_chess.core.terminal import TerminalStatus
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
FAMILY = "standard_shogi"
BASELINE = "a322b9a5b00bc9ad18acde069ef1973fce7308dc"
F127_DIRECT_HOLDOUT_RMSE = 222.54533883442718
F127_DIRECT_HOLDOUT_NRMSE = 0.05158006312777384
RETAINED_COUNTS = {"train": 1995, "dev": 252, "holdout": 254}
SHARD_SIZE = 128


def _write_progress(output: Path, stage: str, payload: dict) -> None:
    path = output.parent / f"{output.stem}.stage-{stage}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _materialize(rows, basis) -> list[dict]:
    result = []
    for row in rows:
        features = basis.vector(row["state"])
        value = float(basis.oracle(features))
        result.append({**row, "features": features.tolist(), "oracle": value, "direct_oracle": value})
    return result


def _direct_metrics(fit: dict, rows: list[dict]) -> dict:
    return _metrics(fit, rows)


def _spectrum_sha(spectrum: list[dict]) -> str:
    return _json_sha(spectrum)


def _validate_shard(path: Path, roots: list[dict], basis: FrozenBasis) -> list[dict] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    expected_ids = [row["identity"] for row in roots]
    if payload.get("schema") != "F129_T1_LABEL_SHARD_V1":
        return None
    if payload.get("oracle_sha256") != ORACLE_HASH or payload.get("basis_sha256") != basis.oracle_weight_sha256:
        return None
    if payload.get("root_identity_sequence") != expected_ids:
        return None
    rows = payload.get("rows")
    if not isinstance(rows, list) or len(rows) != len(roots):
        return None
    for root, record in zip(roots, rows):
        if record.get("identity") != root["identity"] or record.get("direct_value") != root["direct_oracle"]:
            return None
        spectrum = record.get("action_spectrum")
        if not isinstance(spectrum, list) or record.get("action_spectrum_sha256") != _spectrum_sha(spectrum):
            return None
        if not spectrum:
            return None
        best = max(range(len(spectrum)), key=lambda index: (spectrum[index]["score"], -index))
        if record.get("t1") != spectrum[best]["score"] or record.get("teacher_action") != spectrum[best]["action"]:
            return None
    return rows


def _generate_shard(roots: list[dict], basis: FrozenBasis, compiled) -> tuple[list[dict], int]:
    records = []
    child_count = 0
    for root in roots:
        actions = _sorted_actions(root["state"], compiled)
        children = [(action, apply_action(root["state"], action, compiled)) for action in actions]
        eligibility = eligibility_from_children(root["state"], children, compiled)
        if any(eligibility.values()):
            raise RuntimeError("F129_RETAINED_IDENTITY_LOST_ELIGIBILITY")
        spectrum = []
        for action, child in children:
            child_features = basis.vector(child)
            child_value = basis.oracle(child_features)
            spectrum.append({"action": str(action), "score": float(-child_value)})
        if not spectrum:
            raise RuntimeError("F129_RETAINED_STATE_HAS_NO_LEGAL_ACTION")
        best = max(range(len(spectrum)), key=lambda index: (spectrum[index]["score"], -index))
        top_scores = sorted((entry["score"] for entry in spectrum), reverse=True)
        records.append({
            "identity": root["identity"],
            "root_legal_action_count": len(actions),
            "direct_value": root["direct_oracle"],
            "t1": spectrum[best]["score"],
            "teacher_action": spectrum[best]["action"],
            "teacher_top2_gap": float(top_scores[0] - top_scores[1]) if len(top_scores) > 1 else 0.0,
            "action_spectrum": spectrum,
            "action_spectrum_sha256": _spectrum_sha(spectrum),
        })
        child_count += len(children)
    return records, child_count


def _load_or_generate_shards(rows, basis, compiled, output: Path) -> tuple[list[dict], dict]:
    all_records = []
    manifest = []
    total_children = 0
    for shard_index, start in enumerate(range(0, len(rows), SHARD_SIZE)):
        roots = rows[start:start + SHARD_SIZE]
        shard_path = output.parent / f"{output.stem}.shard-{shard_index:04d}.json"
        records = _validate_shard(shard_path, roots, basis)
        reused = records is not None
        if records is None:
            records, child_count = _generate_shard(roots, basis, compiled)
            total_children += child_count
            payload = {
                "schema": "F129_T1_LABEL_SHARD_V1",
                "shard_index": shard_index,
                "root_identity_sequence": [row["identity"] for row in roots],
                "root_identity_sha256": _json_sha([row["identity"] for row in roots]),
                "oracle_sha256": ORACLE_HASH,
                "basis_sha256": basis.oracle_weight_sha256,
                "rows": records,
            }
            shard_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        else:
            child_count = sum(len(record["action_spectrum"]) for record in records)
            total_children += child_count
        all_records.extend(records)
        manifest.append({"shard_index": shard_index, "path": str(shard_path), "root_count": len(roots), "root_identity_sha256": _json_sha([row["identity"] for row in roots]), "reused": reused, "child_states_evaluated": child_count})
    return all_records, {"shard_size": SHARD_SIZE, "shards": manifest, "total_child_states_evaluated": total_children}


def _by_split(records, rows) -> dict[str, list[dict]]:
    split_by_identity = {row["identity"]: row["split"] for row in rows}
    return {split: [record for record in records if split_by_identity[record["identity"]] == split] for split in ("train", "dev", "holdout")}


def _summary(values: list[float]) -> dict:
    data = np.asarray(values, dtype=np.float64)
    return {"count": len(values), "mean": float(np.mean(data)), "standard_deviation": float(np.std(data)), "min": float(np.min(data)), "max": float(np.max(data))}


def _label_telemetry(records_by_split: dict[str, list[dict]], shard_info: dict) -> dict:
    result = {}
    for split, records in records_by_split.items():
        actions = np.asarray([record["root_legal_action_count"] for record in records], dtype=np.float64)
        labels = np.asarray([record["t1"] for record in records], dtype=np.float64)
        result[split] = {
            "retained_roots": len(records),
            "total_child_states_evaluated": int(sum(len(record["action_spectrum"]) for record in records)),
            "legal_action_count_mean": float(np.mean(actions)),
            "legal_action_count_median": float(np.median(actions)),
            "legal_action_count_p90": float(np.percentile(actions, 90)),
            "legal_action_count_p95": float(np.percentile(actions, 95)),
            "legal_action_count_max": int(np.max(actions)),
            "t1_target_mean": float(np.mean(labels)),
            "t1_target_standard_deviation": float(np.std(labels)),
            "t1_target_min": float(np.min(labels)),
            "t1_target_max": float(np.max(labels)),
        }
    return {"by_split": result, "shards": shard_info}


def _correlation(left, right) -> float:
    if len(left) < 2 or not np.std(left) or not np.std(right):
        return 0.0
    return float(np.corrcoef(left, right)[0, 1])


def _rank_correlation(left, right) -> float:
    left_order = np.argsort(left, kind="mergesort")
    right_order = np.argsort(right, kind="mergesort")
    left_rank = np.empty(len(left), dtype=np.float64)
    right_rank = np.empty(len(right), dtype=np.float64)
    left_rank[left_order] = np.arange(len(left), dtype=np.float64)
    right_rank[right_order] = np.arange(len(right), dtype=np.float64)
    return _correlation(left_rank, right_rank)


def _displacement(records_by_split: dict[str, list[dict]]) -> dict:
    result = {}
    for split, records in records_by_split.items():
        t1 = np.asarray([record["t1"] for record in records], dtype=np.float64)
        direct = np.asarray([record["direct_value"] for record in records], dtype=np.float64)
        delta = t1 - direct
        result[split] = {
            "count": len(records),
            "mean": float(np.mean(delta)),
            "median": float(np.median(delta)),
            "standard_deviation": float(np.std(delta)),
            "rms": float(np.sqrt(np.mean(delta * delta))),
            "mean_absolute": float(np.mean(np.abs(delta))),
            "p50_absolute": float(np.percentile(np.abs(delta), 50)),
            "p90_absolute": float(np.percentile(np.abs(delta), 90)),
            "p95_absolute": float(np.percentile(np.abs(delta), 95)),
            "max_absolute": float(np.max(np.abs(delta))),
            "zero_fraction_within_1e-12": float(np.mean(np.abs(delta) <= 1e-12)),
            "pearson_t1_with_v_star": _correlation(t1, direct),
            "spearman_t1_with_v_star": _rank_correlation(t1, direct),
        }
        if split == "holdout":
            order = np.argsort([record["root_legal_action_count"] for record in records], kind="mergesort")
            quartiles = []
            for quartile, group in enumerate(np.array_split(order, 4), start=1):
                quartiles.append({"quartile": quartile, "count": len(group), "mean_absolute": float(np.mean(np.abs(delta[group]))), "min_action_count": int(min(records[index]["root_legal_action_count"] for index in group)), "max_action_count": int(max(records[index]["root_legal_action_count"] for index in group))})
            result[split]["by_legal_action_count_quartile"] = quartiles
    return result


def _static_baseline_metrics(rows_by_split: dict[str, list[dict]], records_by_split: dict[str, list[dict]]) -> dict:
    result = {}
    for split in ("train", "dev", "holdout"):
        target = np.asarray([record["t1"] for record in records_by_split[split]], dtype=np.float64)
        prediction = np.asarray([record["direct_value"] for record in records_by_split[split]], dtype=np.float64)
        result[split] = _scalar_metrics(target, prediction, float(np.std(target)) or 1.0)
    return result


def _gap_diagnostic(records_by_split: dict[str, list[dict]]) -> dict:
    result = {}
    for split, records in records_by_split.items():
        gaps = np.asarray([record["teacher_top2_gap"] for record in records], dtype=np.float64)
        result[split] = {"count": len(gaps), "zero_fraction": float(np.mean(gaps <= 1e-12)), "quartiles": {"p25": float(np.percentile(gaps, 25)), "p50": float(np.percentile(gaps, 50)), "p75": float(np.percentile(gaps, 75)), "p90": float(np.percentile(gaps, 90)), "max": float(np.max(gaps))}}
    return result


def _run(output: Path) -> dict:
    started = time.time()
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
    basis = FrozenBasis(FAMILY, compiled)
    states, corpus = _collect_states(compiled, basis)
    retained_states, eligibility_counts, retained_sha = _eligibility_map(states, compiled)
    selected_ordinals = _selected_ordinals()
    selected = {ordinal for values in selected_ordinals.values() for ordinal in values}
    selected_identity_sha = {split: _json_sha([row["identity"] for row in states if row["ordinal"] in selected_ordinals[split]]) for split in ("train", "dev", "holdout")}
    expected_selected_sha = {
        "train": "c16db7cc19375820ca9a9866493922bf7a0d74eff64a8f909b225e9936f205fc",
        "dev": "91929864cab22ba1fc065f9acdc49855751a9761ebd28b9cda76202fe01e6e63",
        "holdout": "0173ba68eed4c779322214b3ef6c819726cb5476703214d00e4d8255a7b580b3",
    }
    retained_selected = [row for row in retained_states if row["ordinal"] in selected]
    retained_selected_counts = {split: sum(row["split"] == split for row in retained_selected) for split in ("train", "dev", "holdout")}
    if corpus["full_identity_sha256"] != CORPUS_HASH or selected_identity_sha != expected_selected_sha or retained_sha != {
        "train": "74f9778dff9a2a5c08a6623d5452cdf2d15971cc20eab0c3e12a9c5d01d0a15b",
        "dev": "5c9d3acbc6adbd366c8c2b3739fe80b322e67a83e13b3eb1c1153871d70f0448",
        "holdout": "4238175784283f3338294290bb70b1330930a427a213f1a56223471b44d1d456",
    } or retained_selected_counts != RETAINED_COUNTS:
        raise RuntimeError("F129_FROZEN_SURFACE_IDENTITY_MISMATCH")
    if basis.oracle_weight_sha256 != ORACLE_HASH:
        raise RuntimeError("F129_FROZEN_ORACLE_IDENTITY_MISMATCH")
    _write_progress(output, "corpus-eligibility", {"schema": "F129_STAGE_CORPUS_ELIGIBILITY_V1", "corpus": corpus, "eligibility_counts": eligibility_counts, "retained_identity_sha256": retained_sha, "selected_identity_sha256": selected_identity_sha, "retained_selected_counts": retained_selected_counts})

    direct_rows = _materialize(retained_selected, basis)
    direct_fit = _fit_surface(direct_rows, basis)
    direct_holdout = _direct_metrics(direct_fit, [row for row in direct_rows if row["split"] == "holdout"])
    direct_report = {"schema": "F129_STAGE_DIRECT_CONTROL_REPRODUCTION_V1", "retained_counts": retained_selected_counts, "holdout_metrics": direct_holdout, "expected_holdout_nrmse": F127_DIRECT_HOLDOUT_NRMSE, "absolute_nrmse_difference": abs(direct_holdout["normalized_rmse"] - F127_DIRECT_HOLDOUT_NRMSE)}
    _write_progress(output, "direct-control", direct_report)
    if direct_report["absolute_nrmse_difference"] > 1e-9:
        result = {"schema": "F129_SHOGI_KNOWN_ORACLE_T1_SCALAR_COMPRESSION_V1", "baseline": BASELINE, "classification": "F129_DIRECT_CONTROL_REPRODUCTION_FAILURE", "t1_generated": False, "direct_control": direct_report, "runtime_seconds": time.time() - started}
        return result

    records, shard_info = _load_or_generate_shards(direct_rows, basis, compiled, output)
    rows_by_split = _by_split(records, direct_rows)
    telemetry = _label_telemetry(rows_by_split, shard_info)
    _write_progress(output, "t1-labels", {"schema": "F129_STAGE_T1_LABELS_V1", "selection": selected_identity_sha, "retained_identity_sha256": retained_sha, "telemetry": telemetry, "displacement": _displacement(rows_by_split), "teacher_gap": _gap_diagnostic(rows_by_split)})
    t1_by_identity = {record["identity"]: record["t1"] for record in records}
    t1_labels = [t1_by_identity[row["identity"]] for row in direct_rows]
    search_fit = _fit_metrics_tight(direct_rows, t1_labels, basis)
    fit_report = _fit_report(search_fit, "teacher")
    numerical_gate = {**_numerical_gate(search_fit), "pass": all(_numerical_gate(search_fit).values())}
    representation_gate = _search_representation_gate(search_fit["scalar_metrics"]["matched_ridge"])
    static_metrics = _static_baseline_metrics({split: [row for row in direct_rows if row["split"] == split] for split in ("train", "dev", "holdout")}, rows_by_split)
    compressed_metrics = fit_report["scalar_metrics"]["matched_ridge"]
    relative_reduction = {split: 1.0 - compressed_metrics[split]["rmse_oracle_units"] / static_metrics[split]["rmse_oracle_units"] for split in ("dev", "holdout")}
    displacement = _displacement(rows_by_split)
    holdout_compressed_rmse = compressed_metrics["holdout"]["rmse_oracle_units"]
    search_report = {
        "schema": "F129_STAGE_SEARCH_COMPRESSED_FIT_V1",
        "fit": fit_report,
        "numerical_gate": numerical_gate,
        "representation_gate": representation_gate,
        "static_oracle_baseline_to_t1": static_metrics,
        "relative_rmse_reduction_vs_static_oracle": relative_reduction,
        "search_information_displacement": displacement,
        "teacher_action_gap": _gap_diagnostic(rows_by_split),
        "signal_to_control_scale": {
            "direct_control_holdout_rmse": F127_DIRECT_HOLDOUT_RMSE,
            "t1_displacement_rms_over_direct_control_rmse": displacement["holdout"]["rms"] / F127_DIRECT_HOLDOUT_RMSE,
            "compressed_t1_holdout_rmse_over_direct_control_rmse": holdout_compressed_rmse / F127_DIRECT_HOLDOUT_RMSE,
        },
    }
    _write_progress(output, "search-fit", search_report)
    if not representation_gate["pass"]:
        classification = "SHOGI_HANDCRAFTED_T1_SEARCH_TARGET_COMPRESSION_LIMIT_SUPPORTED"
    elif not numerical_gate["pass"]:
        classification = "F129_SHOGI_T1_SOLVER_NUMERICAL_FAILURE"
    else:
        classification = "SHOGI_KNOWN_ORACLE_T1_SCALAR_COMPRESSION_PASSES"
    return {
        "schema": "F129_SHOGI_KNOWN_ORACLE_T1_SCALAR_COMPRESSION_V1",
        "baseline": BASELINE,
        "family": FAMILY,
        "corpus": corpus,
        "eligibility": {"counts_by_split": eligibility_counts, "retained_identity_sha256": retained_sha, "selected_identity_sha256": selected_identity_sha, "retained_selected_counts": retained_selected_counts},
        "direct_control": direct_report,
        "t1_generated": True,
        "t1_telemetry": telemetry,
        "shards": shard_info,
        "search_compressed_v1": search_report,
        "classification": classification,
        "runtime_seconds": time.time() - started,
    }


def run(output: Path | None = None) -> dict:
    return _run(output or Path(".generic_chess_flow/f129-shogi-result.json"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"classification": result["classification"], "runtime_seconds": result["runtime_seconds"], "t1_generated": result["t1_generated"]}, sort_keys=True))


if __name__ == "__main__":
    main()
