"""Malformed caller actions retain Core's illegal-action and rollback contract."""
import pytest
from generic_chess import build_builtin_ruleset,compile_ruleset_for_execution
from generic_chess.core.errors import IllegalActionError
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.session.session import GameSession

@pytest.mark.parametrize("bad", [[], {"bad": "action"}])
def test_unhashable_action_rejection_preserves_full_runtime_state(bad):
    c=compile_ruleset_for_execution(build_builtin_ruleset("standard_shogi"))
    s=GameSession(c)
    r=SearchPathRuntime.from_state(s.state,c,history_witnesses=s._search_witnesses)
    r.legal_actions()
    before=(r.position,tuple(r.history),r.repetition_counts,r.current_identity,
            r.runtime_hash,r.search_key(),r.depth,r.pushes,r.pops)
    with pytest.raises(IllegalActionError):
        r.push(bad)
    assert (r.position,tuple(r.history),r.repetition_counts,r.current_identity,
            r.runtime_hash,r.search_key(),r.depth,r.pushes,r.pops)==before
    r.assert_balanced()

from generic_chess.core.actions import action_from_dict,action_to_dict
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from scripts.search_backend_comparison import CASES,CoreBoard

@pytest.mark.parametrize("name", ["chess-ep","shogi-promotion","shogi-drop"])
@pytest.mark.parametrize("native", [False,True])
def test_reconstructed_equal_actions_repeat_after_parent_restore(name,native):
    case=next(x for x in CASES if x["id"]==name)
    c=compile_ruleset_for_execution(build_builtin_ruleset(
        "western_chess" if case["game"]=="chess" else "standard_shogi"))
    board=CoreBoard(case,c)
    provider=NativeSemanticLegalityProvider.try_create(c,strict=True) if native else None
    if native and provider is None:pytest.skip("native provider unavailable")
    r=SearchPathRuntime.from_state(board.initial,c,history_witnesses=board.witnesses,
                                  legal_binding_provider=provider)
    legal=r.legal_actions()
    wanted={"chess-ep":"e5d6","shogi-promotion":"5c5b+","shogi-drop":"R*5e"}[name]
    # Use the existing fixture's canonical UCI/USI label.
    label=board.label
    a=next(x for x in legal if label(x)==wanted)
    parent_bindings=r._bindings
    before=(r.position,tuple(r.history),r.repetition_counts,r.search_key())
    children=[]
    for _ in range(2):
        copy=action_from_dict(action_to_dict(a))
        assert copy==a and copy is not a
        with r.pushed(copy):
            children.append((r.position,tuple(r.history),r.repetition_counts,r.search_key()))
        assert r.legal_actions() is legal and r._bindings is parent_bindings
        assert (r.position,tuple(r.history),r.repetition_counts,r.search_key())==before
    assert children[0]==children[1]
    r.assert_balanced()
