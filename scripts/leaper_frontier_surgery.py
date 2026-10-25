"""One frozen full-history event intervention, never a deployable policy."""
from scripts import leaper_design as L
from generic_chess.ai.alphabeta import search as S


class FrontierEventReplacement:
    def __init__(self,target):
        self.target=target;self.stack=[];self.iteration=None;self.interventions=[]
    def __enter__(self):
        self.old_m,self.old_q=S.negamax,S._quiescence_runtime
        def main(*args,**kw):
            if args[4]==0:self.iteration=args[1]
            parent=self.stack[-1]if self.stack else[]
            action=kw.get('prev_action')
            path=parent+([L.record_value(action)]if action is not None else[])
            self.stack.append(path)
            try:return self.old_m(*args,**kw)
            finally:self.stack.pop()
        def q(*args,**kw):
            result=self.old_q(*args,**kw)
            alpha,beta,ply,qdepth,ctx=args
            t=self.target
            if (not self.interventions and self.iteration==3 and qdepth==0 and
                    self.stack and self.stack[-1]==t['target_path'] and
                    ctx.runtime.ply_count==t['expected_absolute_ply'] and
                    ctx.runtime.position.side_to_move==t['expected_actor'] and
                    alpha==t['entry_alpha']and beta==t['entry_beta']):
                assert result==t['old_value'],'counterfactualtarget originalreturn mismatch; preserve failure'
                self.interventions.append(dict(iteration=3,path=list(self.stack[-1]),absolute_ply=ctx.runtime.ply_count,actor=ctx.runtime.position.side_to_move,entry_alpha=alpha,entry_beta=beta,original_return=result,replacement=t['replacement'],scope='One actual completed event intervention; not a general scoring/search policy.'))
                return t['replacement']
            return result
        S.negamax=main;S._quiescence_runtime=q
        return self
    def __exit__(self,*exc):
        S.negamax=self.old_m;S._quiescence_runtime=self.old_q
        assert not self.stack
