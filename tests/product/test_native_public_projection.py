"""Reused public syntax must never reuse state bindings or bypass validation."""
from dataclasses import FrozenInstanceError, replace
import pytest
from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution, initial_state
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.core.errors import IllegalActionError
from generic_chess.core.actions import SemanticDropMove
from generic_chess.core.position import Hands
from generic_chess.native.semantic import pack_position, transient_legal_actions
from native_test_helpers import requires_native

pytestmark = requires_native


def fixture():
    compiled=compile_ruleset_for_execution(build_builtin_ruleset('standard_shogi'))
    provider=NativeSemanticLegalityProvider.try_create(compiled,strict=True)
    assert provider is not None
    state=initial_state(compiled)
    raw=transient_legal_actions(provider.native_rules,
        pack_position(provider.native_rules,provider._state_only_payload(state.position,state.ply_count)))
    return provider,state,raw


def test_warm_public_actions_keep_fresh_bindings_and_reject_wrong_source(monkeypatch):
    provider,state,raw=fixture()
    first=provider(state.position,0)
    second=provider(state.position,0)
    assert first==second
    assert all(a is b and x is not y for (a,x),(b,y) in zip(first,second))
    assert all(x[1] is not y[1] for (_,x),(_,y) in zip(first,second))
    monkeypatch.setattr('generic_chess.native.semantic.transient_legal_actions',lambda *args:(raw[0],))
    # Exactly the same packed key is cached, but belongs to the old actor.
    with pytest.raises(ValueError,match='side-to-move'):
        provider(replace(state.position,side_to_move=1),1)


def test_warm_public_action_still_rebuilds_and_validates_binding(monkeypatch):
    provider,state,raw=fixture()
    provider(state.position,0)
    def invalid(*args):
        raise IllegalActionError('binding rejected')
    monkeypatch.setattr(provider.engine,'_make_binding_from_action',invalid)
    with pytest.raises(IllegalActionError,match='binding rejected'):
        provider(state.position,0)


def test_warm_projection_keeps_checkpoint_schedule_and_cache_bound():
    provider,state,_=fixture()
    counts=[]
    for _ in range(2):
        ticks=[]
        provider(state.position,0,lambda:ticks.append(True))
        counts.append(len(ticks))
    assert counts[0]==counts[1] and counts[0]>=4
    cache=provider._metrics_local.public_cache
    cache.clear()
    cache.update({-(i+1):object() for i in range(2048)})
    provider(state.position,0)
    assert 0<len(cache)<=2048
    assert all(k>=0 for k in cache)
    class Abort(Exception):pass
    def abort():raise Abort
    with pytest.raises(Abort):provider(state.position,0,abort)


def test_eviction_retains_real_drop_identity_and_immutable_syntax():
    provider,state,_=fixture()
    # Constructed supported state, not a reachability or game-strength claim.
    position=replace(state.position,hands=(Hands((('G',1),)),Hands.empty()))
    first=provider(position,0)
    assert any(isinstance(action,SemanticDropMove) for action,_ in first)
    provider._metrics_local.public_cache.clear()
    provider._metrics_local.public_cache.update({-(i+1):object() for i in range(2048)})
    after_eviction=provider(position,0)
    assert first==after_eviction
    assert len(provider._metrics_local.public_cache)<=2048
    assert all(k>=0 for k in provider._metrics_local.public_cache)
    drop=next(action for action,_ in after_eviction if isinstance(action,SemanticDropMove))
    with pytest.raises(FrozenInstanceError):
        drop.base_type_id='R'
