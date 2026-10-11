"""Iterator priming work, using retained selection counts without engine imports."""
import collections,hashlib,heapq,itertools,json
from pathlib import Path
B=Path(__file__).parent
data=(B.parent/'task034/selection_work.json').read_bytes();v=json.loads(data)
assert v['complete'] and len(v['rows'])==580
assert all(r['selected_rows_materialized_by_sort']==r['active_ranked_groups'] for r in v['rows'])
class Counted:
 def __init__(self,values,counts):self.it=iter(values);self.counts=counts
 def __iter__(self):return self
 def __next__(self):
  self.counts['next_attempts']+=1
  value=next(self.it);self.counts['items_retrieved']+=1;return value
rows=[]
for r in v['rows']:
 n=r['selected_rows_materialized_by_sort'];m=r['rows_consumed_until_original_return'];counts=collections.Counter()
 # Each actual selected source tuple has one row; exact rank ordering doesn't
 # change priming count. Numeric singleton streams are a structural assay.
 iterators=[Counted(((rank,rank),),counts) for rank in range(n)]
 consumed=list(itertools.islice(heapq.merge(*iterators),m))
 assert consumed==[(rank,rank) for rank in range(m)]
 assert counts['items_retrieved']==(n if m else 0)
 rows.append({'game':r['game'],'phase':r['phase'],'owner':r['owner'],'target':r['target'],
  'selected_rows':n,'retained_actual_consumed_prefix':m,'structural_merge_items_retrieved':counts['items_retrieved'],
  'items_not_retrieved_before_prefix_return':n-counts['items_retrieved'],
  'structural_next_attempts':counts['next_attempts']})
# Changed multirow premise demonstrates why singleton result is not universal.
counts=collections.Counter();multi=[Counted(((0,'a'),(2,'c'),(4,'e')),counts),Counted(((1,'b'),(3,'d'),(5,'f')),counts)]
assert next(heapq.merge(*multi))==(0,'a') and counts['items_retrieved']==2
out={'complete':True,'input_sha256':hashlib.sha256(data).hexdigest(),'new_engine_imports_or_calls':0,
 'reused_actual_query_records':580,'all_actual_selected_groups_singleton':True,'rows':rows,
 'totals':{'selected_rows':sum(r['selected_rows'] for r in rows),'consumed_rows':sum(r['retained_actual_consumed_prefix'] for r in rows),
 'merge_retrieved_before_return':sum(r['structural_merge_items_retrieved'] for r in rows),
 'not_retrieved':sum(r['items_not_retrieved_before_prefix_return'] for r in rows)},
 'changed_multirow_structural_control':{'selected_rows':6,'groups':2,'consumed_prefix':1,'items_retrieved':2},
 'decision':'DEFER caller timing for this singleton shape: heap merge still primes all selected rows before first answer. Task034 leftover212rows are not avoided reads here. It changes sorting/heap representation, with no demonstrated useful caller saving. Multirow generated predicates would be a changed premise requiring separately declared useful input, not cap growth.',
 'limits':'Counted numeric iterators are structural, not production primitive instrumentation or allocation/time savings. Existing compiled input tuples already own all rows. No universal rejection of streaming.'}
(B/'iterator_priming.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print(json.dumps(out['totals']),';singleton580, no row retrieval saved; multirow structural6rows2groups primes2')
