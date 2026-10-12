"""Typed auxiliary identity at imported-state and runtime collision boundaries."""

from dataclasses import replace

import pytest

from generic_chess.ai.alphabeta.transposition import BoundType, TranspositionTable
from generic_chess.core.actions import SemanticBoardMove
from generic_chess.core.identity import position_identity_key
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.core.position import HistoryRecord
from generic_chess.core.search_runtime import (
    RuntimeCountsSnapshot,
    RuntimeHistoryContext,
    SearchPathRuntime,
    _full_runtime_hash,
    _identity_equal,
    _runtime_position_identity,
    _semantic_component_diff_hash,
)
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleActionEffect, RuleAuxState, RuleGeometrySpec, RuleInvariant,
    RuleSemanticAction, RuleSquareRef,
)
from rule_semantics_ir_fixtures import _king_type, _semantic_ruleset


def _compiled(initial=0, value=1):
    action = RuleSemanticAction(
        name="write", type_ids=("A",),
        geometry=RuleGeometrySpec(kind="leap", offset=(1, 0)),
        target_relation="empty", composition="augment",
        aux_state=(RuleAuxState("flag", "bool", "global", "persistent", initial),),
        effects=(
            RuleActionEffect("move", from_ref=RuleSquareRef("source"),
                             to_ref=RuleSquareRef("target")),
            RuleActionEffect("set_bool", slot_name="flag", value=value),
        ),
        invariants=(RuleInvariant("own_anchor_safe"),),
    )
    rows = [[None] * 5 for _ in range(5)]
    rows[0][0] = Piece(0, "K", "K")
    rows[4][4] = Piece(1, "K", "K")
    rows[1][1] = Piece(0, "A", "A")
    return compile_semantic_ruleset(_semantic_ruleset(
        (_king_type(), PieceType("A", "A", ())), (action,), n=5,
        rows=tuple(tuple(row) for row in rows),
    ))


def _imported(compiled, aux):
    state = initial_state(compiled)
    position = replace(state.position, aux_state=aux)
    key = position_identity_key(position, compiled)
    return replace(state, position=position, repetition_counts=((key, 1),),
                   history=(HistoryRecord(key, -1, ""),))


@pytest.mark.parametrize("initial", (0, 1))
@pytest.mark.parametrize("value", (0, 1))
def test_actual_imported_bool_write_matches_full_hash_and_undo(initial, value):
    compiled = _compiled(initial, value)
    state = _imported(compiled, (((0, -1), bool(value)),))
    runtime = SearchPathRuntime.from_state(state, compiled)
    before_hash = runtime.runtime_hash
    before_key = runtime.search_key()
    action = next(a for a in runtime.legal_actions()
                  if isinstance(a, SemanticBoardMove) and a.pattern_id.startswith("sem_"))
    expected = apply_action(state, action, compiled)
    with runtime.pushed(action):
        assert type(dict(runtime.position.aux_state)[(0, -1)]) is int
        assert runtime.position == expected.position
        assert runtime.runtime_hash == _full_runtime_hash(expected.position, compiled)
    runtime.assert_balanced()
    assert runtime.runtime_hash == before_hash
    assert runtime.search_key() == before_key


@pytest.mark.parametrize("strict", (False, True))
def test_pure_semantic_support_keeps_native_provider_active(strict):
    from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
    from generic_chess.native import native_available

    if not native_available():
        pytest.skip("native unavailable")
    compiled = _compiled()
    assert not hasattr(compiled, "max_ply")
    provider = NativeSemanticLegalityProvider.try_create(compiled, strict=strict)
    assert provider is not None
    state = _imported(compiled, (((0, -1), False),))
    assert provider.supports_position(state.position, 0)
    assert not provider.supports_position(state.position, compiled.support.max_ply)
    runtime = SearchPathRuntime.from_state(
        state, compiled, history_witnesses=(state.position,),
        legal_binding_provider=provider,
    )
    actions = runtime.legal_actions()
    from generic_chess.core.transition import legal_actions
    assert set(actions) == set(legal_actions(state, compiled))
    assert runtime.legal_provider_calls == 1
    assert runtime.legal_provider_fallbacks == 0
    action = next(a for a in actions if a.pattern_id.startswith("sem_"))
    expected = apply_action(state, action, compiled)
    with runtime.pushed(action):
        assert runtime.position == expected.position
        assert runtime.terminal_status == expected.terminal_status
        assert set(runtime.legal_actions()) == set(legal_actions(expected, compiled))
        assert runtime.legal_provider_calls == 2
        assert runtime.legal_provider_operational_failures == 0
    runtime.assert_balanced()
    assert runtime.position is state.position


@pytest.mark.parametrize("left,right", ((1, True), (0, False), ((1, 2), (True, 2))))
def test_foreign_scalar_types_survive_forced_runtime_tt_collision(left, right):
    compiled = _compiled()
    runtimes = []
    for value in (left, right):
        state = _imported(compiled, (((99, -1), value),))
        runtimes.append(SearchPathRuntime.from_state(
            state, compiled, hash_override=17, history_witnesses=(state.position,),
        ))
    a, b = runtimes
    assert position_identity_key(a.position, compiled) != position_identity_key(b.position, compiled)
    assert a.current_identity != b.current_identity
    assert not _identity_equal(a.current_identity, b.current_identity)
    assert a.search_key() != b.search_key()
    table = TranspositionTable()
    table.store(a.search_key(), 2, 12345, BoundType.EXACT, None)
    assert table.probe(b.search_key()) is None
    assert a._occurrence_add(b.current_identity, a.runtime_hash) == 0
    assert len(a._occurrences[a.runtime_hash]) == 2


@pytest.mark.parametrize("before_aux,after_aux", (
    ((), (((99, -1), None),)),
    ((((99, -1), None),), ()),
    ((((99, -1), 0),), (((99, -1), False),)),
    ((((99, -1), (1, 2)),), (((99, -1), (True, 2)),)),
))
def test_component_presence_and_nested_scalar_oracle(before_aux, after_aux):
    compiled = _compiled()
    position = initial_state(compiled).position
    before = replace(position, aux_state=before_aux)
    after = replace(position, aux_state=after_aux)
    actual = _semantic_component_diff_hash(before, after, compiled,
                                           _full_runtime_hash(before, compiled))
    assert actual == _full_runtime_hash(after, compiled)


def test_exact_count_and_history_guards_keep_scalar_types(monkeypatch):
    compiled = _compiled()
    state = initial_state(compiled)
    identities = [_runtime_position_identity(
        replace(state.position, aux_state=(((99, -1), value),)), compiled,
    ) for value in (1, True)]
    left, right = identities
    assert len({left: 1, right: 2}) == 2
    counts = RuntimeCountsSnapshot.from_counts({left: 1, right: 2})
    assert counts.count_for(left) == 1
    assert counts.count_for(right) == 2
    updated = counts.updated(right, 3)
    assert updated.count_for(left) == 1
    assert updated.count_for(right) == 3
    monkeypatch.setattr(RuntimeHistoryContext, "_record_digest",
                        staticmethod(lambda *_: bytes(16)))
    from generic_chess.core.identity import RuntimeHash
    a = RuntimeHistoryContext.append(None, left, RuntimeHash(17, 17), -1, False)
    b = RuntimeHistoryContext.append(None, right, RuntimeHash(17, 17), -1, False)
    assert a != b


def test_declared_square_default_keeps_nested_scalar_type():
    from rule_semantics_ir_fixtures import en_passant_ruleset

    ruleset = en_passant_ruleset()
    actions = tuple(replace(action, aux_state=tuple(
        replace(slot, initial=(1, 2)) if slot.value_kind == "square_or_none" else slot
        for slot in action.aux_state)) for action in ruleset.semantic_actions)
    compiled = compile_semantic_ruleset(replace(ruleset, semantic_actions=actions))
    slot = next(slot for slot in compiled.ir.aux_slots if slot.value_kind == "square_or_none")
    root = initial_state(compiled).position
    explicit_default = replace(root, aux_state=(((slot.slot_id, -1), (1, 2)),))
    typed_import = replace(root, aux_state=(((slot.slot_id, -1), (True, 2)),))
    assert position_identity_key(root, compiled) == position_identity_key(explicit_default, compiled)
    assert _runtime_position_identity(root, compiled) == _runtime_position_identity(explicit_default, compiled)
    assert position_identity_key(root, compiled) != position_identity_key(typed_import, compiled)
    assert _runtime_position_identity(root, compiled) != _runtime_position_identity(typed_import, compiled)
