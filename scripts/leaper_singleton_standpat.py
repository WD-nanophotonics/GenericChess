"""Research ablation: singleton stand-pat removal INSIDE existing ordinary q depth."""
import ast,inspect
from scripts.leaper_forced_quiet_q import ForcedQuietQ,transform
from generic_chess.ai.alphabeta import search as S

class SingletonStandPat(ForcedQuietQ):
    """No extension beyond ordinary depth; no initial Q0 or explicit Q0 change."""
    def __enter__(self):
        assert not hasattr(S,'_forced_quiet_continuation');self.original=S._quiescence_runtime
        tree=transform(inspect.getsource(self.original));changed=0
        # Match only the added noncheck guard, never the original >=hard check evasion.
        # Original qhard comparisons also exist, so restrict to strict-less-than.
        class GuardLimit(ast.NodeTransformer):
            def visit_Compare(self,node):
                nonlocal changed
                if isinstance(node.left,ast.Name)and node.left.id=='qdepth'and len(node.ops)==1 and isinstance(node.ops[0],ast.Lt)and isinstance(node.comparators[0],ast.Attribute)and node.comparators[0].attr=='qhard_depth_limit':
                    changed+=1;node.comparators=[ast.Call(ast.Name('_ordinary_qdepth_limit',ast.Load()),[ast.Name('ctx',ast.Load())],[])]
                return self.generic_visit(node)
        GuardLimit().visit(tree);assert changed==1;ast.fix_missing_locations(tree)
        S._forced_quiet_continuation=self.continuation
        exec(compile(tree,'<research-singleton-standpat-only>','exec'),S.__dict__)
        return self
