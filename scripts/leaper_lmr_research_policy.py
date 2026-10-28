"""Private-process, fixed-policy LMR prototype; desktop defaults unchanged.

Only the caller's fresh, policy-owned TT may be used. This is selective search,
not an exact nominal-depth solver. A reduced fail-low need not be sound.
"""
import sys
import time
from collections import Counter
from types import SimpleNamespace
from generic_chess.ai.alphabeta.quiescence import classify_noisy
from generic_chess.ai.evaluation.config import MATE_THRESHOLD
from generic_chess.core.semantic_executor import semantic_engine_for


class LateQuietReduction:
    def __init__(self,original):
        self.original=original;self.stack=[];self.counts=Counter();self.classification_seconds=0.0

    def _eligible(self,parent,depth,alpha,beta,ply,ctx,pv,previous,caller):
        if (parent is None or parent['ply']<1 or parent['depth']<3 or depth<2
                or parent['pv'] or pv or beta-alpha!=1
                or not(-MATE_THRESHOLD<alpha<beta<MATE_THRESHOLD)):
            return False
        if caller.f_code.co_name!='child_search' or caller.f_back is None:return False
        loc=caller.f_back.f_locals
        if loc.get('ctx') is not ctx or loc.get('ply')!=parent['ply']:raise AssertionError('unexpected search frame')
        index=loc.get('move_index')
        if type(index) is not int:raise AssertionError('missing actual move index')
        if index<4 or ctx.runtime.terminal_status.is_terminal:return False
        self.counts['eligible_dispatch_attempts']+=1
        ctx.budget.check(ctx.stats,force=True)
        t=time.perf_counter();engine=semantic_engine_for(ctx.compiled)
        checked=engine.in_check(parent['position'],parent['position'].side_to_move,checkpoint=ctx.checkpoint)
        noisy=True
        if not checked:
            noisy=bool(classify_noisy(SimpleNamespace(position=parent['position']),[(previous,ctx.runtime.state)],ctx.compiled))
        self.classification_seconds+=time.perf_counter()-t
        ctx.budget.check(ctx.stats,force=True)
        if checked:self.counts['in_check_rejected']+=1
        if noisy:self.counts['noisy_rejected']+=1
        return not checked and not noisy

    def _call(self,args,kw,depth,path,pv):
        args=list(args);args[1]=depth
        ctx=args[5]
        frame=dict(depth=depth,ply=args[4],pv=pv,position=ctx.runtime.position,path=path)
        self.stack.append(frame)
        try:return self.original(*args,**kw)
        finally:assert self.stack.pop() is frame

    def __call__(self,*args,**kw):
        state,depth,alpha,beta,ply,ctx=args[:6]
        parent=self.stack[-1] if self.stack else None
        pv=kw.get('pv_node',True);previous=kw.get('prev_action')
        path=() if parent is None else parent['path']+((previous,) if previous is not None else ())
        if not self._eligible(parent,depth,alpha,beta,ply,ctx,pv,previous,sys._getframe(1)):
            return self._call(args,kw,depth,path,pv)
        self.counts['reductions']+=1
        reduced=self._call(args,kw,depth-1,path,False)
        # Child windows are negated: a parent fail-high means childscore<beta.
        # A child fail-high (>=beta) is the intentionally selective parent
        # fail-low. It is NOT a proof that a deeper improvement is impossible.
        if reduced.score<beta:
            self.counts['full_depth_researches']+=1
            ctx.budget.check(ctx.stats,force=True)
            return self._call(args,kw,depth,path,False)
        self.counts['reduced_fail_low_kept']+=1
        return reduced
