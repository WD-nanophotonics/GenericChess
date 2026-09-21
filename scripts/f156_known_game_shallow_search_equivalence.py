"""F156 causal diagnostic: shallow Python/native search equivalence.

This is deliberately a small fixed-position probe.  It compares the existing
Python AlphaBetaPlayer with the existing semantic Native search engine using
the same integer material profile and qsearch disabled.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import position_identity_key
from generic_chess.core.position import GameState, HistoryRecord
from generic_chess.core.terminal import TerminalResult, TerminalStatus
from generic_chess.learning.shogi_rules import sfen_to_gc_state
from generic_chess.native import SemanticSearchEngine, native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.rules.compiler import compile_ruleset_for_execution, compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession
from scripts.audit_f24f_western_chess_perft import position_from_fen


ROOT = Path(__file__).resolve().parents[1]
DEPTHS = (1, 2)
REPEATS = 2


class CommonMaterialEvaluator:
    """Exact material-only evaluator shared with the native profile."""

    def __init__(self, values: dict[str, int]):
        self.values = dict(values)

    def evaluate(self, state: GameState) -> int:
        score = 0
        for piece in state.position.board:
            if piece is None:
                continue
            value = self.values[piece.current_type_id]
            score += value if piece.owner == 0 else -value
        for owner, hand in enumerate(state.position.hands):
            for type_id, count in hand.counts:
                value = self.values[type_id]
                score += count * value if owner == 0 else -count * value
        return score if state.position.side_to_move == 0 else -score

    def capture_order_value(self, moving_piece, captured_piece) -> int:
        return self.values[captured_piece.current_type_id] * 10 - self.values[moving_piece.current_type_id] // 10

    def type_value(self, type_id: str) -> int:
        return self.values[type_id]


def _values(compiled) -> dict[str, int]:
    values = {}
    for index, piece_type in enumerate(sorted(compiled.piece_types, key=lambda item: item.type_id)):
        values[piece_type.type_id] = 0 if piece_type.is_anchor else index + 1
    return values


def _western_pair():
    definition = build_western_chess_ruleset()
    return compile_ruleset_for_execution(definition), compile_semantic_ruleset(definition)


def _shogi_pair():
    definition = build_standard_shogi_ruleset()
    return compile_ruleset_for_execution(definition), compile_semantic_ruleset(definition)


def _state_from_position(compiled, position, *, terminal_override=None):
    key = position_identity_key(position, compiled)
    if terminal_override is None:
        from generic_chess.core.semantic_executor import semantic_engine_for

        terminal_override = semantic_engine_for(compiled).terminal_result(
            position, 0, ((key, 1),)
        )
    return GameState(
        position=position,
        ply_count=0,
        repetition_counts=((key, 1),),
        terminal_status=terminal_override,
        history=(HistoryRecord(key, -1, "", False),),
    )


def _western_state(compiled, fen):
    return _state_from_position(compiled, position_from_fen(fen, compiled))


def _root_specs():
    def shogi_state(compiled):
        state = sfen_to_gc_state(
            compiled, "4k4/3P5/3R5/9/3pP4/9/9/9/4K4 b R 1"
        )
        key = position_identity_key(state.position, compiled)
        return GameState(
            position=state.position,
            ply_count=state.ply_count,
            repetition_counts=state.repetition_counts,
            terminal_status=state.terminal_status,
            history=(HistoryRecord(key, -1, "", False),),
        )

    return {
        "western": {
            "builder": _western_pair,
            "w1": lambda compiled: _western_state(
                compiled, "4k3/8/8/p7/8/8/8/R3K3 w - - 0 1"
            ),
            "w2": lambda compiled: _western_state(
                compiled, "7k/6Q1/5K2/8/8/8/8/8 b - - 0 1"
            ),
        },
        "shogi": {
            "builder": _shogi_pair,
            # A compact legal midgame with an in-hand rook and pawns in and
            # near the promotion zone; it exposes drops, promotion-sensitive
            # moves, captures, and material choice.
            "s1": shogi_state,
        },
    }


def _session(compiled, state):
    session = GameSession(compiled)
    session._state = state
    session._search_history_witnesses = (state.position,) * max(1, len(state.history))
    return session


def _python_run(compiled, state, values, depth):
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
            max_nodes=None,
            quiescence_max_depth=0,
            quiescence_hard_max_depth=0,
            deterministic=True,
        ),
    )
    return {
        "action": action_to_dict(decision.action) if decision.action is not None else None,
        "score": decision.score,
        "pv": [action_to_dict(action) for action in decision.principal_variation],
        "completed_depth": decision.completed_depth,
        "nodes": decision.nodes,
        "termination_reason": decision.termination_reason,
    }


def _native_run(compiled, native, state, values, depth):
    engine = SemanticSearchEngine(
        compiled,
        native,
        board_values=values,
        hand_values=values,
        tt_megabytes=0,
        ordering_cache_enabled=False,
        ordering_feature_reuse_enabled=False,
    )
    result = engine.search(
        _session(compiled, state),
        SearchLimits(
            max_depth=depth,
            max_nodes=None,
            quiescence_max_depth=0,
            quiescence_hard_max_depth=0,
            deterministic=True,
        ),
        root_window_pruning=False,
    )
    return {
        "action": action_to_dict(result.action) if result.action is not None else None,
        "score": result.score,
        "pv": [action_to_dict(action) for action in result.principal_variation],
        "completed_depth": result.completed_depth,
        "nodes": result.nodes,
        "termination_reason": result.termination_reason,
    }


def _static_rows(compiled, state, values):
    evaluator = CommonMaterialEvaluator(values)
    rows = []
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.transition import apply_action

    for action in legal_actions(state, compiled):
        child = apply_action(state, action, compiled)
        rows.append({"action": action_to_dict(action), "score": evaluator.evaluate(child)})
    return rows


def _terminal_pair(py_compiled, py_state, native_compiled, native_state, native, values):
    python_row = _python_run(py_compiled, py_state, values, 1)
    native_row = _native_run(native_compiled, native, native_state, values, 1)
    return {
        "python": python_row,
        "native": native_row,
            "status": py_state.terminal_status.status.value,
            "winner": py_state.terminal_status.winner,
            "outcome_category": (
                "WIN" if py_state.terminal_status.winner is not None else py_state.terminal_status.status.value
            ),
            "agree": (
                python_row["action"] is None
                and native_row["action"] is None
                and python_row["termination_reason"] == "terminal_position"
                and native_row["termination_reason"] == "terminal_position"
                and py_state.terminal_status == native_state.terminal_status
            ),
        }


def _termination_category(reason: str) -> str:
    # The two existing implementations use different labels for a completed
    # fixed-depth iteration; this is the same non-terminal outcome category.
    return "completed" if reason in {"completed", "completed_depth"} else reason


def run_probe():
    if not native_available():
        return {"classification": "GATE1_NATIVE_UNAVAILABLE", "native_available": False}

    specs = _root_specs()
    output = {
        "classification": None,
        "native_available": True,
        "run_config": {
            "depths": list(DEPTHS),
            "repeats": REPEATS,
            "quiescence_max_depth": 0,
            "tt_megabytes": 0,
            "python_ordering": False,
            "native_ordering_cache": False,
        },
        "roots": {
            "western_w1": "4k3/8/8/p7/8/8/8/R3K3 w - - 0 1",
            "western_w2": "7k/6Q1/5K2/8/8/8/8/8 b - - 0 1",
            "shogi_s1": "4k4/3P5/3R5/9/3pP4/9/9/9/4K4 b R 1",
            "shogi_s2": "shogi_s1 with current-position repetition count set to 4",
        },
        "search": {},
        "static": {},
        "terminal": {},
        "tie_witnesses": [],
    }
    mismatch = None

    for game, spec in specs.items():
        legacy, semantic = spec["builder"]()
        values = _values(legacy)
        native = compile_native_semantic_rules(semantic)
        output["search"][game] = {"values": values, "depths": {}}
        output["static"][game] = {}

        search_key = "w1" if game == "western" else "s1"
        legacy_state = spec[search_key](legacy)
        semantic_state = spec[search_key](semantic)
        output["static"][game][search_key] = {
            "python": _static_rows(legacy, legacy_state, values),
            "native": _static_rows(semantic, semantic_state, values),
        }
        if output["static"][game][search_key]["python"] != output["static"][game][search_key]["native"]:
            mismatch = "GATE1_MATERIAL_SEMANTICS_MISMATCH"

        for depth in DEPTHS:
            rows = []
            for repeat in range(REPEATS):
                rows.append({
                    "repeat": repeat + 1,
                    "python": _python_run(legacy, legacy_state, values, depth),
                    "native": _native_run(semantic, native, semantic_state, values, depth),
                })
            output["search"][game]["depths"][str(depth)] = rows
            for row in rows:
                py = row["python"]
                na = row["native"]
                if (py["action"], py["score"], py["completed_depth"], _termination_category(py["termination_reason"])) != (
                    na["action"], na["score"], na["completed_depth"], _termination_category(na["termination_reason"])
                ):
                    if py["score"] != na["score"]:
                        mismatch = mismatch or "GATE1_NEGAMAX_DECISION_MISMATCH"
                    elif py["action"] != na["action"]:
                        output["tie_witnesses"].append({
                            "game": game,
                            "depth": depth,
                            "python_action": py["action"],
                            "native_action": na["action"],
                            "score": py["score"],
                            "classification": "ORDERING_TIE_WITNESS",
                        })
                    else:
                        mismatch = mismatch or "GATE1_SEARCH_COMPLETION_MISMATCH"
            first = rows[0]
            if any(row["python"] != first["python"] or row["native"] != first["native"] for row in rows[1:]):
                mismatch = mismatch or "GATE1_DETERMINISM_MISMATCH"

        if game == "western":
            output["terminal"]["w2_checkmate"] = _terminal_pair(
                legacy, spec["w2"](legacy), semantic, spec["w2"](semantic), native, values
            )
            if not output["terminal"]["w2_checkmate"]["agree"]:
                mismatch = mismatch or "GATE1_TERMINAL_SEMANTICS_MISMATCH"
        else:
            def repeated_state(state, compiled):
                key = position_identity_key(state.position, compiled)
                return GameState(
                    position=state.position,
                    ply_count=state.ply_count,
                    repetition_counts=((key, 4),),
                    terminal_status=TerminalResult(TerminalStatus.REPETITION),
                    history=(HistoryRecord(key, -1, "", False),) * 4,
                )

            output["terminal"]["s2_repetition"] = _terminal_pair(
                legacy, repeated_state(legacy_state, legacy),
                semantic, repeated_state(semantic_state, semantic),
                native, values,
            )
            if not output["terminal"]["s2_repetition"]["agree"]:
                mismatch = mismatch or "GATE1_TERMINAL_SEMANTICS_MISMATCH"

    output["classification"] = mismatch or "KNOWN_GAME_SHALLOW_SEARCH_EQUIVALENCE_PASS"
    return output


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)
    result = run_probe()
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8")
    print(f"F156_CLASSIFICATION={result['classification']}")
    return 0 if result["classification"] == "KNOWN_GAME_SHALLOW_SEARCH_EQUIVALENCE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
