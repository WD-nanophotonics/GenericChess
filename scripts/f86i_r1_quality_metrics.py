"""Derive compact F86I-R1 quality metrics from the frozen local raw games."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from generic_chess.benchmark.game_quality import QualityObservation, profile_from_observations


SAMPLES = ("V4-2", "V4-3", "V4-4", "V4-5", "V5-2", "V5-3", "V5-4", "V5-5")
SOURCE_COMMIT = "0fbfbf2b5c3cc1e2efd1300cba4da0f5587f4976"
SOURCE_BLOBS = {
    "artifacts/f86i_reversibility_rescue/game_results.json": "7723862c4f18f297d239590f49fa1265462efdc9",
    "artifacts/f86i_reversibility_rescue/results.json": "21ecbe3d87fe06e92848c231b290ea2148dcd95b",
    "artifacts/f86i_reversibility_rescue/static_results.json": "e2d8dfa8aced6aed750d0d0bb9dc3d4026eeac4a",
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _profile(games: list[dict[str, Any]]) -> dict[str, Any]:
    observations = [
        QualityObservation(
            tuple(game["branching_counts"]),
            game["plies"],
            game["terminal_status"],
        )
        for game in games
    ]
    profile = profile_from_observations(observations)
    return {
        "trajectory_count": profile.trajectory_count,
        "trajectory_lengths": list(profile.trajectory_lengths),
        "median_branching": profile.median_branching,
        "p10_game_branching": profile.p10_game_branching,
        "p90_game_branching": profile.p90_game_branching,
        "forced_move_fraction": profile.forced_move_fraction,
        "low_branch_fraction": profile.low_branch_fraction,
        "branching_collapse_fraction": profile.branching_collapse_fraction,
        "median_game_length": profile.median_game_length,
        "p10_game_length": profile.p10_game_length,
        "p90_game_length": profile.p90_game_length,
        "terminal_distribution": dict(sorted(profile.terminal_distribution.items())),
    }


def _outcomes(games: list[dict[str, Any]]) -> dict[str, Any]:
    labels = Counter(game["outcome_label"] for game in games)
    lengths = Counter(str(game["plies"]) for game in games)
    return {
        "terminal_distribution": dict(sorted(labels.items())),
        "game_length_distribution": dict(sorted(lengths.items(), key=lambda item: int(item[0]))),
    }


def _paired_outcomes(games: list[dict[str, Any]]) -> dict[str, Any]:
    by_sample = {}
    for sample_id in SAMPLES:
        pair = [game for game in games if game["sample_id"] == sample_id]
        complete = all(game["terminal_status"] != "ongoing" for game in pair)
        if len(pair) == 2 and complete:
            scores = []
            for game in pair:
                winner = game["winner"]
                if winner is None:
                    scores.append((0.5, 0.5))
                else:
                    scores.append((1.0 if winner == 0 else 0.0, 1.0 if winner == 1 else 0.0))
            by_sample[sample_id] = {
                "scoreable": True,
                "first_player_score": sum(score[0] for score in scores) / len(scores),
                "second_player_score": sum(score[1] for score in scores) / len(scores),
            }
        else:
            by_sample[sample_id] = {
                "scoreable": False,
                "first_player_score": None,
                "second_player_score": None,
            }
    scoreable = [row for row in by_sample.values() if row["scoreable"]]
    return {
        "scoreable_pair_count": len(scoreable),
        "first_player_score": (
            sum(row["first_player_score"] for row in scoreable) / len(scoreable)
            if scoreable else None
        ),
        "second_player_score": (
            sum(row["second_player_score"] for row in scoreable) / len(scoreable)
            if scoreable else None
        ),
        "by_sample": by_sample,
        "incomplete_pairs_are_unresolved": True,
    }


def build(root: Path, output: Path) -> dict[str, Any]:
    raw_games = _load(root / "artifacts/f86i_reversibility_rescue/game_results.json")
    raw_results = _load(root / "artifacts/f86i_reversibility_rescue/results.json")
    games = raw_games["games"]
    by_sample = {
        sample_id: _profile([game for game in games if game["sample_id"] == sample_id])
        for sample_id in SAMPLES
    }
    static = []
    for row in raw_results["static"]:
        mechanism = row["mechanism"]
        static.append({
            "sample_id": row["sample_id"],
            "board_size": row["board_size"],
            "source_seed": row["source_seed"],
            "source_ruleset_fingerprint": row["source_ruleset_fingerprint"],
            "candidate_ruleset_fingerprint": row["candidate_ruleset_fingerprint"],
            "mechanism": {
                "ordinary_sink_fraction": mechanism["ordinary_sink_fraction"],
                "ordinary_direct_reverse_edge_fraction": mechanism["ordinary_direct_reverse_edge_fraction"],
                "ordinary_nontrivial_scc_vertex_fraction": mechanism["ordinary_nontrivial_scc_vertex_fraction"],
                "ordinary_all_monotone_dag": mechanism["ordinary_all_monotone_dag"],
            },
        })
    candidate = []
    for row in raw_results["candidate_static_mate_capacity"]:
        census = row["census"]
        kinematic = row["kinematic"]
        candidate.append({
            "sample_id": census["sample_id"],
            "cell": census["cell"],
            "ruleset_fingerprint": census["ruleset_fingerprint"],
            "candidate_position_count": census["candidate_position_count"],
            "validated_position_count": census["validated_position_count"],
            "validated_template_count": census["validated_template_count"],
            "truncation": census["truncation"],
            "ordinary_assignment_reachable_count": kinematic["ordinary_assignment_reachable_count"],
            "joint_kinematically_reachable_count": kinematic["joint_kinematically_reachable_count"],
            "minimum_optimistic_ply_lower_bound": kinematic["minimum_optimistic_ply_lower_bound"],
        })
    total_checks = sum(row["candidate_position_count"] for row in candidate)
    payload = {
        "schema_version": 2,
        "status": "F86I_R1_ZERO_NEW_COMPUTE_CORRECTIVE",
        "source_evidence": {
            "commit": SOURCE_COMMIT,
            "raw_artifacts": {
                path: {
                    "blob": blob,
                    "retained_local_ignored": True,
                }
                for path, blob in SOURCE_BLOBS.items()
            },
        },
        "source_raw_game_artifact": "artifacts/f86i_reversibility_rescue/game_results.json",
        "source_raw_result_artifact": "artifacts/f86i_reversibility_rescue/results.json",
        "raw_evidence_retained_in_checkpoint": False,
        "raw_evidence_retained_local_only": True,
        "real_games": len(games),
        "max_ply": raw_games["max_ply"],
        "tactical_probe_nodes": raw_games["tactical_probe_nodes"],
        "static_candidate_checks": {
            "V4-3": 504,
            "V5-3": 2048,
            "total": total_checks,
            "per_cell_cap": 2048,
            "total_cap": 4096,
        },
        "static": static,
        "candidate_static_mate_capacity": candidate,
        "quality": {
            "definition": "generic_chess.benchmark.game_quality.profile_from_observations",
            "aggregate": _profile(games),
            "by_sample": by_sample,
            "outcomes": _outcomes(games),
            "paired_outcomes": _paired_outcomes(games),
        },
        "routing": {
            "static": raw_results["routing"]["static"],
            "dynamic": ["REVERSIBILITY_OVERCOMPENSATES_TO_CYCLIC_NONTERMINATION"],
            "overall": [
                "REVERSIBILITY_RESCUE_INSUFFICIENT_KINEMATICALLY",
                "MATE_CAPACITY_UNRESOLVED_DUE_TO_CENSUS_CAP",
                "REVERSIBILITY_OVERCOMPENSATES_TO_CYCLIC_NONTERMINATION",
            ],
            "reason": {
                "directional_dag_obstruction_removed": True,
                "partial_static_kinematic_rescue_on_V5_3": True,
                "checkmate_observed": 1,
                "ongoing_at_32": 15,
                "dynamic_outcomes_dominated_by_censored_nontermination": True,
                "repetition_observed": False,
            },
        },
        "default_generator_changed": False,
        "bfs_expansions": 0,
        "teacher_search_compute": 0,
        "f85_actual_compute": 0,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/f86i_reversibility_rescue/quality_summary.json"),
    )
    args = parser.parse_args()
    payload = build(args.root, args.output)
    print(json.dumps({
        "status": payload["status"],
        "real_games": payload["real_games"],
        "static_candidate_checks": payload["static_candidate_checks"]["total"],
        "scoreable_pair_count": payload["quality"]["paired_outcomes"]["scoreable_pair_count"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
