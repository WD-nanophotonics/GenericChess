"""Scalar research observer. No search cutoff or product activation.

Counts actual main/q calls and their own return site, never infers TT returns
from descendant counters. No runtime view/owner is retained by a token.
"""
import ast
from collections import Counter
import inspect
import textwrap
import time
from scripts import leaper_design as L
from generic_chess.ai.alphabeta import search as S

KING_OFFSETS = {(x,y) for x in (-1,0,1) for y in (-1,0,1) if (x,y)!=(0,0)}

def rule_gate(r):
    if (r.board_size not in (4,5,6) or r.max_ply != 96 or r.repetition_limit != 4
            or r.stalemate_result != 'draw' or r.capture_disposition != 'remove_from_game'):
        return None
    anchors=[p for p in r.piece_types if p.is_anchor]
    if len(anchors)!=1 or any(not isinstance(a,L.LeapAtom) for p in r.piece_types for a in p.movement_atoms):
        return None
    k=anchors[0]
    if {a.offset for a in k.movement_atoms} != KING_OFFSETS:
        return None
    if any(any(mask) for both in r.drop_allowed.values() for mask in both):
        return None
    simple=L.RuleSet(board_size=r.board_size,piece_types=tuple(
        L.PieceType(p.type_id,p.name,p.movement_atoms,is_anchor=p.is_anchor) for p in r.piece_types),
        initial_position=r.initial_position,drop_allowed=r.drop_allowed,max_ply=96,
        repetition_limit=4,stalemate_result='draw',capture_disposition='remove_from_game')
    if L.ruleset_to_dict(simple,include_metadata=True) != L.ruleset_to_dict(r,include_metadata=True):
        return None
    return k.type_id

def inventory(pos, anchor):
    if anchor is None or pos.aux_state or any(h.counts for h in pos.hands):
        return False
    owners=0; count=0
    for p in pos.board:
        if p is None:
            continue
        if p.current_type_id != anchor or p.base_type_id != anchor or p.promoted or p.owner not in (0,1):
            return False
        bit=1 << p.owner
        if owners & bit:
            return False
        owners |= bit; count += 1
    return count == 2 and owners == 3

LABELS={
    'negamax':('terminal','declaration','leaf','mate_bound','tt_full_pv','tt_exact','tt_bound','no_actions','searched'),
    '_quiescence_runtime':('terminal','declaration','check_beta','check_alpha','standpat','qdepth','noisy_beta','quiet_alpha'),
}

class Returns(ast.NodeTransformer):
    def __init__(self, labels):
        self.labels=iter(labels); self.seen=[]
    def visit_FunctionDef(self,node):
        return node  # child_search has its own locals, not this call's token.
    visit_AsyncFunctionDef=visit_FunctionDef
    def visit_Return(self,node):
        label=next(self.labels); self.seen.append(label)
        return ast.copy_location(ast.Return(ast.Call(
            func=ast.Attribute(ast.Name('_draw_observer',ast.Load()),'returned',ast.Load()),
            args=[ast.Name('_draw_token',ast.Load()),ast.Constant(label),node.value],keywords=[])),node)

def transform(function):
    src=textwrap.dedent(inspect.getsource(function)); tree=ast.parse(src); f=tree.body[0]
    # Main and runtime-q observe only after the existing initial budget check.
    marker='state = runtime.state' if f.name=='_quiescence_runtime' else 'ctx.budget.check(ctx.stats)'
    indices=[i for i,n in enumerate(f.body) if ast.unparse(n)==marker]
    assert len(indices)==1
    split=indices[0]+1
    observed=f.body[split:]
    # Observe the actual probe value before any later store changes that entry.
    class Probe(ast.NodeTransformer):
        def visit_FunctionDef(self,node): return node
        def visit_Assign(self,node):
            if ast.unparse(node)=='entry = ctx.tt.probe(key)':
                node.value=ast.Call(ast.Attribute(ast.Name('_draw_observer',ast.Load()),'probed',ast.Load()),[ast.Name('_draw_token',ast.Load()),node.value],[])
            return node
    observed=[Probe().visit(n) for n in observed]
    insert_marker='lazy = False' if f.name=='negamax' else 'side = state.position.side_to_move'
    places=[i for i,n in enumerate(observed) if ast.unparse(n)==insert_marker]
    assert len(places)==1
    observed[places[0]:places[0]]=ast.parse('_draw_observer.survived(_draw_token, ctx)').body
    t=Returns(LABELS[f.name]); observed=[t.visit(n) for n in observed]
    assert tuple(t.seen)==LABELS[f.name], (f.name,t.seen)
    try:
        next(t.labels)
    except StopIteration:
        pass
    else:
        raise AssertionError('unused return label')
    stage='main' if f.name=='negamax' else 'q'
    depth='depth' if stage=='main' else '-qdepth'
    enter=ast.parse(f"_draw_token = _draw_observer.enter(state, {depth}, ply, ctx, '{stage}')").body
    final=ast.parse('_draw_observer.exited(_draw_token, ctx)').body
    f.body=f.body[:split]+enter+[ast.Try(body=observed,handlers=[],orelse=[],finalbody=final)]
    ast.fix_missing_locations(tree)
    return tree

class DrawObserver:
    def __init__(self, rule, enabled=True):
        self.enabled=enabled
        tick=time.perf_counter(); self.anchor=rule_gate(rule)
        self.gate_seconds=time.perf_counter()-tick
        self.counts=Counter(); self.depths=Counter(); self.top_depths=Counter()
        self.classifier_seconds=0.; self.top_seconds=0.; self.top_events=0
        self.active_regions=0; self.open_tokens=0; self.top_aborted=0
        self.next_id=0; self.stack=[]; self.calls=[]; self.log_cap=256; self.dropped_calls=0
    def enter(self,state,depth,ply,ctx,stage):
        if not self.enabled:
            return None
        tick=time.perf_counter(); match=inventory(state.position,self.anchor)
        self.classifier_seconds += time.perf_counter()-tick
        terminal=state.terminal_status.is_terminal
        eligible=bool(match and ply>0 and not terminal)
        self.counts[f'{stage}_calls']+=1
        self.counts[f'{stage}_root_calls']+=int(ply==0)
        self.counts[f'{stage}_matched']+=int(match)
        self.counts[f'{stage}_matched_terminal']+=int(match and terminal)
        self.counts[f'{stage}_eligible']+=int(eligible)
        self.open_tokens+=1
        if eligible:
            self.depths[(stage,depth)]+=1
        self.next_id+=1
        token=dict(call_id=self.next_id,parent_id=self.stack[-1]['call_id'] if self.stack else None,
            stage=stage,depth=depth if stage=='main' else None,qdepth=-depth if stage=='q' else None,
            ply=ply,clock=state.ply_count,eligible=eligible,matched=match,terminal=terminal,
            probe='not_reached_or_disabled',returned=None,survived=False,top=False)
        self.stack.append(token)
        return token
    def probed(self,token,entry):
        if token is not None:
            token['probe']='miss' if entry is None else 'hit'
            self.counts[token['stage']+'_eligible_probe_'+token['probe']]+=int(token['eligible'])
        return entry
    def survived(self,token,ctx):
        if token is None or not token['eligible']: return
        token['survived']=True
        self.counts[token['stage']+'_eligible_survived']+=1
        token['top']=self.active_regions==0
        self.active_regions+=1
        if token['top']:
            depth=token['depth'] if token['stage']=='main' else -token['qdepth']
            self.top_depths[(token['stage'],depth)]+=1
            token['start']=time.perf_counter();token['events']=ctx.stats.nodes+ctx.stats.qnodes
    def returned(self,token,label,value):
        if token is not None:
            stage=token['stage']; token['returned']=label
            self.counts[f'{stage}_return_{label}']+=1
            if token['eligible']: self.counts[f'{stage}_eligible_return_{label}']+=1
            if token['top']: self.counts[f'top_{stage}_return_{label}']+=1
        return value
    def exited(self,token,ctx):
        if token is None: return
        assert self.stack.pop() is token
        self.open_tokens-=1
        if token['survived']: self.active_regions-=1
        if token['returned'] is None: self.counts[token['stage']+'_aborted']+=1
        if token['top']:
            self.top_seconds += time.perf_counter()-token.pop('start')
            # Work strictly AFTER the chosen insertion point, excluding its entry.
            self.top_events += ctx.stats.nodes+ctx.stats.qnodes-token.pop('events')
            self.top_aborted += int(token['returned'] is None)
        if len(self.calls)<self.log_cap:self.calls.append(dict(token))
        else:self.dropped_calls+=1
    def summary(self):
        assert self.open_tokens==self.active_regions==0 and not self.stack
        return dict(calls=self.calls,dropped_call_details=self.dropped_calls,aggregate_coverage='ALL entered calls; bounded details256; no causal graph completeness claim',counts=dict(self.counts),depths={f'{k[0]}:{k[1]}':v for k,v in self.depths.items()},
            top_depths={f'{k[0]}:{k[1]}':v for k,v in self.top_depths.items()},
            rule_gate_seconds=self.gate_seconds,classifier_seconds=self.classifier_seconds,
            nonoverlapping_top_instrumented_seconds=self.top_seconds,top_budget_events=self.top_events,
            top_aborted=self.top_aborted,scope='Actual calls, not distinct states. Top regions do not overlap. Instrumented inclusive time is NOT measured cutoff saving. Runtime-q only; no portable-q claim.')
    def __enter__(self):
        assert not hasattr(S,'_draw_observer')
        self.originals={n:getattr(S,n) for n in LABELS}
        trees={n:transform(f) for n,f in self.originals.items()}
        S._draw_observer=self
        try:
            for n,tree in trees.items(): exec(compile(tree,'<research-draw-observer>','exec'),S.__dict__)
        except BaseException:
            self.__exit__(); raise
        return self
    def __exit__(self,*args):
        for n,f in self.originals.items(): setattr(S,n,f)
        del S._draw_observer
