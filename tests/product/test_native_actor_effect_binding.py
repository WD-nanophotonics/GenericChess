"""Actor-relative effect types bind to the original actor, not affected pieces."""
from dataclasses import replace
from scripts.research_record import record_value
import pytest
from generic_chess import native
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core.movement import LeapAtom
from generic_chess.core.semantic_executor import semantic_engine_for, _semantic_public_action
from generic_chess.native import semantic as sem
from generic_chess.native.compiler import compile_native_semantic_rules, NativeUnsupportedRuleError
from generic_chess.native.mirror import expected_snapshot
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import RuleActionEffect, RuleInvariant, RuleSquareRef, RuleTypeRef
from test_native_dynamic_feature_views import reference_features
from generic_chess.learning.features import localized_control_features
from test_f24c_mixed_mechanic_certification import (
    _mixed_ruleset, _position, _move, A0, A1, B0, H0, Piece,
)

pytestmark = pytest.mark.skipif(not native.native_available(), reason='Native unavailable')


def affected(kind, ref, owner=0, promoted=False, guarded=True):
    rule = _mixed_ruleset()
    if kind == 'set_current_type':
        actor = A1 if promoted else A0
        enemy_square = (1, 0) if owner == 0 else (5, 6)
        protected_square = (2, 0) if owner == 0 else (4, 6)
        types = tuple(
            replace(t, movement_atoms=(LeapAtom((1, 0)), LeapAtom((-1, 0))))
            if t.type_id == actor else
            replace(t, movement_atoms=(LeapAtom((0, 1)),))
            if t.type_id in (A0, B0) else t
            for t in rule.piece_types)
        action = _move(actor)
        action = replace(action, effects=action.effects + (
            RuleActionEffect('set_current_type',
                square_ref=RuleSquareRef('fixed', square=enemy_square, owner_relative=False),
                type_ref=RuleTypeRef(ref)),),
            invariants=action.invariants + ((RuleInvariant('squares_not_attacked',
                square_refs=(RuleSquareRef('fixed', square=protected_square,
                                          owner_relative=False),)),) if guarded else ()))
        actions = tuple(a for a in rule.semantic_actions if a.name != action.name) + (action,)
        compiled = compile_semantic_ruleset(replace(rule, piece_types=types,
            semantic_actions=actions, max_ply=2))
        entries = [(3, 3, Piece(owner, A0, actor, promoted=promoted)),
                   (*enemy_square, Piece(1-owner, B0, B0)),
                   (*protected_square, Piece(owner, B0, B0))]
    else:
        types = tuple(replace(t, movement_atoms=(LeapAtom((1, 0)), LeapAtom((-1, 0))))
                      if t.type_id == A0 else t for t in rule.piece_types)
        if kind == 'remove':
            actions = tuple(replace(a, effects=(replace(a.effects[0],
                piece_type_ref=RuleTypeRef(ref)),) + a.effects[1:])
                if a.name == 'capture_A0_B0_leap' else a for a in rule.semantic_actions)
            entries = [(1, 1, Piece(owner, A0, A0)), (2, 1, Piece(1-owner, B0, B0))]
        else:
            effect = RuleActionEffect(kind,
                from_ref=RuleSquareRef('fixed', square=(1, 0), owner_relative=False),
                to_ref=RuleSquareRef('fixed', square=(1, 1), owner_relative=False),
                piece_type_ref=RuleTypeRef(ref), piece_owner='opponent')
            actions = tuple(replace(a, effects=a.effects+(effect,))
                if a.name == 'advance_A0' else a for a in rule.semantic_actions)
            entries = [(3, 3, Piece(owner, A0, A0)), (1, 0, Piece(1-owner, B0, B0))]
        compiled = compile_semantic_ruleset(replace(rule, piece_types=types,
            semantic_actions=actions, max_ply=2))
    position = _position(compiled, entries+[(0, 0, Piece(0, H0, H0)),
                                          (6, 6, Piece(1, H0, H0))], side=owner)
    return compiled, position


def exact_frontier_and_children(compiled, position):
    engine = semantic_engine_for(compiled)
    rules = compile_native_semantic_rules(compiled)
    packed = sem.pack_current_position(rules, position, ply_count=0)
    before = sem.snapshot(rules, packed)
    expected = {_semantic_public_action(engine, a): a for a in engine.legal_actions(position)}
    actual = {sem.public_action(rules, raw): raw for raw in sem.guarded_actions(rules, packed)}
    assert set(actual) == set(expected)
    assert sem.dynamic_features(rules, packed) == reference_features(compiled, position)
    assert sem.spatial_features(rules, packed)['localized_control'] == localized_control_features(position, compiled)
    for action, raw in actual.items():
        child = engine.apply(position, expected[action])
        wanted = expected_snapshot(child, rules, compiled)
        got = sem.snapshot(rules, sem.make_checked(rules, packed, raw))
        for field in ('board', 'hands', 'aux_state', 'side'):
            assert record_value(got[field]) == record_value(wanted[field])
    assert sem.snapshot(rules, packed) == before


@pytest.mark.parametrize('kind', ('move', 'shift', 'remove'))
@pytest.mark.parametrize('ref', ('action_base', 'action_current'))
@pytest.mark.parametrize('owner', (0, 1))
def test_actor_relative_filter_frontier_and_all_children(kind, ref, owner):
    c, p = affected(kind, ref, owner)
    # Preserve the existing conservative provider boundary, even with fixed C.
    assert NativeSemanticLegalityProvider.try_create(c) is None
    exact_frontier_and_children(c, p)


@pytest.mark.parametrize('ref', ('action_base', 'action_current'))
@pytest.mark.parametrize('owner', (0, 1))
@pytest.mark.parametrize('promoted', (False, True))
@pytest.mark.parametrize('guarded', (False, True))
def test_set_current_type_uses_original_actor_before_invariants(ref, owner, promoted, guarded):
    c, p = affected('set_current_type', ref, owner, promoted, guarded)
    assert NativeSemanticLegalityProvider.try_create(c) is not None
    exact_frontier_and_children(c, p)


@pytest.mark.parametrize('advertise', (None, False))
def test_old_kernel_declines_affected_rules_but_keeps_ordinary_rules(monkeypatch, advertise):
    module = native._module()
    caps = module.native_capabilities().copy()
    assert caps.pop('semantic_actor_relative_effect_binding') is True
    if advertise is not None:
        caps['semantic_actor_relative_effect_binding'] = advertise
    class OldBackend:
        def native_capabilities(self):
            return caps
        def __getattr__(self, name):
            return getattr(module, name)
    c, p = affected('set_current_type', 'action_current')
    with pytest.raises(NativeUnsupportedRuleError, match='rebuilt kernel'):
        compile_native_semantic_rules(c, backend_module=OldBackend())
    ordinary = compile_semantic_ruleset(_mixed_ruleset())
    assert compile_native_semantic_rules(ordinary, backend_module=OldBackend()).native_executable
    monkeypatch.setattr(module, 'native_capabilities', lambda: caps)
    assert NativeSemanticLegalityProvider.try_create(c) is None
    # The complete explicit Core path remains usable after normal refusal.
    assert semantic_engine_for(c).legal_actions(p)
