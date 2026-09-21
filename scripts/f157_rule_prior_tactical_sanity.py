"""F157 causal diagnostic for the frozen rule-derived evaluator prior."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.benchmark.minimal_generator import generate_minimal_game
from generic_chess.core.actions import (
    action_is_board,
    action_source_square,
    action_target_square,
    action_to_dict,
)
from generic_chess.core.identity import position_identity_key
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.position import GameState, Hands, HistoryRecord, Position
from generic_chess.core.coordinates import Square
from generic_chess.core.terminal import TerminalStatus, _terminal_from_parts
from generic_chess.core.transition import apply_action
from generic_chess.session.session import GameSession


ROOT = Path(__file__).resolve().parents[1]
SEEDS = tuple(range(15701, 15711))
BOARD_SIZE = 5
ORDINARY_COUNT = 4
CONFIG = EvaluationConfig()


def _state(compiled, board):
    position = Position(
        board=tuple(board),
        hands=(Hands.empty(), Hands.empty()),
        side_to_move=0,
        ruleset_fingerprint=compiled.ruleset_fingerprint,
    )
    key = position_identity_key(position, compiled)
    return GameState(
        position=position,
        ply_count=0,
        repetition_counts=((key, 1),),
        terminal_status=_terminal_from_parts(position, 0, ((key, 1),), compiled),
        history=(HistoryRecord(key, -1, "", False),),
    )


def _empty_board(n):
    return [None] * (n * n)


def _put(board, n, square, owner, type_id):
    board[square.rank * n + square.file] = Piece(
        owner=owner, base_type_id=type_id, current_type_id=type_id
    )


def _squares(n):
    return tuple(Square(file, rank) for rank in range(n) for file in range(n))


def _find_move(state, compiled, source, target):
    for action in legal_actions(state, compiled):
        if not action_is_board(action):
            continue
        if action_source_square(action) == source and action_target_square(action) == target:
            return action
    return None


def _witness(compiled, high_type, low_type, attacker_type):
    n = compiled.board_size
    squares = _squares(n)
    for anchor0 in squares:
        for anchor1 in squares:
            if anchor1 == anchor0:
                continue
            for attacker in squares:
                if attacker in (anchor0, anchor1):
                    continue
                base = _empty_board(n)
                _put(base, n, anchor0, 0, "K")
                _put(base, n, anchor1, 1, "K")
                _put(base, n, attacker, 0, attacker_type)
                base_state = _state(compiled, base)
                if base_state.terminal_status.status is not TerminalStatus.ONGOING:
                    continue
                for high_square in squares:
                    if high_square in (anchor0, anchor1, attacker):
                        continue
                    high_board = list(base)
                    _put(high_board, n, high_square, 1, high_type)
                    high_state = _state(compiled, high_board)
                    if _find_move(high_state, compiled, attacker, high_square) is None:
                        continue
                    for low_square in squares:
                        if low_square in (anchor0, anchor1, attacker, high_square):
                            continue
                        board = list(high_board)
                        _put(board, n, low_square, 1, low_type)
                        root = _state(compiled, board)
                        if root.terminal_status.status is not TerminalStatus.ONGOING:
                            continue
                        high_action = _find_move(root, compiled, attacker, high_square)
                        low_action = _find_move(root, compiled, attacker, low_square)
                        if high_action is None or low_action is None:
                            continue
                        high_child = apply_action(root, high_action, compiled)
                        low_child = apply_action(root, low_action, compiled)
                        if high_child.terminal_status.is_terminal or low_child.terminal_status.is_terminal:
                            continue
                        return {
                            "root": root,
                            "high_action": high_action,
                            "low_action": low_action,
                            "high_child": high_child,
                            "low_child": low_child,
                            "anchor0": anchor0,
                            "anchor1": anchor1,
                            "attacker": attacker,
                            "high_square": high_square,
                            "low_square": low_square,
                        }
    return None


def _material_score(state, profile):
    score = 0
    for piece in state.position.board:
        if piece is None:
            continue
        value = profile.board_value_by_type[piece.current_type_id]
        score += value if piece.owner == 0 else -value
    for owner, hand in enumerate(state.position.hands):
        for type_id, count in hand.counts:
            value = profile.hand_value_by_base_type[type_id]
            score += count * value if owner == 0 else -count * value
    return score


def _perspective_score(evaluator, state):
    # Children hand the move to owner 1; restore owner 0's perspective.
    return evaluator.evaluate(state) * (-1 if state.position.side_to_move else 1)


def _search_smoke(compiled, state, high_action):
    session = GameSession(compiled)
    session._state = state
    session._search_history_witnesses = (state.position,)
    decision = AlphaBetaPlayer(
        compiled,
        evaluation_config=CONFIG,
        use_disk_cache=False,
        use_tt=True,
        use_ordering=True,
        use_native_semantic_legality=False,
    ).choose_action(
        session,
        SearchLimits(
            max_depth=1,
            quiescence_max_depth=0,
            quiescence_hard_max_depth=0,
            deterministic=True,
        ),
    )
    return {
        "chosen_action": action_to_dict(decision.action) if decision.action else None,
        "high_capture_chosen": decision.action == high_action,
        "score": decision.score,
        "completed_depth": decision.completed_depth,
        "nodes": decision.nodes,
        "termination_reason": decision.termination_reason,
    }


def _row(game, profile, witness):
    evaluator = Evaluator(game.compiled, profile, CONFIG)
    root = witness["root"]
    high_child = witness["high_child"]
    low_child = witness["low_child"]
    full_root = _perspective_score(evaluator, root)
    high_full = _perspective_score(evaluator, high_child)
    low_full = _perspective_score(evaluator, low_child)
    high_material = _material_score(high_child, profile)
    low_material = _material_score(low_child, profile)
    all_children = []
    for action in legal_actions(root, game.compiled):
        child = apply_action(root, action, game.compiled)
        all_children.append((_perspective_score(evaluator, child), action))
    highest = max(score for score, _action in all_children)
    unique_high = high_full == highest and sum(score == highest for score, _action in all_children) == 1
    return {
        "seed": game.seed,
        "ruleset_fingerprint": game.ruleset_fingerprint,
        "board_size": game.board_size,
        "type_values": dict(profile.board_value_by_type),
        "high_type": witness["high_type"],
        "low_type": witness["low_type"],
        "attacker_type": witness["attacker_type"],
        "high_value": profile.board_value_by_type[witness["high_type"]],
        "low_value": profile.board_value_by_type[witness["low_type"]],
        "actions": {
            "capture_high": action_to_dict(witness["high_action"]),
            "capture_low": action_to_dict(witness["low_action"]),
        },
        "scores_owner0_perspective": {
            "root": full_root,
            "capture_high": high_full,
            "capture_low": low_full,
            "difference": high_full - low_full,
        },
        "material_owner0_perspective": {
            "capture_high": high_material,
            "capture_low": low_material,
            "difference": high_material - low_material,
        },
        "high_capture_unique_full_best": unique_high,
        "search_smoke": _search_smoke(game.compiled, root, witness["high_action"]),
    }


def run_probe():
    checked = []
    rows = []
    for seed in SEEDS:
        try:
            game = generate_minimal_game(
                seed, board_size=BOARD_SIZE, ordinary_count=ORDINARY_COUNT
            )
            profile = build_ruleset_profile(game.compiled, CONFIG)
        except Exception as exc:
            checked.append({"seed": seed, "status": "generation_failure", "error": type(exc).__name__})
            continue
        ordinary = [pt.type_id for pt in game.compiled.piece_types if not pt.is_anchor]
        values = {type_id: profile.board_value_by_type[type_id] for type_id in ordinary}
        valid = len(ordinary) >= 2 and len(set(values.values())) > 1
        checked.append({"seed": seed, "status": "candidate" if valid else "rejected", "ordinary_types": ordinary, "values": values})
        if not valid:
            continue
        high_type = max(ordinary, key=lambda type_id: (values[type_id], type_id))
        low_type = min(ordinary, key=lambda type_id: (values[type_id], type_id))
        for attacker_type in ordinary:
            witness = _witness(game.compiled, high_type, low_type, attacker_type)
            if witness is None:
                continue
            witness.update({"high_type": high_type, "low_type": low_type, "attacker_type": attacker_type})
            rows.append(_row(game, profile, witness))
            break
        if len(rows) == 2:
            break

    if len(rows) < 2:
        classification = (
            "GATE2_TINY_SAMPLE_LACKS_VALUE_CONTRAST"
            if sum(item.get("status") == "candidate" for item in checked) < 2
            else "GATE2_TINY_SAMPLE_LACKS_CAPTURE_WITNESS"
        )
    elif all(
        row["material_owner0_perspective"]["difference"] > 0
        and row["scores_owner0_perspective"]["difference"] > 0
        for row in rows
    ):
        classification = "RULE_PRIOR_TACTICAL_SANITY_PASS"
    elif any(row["material_owner0_perspective"]["difference"] > 0 and row["scores_owner0_perspective"]["difference"] <= 0 for row in rows):
        classification = "RULE_PRIOR_DYNAMIC_TERMS_REVERSE_BASIC_TACTICAL_PRIOR"
    else:
        classification = "RULE_PRIOR_VALUE_PROFILE_SANITY_FAILURE"
    return {
        "classification": classification,
        "seed_cap": list(SEEDS),
        "checked": checked,
        "witnesses": rows,
        "compute": {"games": 0, "heavy": False, "depth1_searches": len(rows), "depth2_searches": 0},
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    result = run_probe()
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    print(f"F157_CLASSIFICATION={result['classification']}")
    return 0 if result["classification"] == "RULE_PRIOR_TACTICAL_SANITY_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
