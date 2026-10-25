"""Compulsory quiet two-ply Core clock and preserved first reserve/budgets."""
import pytest
from test_leaper_forced_quiet_q import context
from scripts.leaper_forced_branch_depth import ForcedBranchDepth
from generic_chess.ai.alphabeta import search as S
from generic_chess.core.search_runtime import SearchPathRuntime
from dataclasses import replace
from scripts import leaper_design as L

def setup(**kw):
    return context(clock=2,**kw)

def test_singleton_main_depth_reaches_actual_clock_without_standpat():
    _,ctx=setup();old=S.negamax(ctx.runtime.state,1,-S.INF,S.INF,0,ctx);assert old.score==-4242
    _,ctx=setup() # Fresh policy TT; the baseline EXACT entry is incompatible.
    with ForcedBranchDepth()as p:
        r=S.negamax(ctx.runtime.state,1,-S.INF,S.INF,0,ctx)
    assert r.score==0 and len(r.pv)==2 and p.counts['extensions']==2
    ctx.runtime.assert_balanced()

def test_first_q0_reserve_unchanged():
    _,ctx=setup(first=False)
    with ForcedBranchDepth()as p:r=S.negamax(ctx.runtime.state,1,-S.INF,S.INF,0,ctx)
    assert r.score==-4242 and not p.counts['extensions'];ctx.runtime.assert_balanced()

def test_node_abort_restores_policy_and_runtime():
    from generic_chess.ai.limits import SearchLimits
    _,ctx=setup();ctx.budget=S._Budget(SearchLimits(max_nodes=1),None);old=S.negamax
    with pytest.raises(S.SearchAborted,match='node_limit'):
        with ForcedBranchDepth():S.negamax(ctx.runtime.state,1,-S.INF,S.INF,0,ctx)
    assert S.negamax is old;ctx.runtime.assert_balanced()

def test_cancel_during_forced_child_restores_runtime():
    from generic_chess.ai.limits import SearchLimits
    _,ctx=setup()
    class Cancel:
        def is_cancelled(self):return ctx.stats.nodes>=2
    ctx.budget=S._Budget(SearchLimits(max_nodes=1000),Cancel());original=S.negamax
    with pytest.raises(S.SearchAborted,match='cancelled'):
        with ForcedBranchDepth():S.negamax(ctx.runtime.state,1,-S.INF,S.INF,0,ctx)
    assert S.negamax is original;ctx.runtime.assert_balanced()
