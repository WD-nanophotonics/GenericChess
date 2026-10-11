"""Readonly candidate chunks preserve legality, order, input and rule binding."""
import pytest
from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.native import native_available
from generic_chess.native import semantic as ns
from scripts.search_backend_comparison import CASES, CoreBoard

pytestmark = pytest.mark.skipif(not native_available(), reason="Native unavailable")

def root(case_id):
    case = next(x for x in CASES if x['id'] == case_id)
    compiled = compile_ruleset_for_execution(build_builtin_ruleset('western_chess' if case['game'] == 'chess' else 'standard_shogi'))
    board = CoreBoard(case, compiled)
    provider = NativeSemanticLegalityProvider.try_create(compiled, strict=True)
    assert provider is not None
    position = ns.pack_position(provider.native_rules, provider._state_only_payload(board.runtime.position, board.runtime.ply_count))
    return provider, position

@pytest.mark.parametrize('case_id', ['chess-ep', 'chess-promotion', 'shogi-promotion', 'shogi-drop'])
@pytest.mark.parametrize('chunk_size', [1, 8, 32])
def test_chunks_match_full_ordered_membership_and_leave_parent_unchanged(case_id, chunk_size):
    provider, position = root(case_id)
    candidates = tuple(reversed(ns.candidate_actions(provider.native_rules, position)))
    legal = set(ns.transient_legal_actions(provider.native_rules, position))
    before = ns.snapshot(provider.native_rules, position)
    observed = tuple(action for i in range(0, len(candidates), chunk_size)
                     for action in ns.transient_legal_subset(provider.native_rules, position, candidates[i:i+chunk_size]))
    assert observed == tuple(x for x in candidates if x in legal)
    assert ns.snapshot(provider.native_rules, position) == before
    assert ns.transient_legal_subset(provider.native_rules, position, ()) == ()
    if legal:
        action = next(iter(legal))
        assert ns.transient_legal_subset(provider.native_rules, position, (action, action)) == (action, action)

@pytest.mark.parametrize('bad,error', [(True, TypeError), (1.5, TypeError), ('3', TypeError), (-1, OverflowError), (1 << 64, OverflowError)])
def test_malformed_chunks_fail_before_trials_and_next_call_is_unaffected(bad, error):
    provider, position = root('chess-ep')
    legal = ns.transient_legal_actions(provider.native_rules, position)
    with pytest.raises(error):
        ns.transient_legal_subset(provider.native_rules, position, [legal[0], bad])
    assert ns.transient_legal_subset(provider.native_rules, position, legal) == legal

def test_foreign_compiled_position_is_rejected():
    a, position = root('chess-ep')
    b, _ = root('shogi-drop')
    with pytest.raises(ValueError):
        ns.transient_legal_subset(b.native_rules, position, ())

@pytest.mark.parametrize('invalid', [0, (1 << 64) - 1])
def test_malformed_u64_is_not_a_legal_action(invalid):
    provider, position = root('chess-ep')
    assert ns.transient_legal_subset(provider.native_rules, position, (invalid,)) == ()


def test_old_native_extension_reports_missing_capability(monkeypatch):
    from types import SimpleNamespace
    provider, position = root('chess-ep')
    monkeypatch.setattr(ns, '_module', lambda: SimpleNamespace())
    with pytest.raises(RuntimeError, match='lacks candidate chunk legality'):
        ns.transient_legal_subset(provider.native_rules, position, ())

@pytest.mark.parametrize('chunk_size', [1, 8, 32])
def test_compound_four_cell_effect_and_persistent_aux_right(chunk_size):
    from rule_semantics_ir_fixtures import castling_ruleset
    from generic_chess.session.session import GameSession
    compiled = compile_ruleset_for_execution(castling_ruleset())
    session = GameSession(compiled)
    provider = NativeSemanticLegalityProvider.try_create(compiled, strict=True)
    assert provider is not None
    for ply in range(2):
        position = ns.pack_position(provider.native_rules, provider._state_only_payload(session.state.position, session.state.ply_count))
        candidates = ns.candidate_actions(provider.native_rules, position)
        full = ns.transient_legal_actions(provider.native_rules, position)
        chunked = tuple(a for i in range(0, len(candidates), chunk_size)
                        for a in ns.transient_legal_subset(provider.native_rules, position, candidates[i:i+chunk_size]))
        assert chunked == full
        assert set(ns.public_action(provider.native_rules, a) for a in chunked) == set(session.legal_actions())
        if ply == 0:
            action = next(a for a in session.legal_actions() if a.pattern_id == 'sem_00_king_side_shift')
            before = session.state.position
            session.submit(action)
            after = session.state.position
            assert sum(x != y for x, y in zip(before.board, after.board)) == 4
            assert after.aux_state != before.aux_state

@pytest.mark.parametrize('chunk_size',[1,8,32])
def test_nested_s4_checks_leave_parent_and_subsequent_full_calls_unchanged(chunk_size):
    from rule_semantics_ir_fixtures import uchifuzume_ruleset
    from generic_chess.session.session import GameSession
    c=compile_ruleset_for_execution(uchifuzume_ruleset());session=GameSession(c)
    provider=NativeSemanticLegalityProvider.try_create(c,strict=True);assert provider is not None
    for _ in range(4):
        position=ns.pack_position(provider.native_rules,provider._state_only_payload(session.state.position,session.state.ply_count))
        candidates=ns.candidate_actions(provider.native_rules,position);before=ns.snapshot(provider.native_rules,position)
        full=ns.transient_legal_actions(provider.native_rules,position)
        chunked=tuple(a for i in range(0,len(candidates),chunk_size) for a in ns.transient_legal_subset(provider.native_rules,position,candidates[i:i+chunk_size]))
        assert chunked==full and ns.transient_legal_actions(provider.native_rules,position)==full
        assert ns.snapshot(provider.native_rules,position)==before
        assert set(ns.public_action(provider.native_rules,a) for a in full)==set(session.legal_actions())
        if not full:break
        session.submit(ns.public_action(provider.native_rules,full[0]))
