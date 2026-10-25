"""Research-only compulsory quiet continuation, never a production default."""
import ast, inspect, textwrap
from collections import Counter
from generic_chess.ai.alphabeta import search as S

def transform(source):
    tree=ast.parse(textwrap.dedent(source));old=ast.dump(tree,include_attributes=False);body=tree.body[0].body
    ids=[i for i,n in enumerate(body)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='stand_pat'for t in n.targets)]
    assert len(ids)==1
    code="""if neutral is None and ctx.first_main_iteration_complete is not False and qdepth < ctx.qhard_depth_limit:
    forced_value = _forced_quiet_continuation(alpha,beta,ply,qdepth,ctx)
    if forced_value is not None:
        return forced_value
"""
    body.insert(ids[0],ast.parse(code).body[0]);ast.fix_missing_locations(tree)
    check=ast.parse(ast.unparse(tree));del check.body[0].body[ids[0]]
    assert ast.dump(check,include_attributes=False)==old
    return tree

class ForcedQuietQ:
    """Only noncheck singleton-action nodes lose the optional stand-pat.

    Preserve terminal/declarations/check paths, initial Q0 reserve, hard q depth,
    all live budgets and the full-history runtime. Branching quiet frontiers use
    original qsearch. Fresh Player/TT per policy is mandatory.
    """
    def __init__(self):self.counts=Counter();self.original=None
    def continuation(self,alpha,beta,ply,qdepth,ctx):
        self.counts['classified']+=1
        actions=S._runtime_legal_actions(ctx,ctx.checkpoint);ctx.budget.check(ctx.stats,force=True)
        if len(actions)!=1:return None
        if ctx.qnode_limit is not None and ctx.stats.qnodes>=ctx.qnode_limit:
            ctx.stats.qsearch_budget_aborts+=1;raise S.SearchAborted('qsearch_budget')
        self.counts['forced']+=1
        self.counts['beyond_ordinary']+=int(qdepth>=S._ordinary_qdepth_limit(ctx))
        with ctx.runtime.pushed(actions[0],checkpoint=ctx.checkpoint):
            value=-S._quiescence_runtime(-beta,-alpha,ply+1,qdepth+1,ctx)
        return value
    def __enter__(self):
        assert not hasattr(S,'_forced_quiet_continuation')
        self.original=S._quiescence_runtime;S._forced_quiet_continuation=self.continuation
        exec(compile(transform(inspect.getsource(self.original)),'<research-forced-quiet-q>','exec'),S.__dict__)
        return self
    def __exit__(self,*args):
        S._quiescence_runtime=self.original;del S._forced_quiet_continuation
