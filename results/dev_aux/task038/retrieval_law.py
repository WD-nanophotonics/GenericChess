"""Finite ranked-stream retrieval law, no engine imports or timing."""
import collections,hashlib,heapq,itertools,json
from pathlib import Path
B=Path(__file__).parent
raw=(B.parent/'task037/multirow_contract.json').read_bytes()
v=json.loads(raw)
class Counted:
 def __init__(self,values,counts): self.it=iter(values);self.counts=counts
 def __iter__(self): return self
 def __next__(self):
  self.counts['attempts']+=1
  x=next(self.it);self.counts['retrieved']+=1;return x
def assay(groups,p):
 flat=sorted(x for g in groups for x in g)
 assert all(list(g)==sorted(g) for g in groups) and len(set(flat))==len(flat)
 assert 0<=p<=len(flat)
 counts=collections.Counter()
 streams=[Counted(g,counts) for g in groups]
 actual=list(itertools.islice(heapq.merge(*streams),p))
 assert actual==flat[:p]
 later={x: i+1<len(g) for g in groups for i,x in enumerate(g)}
 k=sum(bool(g) for g in groups)
 predicted=(k+sum(later[x] for x in flat[:p-1])) if p else 0
 assert counts['retrieved']==predicted
 return dict(groups=groups,n=len(flat),k=k,p=p,actual_prefix=actual,
  retrieved=counts['retrieved'],predicted=predicted,
  avoided_retrievals=len(flat)-predicted,next_attempts=counts['attempts'])
# Same n,k,p can produce different retrieval counts: rank layout matters.
layouts=[[[0,1],[2,3],[4,5]],[[0,3],[1,4],[2,5]]]
contrasts=[assay(g,3) for g in layouts]
assert [x['retrieved'] for x in contrasts]==[4,5]
# Empty inputs and complete consumption retain exact byte-independent laws.
controls=[assay(g,p) for g in layouts+[[],[[],[0,1,2],[]]] for p in (0,sum(map(len,g)))]
# Reuse only the eight isolated source/target records; no fixture reconstruction.
selected=[r for r in v['rows'] if r['target']==(9 if r['owner']==0 else 6)]
assert len(selected)==8 and all(r['selected_rows']==6 and r['selected_groups']==1 for r in selected)
actual_shapes=[]
for r in selected:
 p=r['consumed_guard_rows']
 assert p==(1 if r['permit']==0 else 4)
 a=assay([list(range(6))],p)
 actual_shapes.append(dict(carrier=r['carrier'],owner=r['owner'],permit=r['permit'],**a))
out=dict(complete=True,input_sha256=hashlib.sha256(raw).hexdigest(),new_engine_imports_or_calls=0,
 law='For p>=1 yielded rows: R=k+sum(next row exists in its same group for each of first p-1 global ranks). For p=0, R=0. R counts successful retrievals, excluding exhausted next attempts.',
 contrasts=contrasts,controls=controls,isolated_public_shapes=actual_shapes,
 decision='The public single-group shape can avoid5 or2 selected-tuple reads at prefix1 or4; it still performs the same guards and eager source polls. Counts n/k/p alone do not identify retrieval cost in general. No actual caller saving or deployment established; retain DEFER until a justified workload changes a concrete decision.',
 limits='Numeric structural iterators model ordered tuples, not production memory allocation or CPU time. All IR rows already exist. Task037 isolated public targets have one active A group and guard-bearing path acceptance, so their guard count supplies this prefix. Guard counts are not generally row-inspection counts when paths or eligibility skip guards.')
(B/'retrieval_law.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
print('retrieval law: same n/k/p gives4vs5;8public shapes retrieve1/4 of6; no engine calls')
