"""Deterministically describe the completed F94 R6 result without recomputing it."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / ".generic_chess_flow/f94-r6-layer-d-authority-refresh-result.json"
PROGRESS_PATH = ROOT / ".generic_chess_flow/f94-r6-progress"
AGGREGATE_SCHEMA = "generic-chess-f94-r6-result-aggregate-v1"
EXPECTED_RESULT_SHA256 = "a3008d1cc0150b82bc1682e7873a9cbe6c27232f359e57479689b486c956e4fe"
MAX_DEPTH = 12


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _attribution(tape_means: list[float], bootstrap_lower: float | None) -> dict[str, Any]:
    any_tape_mean_le_half = any(mean <= 0.5 for mean in tape_means)
    bootstrap_lower_le_half = bootstrap_lower is not None and bootstrap_lower <= 0.5
    underpowered = (not any_tape_mean_le_half and bootstrap_lower_le_half)
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


def _progress_directory(progress_root: Path, control: str, matchup: str, seed: int) -> Path | None:
    prefix = f"{control}-{matchup}-{seed}-"
    candidates = sorted(path for path in progress_root.glob(prefix + "*") if path.is_dir())
    return candidates[0] if len(candidates) == 1 else None


def _telemetry_censoring(progress_root: Path, control: str, matchup: str,
                         tape_results: list[dict[str, Any]]) -> dict[str, Any]:
    child_hits = child_count = 0
    for tape in tape_results:
        directory = _progress_directory(progress_root, control, matchup, int(tape["tape_seed"]))
        if directory is None:
            continue
        for pair_path in sorted(directory.glob("pair-*.json")):
            payload = json.loads(pair_path.read_text(encoding="utf-8"))
            for game_key in ("game_child_owner0", "game_child_owner1"):
                for metric in payload[game_key].get("search_metrics", ()):  # timing is not emitted
                    if metric.get("engine_role") == "child":
                        child_count += 1
                        child_hits += int(int(metric.get("completed_depth", 0)) >= MAX_DEPTH)
    fraction = child_hits / child_count if child_count else 0.0
    return {
        "hits": child_hits,
        "count": child_count,
        "fraction": fraction,
        "source": "identity-bound resumable pair checkpoints",
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

    controls: dict[str, Any] = {}
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
                progress_root, control_name, matchup["name"], matchup["tape_results"]
            )
            censoring["strongest_vs_weakest_horizon"] = {
                "hits": horizon_hits if matchup["name"] == "4096_vs_256" else 0,
                "games": horizon_games if matchup["name"] == "4096_vs_256" else 0,
                "fraction": (horizon_hits / horizon_games
                             if matchup["name"] == "4096_vs_256" and horizon_games else 0.0),
            }
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
        "source_result_path": str(result_path),
        "experiment": result["experiment"],
        "prep_artifact_sha256": result["prep_artifact_sha256"],
        "protocol_source_sha": result["protocol_source_sha"],
        "derived_compute": result["derived_compute"],
        "controls": controls,
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
