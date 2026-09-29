"""Bounded exact mate-in-two certificate and search-policy comparison on Chess."""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import legal_successors
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic import guarded_actions, make_checked, public_action, terminal_status
from scripts.audit_chess_root_terminal_labels import native_position_from_fen
from scripts.f156_known_game_shallow_search_equivalence import (
    CommonMaterialEvaluator,
    _native_run,
    _session,
    _values,
    _western_pair,
    _western_state,
)


FEN = "8/8/8/1R6/8/8/5R2/k2K4 w - - 0 1"
MAX_SUCCESSORS = 8192
MAX_CERT_SECONDS = 10


def _key(action) -> str:
    return json.dumps(action_to_dict(action), sort_keys=True)


def _certificate(compiled, state) -> tuple[dict[str, str], dict]:
    labels = {}
    counts = Counter()
    generated = 0
    start = time.monotonic()
    for action, child in legal_successors(state, compiled):
        generated += 1
        if child.terminal_status.status is TerminalStatus.CHECKMATE and child.terminal_status.winner == 0:
            label = "IMMEDIATE_WIN"
        elif child.terminal_status.is_terminal:
            label = "IMMEDIATE_DRAW" if child.terminal_status.winner is None else "OTHER_TERMINAL"
        else:
            replies = list(legal_successors(child, compiled))
            generated += len(replies)
            all_replies_mated = bool(replies)
            for _reply, reply_child in replies:
                if reply_child.terminal_status.is_terminal:
                    all_replies_mated = False
                    continue
                continuations = list(legal_successors(reply_child, compiled))
                generated += len(continuations)
                if not any(
                    result.terminal_status.status is TerminalStatus.CHECKMATE
                    and result.terminal_status.winner == 0
                    for _move, result in continuations
                ):
                    all_replies_mated = False
                if generated > MAX_SUCCESSORS or time.monotonic() - start > MAX_CERT_SECONDS:
                    raise RuntimeError("mate-in-two certificate resource cap reached")
            label = "FORCED_MATE_IN_TWO" if all_replies_mated else "UNRESOLVED"
        labels[_key(action)] = label
        counts[label] += 1
    return labels, {"generated_successors": generated, "label_counts": dict(sorted(counts.items()))}


def _python_search(compiled, state, values, depth, qdepth) -> dict:
    player = AlphaBetaPlayer(
        compiled,
        evaluation_config=None,
        use_disk_cache=False,
        use_tt=False,
        use_ordering=False,
        use_native_semantic_legality=True,
        tuning=SearchTuning(),
        evaluator_override=CommonMaterialEvaluator(values),
    )
    decision = player.choose_action(
        _session(compiled, state),
        SearchLimits(
            max_depth=depth,
            max_nodes=2000,
            max_time_seconds=5,
            quiescence_max_depth=qdepth,
            quiescence_hard_max_depth=0 if qdepth == 0 else 8,
            deterministic=True,
        ),
    )
    return {
        "action": action_to_dict(decision.action) if decision.action else None,
        "score": decision.score,
        "completed_depth": decision.completed_depth,
        "nodes": decision.nodes,
        "qnodes": decision.qnodes,
        "termination_reason": decision.termination_reason,
    }


def _native_mate2_certificate(native, root, action_dict) -> dict:
    matching = [
        action for action in guarded_actions(native, root)
        if action_to_dict(public_action(native, action)) == action_dict
    ]
    if len(matching) != 1:
        raise AssertionError("selected action is not uniquely legal in native Chess")
    child = make_checked(native, root, matching[0])
    replies = guarded_actions(native, child)
    witness = []
    for reply in replies:
        grandchild = make_checked(native, child, reply)
        mates = [
            action_to_dict(public_action(native, continuation))
            for continuation in guarded_actions(native, grandchild)
            if terminal_status(native, make_checked(native, grandchild, continuation))
            == {"status": "checkmate", "winner": 0}
        ]
        witness.append({"reply": action_to_dict(public_action(native, reply)), "mate_count": len(mates)})
    return {
        "child_status": terminal_status(native, child),
        "reply_count": len(replies),
        "all_replies_have_mate": bool(replies) and all(row["mate_count"] > 0 for row in witness),
        "witness": witness,
    }


def _later_mate_certificate(compiled, selected_child) -> dict:
    """Exact attacker OR / defender AND proof with four plies after selection."""
    generated = 0
    start = time.monotonic()
    memo = {}

    def forced(state, plies):
        nonlocal generated
        terminal = state.terminal_status
        if terminal.is_terminal:
            return terminal.status is TerminalStatus.CHECKMATE and terminal.winner == 0
        if plies == 0:
            return False
        key = (state.position, state.repetition_counts, plies)
        if key in memo:
            return memo[key]
        children = list(legal_successors(state, compiled))
        generated += len(children)
        if generated > MAX_SUCCESSORS or time.monotonic() - start > MAX_CERT_SECONDS:
            raise RuntimeError("later-mate certificate resource cap reached")
        if state.position.side_to_move == 0:
            result = any(forced(child, plies - 1) for _action, child in children)
        else:
            result = bool(children) and all(
                forced(child, plies - 1) for _action, child in children
            )
        memo[key] = result
        return result

    within_three_plies = forced(selected_child, 2)
    within_five_plies = forced(selected_child, 4)
    return {
        "forced_mate_within_three_plies_from_root": within_three_plies,
        "forced_mate_within_five_plies_from_root": within_five_plies,
        "generated_successors": generated,
    }


def _native_later_line(native, root, selected_action) -> dict:
    def same_route(action, source, target):
        row = action_to_dict(public_action(native, action))
        return row.get("from") == source and row.get("to") == target

    current = root
    black_reply_counts = []
    line = [
        (selected_action["from"], selected_action["to"]),
        ([0, 0], [0, 1]),
        ([5, 1], [5, 2]),
        ([0, 1], [0, 0]),
        ([5, 2], [0, 2]),
    ]
    for ply, (source, target) in enumerate(line):
        actions = guarded_actions(native, current)
        if ply in (1, 3):
            black_reply_counts.append(len(actions))
        matches = [
            action for action in actions
            if same_route(action, source, target)
        ]
        if len(matches) != 1:
            raise AssertionError("native later-mate line is not uniquely legal")
        current = make_checked(native, current, matches[0])
    return {"black_reply_counts": black_reply_counts, "terminal": terminal_status(native, current)}


def run_probe() -> dict:
    compiled, semantic = _western_pair()
    state = _western_state(compiled, FEN)
    labels, certificate = _certificate(compiled, state)
    values = _values(compiled)
    python = {
        f"d{depth}_q{qdepth}": _python_search(compiled, state, values, depth, qdepth)
        for depth in (1, 2) for qdepth in (0, 4)
    }
    for row in python.values():
        row["certified_label"] = labels.get(json.dumps(row["action"], sort_keys=True))

    native = compile_native_semantic_rules(semantic)
    native_state = _western_state(semantic, FEN)
    native_rows = {f"d{depth}_q0": _native_run(semantic, native, native_state, values, depth) for depth in (1, 2)}
    for row in native_rows.values():
        row["certified_label"] = labels.get(json.dumps(row["action"], sort_keys=True))
    packed = native_position_from_fen(semantic, native, FEN)
    native_certificate = _native_mate2_certificate(native, packed, python["d2_q4"]["action"])
    q0_selected_child = next(
        child for action, child in legal_successors(state, compiled)
        if action_to_dict(action) == python["d2_q0"]["action"]
    )
    later_certificate = _later_mate_certificate(compiled, q0_selected_child)
    native_later_line = _native_later_line(native, packed, python["d2_q0"]["action"])
    valid = (
        state.terminal_status.status is TerminalStatus.ONGOING
        and certificate["label_counts"].get("IMMEDIATE_WIN", 0) == 0
        and certificate["label_counts"].get("IMMEDIATE_DRAW", 0) > 0
        and python["d2_q4"]["certified_label"] == "FORCED_MATE_IN_TWO"
        and python["d2_q0"]["certified_label"] == "UNRESOLVED"
        and python["d2_q4"]["completed_depth"] == python["d2_q0"]["completed_depth"] == 2
        and native_rows["d2_q0"]["action"] == python["d2_q0"]["action"]
        and native_certificate["all_replies_have_mate"]
        and not later_certificate["forced_mate_within_three_plies_from_root"]
        and later_certificate["forced_mate_within_five_plies_from_root"]
        and native_later_line["black_reply_counts"] == [1, 1]
        and native_later_line["terminal"] == {"status": "checkmate", "winner": 0}
    )
    return {
        "classification": "MATE2_QSEARCH_BOUNDARY_PASS" if valid else "BOUNDARY_OBSERVATION_CHANGED",
        "root_fen": FEN,
        "material_values": values,
        "certificate": certificate,
        "python": python,
        "native_no_quiescence": native_rows,
        "native_selected_mate2_certificate": native_certificate,
        "q0_selected_later_mate_certificate": later_certificate,
        "native_q0_selected_later_line": native_later_line,
    }


if __name__ == "__main__":
    result = run_probe()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["classification"] == "MATE2_QSEARCH_BOUNDARY_PASS" else 1)
