"""F151: bounded material-vector decision and paired-score microprobe.

This diagnostic keeps the F149 search and score-race contracts unchanged.  It
first compares independent root searches for F144 Gen0 and the historical
sigma-1.40 M140 vector.  Only openings with an observed action disagreement
may enter the small, role-swapped F149 pair probe.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.session.session import GameSession

from scripts import f149_shogi_material_score_race_deep_openings as race
from scripts.f144_shogi_material_only_arena_evolution import (
    GEN0_SEED,
    TYPE_IDS,
    _ordering_values,
    _player,
    _sha,
    _vector_record,
    gen0_vector,
)
from scripts.f145_shogi_material_only_fitness_signal_diagnosis import diagnostic_vectors


ROOT = Path(__file__).resolve().parents[1]
MICROPROBE_SEED = 1_510_101
MICROPROBE_OPENING_COUNT = 32
INITIAL_OPENING_COUNT = 16
MAX_STAGE_B_PAIRS = 2
M140_SEED = 1_440_401
M140_SIGMA = 1.40

SEARCH_LIMITS = SearchLimits(
    max_nodes=1000,
    max_depth=12,
    quiescence_max_depth=4,
    quiescence_hard_max_depth=8,
    deterministic=True,
)


def _canonical_json(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _action_key(action) -> str | None:
    if action is None:
        return None
    return _canonical_json(action if isinstance(action, dict) else action_to_dict(action))


def _new_session(compiled, opening):
    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    return session


def root_probe(compiled, opening, values, ordering_values) -> dict:
    """Run one fresh root search with no TT sharing between vector probes."""
    session = _new_session(compiled, opening)
    player = _player(compiled, tuple(values), ordering_values)
    side_to_move = session.state.position.side_to_move
    decision = player.choose_action(session, SEARCH_LIMITS)
    action = None if decision.action is None else action_to_dict(decision.action)
    return {
        "side_to_move": side_to_move,
        "best_action": action,
        "best_action_key": _action_key(action),
        "score": decision.score,
        "completed_depth": decision.completed_depth,
        "nodes": decision.nodes,
        "qnodes": decision.qnodes,
        "termination_reason": decision.termination_reason,
        "choice_kind": decision.choice_kind,
    }


def _distribution(values: list[int | float]) -> dict:
    if not values:
        return {"count": 0, "values": []}
    return {
        "count": len(values),
        "values": list(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
    }


def _stage_a(compiled, ordering_values, gen0, m140) -> tuple[list, dict, list]:
    openings = race.opening_corpus(compiled, MICROPROBE_SEED, MICROPROBE_OPENING_COUNT)
    rows = []
    first_wave = openings[:INITIAL_OPENING_COUNT]
    for opening in first_wave:
        gen0_probe = root_probe(compiled, opening, gen0, ordering_values)
        m140_probe = root_probe(compiled, opening, m140, ordering_values)
        disagreement = gen0_probe["best_action_key"] != m140_probe["best_action_key"]
        rows.append(
            {
                "opening_id": opening.final_position_key,
                "opening_index": opening.index,
                "opening_target_plies": opening.target_plies,
                "opening_actual_plies": len(opening.actions),
                "gen0": gen0_probe,
                "m140": m140_probe,
                "exact_action_equal": not disagreement,
                "action_disagreement": disagreement,
                "score_difference_m140_minus_gen0": m140_probe["score"] - gen0_probe["score"],
                "node_difference_m140_minus_gen0": m140_probe["nodes"] - gen0_probe["nodes"],
            }
        )
    if sum(row["action_disagreement"] for row in rows) < 2:
        for opening in openings[INITIAL_OPENING_COUNT:]:
            gen0_probe = root_probe(compiled, opening, gen0, ordering_values)
            m140_probe = root_probe(compiled, opening, m140, ordering_values)
            disagreement = gen0_probe["best_action_key"] != m140_probe["best_action_key"]
            rows.append(
                {
                    "opening_id": opening.final_position_key,
                    "opening_index": opening.index,
                    "opening_target_plies": opening.target_plies,
                    "opening_actual_plies": len(opening.actions),
                    "gen0": gen0_probe,
                    "m140": m140_probe,
                    "exact_action_equal": not disagreement,
                    "action_disagreement": disagreement,
                    "score_difference_m140_minus_gen0": m140_probe["score"] - gen0_probe["score"],
                    "node_difference_m140_minus_gen0": m140_probe["nodes"] - gen0_probe["nodes"],
                }
            )
    disagreements = [row for row in rows if row["action_disagreement"]]
    score_differences = [row["score_difference_m140_minus_gen0"] for row in rows]
    depth_values = [
        value
        for row in rows
        for value in (row["gen0"]["completed_depth"], row["m140"]["completed_depth"])
    ]
    node_differences = [row["node_difference_m140_minus_gen0"] for row in rows]
    metadata = {
        "seed": MICROPROBE_SEED,
        "corpus_count": len(openings),
        "initial_count": INITIAL_OPENING_COUNT,
        "processed_count": len(rows),
        "stopped_after_initial_wave": len(rows) == INITIAL_OPENING_COUNT and len(disagreements) >= 2,
        "action_disagreement_count": len(disagreements),
        "action_disagreement_rate": len(disagreements) / len(rows),
        "first_two_divergent_opening_ids": [row["opening_id"] for row in disagreements[:2]],
        "score_difference_distribution": _distribution(score_differences),
        "completed_depth_distribution": _distribution(depth_values),
        "node_difference_distribution_m140_minus_gen0": _distribution(node_differences),
        "termination_reasons": dict(Counter(
            probe["termination_reason"]
            for row in rows
            for probe in (row["gen0"], row["m140"])
        )),
    }
    return rows, metadata, openings


def _trajectory(game: dict) -> list[dict]:
    return [{"actor": step["actor"], "action": step["action"]} for step in game["actions"]]


def _trajectory_sha(trajectory: list[dict]) -> str:
    return hashlib.sha256(_canonical_json(trajectory).encode()).hexdigest()


def _annotate_pair(pair: dict) -> dict:
    games = pair["games"]
    trajectories = [_trajectory(game) for game in games]
    for game, trajectory in zip(games, trajectories):
        game["action_sequence_sha256"] = _trajectory_sha(trajectory)
    pair["role_swapped_action_trajectories_identical"] = trajectories[0] == trajectories[1]
    pair["pair_score_differs_from_half"] = pair["pair_score"] is not None and pair["pair_score"] != 0.5
    return pair


def _stage_b(compiled, ordering_values, gen0, m140, stage_a_rows) -> list[dict]:
    divergent_ids = [row["opening_id"] for row in stage_a_rows if row["action_disagreement"]][:MAX_STAGE_B_PAIRS]
    by_id = {opening.final_position_key: opening for opening in race.opening_corpus(compiled, MICROPROBE_SEED, MICROPROBE_OPENING_COUNT)}
    pairs = []
    for opening_id in divergent_ids:
        opening = by_id[opening_id]
        pair = race._pair_task(
            {
                "opening": race.v2._opening_payload(opening),
                "champion": list(gen0),
                "child": list(m140),
                "ordering_values": ordering_values,
                "max_nodes": 1000,
            }
        )
        pairs.append(_annotate_pair(pair))
    return pairs


def _classification(stage_a_rows: list[dict], stage_b_pairs: list[dict]) -> str:
    if not any(row["action_disagreement"] for row in stage_a_rows):
        return "MATERIAL_VECTOR_NO_ABP_DECISION_LEVERAGE_MICROPROBE"
    if stage_b_pairs and all(not pair["valid"] for pair in stage_b_pairs):
        return "MATERIAL_VECTOR_CHANGES_DECISIONS_BUT_SCORE_RACE_UNSCORABLE_MICROPROBE"
    if any(pair["valid"] and pair["pair_score_differs_from_half"] for pair in stage_b_pairs):
        return "MATERIAL_VECTOR_PRODUCES_PAIRED_SCORE_DISCRIMINATION_MICROPROBE"
    return "MATERIAL_VECTOR_CHANGES_DECISIONS_BUT_PAIRED_SCORE_CANCELS_MICROPROBE"


def run(*, output: Path) -> dict:
    compiled = race._compile()
    ordering_values = _ordering_values(compiled)
    gen0 = tuple(gen0_vector(GEN0_SEED))
    vectors = diagnostic_vectors()
    expected_gen0 = (250, 634, 1000, 3195, 433, 1155, 3613, 658, 1351, 1822, 2299, 856, 240)
    if gen0 != expected_gen0 or tuple(vectors["Gen0"]) != expected_gen0:
        raise RuntimeError("Gen0 vector parity failure")
    m140 = tuple(vectors["M140"])
    if m140 == gen0:
        raise RuntimeError("M140 must differ from Gen0")
    stage_a_rows, stage_a, openings = _stage_a(compiled, ordering_values, gen0, m140)
    stage_b_pairs = [] if not any(row["action_disagreement"] for row in stage_a_rows) else _stage_b(compiled, ordering_values, gen0, m140, stage_a_rows)
    classification = _classification(stage_a_rows, stage_b_pairs)
    result = {
        "schema": "F151_SHOGI_MATERIAL_PAIRED_SCORE_MICROPROBE_V1",
        "classification": classification,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "type_ids": list(TYPE_IDS),
        "vectors": {
            "Gen0": {"seed": GEN0_SEED, **_vector_record(gen0)},
            "M140": {"seed": M140_SEED, "sigma": M140_SIGMA, **_vector_record(m140)},
        },
        "score_race": {
            "source": "F149 deep-opening score race",
            "threshold": race.SCORE_THRESHOLD,
            "capture_points": race.CAPTURE_POINTS,
            "check_points": race.CHECK_POINTS,
            "capture_plus_check_points": 2,
            "formal_core_winner_precedence": True,
            "unequal_nondecisive_terminal": "score_tiebreak",
            "equal_nondecisive_terminal": "invalid",
            "safety_max_plies": race.SAFETY_MAX_PLIES,
        },
        "search": {
            "max_nodes": SEARCH_LIMITS.max_nodes,
            "max_depth": SEARCH_LIMITS.max_depth,
            "qdepth": [SEARCH_LIMITS.quiescence_max_depth, SEARCH_LIMITS.quiescence_hard_max_depth],
            "tt_max_entries": race.TT_MAX_ENTRIES,
            "tuning": "SearchTuning()",
            "fixed_ordering_values": ordering_values,
            "fixed_ordering_sha256": _sha(ordering_values),
            "fresh_player_per_root_probe": True,
            "tt_reused_between_vectors": False,
        },
        "opening_contract": {
            "seed": MICROPROBE_SEED,
            "count": MICROPROBE_OPENING_COUNT,
            "min_plies": race.OPENING_MIN_PLIES,
            "max_plies": race.OPENING_MAX_PLIES,
            "evaluator_neutral": True,
            "stage_b_reuses_stage_a_openings_only_for_diagnostic_pairing": True,
        },
        "stage_a": stage_a,
        "stage_a_rows": stage_a_rows,
        "stage_b": {
            "max_pairs": MAX_STAGE_B_PAIRS,
            "selected_opening_ids": [pair["opening_id"] for pair in stage_b_pairs],
            "pairs": stage_b_pairs,
            "valid_pair_count": sum(pair["valid"] for pair in stage_b_pairs),
            "non_0_5_valid_pair_count": sum(pair["valid"] and pair["pair_score_differs_from_half"] for pair in stage_b_pairs),
        },
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(output=args.output)
    print(json.dumps({"classification": result["classification"], "stage_a_processed": result["stage_a"]["processed_count"], "stage_b_pairs": len(result["stage_b"]["pairs"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
