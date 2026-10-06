"""Pseudo-attack approximation has explicit Pawn/pin/off-target boundaries."""
import pytest

from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core.attacks import pseudo_attacks
from generic_chess.core.coordinates import index_to_square
from generic_chess.native.semantic import is_square_attacked, pack_position
import scripts.chess_development as d
from scripts.chess_capture_risk import SemanticHangingRisk


@pytest.fixture(scope='module')
def provider():
    compiled = d.compile_ruleset_for_execution(d.build_western_chess_ruleset())
    value = NativeSemanticLegalityProvider.try_create(compiled, strict=True)
    if value is None:
        pytest.skip('supported native extension unavailable')
    return value


@pytest.mark.parametrize('fen', [
    '7k/8/8/4r3/3P4/8/8/K7 b - - 0 1',
    '4k3/8/4n3/8/3Q4/8/8/K3R3 w - - 0 1',
    '7k/8/8/3pP3/8/8/8/K7 w - d6 0 1',
])
def test_native_semantic_pseudo_attacks_match_reference_preserve_state(provider, fen):
    state = d.root_from_fen(fen, provider.compiled)
    before = d.record_value(state)
    native = pack_position(provider.native_rules, provider._state_only_payload(state.position, state.ply_count))
    for square in range(64):
        for owner in (0, 1):
            assert is_square_attacked(provider.native_rules, native, square, owner) == provider.engine.is_square_attacked(state.position, square, owner)
    risk = SemanticHangingRisk(d.evaluator('geometric_half'), provider)
    value = risk.evaluate(state)
    assert d.record_value(state) == before
    assert risk.risk_calls == risk.calls == 1
    assert abs(value) < 10_000_000


def test_pawn_attack_not_legacy_geometry_and_discount_is_fixed(provider):
    state = d.root_from_fen('7k/8/8/4r3/3P4/8/8/K7 b - - 0 1', provider.compiled)
    risk = SemanticHangingRisk(d.evaluator('geometric_half'), provider)
    terms = risk.terms(state)
    rook = 4+4*8
    assert index_to_square(rook, 8) not in pseudo_attacks(state.position, 0, provider.compiled)
    assert any(r['square'] == rook and r['type_id'] == 'R' for r in terms['exposed'])
    assert terms['correction'] == -(risk.weights['R']//2)


def test_pin_is_explicit_pseudo_risk_not_legal_capture(provider):
    state = d.root_from_fen('4k3/8/4n3/8/3Q4/8/8/K3R3 w - - 0 1', provider.compiled)
    risk = SemanticHangingRisk(d.evaluator('unit'), provider)
    assert any(r['type_id'] == 'Q' for r in risk.terms(state)['exposed'])
    # Native/Python pseudo-attack intentionally includes the pinned Knight;
    # the helper does not claim a legal Black capture or create a Black turn.
    assert state.position.side_to_move == 0 and len(state.history) == 1


def test_ep_off_target_victim_is_not_claimed_by_square_query(provider):
    state = d.root_from_fen('7k/8/8/3pP3/8/8/8/K7 w - d6 0 1', provider.compiled)
    risk = SemanticHangingRisk(d.evaluator('unit'), provider)
    assert not any(r['square'] == 3+4*8 for r in risk.terms(state)['exposed'])


def test_requires_provider_and_preserves_common_order_prices(provider):
    with pytest.raises(ValueError, match='native provider'):
        SemanticHangingRisk(d.evaluator('unit'), None)
    risks = [SemanticHangingRisk(d.evaluator(p), provider) for p in d.POLICIES]
    assert risks[0].order_values == risks[1].order_values == risks[2].order_values


def test_comparison_and_play_share_opt_in_risk_with_history(provider):
    case = dict(id='capture', fen='7K/8/8/8/8/1Rk5/2N5/8 b - - 0 1',
                accepted_uci=['c3b3'], answer_basis='exposed capture control')
    limits = d.SearchLimits(max_depth=2, max_nodes=2048, max_time_seconds=1,
                            quiescence_max_depth=0, quiescence_hard_max_depth=0)
    result = d.compare_case(case, provider.compiled, limits, provider=provider,
                            ordering=True, use_tt=True, capture_risk=True)
    assert all(r['legal'] and r['completed'] and r['state_preserved'] for r in result['rows'])
    assert all(r['capture_risk']['calls'] == r['evaluation_calls'] > 0 for r in result['rows'])
    game = d.play_game(case['fen'], provider.compiled, 'geometric_half','unit',
                       limits,3,provider=provider,capture_risk=True)
    assert game['plies_played'] == 3
    assert all(r['legal'] and r['capture_risk']['queries'] > 0 for r in game['moves'])
    assert len(game['final_state']['history']) == 4


def test_terminal_play_does_not_call_risk_or_invent_moves(provider):
    game = d.play_game('7k/6Q1/5K2/8/8/8/8/8 b - - 0 1', provider.compiled,
                       'unit','geometric_half',d.SearchLimits(),3,
                       provider=provider,capture_risk=True)
    assert game['finished'] and game['end'] == 'checkmate' and not game['moves']
