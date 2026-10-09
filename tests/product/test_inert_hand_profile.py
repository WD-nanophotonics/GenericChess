"""A narrow rule-only hand boundary; real hands and identity stay intact."""
from dataclasses import replace

import pytest

from conftest import T, king_type, make_ruleset
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.movement import LeapAtom
from generic_chess.core.position import Hands
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import (
    RuleDeclaration, RuleDeclarationOutcomeBand, RuleWeightedMaterialMetric,
)
from generic_chess.rules.western_chess import build_western_chess_ruleset


def definition():
    return make_ruleset(4, [king_type(), T('P', LeapAtom((0, 1)))],
                        drop_all={'P': (False,) * 16})


@pytest.mark.parametrize('disposition', ['capture_to_hand', 'remove_from_game'])
def test_known_no_drop_no_declaration_legacy_stock_has_zero_leaf_coefficient(disposition):
    compiled = compile_ruleset_for_execution(replace(definition(), capture_disposition=disposition))
    before = compiled.initial_position
    profile, scope = build_semantic_opportunity_profile(compiled, EvaluationConfig())
    assert profile.board_value_by_type['P'] == 1000
    assert profile.hand_value_by_base_type['P'] == 0
    assert profile.piece_profiles['P'].normalized_hand_value == 0
    assert scope['hand_policy'] == 'zero_proved_inert'
    assert profile.evaluator_version == 'semantic-opportunity-v3-inert-hand'
    with_stock = replace(before, hands=(Hands((('P', 1),)), Hands.empty()))
    assert repetition_identity_key(before, compiled) != repetition_identity_key(with_stock, compiled)
    assert compiled.initial_position == before


@pytest.mark.parametrize('dependency', ['drop', 'declaration'])
def test_one_known_hand_reader_excludes_inert_classification(dependency):
    rule = definition()
    if dependency == 'drop':
        rule = replace(rule, drop_allowed={'P': ((True,) + (False,) * 15,) * 2})
    else:
        rule = replace(rule, declarations=(RuleDeclaration(
            declaration_id='stock', owner=0,
            weighted_metric=RuleWeightedMaterialMetric(weights={'P': 1}, include_hands=True),
            outcome_bands=(RuleDeclarationOutcomeBand(1, 'WIN'),)),))
    compiled = compile_ruleset_for_execution(rule)
    profile, scope = build_semantic_opportunity_profile(compiled, EvaluationConfig())
    assert profile.hand_value_by_base_type['P'] == 900
    assert scope['hand_policy'] == 'legacy_scale_unvalidated'


def test_semantic_no_drop_rules_are_not_implicitly_classified_as_inert():
    compiled = compile_ruleset_for_execution(build_western_chess_ruleset())
    profile, scope = build_semantic_opportunity_profile(compiled, EvaluationConfig())
    assert any(profile.hand_value_by_base_type.values())
    assert scope['hand_policy'] == 'legacy_scale_unvalidated'


def test_equivalent_legacy_lowered_ir_and_stripped_handle_have_equal_hand_policy():
    from generic_chess.rules.compiler import compile_semantic_ir, _build_semantic_support
    from generic_chess.rules.ir import CompiledSemanticRuleset
    compiled = compile_ruleset_for_execution(definition())
    lowered = CompiledSemanticRuleset(ir=compile_semantic_ir(compiled),
                                     support=_build_semantic_support(compiled))
    a, sa = build_semantic_opportunity_profile(compiled, EvaluationConfig())
    b, sb = build_semantic_opportunity_profile(lowered, EvaluationConfig())
    assert a == b
    assert sa['hand_policy'] == sb['hand_policy'] == 'zero_proved_inert'


def test_unknown_state_effect_keeps_legacy_hand_scale():
    from generic_chess.rules.compiler import compile_semantic_ir, _build_semantic_support
    from generic_chess.rules.ir import CompiledSemanticRuleset, CompiledEffect
    compiled = compile_ruleset_for_execution(definition())
    ir = compile_semantic_ir(compiled)
    first = ir.patterns[0]
    # A hand-consuming board action is a real dependency even with no drops.
    from generic_chess.rules.ir import CompiledTypeRef
    changed = replace(first, effects=first.effects + (CompiledEffect(
        'remove_from_hand', piece_type_ref=CompiledTypeRef('explicit', 'P')),))
    lowered = CompiledSemanticRuleset(ir=replace(ir, patterns=(changed,) + ir.patterns[1:]),
                                     support=_build_semantic_support(compiled))
    p, s = build_semantic_opportunity_profile(lowered, EvaluationConfig())
    assert p.hand_value_by_base_type['P'] == 900
    assert s['hand_policy'] == 'legacy_scale_unvalidated'
