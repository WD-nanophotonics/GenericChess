"""Research-only anytime D1Q0 -> isolated D1Q4 refinement, then normal D2+."""
import ast,inspect,textwrap
from collections import Counter
from generic_chess.ai.alphabeta import search as S

def transform(source):
    tree=ast.parse(textwrap.dedent(source));old=ast.dump(tree,include_attributes=False);changed=0
    class Change(ast.NodeTransformer):
        def visit_For(self,node):
            nonlocal changed
            if isinstance(node.target,ast.Name)and node.target.id=='depth'and isinstance(node.iter,ast.Call)and isinstance(node.iter.func,ast.Name)and node.iter.func.id=='range':
                changed+=1;node.iter=ast.Call(ast.Name('_first_q_refinement_depths',ast.Load()),[ast.Name('max_depth',ast.Load()),ast.Name('ctx',ast.Load())],[])
            return self.generic_visit(node)
    Change().visit(tree);assert changed==1;ast.fix_missing_locations(tree)
    class Restore(ast.NodeTransformer):
        def visit_For(self,node):
            if isinstance(node.iter,ast.Call)and isinstance(node.iter.func,ast.Name)and node.iter.func.id=='_first_q_refinement_depths':node.iter=ast.parse('range(1,max_depth+1)',mode='eval').body
            return self.generic_visit(node)
    check=ast.parse(ast.unparse(tree));Restore().visit(check);assert ast.dump(check,include_attributes=False)==old
    return tree

class FirstQRefinement:
    """Keep first Q0 callback/fallback, isolate its TT before one ordinary-Q D1.

    Original full-query budget, cancellation and best-on-abort logic stay. A
    second depth1 callback is a refinement stage, not a completed depth2. Caller
    records actual ordinary-q provenance per iteration. Fresh Player/TT only.
    """
    def __init__(self):self.counts=Counter();self.original=None;self.player_original=None
    def depths(self,maximum,ctx):
        if maximum<1:return
        yield 1
        if ctx.first_main_iteration_complete and ctx.qdepth_limit>0:
            ctx.tt.clear();self.counts['q_semantic_tt_clears']+=1
            self.counts['refinement_scheduled']+=1
            yield 1
        yield from range(2,maximum+1)
    def __enter__(self):
        from generic_chess.ai.alphabeta import player as P
        assert not hasattr(S,'_first_q_refinement_depths');self.original=S.run_root_search;self.player_original=P.run_root_search
        S._first_q_refinement_depths=self.depths
        exec(compile(transform(inspect.getsource(self.original)),'<research-first-q-refinement>','exec'),S.__dict__)
        P.run_root_search=S.run_root_search
        return self
    def __exit__(self,*args):
        from generic_chess.ai.alphabeta import player as P
        S.run_root_search=self.original;P.run_root_search=self.player_original;del S._first_q_refinement_depths
