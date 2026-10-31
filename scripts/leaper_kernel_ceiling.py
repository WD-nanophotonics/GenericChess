"""Research-only nested wall ownership; no semantic/search policy changes."""
from contextlib import contextmanager
from functools import wraps
from time import perf_counter_ns

class NestedWall:
    def __init__(self, clock=perf_counter_ns):
        self.clock=clock;self.stack=[];self.rows={};self.originals=[]
    def wrap(self, label, function):
        @wraps(function)
        def observed(*args, **kwargs):
            start=self.clock();frame=[label,start,0];self.stack.append(frame)
            failed=False
            try:return function(*args,**kwargs)
            except BaseException:
                failed=True;raise
            finally:
                elapsed=self.clock()-start
                assert self.stack.pop() is frame
                row=self.rows.setdefault(label,dict(calls=0,exceptions=0,inclusive_ns=0,self_ns=0))
                row['calls']+=1;row['exceptions']+=int(failed);row['inclusive_ns']+=elapsed;row['self_ns']+=elapsed-frame[2]
                if self.stack:self.stack[-1][2]+=elapsed
        return observed
    @contextmanager
    def installed(self, targets):
        try:
            for owner,name,label in targets:
                original=getattr(owner,name)
                self.originals.append((owner,name,original))
                setattr(owner,name,self.wrap(label,original))
            yield self
        finally:
            for owner,name,original in reversed(self.originals):setattr(owner,name,original)
            self.originals.clear()
            assert not self.stack,'unfinished observation stack'

def targets():
    import generic_chess.core.search_runtime as runtime
    import generic_chess.core.semantic_executor as semantic
    import generic_chess.ai.alphabeta.native_legality as native
    import generic_chess.ai.alphabeta.search as search
    R=runtime.SearchPathRuntime;N=native.NativeSemanticLegalityProvider
    # Only eager callables. Never wrap or advance legal/order generators or contextmanager yields.
    return [(R,'_push_impl','runtime_push'),(R,'pop','runtime_pop'),
            (R,'_sync_stats','runtime_stats'),(R,'search_key','typed_search_key'),
            (runtime,'terminal_from_search_runtime','core_terminal'),
            (semantic.SemanticEngine,'_transition','semantic_transition'),
            (semantic.SemanticEngine,'_make_binding_from_action','action_binding'),
            (N,'_pack_position','native_import'),(N,'_decode_action','action_decode'),
            (N,'__call__','native_legal_frontier'),(N,'in_check','native_check'),
            (N,'has_legal_action','native_availability'),(search,'_evaluate','leaf_evaluation')]

# Nested children are assigned to their own eager consumer; outer residuals stay separate.
KERNEL_LABELS={'runtime_push','runtime_pop','core_terminal','semantic_transition',
               'native_import','action_binding','action_decode','native_legal_frontier',
               'native_check','native_availability'}
TRANSPORT_LABELS={'native_import','action_decode','action_binding'}
def partition(rows, total_seconds):
    self_ns=sum(v['self_ns'] for v in rows.values())
    return {'observed_seconds':total_seconds,'all_observed_self_seconds':self_ns/1e9,
            'outside_and_unwrapped_seconds':total_seconds-self_ns/1e9,
            'broad_observed_union_seconds':sum(v['self_ns'] for k,v in rows.items() if k in KERNEL_LABELS)/1e9,
            'transport_binding_observed_union_seconds':sum(v['self_ns'] for k,v in rows.items() if k in TRANSPORT_LABELS)/1e9,
            'limits':'Observed instrumented wall ownership only. Parent residual includes observer bookkeeping. Hypothetical zero-cost category union is not removable work or unbiased uninstrumented bound. Evaluation/TT/ordering/clocks/history contracts remain; no source inference of a built kernel speedup.'}
