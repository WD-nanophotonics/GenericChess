"""Research-only one-ply clock frontier. No production search/default modification."""
import ast,inspect,textwrap
from collections import Counter
from generic_chess.ai.alphabeta import search as S

def transformed_q(source):
    tree=ast.parse(textwrap.dedent(source));original=ast.dump(tree,include_attributes=False);f=tree.body[0]
    indices=[i for i,n in enumerate(f.body)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='stand_pat'for t in n.targets)]
    assert len(indices)==1
    node=ast.parse('if neutral is None and ctx.compiled.max_ply - runtime.ply_count == 1:\n    return _last_clock_ply(alpha,beta,ply,qdepth,ctx)').body[0]
    f.body.insert(indices[0],node);ast.fix_missing_locations(tree)
    check=ast.parse(ast.unparse(tree));del check.body[0].body[indices[0]]
    assert ast.dump(check,include_attributes=False)==original
    return tree

class LastClockShield:
    """Only noncheck/no-neutral-declaration q nodes with one remaining clock ply change.

    Terminal/declarations/check evasions keep original code/precedence. Every
    actual child must end under Core. Fresh TT per policy is required by caller.
    """
    def __init__(self):self.counts=Counter();self.original=None
    def last(self,alpha,beta,ply,qdepth,ctx):
        self.counts['entered']+=1
        if qdepth>=ctx.qhard_depth_limit:
            self.counts['hard_limit']+=1;raise S.SearchAborted('clock_shield_hard_limit')
        if ctx.qnode_limit is not None and ctx.stats.qnodes>=ctx.qnode_limit:
            ctx.stats.qsearch_budget_aborts+=1;raise S.SearchAborted('qsearch_budget')
        actions=S._runtime_legal_actions(ctx,ctx.checkpoint);ctx.budget.check(ctx.stats,force=True)
        if not actions:raise S.SearchAborted('clock_shield_no_legal_frontier')
        best=-S.INF
        for action in S._order_qactions(ctx.runtime.state,actions,ply,ctx,in_check=False):
            with ctx.runtime.pushed(action,checkpoint=ctx.checkpoint):
                self.counts['children']+=1
                if not ctx.runtime.terminal_status.is_terminal:
                    self.counts['nonterminal_child']+=1;raise S.SearchAborted('clock_shield_unproved_terminal')
                score=-S._quiescence_runtime(-beta,-alpha,ply+1,qdepth+1,ctx)
            if score>best:best=score
            if score>alpha:alpha=score
            if alpha>=beta:self.counts['beta_cutoffs']+=1;break
        return best
    def __enter__(self):
        assert not hasattr(S,'_last_clock_ply'),'no overlapping policy writer'
        self.original=S._quiescence_runtime
        S._last_clock_ply=self.last
        exec(compile(transformed_q(inspect.getsource(self.original)),'<research-last-clock-ply>','exec'),S.__dict__)
        return self
    def __exit__(self,*args):
        S._quiescence_runtime=self.original;del S._last_clock_ply
