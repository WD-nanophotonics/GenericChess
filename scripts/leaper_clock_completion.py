"""Research-only full completion of an eligible <=4-ply rules-clock frontier."""
import ast,inspect,textwrap
from collections import Counter
from generic_chess.ai.alphabeta import search as S

def transformed(source):
    tree=ast.parse(textwrap.dedent(source));original=ast.dump(tree,include_attributes=False);f=tree.body[0]
    ii=[i for i,n in enumerate(f.body)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='stand_pat'for t in n.targets)];assert len(ii)==1
    node=ast.parse('if neutral is None and 0 < ctx.compiled.max_ply-runtime.ply_count <= 4 and qdepth+ctx.compiled.max_ply-runtime.ply_count <= ctx.qhard_depth_limit:\n    return _complete_rules_clock(alpha,beta,ply,qdepth,ctx,True)').body[0]
    f.body.insert(ii[0],node);ast.fix_missing_locations(tree);check=ast.parse(ast.unparse(tree));del check.body[0].body[ii[0]];assert ast.dump(check,include_attributes=False)==original
    return tree

class ClockCompletion:
    def __init__(self):self.counts=Counter();self.original=None
    def exact(self,alpha,beta,ply,qdepth,ctx,already_counted=False):
        if not already_counted:ctx.stats.qnodes+=1
        ctx.budget.check(ctx.stats);rt=ctx.runtime;state=rt.state;rem=ctx.compiled.max_ply-rt.ply_count
        self.counts['visits']+=1
        if rt.terminal_status.is_terminal:
            self.counts['terminal']+=1;return S.terminal_score(rt.terminal_status,state.position.side_to_move,ply)
        if rem<=0:raise S.SearchAborted('clock_completion_unproved_terminal')
        if qdepth>=ctx.qhard_depth_limit:raise S.SearchAborted('clock_completion_hard_limit')
        if ctx.qnode_limit is not None and ctx.stats.qnodes>=ctx.qnode_limit:
            ctx.stats.qsearch_budget_aborts+=1;raise S.SearchAborted('qsearch_budget')
        options=S._declaration_options(state,ctx.compiled,ctx.stats)
        if any(x.outcome=='WIN'for x in options):return S.MATE_SCORE-ply
        neutral=S._neutral_declaration(options);best=0 if neutral is not None else-S.INF
        if neutral is not None:alpha=max(alpha,0)
        actions=S._runtime_legal_actions(ctx,ctx.checkpoint);ctx.budget.check(ctx.stats,force=True)
        if not actions:raise S.SearchAborted('clock_completion_no_legal_frontier')
        if already_counted:self.counts['roots']+=1;self.counts['root_remaining_'+str(rem)]+=1
        for action in S._order_qactions(state,actions,ply,ctx,in_check=False):
            with rt.pushed(action,checkpoint=ctx.checkpoint):
                score=-self.exact(-beta,-alpha,ply+1,qdepth+1,ctx)
            if score>best:best=score
            if score>alpha:alpha=score
            if alpha>=beta:self.counts['beta_cutoffs']+=1;break
        return best
    def __enter__(self):
        assert not hasattr(S,'_complete_rules_clock')
        self.original=S._quiescence_runtime
        code=compile(transformed(inspect.getsource(self.original)),'<research-clock-completion>','exec')
        S._complete_rules_clock=self.exact
        try:exec(code,S.__dict__)
        except BaseException:
            S._quiescence_runtime=self.original;del S._complete_rules_clock;raise
        return self
    def __exit__(self,*args):S._quiescence_runtime=self.original;del S._complete_rules_clock
