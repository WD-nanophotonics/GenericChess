from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from generic_chess.ai.alphabeta.search import _tt_key
from generic_chess.core.identity import (
    position_identity,
    position_identity_key,
    repetition_identity_key,
    search_state_identity,
)
from generic_chess.core.keys import position_key
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import HistoryRecord
from generic_chess.core.transition import initial_state
from generic_chess.learning.shogi_semantic_rules import build_semantic_shogi_ruleset
from generic_chess.rules.compiler import compile_ruleset, compile_semantic_ruleset
from generic_chess.rules.schema import RuleSet
from generic_chess.session.session import GameSession
from generic_chess.ui.controller import UIController
from rule_semantics_ir_fixtures import castling_ruleset


def _legacy_compiled(max_ply: int = 64):
    n = 4
    king_steps = tuple(
        (df, dr)
        for df in (-1, 0, 1)
        for dr in (-1, 0, 1)
        if (df, dr) != (0, 0)
    )
    king = PieceType("K", "K", tuple(LeapAtom(offset) for offset in king_steps), is_anchor=True)
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[3][3] = Piece(1, "K", "K", False)
    return compile_ruleset(
        RuleSet(
            board_size=n,
            piece_types=(king,),
            initial_position=tuple(tuple(row) for row in rows),
            repetition_limit=4,
            max_ply=max_ply,
            stalemate_result="draw",
        )
    )


def _semantic_compiled():
    return compile_semantic_ruleset(castling_ruleset())


def _shogi_compiled():
    return compile_semantic_ruleset(build_semantic_shogi_ruleset())


def _changed_aux_position(compiled, position):
    slot = compiled.ir.aux_slots[0]
    owner = -1 if slot.scope == "global" else 0
    changed = 0 if slot.initial != 0 else 1
    return replace(position, aux_state=(((slot.slot_id, owner), changed),))


def test_position_identity_dispatches_semantic_aux_and_canonical_defaults():
    compiled = _semantic_compiled()
    position = initial_state(compiled).position
    changed = _changed_aux_position(compiled, position)
    slot = compiled.ir.aux_slots[0]
    owner = -1 if slot.scope == "global" else 0
    explicit_default = replace(
        position,
        aux_state=(((slot.slot_id, owner), slot.initial),),
    )

    assert position_identity_key(position, compiled) != position_identity_key(changed, compiled)
    assert position_identity_key(position, compiled) == position_identity_key(
        explicit_default, compiled
    )
    assert position_identity(changed, compiled).semantic is True


def test_unknown_aux_and_ruleset_fingerprint_remain_identity_inputs():
    compiled = _semantic_compiled()
    position = initial_state(compiled).position
    unknown = replace(position, aux_state=(((9999, 77), 1),))
    assert position_identity_key(position, compiled) != position_identity_key(unknown, compiled)

    legacy_a = _legacy_compiled(max_ply=64)
    legacy_b = _legacy_compiled(max_ply=65)
    assert legacy_a.ruleset_fingerprint != legacy_b.ruleset_fingerprint
    assert position_identity_key(
        legacy_a.initial_position, legacy_a
    ) != position_identity_key(legacy_b.initial_position, legacy_b)
    assert position_identity_key(legacy_a.initial_position, legacy_a) == position_key(
        legacy_a.initial_position, legacy_a
    )


def test_stable_identity_survives_reconstruction_and_session_records_use_it():
    compiled = _semantic_compiled()
    session = GameSession(compiled)
    root = session.state
    root_key = position_identity_key(root.position, compiled)
    rebuilt = replace(root.position, board=tuple(root.position.board))
    assert position_identity_key(rebuilt, compiled) == root_key
    assert root.history[0].position_key == repetition_identity_key(root.position, compiled)

    action = session.legal_actions()[0]
    child = session.submit(action)
    record = session.history[-1]
    assert record.before_key == root_key
    assert record.after_key == position_identity_key(child.position, compiled)
    assert record.after_key == repetition_identity_key(child.position, compiled)


def test_search_identity_keeps_repetition_path_and_near_max_ply_distinct():
    compiled = _shogi_compiled()
    state = initial_state(compiled)
    key = repetition_identity_key(state.position, compiled)
    repeated = replace(
        state,
        ply_count=compiled.support.max_ply - 1,
        repetition_counts=((key, 2),),
        history=(
            HistoryRecord(key, -1, "", False),
            HistoryRecord(key, 0, "a", True),
        ),
    )
    near_root = replace(repeated, ply_count=compiled.support.max_ply - 2)
    different_history = replace(
        repeated,
        history=(
            HistoryRecord(key, -1, "", False),
            HistoryRecord(key, 0, "b", False),
        ),
    )
    assert search_state_identity(repeated, compiled) != search_state_identity(
        near_root, compiled
    )
    assert _tt_key(repeated, compiled) != _tt_key(different_history, compiled)


def test_ui_stale_root_rejects_aux_only_semantic_mismatch():
    compiled = _semantic_compiled()
    session = GameSession(compiled)
    root = session.state
    controller = UIController()
    controller._compiled = compiled
    controller._session = session
    controller._ai_session = session
    controller._ai_generation = 1
    controller._ai_search_generation = 1
    controller._ai_fingerprint = compiled.ruleset_fingerprint
    controller._ai_root_key = position_identity_key(root.position, compiled)

    session._state = replace(
        root,
        position=_changed_aux_position(compiled, root.position),
    )

    assert not controller.finish_ai_move(None)
