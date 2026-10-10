"""Compiled event dispatch preserves auxiliary ownership and dynamic operands."""
from dataclasses import replace
from types import SimpleNamespace
import pytest
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import SemanticEngine, _WorkingPosition
from generic_chess.rules.compiler import compile_semantic_ruleset
from rule_semantics_ir_fixtures import castling_ruleset

@pytest.mark.parametrize('scope', ['per_owner', 'global'])
@pytest.mark.parametrize('owner_filter', ['self', 'opponent', 'any'])
@pytest.mark.parametrize('relative', [False, True])
def test_event_square_owner_and_slot_ownership(scope, owner_filter, relative):
    compiled = compile_semantic_ruleset(castling_ruleset())
    slot = replace(compiled.ir.aux_slots[0], scope=scope)
    trigger = replace(compiled.ir.triggers[0], owner=owner_filter,
                      square_ref=replace(compiled.ir.triggers[0].square_ref,
                                         owner_relative=relative))
    compiled = replace(compiled, ir=replace(compiled.ir, aux_slots=(slot,), triggers=(trigger,)))
    engine = SemanticEngine(compiled)
    for side in (0, 1):
        position = replace(engine._initial_position(), side_to_move=side)
        for event_owner in (0, 1):
            for square in (4, 59, 20):
                work = _WorkingPosition(position, compiled.support)
                work.events = [('piece_leaves_square', Piece(event_owner, 'K', 'K'), square)]
                aux = {}
                engine._apply_transition_triggers(position, work, SimpleNamespace(source=4,target=5,path=()), aux, None)
                expected = {}
                for owner in ((0, 1) if scope == 'per_owner' else (side,)):
                    hit = square == (59 if relative and owner == 1 else 4)
                    hit &= owner_filter == 'any' or (event_owner == owner) == (owner_filter == 'self')
                    if hit:expected[(slot.slot_id, owner if scope == 'per_owner' else -1)] = 0
                assert aux == expected

@pytest.mark.parametrize('kind', ['source', 'target'])
def test_dynamic_square_fallback_and_replacement_rebuild(kind):
    original = compile_semantic_ruleset(castling_ruleset())
    trigger = replace(original.ir.triggers[0], square_ref=replace(
        original.ir.triggers[0].square_ref, kind=kind, square=None))
    changed = replace(original, ir=replace(original.ir, triggers=(trigger,)))
    assert changed._fixed_transition_triggers is not original._fixed_transition_triggers
    engine = SemanticEngine(changed);position = engine._initial_position()
    work = _WorkingPosition(position,changed.support)
    work.events = [('piece_leaves_square',Piece(0,'K','K'),20)]
    aux = {}
    binding=SimpleNamespace(source=20 if kind=='source' else 21,target=20 if kind=='target' else 21,path=())
    engine._apply_transition_triggers(position,work,binding,aux,None)
    assert aux == {(trigger.slot_id,0):0}
    assert original.ir.triggers[0].square_ref.kind == 'fixed'


def test_matching_event_keeps_live_cancellation_boundary():
    compiled=compile_semantic_ruleset(castling_ruleset());engine=SemanticEngine(compiled)
    position=engine._initial_position();work=_WorkingPosition(position,compiled.support)
    work.events=[('piece_leaves_square',Piece(0,'K','K'),4)]
    def cancel():raise RuntimeError('cancelled')
    with pytest.raises(RuntimeError,match='cancelled'):
        engine._apply_transition_triggers(position,work,SimpleNamespace(source=4,target=5,path=()),{},cancel)
    assert position == engine._initial_position()


def test_explicit_auxiliary_effect_runs_after_matching_trigger_clear():
    compiled=compile_semantic_ruleset(castling_ruleset())
    pattern=next(p for p in compiled.ir.patterns if p.pattern_id=='sem_00_king_side_shift')
    pattern=replace(pattern,effects=tuple(replace(e,kind='set_bool',value=1) if e.kind=='clear_right' else e for e in pattern.effects))
    compiled=replace(compiled,ir=replace(compiled.ir,patterns=tuple(pattern if p.pattern_id==pattern.pattern_id else p for p in compiled.ir.patterns)))
    engine=SemanticEngine(compiled);position=engine._initial_position()
    action=next(a for a in engine.legal_actions(position) if a.pattern_id==pattern.pattern_id)
    child=engine.apply(position,action)
    assert dict(child.aux_state)[(compiled.ir.aux_slots[0].slot_id,0)] == 1
    assert child != position
