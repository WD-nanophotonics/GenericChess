"""Corrected single-entry Gate 2 competence benchmark.

The benchmark executes actual directional microproblems, then (only if every
microproblem passes) runs initial and fixed shallow-opening role-swapped
30-ply games on Chess, Shogi, and five fixed generated rulesets. The deployed
1000-node rule-prior player is compared with a 128-node weak ABP and an
8000-node reviewer, except that certified mate-in-three tasks guarantee a
complete depth-3 search and controlled immediate-material tasks use their
exact depth-1 horizon. The first real hard failure stops the run.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.search import terminal_score
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import (
    action_is_board,
    action_is_drop,
    action_drop_base_type_id,
    action_promotion_target_id,
    action_source_square,
    action_target_square,
    action_to_dict,
)
from generic_chess.core.attacks import is_in_check
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.position import HistoryRecord
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import initial_state
from generic_chess.learning.shogi_rules import sfen_to_gc_state
from generic_chess.rules.compiler import compile_ruleset, compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession
from scripts import f86q_check_forcing_depth3_probe as f86q
from scripts.audit_f24f_western_chess_perft import position_from_fen


ROOT = Path(__file__).resolve().parents[1]
GATE1_CHECKPOINT = "0c47b355bc34ab1cdff605bb49ec63714058be96"
GENERATED_SOURCE = ROOT / "artifacts/f86o_common_tape_triarm_dynamic_smoke/manifest.json"
GENERATED_COUNT = 5
MAX_PLIES = 30
OPENING_PLIES = 4
PRIMARY_NODES = 1000
WEAK_NODES = 128
REVIEW_NODES = 8000
TREND_PLIES = (10, 20, 30)
PASS_RATIO = 0.5
OBVIOUS_REGRET = 0.5
CAPABILITY_STATE_LIMIT = 240
CAPABILITY_BRANCH_LIMIT = 4
TASK_ORDER = (
    "mate_in_one",
    "mate_in_three",
    "avoid_immediate_mate",
    "extreme_material",
    "mobility",
    "anchor_danger",
    "promotion",
    "drop",
)


def _action_key(action):
    return json.dumps(action_to_dict(action), sort_keys=True, separators=(",", ":"))


def _successors(state, compiled):
    return f86q._canonical_successors(state, compiled)


def _limits(nodes):
    return SearchLimits(
        max_nodes=nodes,
        quiescence_max_depth=0,
        quiescence_hard_max_depth=0,
    )


def _fixed_depth_limits(depth):
    return SearchLimits(
        max_depth=depth,
        max_nodes=None,
        quiescence_max_depth=0,
        quiescence_hard_max_depth=0,
    )


def _session_with_state(compiled, state, witnesses):
    session = GameSession(compiled)
    session._state = state
    session._search_history_witnesses = tuple(witnesses)
    return session


def _make_player(compiled, profile, config):
    return AlphaBetaPlayer(
        compiled,
        evaluation_config=config,
        evaluator_override=Evaluator(compiled, profile, config),
        use_disk_cache=False,
        use_tt=False,
        use_ordering=False,
        use_native_semantic_legality=False,
    )


def _decision(compiled, profile, config, state, witnesses, nodes):
    return _make_player(compiled, profile, config).choose_action(
        _session_with_state(compiled, state, witnesses), _limits(nodes)
    )


def _fixed_depth_decision(compiled, profile, config, state, witnesses, depth):
    return _make_player(compiled, profile, config).choose_action(
        _session_with_state(compiled, state, witnesses), _fixed_depth_limits(depth)
    )


def _decision_telemetry(decision, search_limit_mode, *, max_nodes, max_depth):
    return {
        "selected_action": (
            None if decision.action is None else action_to_dict(decision.action)
        ),
        "nodes": decision.nodes + decision.qnodes,
        "completed_depth": decision.completed_depth,
        "termination_reason": decision.termination_reason,
        "search_limit_mode": search_limit_mode,
        "max_nodes": max_nodes,
        "max_depth": max_depth,
    }


def _in_check(state, owner, compiled):
    engine = semantic_engine_for(compiled)
    if engine is not None:
        return engine.in_check(state.position, owner)
    return is_in_check(state.position, owner, compiled)


def _mate_in_one_actions(state, compiled):
    actor = state.position.side_to_move
    return tuple(
        action
        for action, child in _successors(state, compiled)
        if child.terminal_status.status is TerminalStatus.CHECKMATE
        and child.terminal_status.winner == actor
    )


def _has_mate_in_one(state, compiled):
    return bool(_mate_in_one_actions(state, compiled))


def _forced_mate_in_exactly_three(state, action, compiled):
    """True only for a non-immediate move forcing mate on the third ply."""
    actor = state.position.side_to_move
    child = next(child for candidate, child in _successors(state, compiled) if candidate == action)
    if child.terminal_status.status is TerminalStatus.CHECKMATE:
        return False
    replies = _successors(child, compiled)
    if not replies:
        return False
    return all(
        any(
            continuation.terminal_status.status is TerminalStatus.CHECKMATE
            and continuation.terminal_status.winner == actor
            for _continuation_action, continuation in _successors(reply_child, compiled)
        )
        for _reply, reply_child in replies
    )


def _forced_mate_within_three_actions(state, compiled):
    immediate = set(_mate_in_one_actions(state, compiled))
    return tuple(
        action
        for action, _child in _successors(state, compiled)
        if action in immediate or _forced_mate_in_exactly_three(state, action, compiled)
    )


def _fixed_state_from_position(compiled, position):
    base = initial_state(compiled)
    key = repetition_identity_key(position, compiled)
    engine = semantic_engine_for(compiled)
    if engine is not None:
        status = engine.terminal_result(position, 0, ((key, 1),))
    else:
        from generic_chess.core.terminal import terminal_result

        status = terminal_result(
            replace(base, position=position, repetition_counts=((key, 1),)), compiled
        )
    return replace(
        base,
        position=position,
        repetition_counts=((key, 1),),
        terminal_status=status,
        history=(HistoryRecord(key, -1, "", False),),
    )


def _special_states(label, compiled):
    states = [("initial", initial_state(compiled))]
    if label == "chess":
        fens = (
            ("mate_one", "7k/6Q1/5K2/8/8/8/8/8 w - - 0 1"),
            ("mate_three", "2r5/4np2/1p1k2p1/p1R1br2/Pp1P3p/3QPP2/1B2N2P/4K2R w - - 12 41"),
            ("avoid_immediate_mate", "rnb1k2r/pp1p2pp/2p2p2/PBb5/3qn2P/5NP1/RPP2P2/1NBQ1K1R w kq - 2 14"),
            ("promotion", "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"),
        )
        states.extend(
            (name, _fixed_state_from_position(compiled, position_from_fen(fen, compiled)))
            for name, fen in fens
        )
    elif label == "shogi":
        sfens = (
            ("mate_one", "2B2s3/l1r3g1l/8n/pG1k4S/1g1pPG2p/P1PP1PPP1/N1+n4RP/L1S3K1L/b6N1 b 6Psp 139"),
            ("mate_three", "5s3/l1G4gl/4k1p1n/pG6S/1N1pPG2p/P1PP1PPP1/2+n1sKNRP/L1S5L/b3b4 w R6P 150"),
            ("avoid_immediate_mate", "+N+N+P2s2b/5p3/l2+Pl2k1/g1P2P2p/1rp+B1KP1g/L2p+s4/Pn3s3/pg5Sl/1N2PR2G b 2P4p 245"),
            ("drop", "ln4rnl/1gk1gs3/3ps1p1b/p1p2p1pp/1P1P5/PpR1p1PPP/4PP1S1/4G3L/LNSKG2NB b P 59"),
            ("promotion", "8k/7P1/9/9/9/9/9/9/4K4 w - 1"),
        )
        states.extend((name, sfen_to_gc_state(compiled, sfen)) for name, sfen in sfens)
    return states


def _expected_set(actions, values):
    high = max(values)
    low = min(values)
    if high == low:
        return ()
    return tuple(action for action, value in zip(actions, values) if value == high)


def _capture_value(state, action, compiled, profile):
    if not action_is_board(action):
        return 0
    target = action_target_square(action)
    captured = state.position.board[target.rank * compiled.board_size + target.file]
    if captured is None or captured.owner == state.position.side_to_move:
        return 0
    return int(profile.board_value_by_type[captured.current_type_id])


def _task_witnesses(label, compiled, profile, config):
    witnesses = {name: None for name in TASK_ORDER}
    evaluator = Evaluator(compiled, profile, config)
    queue = list(_special_states(label, compiled))
    seen = set()
    cursor = 0
    while cursor < len(queue) and cursor < CAPABILITY_STATE_LIMIT:
        state_label, state = queue[cursor]
        cursor += 1
        key = (
            state.position.side_to_move,
            tuple(state.position.board),
            state.position.hands,
        )
        if key in seen or state.terminal_status.status is not TerminalStatus.ONGOING:
            continue
        seen.add(key)
        successors = _successors(state, compiled)
        if not successors:
            continue
        actions = tuple(action for action, _child in successors)

        if label in {"chess", "shogi"}:
            mate_one = _mate_in_one_actions(state, compiled)
            if mate_one and witnesses["mate_in_one"] is None:
                witnesses["mate_in_one"] = (state_label, state, mate_one)
            if witnesses["mate_in_three"] is None and not mate_one:
                mate_three = tuple(
                    action
                    for action, _child in successors
                    if _forced_mate_in_exactly_three(state, action, compiled)
                )
                if mate_three:
                    witnesses["mate_in_three"] = (state_label, state, mate_three)
            if witnesses["avoid_immediate_mate"] is None:
                unsafe = tuple(
                    action for action, child in successors if _has_mate_in_one(child, compiled)
                )
                safe = tuple(action for action, child in successors if not _has_mate_in_one(child, compiled))
                if safe and unsafe:
                    witnesses["avoid_immediate_mate"] = (state_label, state, safe)

        if witnesses["extreme_material"] is None:
            capture_values = tuple(
                _capture_value(state, action, compiled, profile) for action in actions
            )
            positive_values = tuple(value for value in capture_values if value > 0)
            all_children_nonterminal = all(
                not child.terminal_status.is_terminal for _action, child in successors
            )
            if (
                all_children_nonterminal
                and len(positive_values) >= 2
                and len(set(positive_values)) >= 2
            ):
                max_capture_value = max(positive_values)
                expected = tuple(
                    action
                    for action, value in zip(actions, capture_values)
                    if value == max_capture_value
                )
                one_ply_scores = tuple(
                    -evaluator.evaluate(child) for _action, child in successors
                )
                best_score = max(one_ply_scores)
                one_ply_best = tuple(
                    action
                    for action, score in zip(actions, one_ply_scores)
                    if score == best_score
                )
                if set(one_ply_best) == set(expected):
                    witnesses["extreme_material"] = (
                        state_label,
                        state,
                        expected,
                        {
                            "legal_action_count": len(actions),
                            "all_children_nonterminal": True,
                            "positive_capture_action_count": len(positive_values),
                            "positive_capture_value_set": sorted(set(positive_values)),
                            "max_capture_value": max_capture_value,
                            "one_ply_best_actions": [
                                action_to_dict(action) for action in one_ply_best
                            ],
                        },
                    )

        if witnesses["mobility"] is None:
            expected = _expected_set(
                actions,
                tuple(-len(_successors(child, compiled)) for _action, child in successors),
            )
            if expected:
                witnesses["mobility"] = (state_label, state, expected)

        if witnesses["anchor_danger"] is None:
            check_flags = tuple(
                _in_check(child, child.position.side_to_move, compiled)
                for _action, child in successors
            )
            expected = tuple(action for action, gives_check in zip(actions, check_flags) if gives_check)
            if expected and len(expected) < len(actions):
                witnesses["anchor_danger"] = (state_label, state, expected)

        if witnesses["promotion"] is None:
            all_children_nonterminal = all(
                not child.terminal_status.is_terminal for _action, child in successors
            )
            if all_children_nonterminal:
                one_ply_scores = {
                    action: -evaluator.evaluate(child)
                    for action, child in successors
                }
                groups = {}
                for action in actions:
                    if not action_is_board(action):
                        continue
                    key = (action_source_square(action), action_target_square(action))
                    groups.setdefault(key, []).append(action)
                optional_groups = []
                favorable_groups = []
                for (source, target), group_actions in groups.items():
                    promoted = tuple(
                        action
                        for action in group_actions
                        if action_promotion_target_id(action) is not None
                    )
                    unpromoted = tuple(
                        action
                        for action in group_actions
                        if action_promotion_target_id(action) is None
                    )
                    if not promoted or not unpromoted:
                        continue
                    optional_groups.append((source, target, promoted, unpromoted))
                    best_promoted = max(one_ply_scores[action] for action in promoted)
                    best_unpromoted = max(one_ply_scores[action] for action in unpromoted)
                    if best_promoted > best_unpromoted:
                        favorable_groups.append(
                            {
                                "source": [source.file, source.rank],
                                "target": [target.file, target.rank],
                                "promoted": [
                                    {
                                        "action": action_to_dict(action),
                                        "one_ply_score": one_ply_scores[action],
                                    }
                                    for action in promoted
                                ],
                                "unpromoted": [
                                    {
                                        "action": action_to_dict(action),
                                        "one_ply_score": one_ply_scores[action],
                                    }
                                    for action in unpromoted
                                ],
                                "score_advantage": best_promoted - best_unpromoted,
                            }
                        )
                global_best_score = max(one_ply_scores.values())
                one_ply_best = tuple(
                    action
                    for action in actions
                    if one_ply_scores[action] == global_best_score
                )
                favorable_promoted_actions = {
                    action
                    for _source, _target, promoted, unpromoted in optional_groups
                    if max(one_ply_scores[action] for action in promoted)
                    > max(one_ply_scores[action] for action in unpromoted)
                    for action in promoted
                }
                if (
                    favorable_groups
                    and all(
                        action_promotion_target_id(action) is not None
                        for action in one_ply_best
                    )
                    and any(
                        action in favorable_promoted_actions for action in one_ply_best
                    )
                ):
                    witnesses["promotion"] = (
                        state_label,
                        state,
                        one_ply_best,
                        {
                            "legal_action_count": len(actions),
                            "all_children_nonterminal": True,
                            "optional_promotion_group_count": len(optional_groups),
                            "promotion_favorable_group_count": len(favorable_groups),
                            "one_ply_best_actions": [
                                action_to_dict(action) for action in one_ply_best
                            ],
                            "promotion_favorable_groups": favorable_groups,
                        },
                    )

        if witnesses["drop"] is None:
            drops = tuple(action for action in actions if action_is_drop(action))
            non_drops = tuple(action for action in actions if not action_is_drop(action))
            all_children_nonterminal = all(
                not child.terminal_status.is_terminal for _action, child in successors
            )
            if all_children_nonterminal and drops and non_drops:
                one_ply_scores = {
                    action: -evaluator.evaluate(child)
                    for action, child in successors
                }
                best_drop_score = max(one_ply_scores[action] for action in drops)
                best_non_drop_score = max(
                    one_ply_scores[action] for action in non_drops
                )
                global_best_score = max(one_ply_scores.values())
                one_ply_best = tuple(
                    action
                    for action in actions
                    if one_ply_scores[action] == global_best_score
                )
                if best_drop_score > best_non_drop_score and all(
                    action_is_drop(action) for action in one_ply_best
                ):
                    witnesses["drop"] = (
                        state_label,
                        _fixed_state_from_position(compiled, state.position),
                        one_ply_best,
                        {
                            "legal_action_count": len(actions),
                            "drop_action_count": len(drops),
                            "non_drop_action_count": len(non_drops),
                            "all_children_nonterminal": True,
                            "best_drop_score": best_drop_score,
                            "best_non_drop_score": best_non_drop_score,
                            "drop_score_advantage": (
                                best_drop_score - best_non_drop_score
                            ),
                            "one_ply_best_actions": [
                                action_to_dict(action) for action in one_ply_best
                            ],
                            "expected_drop_base_type_ids": sorted(
                                {
                                    action_drop_base_type_id(action)
                                    for action in one_ply_best
                                }
                            ),
                            "witness_history_mode": "fixed_root",
                        },
                    )

        for action, child in successors[:CAPABILITY_BRANCH_LIMIT]:
            queue.append((f"{state_label}:{_action_key(action)}", child))
    for name, witness in tuple(witnesses.items()):
        if witness is None:
            continue
        state_label, state, expected, *metadata = witness
        witnesses[name] = (
            state_label,
            _fixed_state_from_position(compiled, state.position),
            expected,
            *metadata,
        )
    return witnesses


def _required_tasks(label, compiled):
    required = {"extreme_material", "mobility", "anchor_danger"}
    if label in {"chess", "shogi"}:
        required |= {"mate_in_one", "mate_in_three", "avoid_immediate_mate"}
    if label == "shogi":
        required.add("drop")
    if _has_optional_promotion(compiled):
        required.add("promotion")
    if label.startswith("generated_"):
        if any(
            any(any(square_allowed for square_allowed in row) for row in grid)
            for grid in compiled.drop_allowed.values()
        ):
            required.add("drop")
    return required


def _has_optional_promotion(compiled):
    for type_id, allowed_by_owner in compiled.promotion_allowed.items():
        forced_by_owner = compiled.promotion_forced[type_id]
        for owner, allowed_pairs in enumerate(allowed_by_owner):
            forced_targets = forced_by_owner[owner]
            if any(target not in forced_targets for _source, target in allowed_pairs):
                return True
    return False


def _capability_suite(label, compiled, profile, config):
    witnesses = _task_witnesses(label, compiled, profile, config)
    required = _required_tasks(label, compiled)
    rows = {}
    for name in TASK_ORDER:
        witness = witnesses[name]
        if name not in required:
            rows[name] = {"status": "NOT_APPLICABLE"}
            if name == "promotion" and not _has_optional_promotion(compiled):
                rows[name]["reason"] = "NO_OPTIONAL_PROMOTION_SEMANTICS"
            continue
        if witness is None:
            reason = {
                "extreme_material": "CONTROLLED_MATERIAL_WITNESS_NOT_FOUND",
                "promotion": "CONTROLLED_PROMOTION_WITNESS_NOT_FOUND",
                "drop": "CONTROLLED_DROP_WITNESS_NOT_FOUND",
            }.get(name, "WITNESS_NOT_FOUND")
            rows[name] = {"status": "HARNESS_FAILURE", "reason": reason}
            return {
                "status": "HARNESS_FAILURE",
                "first_failure": name,
                "tasks": rows,
            }
        state_label, state, expected, *metadata = witness
        witness_metadata = metadata[0] if metadata else {}
        history = (state.position,)
        weak = _decision(compiled, profile, config, state, history, WEAK_NODES)
        fixed_depth = {
            "mate_in_three": 3,
            "extreme_material": 1,
            "promotion": 1,
            "drop": 1,
        }.get(name)
        if fixed_depth is not None:
            primary = _fixed_depth_decision(
                compiled, profile, config, state, history, fixed_depth
            )
            reviewer = _fixed_depth_decision(
                compiled, profile, config, state, history, fixed_depth
            )
            primary_mode = reviewer_mode = f"fixed_depth_{fixed_depth}"
            primary_nodes = reviewer_nodes = None
            primary_depth = reviewer_depth = fixed_depth
        else:
            primary = _decision(
                compiled, profile, config, state, history, PRIMARY_NODES
            )
            reviewer = _decision(
                compiled, profile, config, state, history, REVIEW_NODES
            )
            primary_mode = reviewer_mode = "node_budget"
            primary_nodes = PRIMARY_NODES
            reviewer_nodes = REVIEW_NODES
            primary_depth = reviewer_depth = None
        primary_expected = primary.action in expected
        reviewer_expected = reviewer.action in expected
        primary_completed = (
            fixed_depth is None
            or (
                primary.completed_depth == fixed_depth
                and primary.termination_reason == "completed_depth"
            )
        )
        reviewer_completed = (
            fixed_depth is None
            or (
                reviewer.completed_depth == fixed_depth
                and reviewer.termination_reason == "completed_depth"
            )
        )
        primary_passed = primary_expected and primary_completed
        reviewer_passed = (
            fixed_depth is None or (reviewer_expected and reviewer_completed)
        )
        status = (
            "HARNESS_FAILURE"
            if not reviewer_passed
            else "PASS" if primary_passed else "HARD_FAILURE"
        )
        rows[name] = {
            "status": status,
            "witness_label": state_label,
            "expected_actions": [action_to_dict(action) for action in expected],
            "primary_action": None if primary.action is None else action_to_dict(primary.action),
            "weak_action": None if weak.action is None else action_to_dict(weak.action),
            "reviewer_action": None if reviewer.action is None else action_to_dict(reviewer.action),
            "primary_expected": primary_expected,
            "weak_expected": weak.action in expected,
            "reviewer_expected": reviewer_expected,
            "decisions": {
                "primary": _decision_telemetry(
                    primary,
                    primary_mode,
                    max_nodes=primary_nodes,
                    max_depth=primary_depth,
                ),
                "weak": _decision_telemetry(
                    weak,
                    "node_budget",
                    max_nodes=WEAK_NODES,
                    max_depth=None,
                ),
                "reviewer": _decision_telemetry(
                    reviewer,
                    reviewer_mode,
                    max_nodes=reviewer_nodes,
                    max_depth=reviewer_depth,
                ),
            },
            **witness_metadata,
        }
        if status != "PASS":
            return {"status": status, "first_failure": name, "tasks": rows}
    return {"status": "PASS", "first_failure": None, "tasks": rows}


def _fixed_opening(compiled, seed):
    session = GameSession(compiled)
    rng = random.Random(seed)
    actions = []
    for _ in range(OPENING_PLIES):
        successors = _successors(session.state, compiled)
        if not successors:
            break
        action, _child = successors[rng.randrange(len(successors))]
        actions.append(action)
        session.submit(action)
    return tuple(actions)


def _review_action_score(compiled, profile, config, state, witnesses, action):
    child = next(child for candidate, child in _successors(state, compiled) if candidate == action)
    if child.terminal_status.is_terminal:
        return -terminal_score(child.terminal_status, child.position.side_to_move, 1), 0
    session = _session_with_state(compiled, state, witnesses)
    session.submit(action)
    decision = _make_player(compiled, profile, config).choose_action(session, _limits(REVIEW_NODES))
    return -decision.score, decision.nodes + decision.qnodes


def _normalized_regrets(best_action, best_score, action_scores):
    best = max((best_score, *action_scores.values()))
    worst = min((best_score, *action_scores.values()))
    span = max(1, best - worst)
    return {
        action: max(0.0, min(1.0, (best - score) / span))
        for action, score in action_scores.items()
    }, best_action


def _review_metrics(compiled, profile, config, state, witnesses, primary, weak, reviewer):
    successors = _successors(state, compiled)
    legal = {action for action, _child in successors}
    if primary.action not in legal or weak.action not in legal or reviewer.action not in legal:
        return {"hard_failure": "ILLEGAL_REVIEW_ACTION"}

    scores = {}
    review_nodes = reviewer.nodes + reviewer.qnodes
    for action in {primary.action, weak.action}:
        if action == reviewer.action:
            scores[action] = reviewer.score
        else:
            scores[action], nodes = _review_action_score(
                compiled, profile, config, state, witnesses, action
            )
            review_nodes += nodes
    regrets, _best_action = _normalized_regrets(reviewer.action, reviewer.score, scores)

    forced = set(_forced_mate_within_three_actions(state, compiled))
    unsafe = {
        action for action, child in successors if _has_mate_in_one(child, compiled)
    }
    safe = legal - unsafe
    avoid_relevant = bool(safe and unsafe)
    primary_forced_miss = bool(forced) and primary.action not in forced
    weak_forced_miss = bool(forced) and weak.action not in forced
    primary_avoid_miss = avoid_relevant and primary.action not in safe
    weak_avoid_miss = avoid_relevant and weak.action not in safe
    primary_regret = regrets[primary.action]
    weak_regret = regrets[weak.action]
    return {
        "hard_failure": None,
        "normalized_regret": primary_regret,
        "weak_normalized_regret": weak_regret,
        "forced_mate_available": bool(forced),
        "forced_mate_miss": primary_forced_miss,
        "weak_forced_mate_miss": weak_forced_miss,
        "avoid_mate_relevant": avoid_relevant,
        "avoid_mate_miss": primary_avoid_miss,
        "weak_avoid_mate_miss": weak_avoid_miss,
        "obvious_error": primary_regret >= OBVIOUS_REGRET or primary_forced_miss or primary_avoid_miss,
        "weak_obvious_error": weak_regret >= OBVIOUS_REGRET or weak_forced_miss or weak_avoid_miss,
        "review_agrees": primary.action == reviewer.action,
        "reviewer_score": reviewer.score,
        "primary_review_score": scores[primary.action],
        "weak_review_score": scores[weak.action],
        "review_nodes": review_nodes,
    }


def _short_game(compiled, profile, config, opening_kind, opening_actions, primary_owner):
    session = GameSession(compiled)
    for action in opening_actions:
        if session.state.terminal_status.status is not TerminalStatus.ONGOING:
            return {"hard_failure": "OPENING_REACHED_TERMINAL", "records": [], "plies": len(session.history)}
        session.submit(action)
    records = []
    while len(session.history) < MAX_PLIES and session.state.terminal_status.status is TerminalStatus.ONGOING:
        successors = _successors(session.state, compiled)
        if not successors:
            break
        actor = session.state.position.side_to_move
        before = session.state
        witnesses = session._search_witnesses
        if actor == primary_owner:
            primary = _decision(compiled, profile, config, before, witnesses, PRIMARY_NODES)
            weak = _decision(compiled, profile, config, before, witnesses, WEAK_NODES)
            reviewer = _decision(compiled, profile, config, before, witnesses, REVIEW_NODES)
            if primary.action is None or weak.action is None or reviewer.action is None:
                return {"hard_failure": "NO_ACTION", "records": records, "plies": len(session.history)}
            metrics = _review_metrics(
                compiled, profile, config, before, witnesses, primary, weak, reviewer
            )
            if metrics["hard_failure"] is not None:
                return {"hard_failure": metrics["hard_failure"], "records": records, "plies": len(session.history)}
            records.append(
                {
                    "ply": len(session.history),
                    "opening": opening_kind,
                    "primary_action": action_to_dict(primary.action),
                    "weak_action": action_to_dict(weak.action),
                    "review_action": action_to_dict(reviewer.action),
                    "primary_nodes": primary.nodes + primary.qnodes,
                    "weak_nodes": weak.nodes + weak.qnodes,
                    **metrics,
                }
            )
            chosen = primary.action
        else:
            weak = _decision(compiled, profile, config, before, witnesses, WEAK_NODES)
            if weak.action is None:
                return {"hard_failure": "WEAK_NO_ACTION", "records": records, "plies": len(session.history)}
            chosen = weak.action
        if chosen not in {action for action, _child in successors}:
            return {"hard_failure": "ILLEGAL_GAME_ACTION", "records": records, "plies": len(session.history)}
        session.submit(chosen)
    status = session.state.terminal_status
    return {
        "hard_failure": None,
        "records": records,
        "plies": len(session.history),
        "terminal_status": status.status.value,
        "winner": status.winner,
    }


def _trend_bucket(rows):
    def mean(key):
        return sum(float(row[key]) for row in rows) / len(rows) if rows else 0.0

    primary = {
        "decisions": len(rows),
        "normalized_regret": mean("normalized_regret"),
        "forced_mate_miss_rate": mean("forced_mate_miss"),
        "avoid_mate_miss_rate": mean("avoid_mate_miss"),
        "obvious_error_rate": mean("obvious_error"),
    }
    weak = {
        "decisions": len(rows),
        "normalized_regret": mean("weak_normalized_regret"),
        "forced_mate_miss_rate": mean("weak_forced_mate_miss"),
        "avoid_mate_miss_rate": mean("weak_avoid_mate_miss"),
        "obvious_error_rate": mean("weak_obvious_error"),
    }
    threshold_metrics = (
        "normalized_regret",
        "forced_mate_miss_rate",
        "obvious_error_rate",
    )
    checks = {
        name: primary[name] <= weak[name] * PASS_RATIO
        for name in threshold_metrics
    }
    return {
        "primary": primary,
        "weak": weak,
        "threshold_checks": checks,
        "primary_at_most_half_weak": all(checks.values()),
    }


def _aggregate_trends(games):
    labels = tuple(dict.fromkeys(game["label"] for game in games))

    def for_games(selected):
        return {
            str(limit): _trend_bucket(
                [
                    record
                    for game in selected
                    for record in game["records"]
                    if record["ply"] < limit
                ]
            )
            for limit in TREND_PLIES
        }

    return {
        "aggregate": for_games(games),
        "by_ruleset": {
            label: for_games([game for game in games if game["label"] == label])
            for label in labels
        },
    }


def _load_generated(root: Path):
    manifest = json.loads((root / GENERATED_SOURCE.relative_to(root)).read_text(encoding="utf-8"))
    if manifest.get("status") != "PRE_REGISTERED_F86O_COMMON_TAPE_TRIARM_DYNAMIC_SMOKE":
        raise AssertionError("generated source manifest drift")
    return manifest["rulesets"][:GENERATED_COUNT]


def _rulesets(root):
    rows = [
        ("chess", compile_ruleset_for_execution(build_western_chess_ruleset())),
        ("shogi", compile_ruleset_for_execution(build_standard_shogi_ruleset())),
    ]
    rows.extend(
        (
            f"generated_{entry['arm']}_{entry['sample_id']}",
            compile_ruleset(ruleset_from_dict(entry["ruleset"])),
        )
        for entry in _load_generated(root)
    )
    return rows


def _trend_failures(trends):
    failures = []
    scoped = [("aggregate", trends["aggregate"]), *trends["by_ruleset"].items()]
    for scope, rows in scoped:
        for limit, row in rows.items():
            failed_metrics = [name for name, passed in row["threshold_checks"].items() if not passed]
            if row["primary"]["decisions"] == 0 or failed_metrics:
                failures.append(
                    {
                        "scope": scope,
                        "plies": int(limit),
                        "decisions": row["primary"]["decisions"],
                        "failed_metrics": failed_metrics,
                    }
                )
    return failures


def run_merged(root: Path = ROOT):
    result = {
        "status": "PASS",
        "classification": None,
        "gate1": {
            "status": "PUBLISHED_EVIDENCE",
            "checkpoint": GATE1_CHECKPOINT,
            "games": ["chess", "shogi"],
        },
        "rulesets": [],
        "short_games": [],
        "review": {
            "primary_node_budget": PRIMARY_NODES,
            "weak_node_budget": WEAK_NODES,
            "review_node_budget": REVIEW_NODES,
            "trend_plies": TREND_PLIES,
            "pass_thresholds": {
                "candidate_to_weak_max_ratio": PASS_RATIO,
                "metrics": [
                    "normalized_regret",
                    "forced_mate_miss_rate",
                    "obvious_error_rate",
                ],
                "obvious_regret_floor": OBVIOUS_REGRET,
            },
        },
        "first_hard_failure": None,
    }
    prepared = []
    for label, compiled in _rulesets(root):
        config = EvaluationConfig()
        profile = build_ruleset_profile(compiled, config)
        capability = _capability_suite(label, compiled, profile, config)
        result["rulesets"].append(
            {
                "label": label,
                "ruleset_fingerprint": compiled.ruleset_fingerprint,
                "capability": capability,
            }
        )
        if capability["status"] != "PASS":
            result["first_hard_failure"] = {
                "layer": "capability",
                "ruleset": label,
                "reason": capability["first_failure"],
                "failure_type": capability["status"],
            }
            break
        prepared.append((label, compiled, profile, config))

    if result["first_hard_failure"] is None:
        for ruleset_index, (label, compiled, profile, config) in enumerate(prepared):
            openings = (
                ("initial", ()),
                ("shallow_random", _fixed_opening(compiled, 31000 + ruleset_index)),
            )
            for opening_kind, opening_actions in openings:
                for primary_owner in (0, 1):
                    trial = _short_game(
                        compiled,
                        profile,
                        config,
                        opening_kind,
                        opening_actions,
                        primary_owner,
                    )
                    result["short_games"].append(
                        {
                            "label": label,
                            "opening": opening_kind,
                            "primary_owner": primary_owner,
                            **trial,
                        }
                    )
                    if trial["hard_failure"] is not None:
                        result["first_hard_failure"] = {
                            "layer": "short_game",
                            "ruleset": label,
                            "opening": opening_kind,
                            "primary_owner": primary_owner,
                            "reason": trial["hard_failure"],
                        }
                        break
                if result["first_hard_failure"] is not None:
                    break
            if result["first_hard_failure"] is not None:
                break

    if result["first_hard_failure"] is None:
        trends = _aggregate_trends(result["short_games"])
        result["review"]["trends"] = trends
        result["review"]["decision_count"] = sum(
            len(game["records"]) for game in result["short_games"]
        )
        failures = _trend_failures(trends)
        if failures:
            result["first_hard_failure"] = {
                "layer": "review_metric",
                "trend_failures": failures,
            }

    if result["first_hard_failure"] is not None:
        result["status"] = "FIRST_HARD_FAILURE"
        result["gate2_status"] = "FAILED"
        result["gate3_status"] = "FROZEN"
        suffix = (
            "CAPABILITY"
            if result["first_hard_failure"]["layer"] == "capability"
            else "STRENGTH"
        )
        result["classification"] = (
            "RULE_PRIOR_ABP_BASIC_COMPETENCE_UNRESOLVED_AT_" + suffix
        )
    else:
        result["classification"] = "RULE_PRIOR_ABP_BASIC_COMPETENCE_SUPPORTED"
        result["gate2_status"] = "PASS"
        result["gate3_status"] = "ELIGIBLE_TO_RESTART"
        result["horizon_aware_capability_protocol"] = True
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_merged()
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "classification": result["classification"],
                "first_hard_failure": result["first_hard_failure"],
                "review": result["review"],
            },
            sort_keys=True,
        )
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
