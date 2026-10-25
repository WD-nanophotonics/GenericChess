"""Research-only singleton main continuation; branch-depth is not ply-depth."""
import ast,inspect,textwrap
from collections import Counter
from generic_chess.ai.alphabeta import search as S

def transform(source):
    tree=ast.parse(textwrap.dedent(source));original=ast.dump(tree,include_attributes=False);count=0
    class Change(ast.NodeTransformer):
        def visit_BinOp(self,node):
            nonlocal count
            if isinstance(node.op,ast.Sub)and isinstance(node.left,ast.Name)and node.left.id=='depth'and isinstance(node.right,ast.Constant)and node.right.value==1:
                count+=1
                return ast.Call(ast.Name('_forced_branch_depth',ast.Load()),[ast.Name(n,ast.Load())for n in ['depth','actions','ctx','ply']],[])
            return self.generic_visit(node)
    Change().visit(tree);assert count==2;ast.fix_missing_locations(tree)
    class Restore(ast.NodeTransformer):
        def visit_Call(self,node):
            if isinstance(node.func,ast.Name)and node.func.id=='_forced_branch_depth':return ast.BinOp(ast.Name('depth',ast.Load()),ast.Sub(),ast.Constant(1))
            return self.generic_visit(node)
    check=ast.parse(ast.unparse(tree));Restore().visit(check);assert ast.dump(check,include_attributes=False)==original
    return tree

class ForcedBranchDepth:
    """Do not spend main depth on a compulsory move after first Q0 completes.

    No move omitted. Core complete history/clock and cancellation bound every
    line. This changes finite-horizon approximation: report branching-depth,
    actual visited ply and quality, never same-depth parity or deeper strength.
    Use fresh TT per policy; no shared persistent/warm-table activation.
    """
    def __init__(self):self.counts=Counter();self.original=None
    def depth(self,depth,actions,ctx,ply):
        self.counts['child_requests']+=1;self.counts['max_parent_ply']=max(self.counts['max_parent_ply'],ply)
        if len(actions)==1 and ctx.first_main_iteration_complete is not False:
            self.counts['extensions']+=1;return depth
        return depth-1
    def __enter__(self):
        assert not hasattr(S,'_forced_branch_depth');self.original=S.negamax;S._forced_branch_depth=self.depth
        exec(compile(transform(inspect.getsource(self.original)),'<research-singleton-branch-depth>','exec'),S.__dict__)
        return self
    def __exit__(self,*args):S.negamax=self.original;del S._forced_branch_depth
