"""Replay-only diagnosis of why the F158 score race missed threshold 10.

This module deliberately performs no player/root/AlphaBeta search and launches
no new game. It rebuilds the one recorded opening, replays the two saved
trajectories, and enumerates legal moves only to count immediate score events.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.core.transition import apply_action
from generic_chess.session.result import SessionStatus
from generic_chess.session.session import GameSession
from scripts import f149_shogi_material_score_race_deep_openings as race

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_GAMES = 2
EXPECTED_GAMES_STARTED = 2
THRESHOLDS = tuple(range(1, 11))


def _canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _piece_counts(position, compiled) -> dict:
    on_board = [0, 0]
    for piece in position.board:
        if piece is not None and not compiled.types_by_id[piece.current_type_id].is_anchor:
            on_board[piece.owner] += 1
    in_hand = [
        sum(count for type_id, count in hand.items()
            if not compiled.types_by_id[type_id].is_anchor)
        for hand in position.hands
    ]
    return {
        "on_board_non_anchor_by_side": on_board,
        "in_hand_non_anchor_by_side": in_hand,
        "total_non_anchor_by_side": [on_board[i] + in_hand[i] for i in (0, 1)],
    }


def _reversal_metrics(actions: list[dict]) -> dict:
    prior_by_actor: dict[int, list[tuple[int, tuple[int, int], tuple[int, int]]]] = {0: [], 1: []}
    exact_counts: Counter[str] = Counter()
    exact_plies: dict[str, list[int]] = {}
    immediate, repeated, reversal_plies = [], [], set()
    last_move_by_actor: dict[int, tuple[int, tuple[int, int], tuple[int, int]]] = {}
    for ply, row in enumerate(actions, 1):
        action = row["action"]
        actor = int(row["actor"])
        exact_key = _canonical({"actor": actor, "action": action})
        exact_counts[exact_key] += 1
        exact_plies.setdefault(exact_key, []).append(ply)
        origin, target = tuple(action["from"]), tuple(action["to"])
        inverses = [
            prior for prior in prior_by_actor[actor]
            if prior[1] == target and prior[2] == origin
        ]
        if inverses:
            reversal_plies.add(ply)
            previous_actor_move = last_move_by_actor.get(actor)
            if previous_actor_move and previous_actor_move[1] == target and previous_actor_move[2] == origin:
                immediate.append({"ply": ply, "prior_ply": previous_actor_move[0], "actor": actor})
            else:
                repeated.append({"ply": ply, "prior_plies": [item[0] for item in inverses], "actor": actor})
        move = (ply, origin, target)
        prior_by_actor[actor].append(move)
        last_move_by_actor[actor] = move
    repeated_exact = [
        {"action_key": key, "plies": plies, "repeat_count": len(plies) - 1}
        for key, plies in exact_plies.items() if len(plies) > 1
    ]
    return {
        "exact_move_definition": "same actor and exact serialized action repeated",
        "exact_repeated_distinct_moves": len(repeated_exact),
        "exact_repeat_occurrences_after_first": sum(row["repeat_count"] for row in repeated_exact),
        "exact_repeated_moves": repeated_exact,
        "reversal_definition": "same actor later moves from the prior move's destination back to its origin; piece identity is not inferred",
        "immediate_reversal_count": len(immediate),
        "immediate_reversals": immediate,
        "repeated_reversal_count": len(repeated),
        "repeated_reversals": repeated,
        "reversal_ply_indices": sorted(reversal_plies),
    }


def _counterfactual_thresholds(actions: list[dict]) -> list[dict]:
    scores = [0, 0]
    reached: dict[int, dict | None] = {threshold: None for threshold in THRESHOLDS}
    for ply, row in enumerate(actions, 1):
        actor = int(row["actor"])
        scores[actor] += int(row["points"])
        for threshold in THRESHOLDS:
            if reached[threshold] is None and scores[actor] >= threshold:
                reached[threshold] = {"scored_ply": ply, "side": actor, "scores": list(scores)}
    return [
        {
            "threshold": threshold,
            "reached_on_recorded_trajectory": reached[threshold] is not None,
            "first_reach": reached[threshold],
            "max_final_score": max(scores),
        }
        for threshold in THRESHOLDS
    ]


def _summarize_trajectory(actions: list[dict], opening_plies: int) -> dict:
    count = len(actions)
    positive = [i for i, row in enumerate(actions, 1) if int(row["points"]) > 0]
    capture_by_side = [0, 0]
    check_by_side = [0, 0]
    pieces = Counter()
    for row in actions:
        actor = int(row["actor"])
        capture_by_side[actor] += int(row["capture"])
        check_by_side[actor] += int(row["check"])
        pieces[row["action"].get("actor_type_id", "UNKNOWN")] += 1

    zero_intervals, start = [], None
    for ply, row in enumerate(actions, 1):
        if int(row["points"]) == 0 and start is None:
            start = ply
        if int(row["points"]) > 0 and start is not None:
            zero_intervals.append({"start_ply": start, "end_ply": ply - 1, "length": ply - start})
            start = None
    if start is not None:
        zero_intervals.append({"start_ply": start, "end_ply": count, "length": count - start + 1})

    cumulative = [0, 0]
    points_at_quantiles = {}
    scored_so_far = 0
    checkpoints = {max(1, math.ceil(count * q)): f"{int(q * 100)}%" for q in (0.25, 0.5, 0.75, 1.0)}
    for ply, row in enumerate(actions, 1):
        cumulative[int(row["actor"])] += int(row["points"])
        scored_so_far = ply
        if ply in checkpoints:
            points_at_quantiles[checkpoints[ply]] = {
                "scored_ply": ply,
                "trajectory_fraction": ply / count if count else 0,
                "scores": list(cumulative),
            }

    reversals = _reversal_metrics(actions)
    zero_plies = {i for i, row in enumerate(actions, 1) if int(row["points"]) == 0}
    repeat_plies = {
        ply
        for move in reversals["exact_repeated_moves"]
        for ply in move["plies"][1:]
    }
    repeat_or_reversal_zero_plies = zero_plies & (
        repeat_plies | set(reversals["reversal_ply_indices"])
    )
    return {
        "opening_plies": opening_plies,
        "scored_ply_count": count,
        "capture_event_count_by_side": capture_by_side,
        "check_event_count_by_side": check_by_side,
        "positive_scored_ply_indices": positive,
        "first_scoring_ply": positive[0] if positive else None,
        "last_scoring_ply": positive[-1] if positive else None,
        "longest_zero_point_interval": max(zero_intervals, key=lambda row: row["length"], default=None),
        "zero_point_intervals": zero_intervals,
        "positive_scored_plies": len(positive),
        "positive_ply_fraction": len(positive) / count if count else 0,
        "cumulative_scores_at_trajectory_quartiles": points_at_quantiles,
        "action_counts_by_moving_piece_type": dict(sorted(pieces.items())),
        "repetition_and_reversal": reversals,
        "zero_point_plies_in_repeated_move_or_reversal_pattern": len(repeat_or_reversal_zero_plies),
        "zero_point_plies_in_repeated_move_or_reversal_pattern_indices": sorted(repeat_or_reversal_zero_plies),
        "counterfactual_thresholds_1_to_10": _counterfactual_thresholds(actions),
    }


def _analyze_game(compiled, opening, game: dict) -> dict:
    session = GameSession(compiled)
    for action in opening.actions:
        session.submit(action)
    opening_plies = len(opening.actions)
    expected_actions = game["actions"]
    calculated_scores = [0, 0]
    root_rows = []
    replayed_actions = []

    for scored_ply, recorded in enumerate(expected_actions, 1):
        if session.result.status is not SessionStatus.ONGOING:
            raise AssertionError(f"game ended before recorded scored ply {scored_ply}")
        mover = session.state.position.side_to_move
        if int(recorded["actor"]) != mover:
            raise AssertionError(f"actor mismatch at scored ply {scored_ply}")
        before_state = session.state
        before = before_state.position
        legal = session.legal_actions()
        legal_capture_moves = legal_check_moves = legal_any_score_moves = 0
        for candidate in legal:
            after = apply_action(before_state, candidate, compiled)
            event = race.score_event(before, candidate, after.position, mover, compiled)
            legal_capture_moves += int(event["capture"] > 0)
            legal_check_moves += int(event["check"] > 0)
            legal_any_score_moves += int(event["points"] > 0)

        expected_action = recorded["action"]
        action = race.v2.action_from_dict(expected_action)
        actual_action = race.v2.action_to_dict(action)
        if actual_action != expected_action:
            raise AssertionError(f"action serialization mismatch at scored ply {scored_ply}")
        if action not in legal:
            raise AssertionError(f"recorded action is illegal at scored ply {scored_ply}")
        after_state = apply_action(before_state, action, compiled)
        event = race.score_event(before, action, after_state.position, mover, compiled)
        calculated_scores[mover] += int(event["points"])
        expected_scores = [int(value) for value in recorded["scores"]]
        if event != {key: recorded[key] for key in ("capture", "check", "points")}:
            raise AssertionError(f"recorded score event mismatch at scored ply {scored_ply}")
        if calculated_scores != expected_scores:
            raise AssertionError(f"cumulative score mismatch at scored ply {scored_ply}")

        root_rows.append({
            "scored_ply": scored_ply,
            "total_game_ply": opening_plies + scored_ply,
            "mover": mover,
            "legal_action_count": len(legal),
            "legal_capture_action_count": legal_capture_moves,
            "legal_check_action_count": legal_check_moves,
            "legal_any_score_action_count": legal_any_score_moves,
            "chosen_action_capture": int(event["capture"]),
            "chosen_action_check": int(event["check"]),
            "chosen_action_points": int(event["points"]),
            "chosen_zero_score_while_scoring_action_available": bool(
                event["points"] == 0 and legal_any_score_moves > 0
            ),
            "scores_after_ply": list(calculated_scores),
            "remaining_non_anchor_pieces": _piece_counts(before, compiled),
        })
        session.submit(action)
        replayed_actions.append({"actor": mover, "action": actual_action, **event, "scores": list(calculated_scores)})

    if replayed_actions != expected_actions:
        raise AssertionError("replayed trajectory differs from recorded actions/events")
    if len(session.history) != int(game["plies"]):
        raise AssertionError("final total ply count mismatch")
    if calculated_scores != [int(value) for value in game["scores"]]:
        raise AssertionError("final score mismatch")
    if int(game["scored_plies"]) != len(expected_actions):
        raise AssertionError("recorded scored-ply count mismatch")
    if session.result.status is not SessionStatus.ONGOING:
        replay_winner, replay_reason = session.result.winner, session.result.status.value
        replay_valid = replay_winner is not None
        replay_cause = replay_reason
    else:
        replay_cause = "max_plies"
        replay_winner, replay_reason, replay_valid = race.resolve_terminal(session.result, calculated_scores)
    if replay_winner != game["winner"] or replay_reason != game["result"] or bool(replay_valid) != bool(game["valid"]):
        raise AssertionError("terminal/tiebreak result mismatch")
    if replay_cause != game["terminal_cause"]:
        raise AssertionError("terminal cause mismatch")

    summary = _summarize_trajectory(replayed_actions, opening_plies)
    no_opportunity_roots = sum(row["legal_any_score_action_count"] == 0 for row in root_rows)
    opportunity_roots = len(root_rows) - no_opportunity_roots
    available_but_not_chosen = sum(row["chosen_zero_score_while_scoring_action_available"] for row in root_rows)
    zero_point_roots = sum(row["chosen_action_points"] == 0 for row in root_rows)
    summary["legal_action_analysis"] = {
        "recorded_roots": len(root_rows),
        "root_rows_with_no_legal_scoring_action": no_opportunity_roots,
        "root_fraction_with_no_legal_scoring_action": no_opportunity_roots / len(root_rows) if root_rows else 0,
        "root_rows_with_at_least_one_legal_scoring_action": opportunity_roots,
        "chosen_zero_score_when_scoring_was_available": available_but_not_chosen,
        "fraction_of_opportunity_roots_choosing_zero_score": available_but_not_chosen / opportunity_roots if opportunity_roots else None,
        "zero_score_chosen_plies": zero_point_roots,
        "per_ply": root_rows,
    }
    summary["replay_validation"] = {
        "opening_identity_matches": True,
        "all_actions_legal_and_identical": True,
        "all_score_events_and_cumulative_scores_match": True,
        "total_plies_match": True,
        "final_scores_match": True,
        "terminal_cause": replay_cause,
        "winner": replay_winner,
        "result": replay_reason,
        "valid": bool(replay_valid),
    }
    summary["side_roles"] = {
        "child_owner": int(game["child_owner"]),
        "winner": replay_winner,
        "child_won": replay_winner == int(game["child_owner"]),
        "final_scores_by_side": list(calculated_scores),
    }
    return summary


def _mechanism_assessment(games: list[dict]) -> dict:
    roots = [row for game in games for row in game["legal_action_analysis"]["per_ply"]]
    zero_roots = [row for row in roots if row["chosen_action_points"] == 0]
    no_opportunity = sum(row["legal_any_score_action_count"] == 0 for row in roots)
    opportunity = len(roots) - no_opportunity
    missed = sum(row["chosen_zero_score_while_scoring_action_available"] for row in roots)
    cycling = len({
        (game_index, ply)
        for game_index, game in enumerate(games)
        for ply in game["zero_point_plies_in_repeated_move_or_reversal_pattern_indices"]
    })
    total_roots = len(roots)
    zero_count = len(zero_roots)
    # “Materially contributes” is operationalized transparently as a strict
    # majority of the relevant roots/zero-score plies, not a hidden model.
    contributions = []
    if total_roots and no_opportunity > total_roots / 2:
        contributions.append("SCORING_OPPORTUNITY_SCARCITY")
    if opportunity and missed > opportunity / 2:
        contributions.append("AVAILABLE_SCORE_NOT_SELECTED")
    if zero_count and cycling > zero_count / 2:
        contributions.append("REPETITIVE_ZERO_SCORE_CYCLING")
    classification = "MIXED" if len(contributions) > 1 else contributions[0] if contributions else "NO_SINGLE_MECHANISM_DOMINATES"
    return {
        "classification": classification,
        "material_contribution_rule": "a proposed mechanism materially contributes when it applies to a strict majority of its stated denominator",
        "scoring_opportunity_scarcity": {
            "no_opportunity_roots": no_opportunity,
            "all_recorded_roots": total_roots,
            "rate": no_opportunity / total_roots if total_roots else None,
            "materially_contributes": "SCORING_OPPORTUNITY_SCARCITY" in contributions,
        },
        "available_score_not_selected": {
            "zero_score_chosen_with_opportunity": missed,
            "roots_with_opportunity": opportunity,
            "rate": missed / opportunity if opportunity else None,
            "materially_contributes": "AVAILABLE_SCORE_NOT_SELECTED" in contributions,
        },
        "repetitive_zero_score_cycling": {
            "zero_score_plies_in_repeated_exact_move_or_reversal": cycling,
            "all_zero_score_plies": zero_count,
            "rate": cycling / zero_count if zero_count else None,
            "materially_contributes": "REPETITIVE_ZERO_SCORE_CYCLING" in contributions,
        },
        "contributing_mechanisms": contributions,
        "recorded_scored_plies": total_roots,
        "recorded_zero_score_plies": zero_count,
    }


def run(*, result_path: Path, output_path: Path) -> dict:
    raw_bytes = result_path.read_bytes()
    source = json.loads(raw_bytes.decode("utf-8"))
    if source.get("schema") != "F158_SHOGI_SIGMA070_SINGLE_PAIR_CAUSAL_DIAGNOSTIC_V1":
        raise ValueError("unexpected source result schema")
    if source.get("bounds", {}).get("games_started") != EXPECTED_GAMES_STARTED:
        raise ValueError("expected exactly two completed F158 games")
    if len(source.get("games", [])) != EXPECTED_GAMES:
        raise ValueError("expected exactly two recorded games")

    compiled = race._compile()
    openings = race.opening_corpus(
        compiled, int(source["opening"]["seed"]), int(source["opening"]["count"])
    )
    if len(openings) != 1:
        raise AssertionError("could not reconstruct the one recorded opening")
    opening = openings[0]
    if opening.final_position_key != source["opening"]["opening_id"]:
        raise AssertionError("reconstructed opening identity mismatch")
    if len(opening.actions) != int(source["opening"]["actual_plies"]):
        raise AssertionError("reconstructed opening ply count mismatch")

    games = [_analyze_game(compiled, opening, game) for game in source["games"]]
    total_roots = sum(game["scored_ply_count"] for game in games)
    total_capture_events = [sum(game["capture_event_count_by_side"][side] for game in games) for side in (0, 1)]
    total_check_events = [sum(game["check_event_count_by_side"][side] for game in games) for side in (0, 1)]
    result = {
        "schema": "F158_SHOGI_SCORE_EVENT_ACCRUAL_CAUSE_REPLAY_V1",
        "diagnostic_type": "CAUSAL_DIAGNOSTIC",
        "classification": "REPLAY_AND_LEGAL_ACTION_ANALYSIS_COMPLETE",
        "source_result_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "source_run_id": source.get("run_id"),
        "source_published_git_sha": source.get("git_sha"),
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "opening": {
            "seed": source["opening"]["seed"],
            "opening_id": opening.final_position_key,
            "opening_plies": len(opening.actions),
            "reconstructed_identity_matches": True,
        },
        "unknown": "whether sparse score-event accrual is due to few legal scoring opportunities, zero-score choices despite opportunities, or repetitive zero-score cycling",
        "no_new_game_or_search": True,
        "analysis_method": "deterministic GameSession replay plus direct apply_action/score_event evaluation of every legal move at each recorded root; no player or AlphaBeta search",
        "score_event_totals_by_side": {
            "capture_events": total_capture_events,
            "check_events": total_check_events,
            "points": [
                total_capture_events[side] + total_check_events[side] for side in (0, 1)
            ],
        },
        "mechanism_assessment": _mechanism_assessment(games),
        "games": games,
        "trajectory_scored_plies": total_roots,
        "counterfactual_threshold_scope": "descriptive replay only; no threshold/weight change is authorized",
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    }
    if output_path.exists():
        raise FileExistsError(f"refusing to overwrite replay analysis: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp = output_path.with_name(output_path.name + ".tmp")
    temp.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(output_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(result_path=args.result, output_path=args.output)
    assessment = result["mechanism_assessment"]
    print(json.dumps({
        "classification": assessment["classification"],
        "recorded_scored_plies": result["trajectory_scored_plies"],
        "capture_events_by_side": result["score_event_totals_by_side"]["capture_events"],
        "check_events_by_side": result["score_event_totals_by_side"]["check_events"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
