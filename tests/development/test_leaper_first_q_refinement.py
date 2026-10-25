"""Anytime first fallback, q semantic TT boundary and depth provenance."""
from scripts import leaper_design as L
from scripts.leaper_first_q_refinement import FirstQRefinement
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.limits import SearchLimits

def run(*,refine=True,q=4,cancel_after_first=False,depth=2):
    c=L.compile_rule(L.definition(5,7));s=L.GameSession(c);p=AlphaBetaPlayer(c,use_disk_cache=False);seen=[]
    class Cancel:
        def is_cancelled(self):return cancel_after_first and bool(seen)
    def progress(dep,n,qn):seen.append((dep,n,qn))
    from contextlib import nullcontext
    policy=FirstQRefinement()if refine else None
    with policy if policy is not None else nullcontext():
        result=p.choose_action(s,SearchLimits(max_depth=depth,max_nodes=100000,max_time_seconds=10,quiescence_max_depth=q),cancel_token=Cancel(),progress_callback=progress)
    return result,seen,policy

def test_preserves_cancel_after_first_q0_prefix_and_fallback():
    old,old_seen,_=run(refine=False,cancel_after_first=True);new,new_seen,p=run(cancel_after_first=True)
    assert old_seen==new_seen and len(new_seen)==1
    assert (old.action,old.score,old.completed_depth,old.nodes,old.qnodes)==(new.action,new.score,new.completed_depth,new.nodes,new.qnodes)
    assert new.result_ordinary_qdepth==0 and new.termination_reason=='cancelled'

def test_second_depth1_is_refinement_not_depth2_and_tt_is_cleared():
    old=S.run_root_search;r,seen,p=run(depth=1)
    assert [d for d,_,_ in seen]==[1,1]and r.completed_depth==1 and r.result_ordinary_qdepth==4
    assert p.counts['q_semantic_tt_clears']==1 and S.run_root_search is old

def test_explicit_q0_does_not_duplicate_iteration():
    r,seen,p=run(q=0)
    assert [d for d,_,_ in seen]==[1,2]and not p.counts

def test_zero_depth_keeps_legal_fallback():
    r,seen,p=run(depth=0)
    assert not seen and r.action is not None and r.completed_depth==0 and not p.counts

def test_incompatible_q0_root_entry_cannot_supply_q4_refinement(monkeypatch):
    from generic_chess.ai.alphabeta.transposition import BoundType
    c=L.compile_rule(L.definition(5,7));sess=L.GameSession(c);player=AlphaBetaPlayer(c,use_disk_cache=False)
    original=S.negamax;contexts=[];scores=[];events=[];poison=424242
    def observe(*args,**kw):
        r=original(*args,**kw)
        if args[4]==0:contexts[:]=[args[5]];scores.append(r.score)
        return r
    monkeypatch.setattr(S,'negamax',observe)
    class Cancel:
        def is_cancelled(self):return len(events)>=2
    def progress(depth,nodes,qnodes):
        events.append(depth)
        if len(events)==1:
            ctx=contexts[0]
            # Deliberately incompatible high-depth EXACT entry at q semantic boundary.
            ctx.tt.store(ctx.runtime.search_key(),999,poison,BoundType.EXACT,None)
    with FirstQRefinement()as policy:
        r=player.choose_action(sess,SearchLimits(max_depth=2,max_nodes=100000,max_time_seconds=10),cancel_token=Cancel(),progress_callback=progress)
    assert events==[1,1]and len(scores)==2 and scores[1]!=poison and r.score==scores[1]
    assert policy.counts['q_semantic_tt_clears']==1 and r.result_ordinary_qdepth==4
    contexts[0].runtime.assert_balanced()
