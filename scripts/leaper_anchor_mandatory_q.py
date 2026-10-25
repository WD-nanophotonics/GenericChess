"""Research-only mandatory all-anchor frontier; not a deployed heuristic."""
import ast,inspect,textwrap
from collections import Counter
from generic_chess.ai.alphabeta import search as S

class AnchorMandatoryQ:
    """All legal actions must be anchor board moves; no standpat at that node.

    General rule semantics, not K IDs, position/WDL labels, or a fitted threshold.
    Initial Q0, explicit Q0, check/declaration paths and existing hard/budget caps
    remain authoritative. Ordinary branching mixed-piece nodes use original q.
    Fresh Player/TT per policy. This is approximate outside full-clock completion.
    """
    def __init__(self):self.counts=Counter()
    def continuation(self,alpha,beta,ply,qdepth,ctx):
        self.counts['classified']+=1;actions=S._runtime_legal_actions(ctx,ctx.checkpoint);ctx.budget.check(ctx.stats,force=True)
        if not actions:return None
        for a in actions:
            square=getattr(a,'from_square',None)
            if square is None:return None
            piece=ctx.runtime.position.board[square.rank*ctx.compiled.board_size+square.file]
            if piece is None or not ctx.compiled.types_by_id[piece.current_type_id].is_anchor:return None
        if ctx.qnode_limit is not None and ctx.stats.qnodes>=ctx.qnode_limit:
            ctx.stats.qsearch_budget_aborts+=1;raise S.SearchAborted('qsearch_budget')
        self.counts['anchor_frontiers']+=1;self.counts['branching_anchor_frontiers']+=int(len(actions)>1);self.counts['beyond_ordinary']+=int(qdepth>=S._ordinary_qdepth_limit(ctx));best=-S.INF
        for a in sorted(actions,key=str):
            self.counts['anchor_actions']+=1
            with ctx.runtime.pushed(a,checkpoint=ctx.checkpoint):score=-S._quiescence_runtime(-beta,-alpha,ply+1,qdepth+1,ctx)
            best=max(best,score);alpha=max(alpha,score)
            if alpha>=beta:break
        return best
    def __enter__(self):
        self.original=S._quiescence_runtime;tree=ast.parse(textwrap.dedent(inspect.getsource(self.original)));before=ast.dump(tree,include_attributes=False);body=tree.body[0].body;indices=[i for i,n in enumerate(body)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='stand_pat'for t in n.targets)];assert len(indices)==1
        code="""if neutral is None and ctx.first_main_iteration_complete is not False and _ordinary_qdepth_limit(ctx)>0 and qdepth<ctx.qhard_depth_limit:
    anchor_value=_anchor_mandatory(alpha,beta,ply,qdepth,ctx)
    if anchor_value is not None:
        return anchor_value
"""
        body.insert(indices[0],ast.parse(code).body[0]);ast.fix_missing_locations(tree);check=ast.parse(ast.unparse(tree));del check.body[0].body[indices[0]];assert ast.dump(check,include_attributes=False)==before
        assert not hasattr(S,'_anchor_mandatory');S._anchor_mandatory=self.continuation;exec(compile(tree,'<research-anchor-mandatory-q>','exec'),S.__dict__);return self
    def __exit__(self,*args):S._quiescence_runtime=self.original;del S._anchor_mandatory
