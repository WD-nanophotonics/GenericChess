"""Interrupt at real runtime mutation checkpoints, including PN path replay."""
import pytest
from scripts.generic_proof_fixtures import compile_krk,krk_state
from scripts.generic_win_proof import prove_win,verify_certificate,UNKNOWN
from scripts.generic_win_proof_pn import prove_win_pn
from generic_chess.core.search_runtime import SearchPathRuntime


@pytest.mark.parametrize('solver',[prove_win,prove_win_pn])
@pytest.mark.parametrize('during_push',[True,False])
@pytest.mark.parametrize('semantic',[False,True])
def test_real_cancel_checkpoint_restores_complete_root(monkeypatch,solver,during_push,semantic):
    if semantic:
        from generic_chess import build_western_chess_ruleset,compile_ruleset_for_execution
        from scripts.chess_development import root_from_fen
        c=compile_ruleset_for_execution(build_western_chess_ruleset())
        s=root_from_fen('7k/8/8/8/8/5K2/8/2R5 w - - 0 1',c)
    else:c=compile_krk();s=krk_state(c,0,2,10,1)
    original=SearchPathRuntime.from_state.__func__;roots=[];keys=[];fired=[]
    def factory(cls,*args,**kwargs):
        rt=original(cls,*args,**kwargs);roots.append(rt);keys.append(rt.search_key());return rt
    monkeypatch.setattr(SearchPathRuntime,'from_state',classmethod(factory))
    def cancel():
        if not roots:return False
        rt=roots[0]
        # Legacy transition is an indivisible atomic step; semantic execution
        # additionally exposes a checkpoint before its push counter commits.
        trigger=(rt.depth>0 and (rt.pushes==0 if semantic else True)) if during_push else rt.depth>=2
        if trigger:fired.append((rt.depth,rt.pushes))
        return trigger
    r=solver(c,s,target=0,max_nodes=65536,seconds=3.,cancel=cancel)
    assert fired and r.status==UNKNOWN and r.reason=='cancelled'
    rt=roots[0];rt.assert_balanced()
    assert rt.position==s.position and rt.ply_count==s.ply_count and rt.terminal_status==s.terminal_status
    assert rt.search_key()==keys[0]


def test_verifier_cancellation_during_mutation_cannot_accept_partial_tree(monkeypatch):
    c=compile_krk();s=krk_state(c,0,2,10,1)
    certificate=prove_win(c,s,target=0,max_nodes=65536,seconds=3.).certificate
    assert certificate is not None
    original=SearchPathRuntime.from_state.__func__;roots=[]
    def factory(cls,*args,**kwargs):
        rt=original(cls,*args,**kwargs);roots.append(rt);return rt
    monkeypatch.setattr(SearchPathRuntime,'from_state',classmethod(factory))
    receipt=verify_certificate(c,s,certificate,seconds=3.,cancel=lambda:bool(roots) and roots[0].depth>0)
    assert not receipt['verified'] and receipt['reason']=='cancelled'
    roots[0].assert_balanced()
    assert verify_certificate(c,s,certificate,seconds=3.)['verified']
