"""Deterministically describe the completed F94 R6 result without recomputing it."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from generic_chess.learning.serialization import stable_sha256

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / ".generic_chess_flow/f94-r6-layer-d-authority-refresh-result.json"
PROGRESS_PATH = ROOT / ".generic_chess_flow/f94-r6-progress"
PREP_PATH = ROOT / "docs/architecture/GENERICCHESS_F94_R6_LAYER_D_AUTHORITY_REFRESH_PREP.json"
AGGREGATE_SCHEMA = "generic-chess-f94-r6-result-aggregate-v1"
EXPECTED_RESULT_SHA256 = "a3008d1cc0150b82bc1682e7873a9cbe6c27232f359e57479689b486c956e4fe"
FROZEN_PREP_SHA256 = "78b935c3cb5391851bd8a8a574d25ac69714f030a49a01e6006c1d7d8133b8ba"
MAX_DEPTH = 12


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _attribution(tape_means: list[float], bootstrap_lower: float | None) -> dict[str, Any]:
    any_tape_mean_le_half = any(mean <= 0.5 for mean in tape_means)
    bootstrap_lower_le_half = bootstrap_lower is not None and bootstrap_lower <= 0.5
    underpowered = bootstrap_lower_le_half
    both = any_tape_mean_le_half and underpowered
    label = "BOTH" if both else (
        "NONMONOTONE" if any_tape_mean_le_half else
        "UNDERPOWERED_OR_UNCERTAIN" if underpowered else "NONE"
    )
    return {
        "any_tape_mean_le_half": any_tape_mean_le_half,
        "bootstrap_lower_le_half": bootstrap_lower_le_half,
        "depth_censored": False,
        "horizon_censored": False,
        "descriptive_attribution": label,
        "authority": "descriptive_only",
    }


def _progress_directory(progress_root: Path, control: str, matchup: str, seed: int,
                        *, experiment: str, protocol_source_sha: str,
                        prep_fingerprint: str) -> Path:
    prefix = f"{control}-{matchup}-{seed}-"
    candidates = sorted(path for path in progress_root.glob(prefix + "*") if path.is_dir())
    identity = {
        "experiment": experiment,
        "protocol_source_sha": protocol_source_sha,
        "prep_fingerprint": prep_fingerprint,
        "control": control,
        "matchup": matchup,
        "tape_seed": seed,
    }
    expected = progress_root / f"{control}-{matchup}-{seed}-{stable_sha256(identity)[:16]}"
    if candidates != [expected]:
        raise RuntimeError(f"R6 aggregate progress directory identity mismatch: {control}/{matchup}/{seed}")
    return expected


def _telemetry_censoring(progress_root: Path, control: str, matchup: str,
                         tape_results: list[dict[str, Any]], *, result: dict[str, Any],
                         prep: dict[str, Any]) -> dict[str, Any]:
    child_hits = child_count = 0
    evidence_invocations: list[dict[str, Any]] = []
    prep_control = next((row for row in prep["controls"] if row["name"] == control), None)
    prep_matchup = next((row for row in prep["matchups"] if row["name"] == matchup), None)
    if prep_control is None or prep_matchup is None:
        raise RuntimeError(f"R6 aggregate PREP identity is missing {control}/{matchup}")
    for tape in tape_results:
        seed = int(tape["tape_seed"])
        directory = _progress_directory(
            progress_root, control, matchup, seed,
            experiment=result["experiment"], protocol_source_sha=result["protocol_source_sha"],
            prep_fingerprint=result["prep_fingerprint"],
        )
        manifest_path = directory / "manifest.json"
        if not manifest_path.is_file():
            raise RuntimeError(f"R6 aggregate progress manifest is missing: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        identity = manifest.get("identity")
        if not isinstance(identity, dict) or manifest.get("identity_sha256") != stable_sha256(identity):
            raise RuntimeError(f"R6 aggregate progress manifest identity is invalid: {manifest_path}")
        config = identity.get("config", {})
        expected_checkpoint = prep_control["checkpoint_id"]
        expected_openings = next((row for row in prep_control["opening_corpora"] if row["tape_seed"] == seed), None)
        expected_config = {
            "pairs": 6, "nodes_per_move": prep_matchup["child_nodes_per_move"],
            "max_depth": 12, "tt_megabytes": 8, "opening_seed": seed,
            "opening_count": 6, "min_plies": 2, "max_plies": 6, "workers": 4,
            "parent_nodes_per_move": prep_matchup["parent_nodes_per_move"],
            "child_nodes_per_move": prep_matchup["child_nodes_per_move"],
        }
        if (
            identity.get("ruleset_fingerprint") != prep_control["ruleset_fingerprint"]
            or identity.get("parent_checkpoint_id") != expected_checkpoint
            or identity.get("child_checkpoint_id") != expected_checkpoint
            or config != expected_config
            or identity.get("capture_search_metrics") is not True
            or expected_openings is None
        ):
            raise RuntimeError(f"R6 aggregate progress manifest budget/telemetry mismatch: {manifest_path}")
        expected_opening_identity = [
            {key: opening[key] for key in ("index", "opening_seed", "target_plies", "final_position_key")}
            for opening in expected_openings["openings"]
        ]
        actual_opening_identity = [
            {key: opening.get(key) for key in ("index", "opening_seed", "target_plies", "final_position_key")}
            for opening in identity.get("ordered_openings", ())
        ]
        if actual_opening_identity != expected_opening_identity:
            raise RuntimeError(f"R6 aggregate progress opening identity mismatch: {manifest_path}")
        pair_paths = sorted(directory.glob("pair-*.json"))
        expected_names = [directory / f"pair-{index:06d}.json" for index in range(6)]
        if {path.name for path in pair_paths} != {path.name for path in expected_names}:
            raise RuntimeError(f"R6 aggregate progress pair set is not exactly 0..5: {directory}")
        expected_pairs = {int(pair["pair_index"]): pair for pair in tape.get("pairs", ())}
        if set(expected_pairs) != set(range(6)):
            raise RuntimeError(f"R6 aggregate result pair set is not exactly 0..5: {directory}")
        for pair_path in pair_paths:
            payload = json.loads(pair_path.read_text(encoding="utf-8"))
            index = payload.get("pair_index")
            if index not in expected_pairs or payload.get("opening_id") != expected_pairs[index]["games"][0]["opening_position_key"]:
                raise RuntimeError(f"R6 aggregate progress pair identity mismatch: {pair_path}")
            for game_key in ("game_child_owner0", "game_child_owner1"):
                game = payload.get(game_key, {})
                if game.get("pair") != index or not game.get("search_metrics"):
                    raise RuntimeError(f"R6 aggregate progress telemetry is incomplete: {pair_path}")
            for game_key in ("game_child_owner0", "game_child_owner1"):
                for metric in payload[game_key].get("search_metrics", ()):  # timing is not emitted
                    if metric.get("engine_role") == "child":
                        child_count += 1
                        child_hits += int(int(metric.get("completed_depth", 0)) >= MAX_DEPTH)
        evidence_invocations.append({
            "control": control,
            "matchup": matchup,
            "tape_seed": seed,
            "manifest_sha256": _sha256(manifest_path),
            "pair_payload_sha256": [
                {"pair_index": index, "sha256": _sha256(directory / f"pair-{index:06d}.json")}
                for index in range(6)
            ],
        })
    fraction = child_hits / child_count if child_count else 0.0
    return {
        "hits": child_hits,
        "count": child_count,
        "fraction": fraction,
        "source": "identity-bound resumable pair checkpoints",
        "evidence_invocations": evidence_invocations,
    }


def aggregate(result_path: Path = RESULT_PATH, progress_root: Path = PROGRESS_PATH,
              *, expected_result_sha256: str = EXPECTED_RESULT_SHA256) -> dict[str, Any]:
    result_path = Path(result_path)
    progress_root = Path(progress_root)
    result_sha256 = _sha256(result_path)
    if expected_result_sha256 and result_sha256 != expected_result_sha256:
        raise RuntimeError(
            f"R6 aggregate source SHA mismatch: {result_sha256} != {expected_result_sha256}"
        )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("status") != "R6_RESULT_COMPLETE":
        raise RuntimeError("R6 aggregate requires a complete result")
    if result.get("derived_compute") != {
        "arena_invocations": 18, "arena_pairs": 108,
        "arena_games": 216, "action_traces": 216,
    }:
        raise RuntimeError("R6 aggregate source accounting is not exact")

    if _sha256(PREP_PATH) != FROZEN_PREP_SHA256 or result.get("prep_artifact_sha256") != FROZEN_PREP_SHA256:
        raise RuntimeError("R6 aggregate PREP SHA mismatch")
    prep = json.loads(PREP_PATH.read_text(encoding="utf-8"))
    if prep.get("prep_fingerprint") != result.get("prep_fingerprint"):
        raise RuntimeError("R6 aggregate PREP fingerprint mismatch")
    expected_directory_names = {
        f"{control}-{matchup}-{seed}-{stable_sha256({'experiment': result['experiment'], 'protocol_source_sha': result['protocol_source_sha'], 'prep_fingerprint': result['prep_fingerprint'], 'control': control, 'matchup': matchup, 'tape_seed': seed})[:16]}"
        for control in result["controls"]
        for matchup in ("1024_vs_256", "4096_vs_1024", "4096_vs_256")
        for seed in (9801, 9802, 9803)
    }
    actual_directory_names = {path.name for path in progress_root.iterdir() if path.is_dir()}
    if actual_directory_names != expected_directory_names:
        raise RuntimeError("R6 aggregate progress root contains missing or extra invocation directories")

    controls: dict[str, Any] = {}
    progress_records: list[dict[str, Any]] = []
    for control_name in sorted(result["controls"]):
        control = result["controls"][control_name]
        matchups: list[dict[str, Any]] = []
        for matchup in control["matchups"]:
            tape_summaries = []
            pair_scores = []
            status_counts: Counter[str] = Counter()
            horizon_hits = horizon_games = 0
            for tape in matchup["tape_results"]:
                pairs = tape.get("pairs", [])
                scores = [float(pair["pair_score"]) for pair in pairs]
                tape_summaries.append({
                    "tape_seed": int(tape["tape_seed"]),
                    "pair_count": int(tape["pair_count"]),
                    "mean_pair_score": float(tape["mean_pair_score"]),
                    "recomputed_mean_pair_score": sum(scores) / len(scores) if scores else None,
                })
                for pair in pairs:
                    status = str(pair["status"])
                    status_counts[status] += 1
                    pair_scores.append({
                        "tape_seed": int(tape["tape_seed"]),
                        "pair_index": int(pair["pair_index"]),
                        "pair_score": float(pair["pair_score"]),
                        "status": status,
                    })
                    for game in pair.get("games", ()):
                        horizon_games += 1
                        horizon_hits += int(bool(game.get("max_ply_hit")))
            bootstrap = dict(matchup["bootstrap"])
            censoring = _telemetry_censoring(
                progress_root, control_name, matchup["name"], matchup["tape_results"],
                result=result, prep=prep,
            )
            progress_records.extend(censoring.pop("evidence_invocations"))
            expected_depth_fraction = float(matchup["pooled_censoring"]["child_depth_ceiling_fraction"])
            if not math.isclose(censoring["fraction"], expected_depth_fraction, rel_tol=0.0, abs_tol=1e-15):
                raise RuntimeError(f"R6 aggregate depth fraction mismatch: {control_name}/{matchup['name']}")
            censoring["strongest_vs_weakest_horizon"] = {
                "hits": horizon_hits if matchup["name"] == "4096_vs_256" else 0,
                "games": horizon_games if matchup["name"] == "4096_vs_256" else 0,
                "fraction": (horizon_hits / horizon_games
                             if matchup["name"] == "4096_vs_256" and horizon_games else 0.0),
            }
            if matchup["name"] == "4096_vs_256":
                expected_horizon_fraction = float(
                    matchup["pooled_censoring"]["strongest_vs_weakest_horizon_fraction"]
                )
                if not math.isclose(
                    censoring["strongest_vs_weakest_horizon"]["fraction"],
                    expected_horizon_fraction,
                    rel_tol=0.0,
                    abs_tol=1e-15,
                ):
                    raise RuntimeError(
                        f"R6 aggregate horizon fraction mismatch: {control_name}/{matchup['name']}"
                    )
            attribution = _attribution(
                [summary["mean_pair_score"] for summary in tape_summaries],
                bootstrap.get("lower"),
            )
            attribution["depth_censored"] = censoring["fraction"] >= 0.5
            attribution["horizon_censored"] = (
                censoring["strongest_vs_weakest_horizon"]["fraction"] >= 0.5
            )
            if attribution["depth_censored"] or attribution["horizon_censored"]:
                attribution["descriptive_attribution"] = "CENSORED"
            matchups.append({
                "name": matchup["name"],
                "pair_scores": pair_scores,
                "tape_summaries": tape_summaries,
                "bootstrap": bootstrap,
                "status_counts": dict(sorted(status_counts.items())),
                "censoring": censoring,
                "classifier_output": matchup["classification"],
                "descriptive_attribution": attribution,
            })
        controls[control_name] = {
            "matchups": matchups,
            "classifier_output": control["classification"],
        }

    return {
        "schema": AGGREGATE_SCHEMA,
        "source_result_sha256": result_sha256,
        "source_result_path": ".generic_chess_flow/f94-r6-layer-d-authority-refresh-result.json",
        "experiment": result["experiment"],
        "prep_artifact_sha256": result["prep_artifact_sha256"],
        "protocol_source_sha": result["protocol_source_sha"],
        "derived_compute": result["derived_compute"],
        "controls": controls,
        "progress_evidence_sha256": stable_sha256(progress_records),
        "authority": "descriptive_only",
        "promotion_or_classifier_effect": "none",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, default=RESULT_PATH)
    parser.add_argument("--progress-root", type=Path, default=PROGRESS_PATH)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = Path(args.output)
    payload = aggregate(args.result, args.progress_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
