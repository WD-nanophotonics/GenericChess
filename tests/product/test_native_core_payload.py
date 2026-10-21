"""Complete input transport remains optional and keeps Core state semantics."""
from dataclasses import replace
from types import SimpleNamespace
import pytest
from generic_chess.native import _module, native_available
from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider as Provider
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.position import Hands
from test_native_check_handoff import root, sess

pytestmark = pytest.mark.skipif(not native_available(), reason="native unavailable")

@pytest.mark.parametrize("name", ["chess-ep", "shogi-promotion", "shogi-drop"])
def test_complete_fields_and_old_kernel_fallback(name, monkeypatch):
    c,b = root(name)
    provider = Provider.try_create(c, strict=True)
    assert provider is not None
    original = provider._python_state_only_payload(b.initial.position, b.initial.ply_count)
    assert provider._state_only_payload(b.initial.position, b.initial.ply_count) == original
    if hasattr(_module(), "semantic_core_payload"):
        monkeypatch.delattr(_module(), "semantic_core_payload")
    legacy = Provider.try_create(c, strict=True)
    assert legacy is not None and legacy._payload_builder is None
    assert legacy._state_only_payload(b.initial.position, b.initial.ply_count) == original
    assert legacy(b.initial.position, b.initial.ply_count) == provider(b.initial.position, b.initial.ply_count)

@pytest.mark.parametrize("defect", ["owner", "base", "current", "hand_type", "negative", "large"])
def test_mapping_error_or_large_integer_matches_python(defect):
    c,b = root("shogi-drop")
    provider = Provider.try_create(c, strict=True)
    assert provider is not None
    if provider._payload_builder is None:
        pytest.skip("older optional kernel has no accelerated builder")
    pos=b.initial.position
    board=list(pos.board); index=next(i for i,p in enumerate(board) if p is not None)
    piece=board[index]; hands=pos.hands
    if defect in ("owner", "base", "current"):
        board[index]=SimpleNamespace(owner=5 if defect=="owner" else piece.owner,
            base_type_id="missing" if defect=="base" else piece.base_type_id,
            current_type_id="missing" if defect=="current" else piece.current_type_id,
            promoted=piece.promoted)
    else:
        tid=next(iter(provider.type_ids))
        hands=(Hands((("missing" if defect=="hand_type" else tid,
                      -1 if defect=="negative" else 2**100),)), Hands())
    pos=replace(pos,board=tuple(board),hands=hands)
    if defect=="large":
        assert provider._state_only_payload(pos,255)==provider._python_state_only_payload(pos,255)
    else:
        errors=[]
        for fn in (provider._state_only_payload,provider._python_state_only_payload):
            with pytest.raises(ValueError) as error: fn(pos,255)
            errors.append((type(error.value),str(error.value),
                           type(error.value.__cause__),str(error.value.__cause__)))
        assert errors[0]==errors[1]

@pytest.mark.parametrize("name", ["chess-ep", "shogi-drop"])
def test_actual_search_transport_parity_and_history(name, monkeypatch):
    c,b=root(name); session=sess(b); before=session.state,session._search_witnesses
    results=[]
    original=Provider._state_only_payload
    for fn in (Provider._python_state_only_payload,original):
        monkeypatch.setattr(Provider,"_state_only_payload",fn)
        p=AlphaBetaPlayer(c,use_disk_cache=False,use_native_semantic_availability=True,use_native_semantic_check=True)
        d=p.choose_action(session,SearchLimits(max_depth=2,max_nodes=512,max_time_seconds=5,quiescence_max_depth=2))
        results.append(tuple(getattr(d,f) for f in ("action","score","principal_variation","nodes","qnodes","completed_depth","termination_reason","result_source","runtime_pushes","runtime_pops")))
        assert d.runtime_depth_balanced and d.native_legality_calls>0
        assert (session.state,session._search_witnesses)==before
    assert results[0]==results[1]
