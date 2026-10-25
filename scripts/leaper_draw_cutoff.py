"""Reversible research-only true-DRAW cutoff; no production/default flag.

The finite two ordinary K8 invariant is independent of a positive hard clock;
only explicitly tested64/96/128 clocks and repeat4/draw are admitted. Full rule
normalization retains every other field. Replacing finite heuristic0 is a real
policy change at parents, not PVS parity or a full-domain solution.
"""
import ast
from collections import Counter
from dataclasses import replace
import inspect,textwrap,time
from scripts.leaper_draw_observer import rule_gate,inventory
from generic_chess.ai.alphabeta import search as S

class ProvenDrawCutoff:
    def __init__(self,rule,compiled):
        tick=time.perf_counter()
        # Alternate setup boards are used only by initial_state/record replay,
        # not future transitions; retain FULL compiled fingerprint and selected
        # complete root history. Normalize this constructor-only registry solely
        # for the conservative transition predicate, explicitly not TT identity.
        normalized=replace(rule,max_ply=96,initial_setup_options=())
        self.anchor=rule_gate(normalized) if rule.max_ply in (64,96,128) else None
        self.fingerprint=compiled.ruleset_fingerprint
        self.gate_seconds=time.perf_counter()-tick;self.counts=Counter()
    def applies(self,state,ply,ctx):
        self.counts['checks']+=1
        if (self.anchor is None or ply==0 or ctx.compiled.ruleset_fingerprint!=self.fingerprint
                or not inventory(state.position,self.anchor)):
            return False
        # Real terminal and declarations precede this point; keep live controls.
        ctx.budget.check(ctx.stats,force=True)
        self.counts['cutoffs']+=1
        return True
    def __enter__(self):
        assert not hasattr(S,'_draw_cutoff') and not hasattr(S,'_draw_observer')
        self.originals={n:getattr(S,n) for n in ('negamax','_quiescence_runtime')}
        trees={}
        for name,f in self.originals.items():
            tree=ast.parse(textwrap.dedent(inspect.getsource(f)));fn=tree.body[0]
            marker='lazy = False' if name=='negamax' else 'side = state.position.side_to_move'
            indices=[i for i,n in enumerate(fn.body)if ast.unparse(n)==marker];assert len(indices)==1
            value='SearchResult(0, None, ())' if name=='negamax' else '0'
            inserted=ast.parse(f'if _draw_cutoff.applies(state, ply, ctx):\n    return {value}').body
            pos=indices[0];before=ast.dump(tree,include_attributes=False)
            fn.body[pos:pos]=inserted
            # Exact removal restores the full original source AST.
            reverse=fn.body[:pos]+fn.body[pos+len(inserted):];changed=fn.body;fn.body=reverse
            assert ast.dump(tree,include_attributes=False)==before
            fn.body=changed;ast.fix_missing_locations(tree);trees[name]=tree
        S._draw_cutoff=self
        try:
            for name,tree in trees.items():exec(compile(tree,'<research-proven-draw>','exec'),S.__dict__)
        except BaseException:self.__exit__();raise
        return self
    def __exit__(self,*args):
        for name,f in self.originals.items():setattr(S,name,f)
        del S._draw_cutoff
