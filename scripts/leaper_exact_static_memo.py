"""Research-only per-call static memo: existing runtime hash + full Position guard.

Caches raw default evaluator outputs, never Q returns/bounds/TT/history truth.
Admits only the already certified plain-Leaper IR; no product default change.
"""
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.core.search_runtime import _plain_leaper_hash_patterns
from generic_chess.core.identity import RuntimeHash
from generic_chess.core.position import Position

class ExactStaticMemo:
 def __init__(self,compiled,base,*,capacity=8192,shadow=False):
  if type(base) is not Evaluator or base._compiled is not compiled or _plain_leaper_hash_patterns(compiled) is None:raise ValueError('default evaluator and certified plain-Leaper IR required')
  if type(capacity) is not int or capacity<1:raise ValueError('positive bounded capacity required')
  self.base=base;self.compiled=compiled;self.capacity=capacity;self.shadow=shadow;self.buckets={};self.entries=0
  self.metrics=dict(requests=0,hits=0,misses=0,bypasses=0,raw_evaluator_calls=0,flushes=0,hash_collision_misses=0,position_comparisons=0,peak_entries=0)
 def __getattr__(self,name):return getattr(self.base,name)
 def raw(self,state):self.metrics['raw_evaluator_calls']+=1;return self.base.evaluate(state)
 def evaluate(self,state):
  m=self.metrics;m['requests']+=1;rt=getattr(state,'_runtime',None);pos=state.position
  if rt is None or type(pos) is not Position or type(rt.runtime_hash) is not RuntimeHash:m['bypasses']+=1;return self.raw(state)
  if pos.ruleset_fingerprint!=self.compiled.ruleset_fingerprint:raise ValueError('foreign RuleSet position')
  # Store immutable Position, never the mutable RuntimeSearchState view.
  key=rt.runtime_hash;bucket=self.buckets.get(key,())
  for old,value in bucket:
   m['position_comparisons']+=1
   if old==pos:
    m['hits']+=1
    if self.shadow:
     observed=self.raw(state)
     if observed!=value:raise AssertionError('position-only evaluator purity violated')
     return observed
    return value
   m['hash_collision_misses']+=1
  m['misses']+=1;value=self.raw(state)
  if self.entries>=self.capacity:self.buckets.clear();self.entries=0;m['flushes']+=1;bucket=()
  self.buckets.setdefault(key,[]).append((pos,value));self.entries+=1;m['peak_entries']=max(m['peak_entries'],self.entries)
  return value
