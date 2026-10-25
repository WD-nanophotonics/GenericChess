"""Diagnostic only: recompute a frozen full-history frontier to its hard clock.

No supplied score/WDL is used. This is an exposed-case coverage intervention,
not a deployable selector; each match runs the existing Player on all remaining
main plies with Q0, charging its nodes and wall time to the outer query.
"""
import time
from generic_chess.ai.alphabeta import search as S
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay

class PointCoverage:
    def __init__(self,compiled,leaf):
        self.compiled=compiled;self.leaf=leaf;ss=replay(compiled,leaf['child_record']);self.path_actions=[]
        for a in leaf['actions']:
            a=L.match_action(ss,a);self.path_actions.append(a);ss.submit(a)
        assert L.state_sha(ss.state)==leaf['state_sha256'];self.path=[];self.busy=False;self.records=[]
    def main(self,*args,**kw):
        if self.busy:return self.original_m(*args,**kw)
        root=args[4]==0
        if root:assert not self.path
        a=kw.get('prev_action');pushed=a is not None
        if pushed:self.path.append(a)
        try:return self.original_m(*args,**kw)
        finally:
            if pushed:self.path.pop()
    def q(self,alpha,beta,ply,qdepth,ctx):
        if self.busy or qdepth!=0 or self.path!=self.path_actions:return self.original_q(alpha,beta,ply,qdepth,ctx)
        runtime=ctx.runtime;assert runtime.ply_count==self.leaf['remaining']*-1+self.compiled.max_ply
        ctx.stats.qnodes+=1;ctx.budget.check(ctx.stats,force=True)
        if ctx.qnode_limit is not None and ctx.stats.qnodes>=ctx.qnode_limit:
            ctx.stats.qsearch_budget_aborts+=1;raise S.SearchAborted('qsearch_budget')
        seconds=2.0 if ctx.budget._deadline is None else min(2.0,ctx.budget._deadline-time.perf_counter())
        if seconds<=0:raise S.SearchAborted('time_limit')
        remaining_nodes=500000 if ctx.budget._max_nodes is None else min(500000,ctx.budget._max_nodes-ctx.stats.nodes-ctx.stats.qnodes)
        if remaining_nodes<=0:raise S.SearchAborted('node_limit')
        ss=replay(self.compiled,self.leaf['child_record'])
        for a in self.path_actions:ss.submit(a)
        assert ss.state.position==runtime.position and ss.state.ply_count==runtime.ply_count
        p=AlphaBetaPlayer(self.compiled,use_disk_cache=False,tuning=SearchTuning());tick=time.perf_counter();self.busy=True
        try:d=p.choose_action(ss,SearchLimits(max_depth=self.leaf['remaining'],max_nodes=remaining_nodes,max_time_seconds=seconds,quiescence_max_depth=0,quiescence_hard_max_depth=8),cancel_token=ctx.budget._cancel)
        finally:self.busy=False
        self.records.append(dict(score=d.score,completed_depth=d.completed_depth,required_depth=self.leaf['remaining'],nodes=d.nodes,qnodes=d.qnodes,seconds=time.perf_counter()-tick,termination=d.termination_reason,source=d.result_source,entry_alpha=alpha,entry_beta=beta,full_history_sha256=self.leaf['state_sha256']))
        ctx.stats.nodes+=d.nodes;ctx.stats.qnodes+=d.qnodes;ctx.budget.check(ctx.stats,force=True)
        if d.completed_depth<self.leaf['remaining']:raise S.SearchAborted('local_coverage_incomplete')
        return d.score
    def __enter__(self):self.original_m=S.negamax;self.original_q=S._quiescence_runtime;S.negamax=self.main;S._quiescence_runtime=self.q;return self
    def __exit__(self,*args):S.negamax=self.original_m;S._quiescence_runtime=self.original_q;assert not self.path and not self.busy
