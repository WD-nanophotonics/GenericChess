"""Finite next-attempt accounting, stdlib only, no timing/engine."""
import collections,hashlib,heapq,inspect,itertools,json,sys
from pathlib import Path
B=Path(__file__).parent
class Counted:
 def __init__(self,values,counts):self.it=iter(values);self.counts=counts
 def __iter__(self):return self
 def __next__(self):
  self.counts['attempts']+=1
  value=next(self.it);self.counts['reads']+=1;return value
layouts=[[],[[],[],[]],[[],[0,1],[]],[[0],[1],[]],[[0,2],[1,3],[]]]
records=[]
for groups in layouts:
 flat=sorted(x for g in groups for x in g);G=len(groups);k=sum(bool(g) for g in groups);n=len(flat)
 assert all(list(g)==sorted(g) for g in groups) and len(set(flat))==n
 later={rank:i+1<len(g) for g in groups for i,rank in enumerate(g)}
 for mode in ('unstarted','prefix_one','prefix_n','full_exhaustion'):
  counts=collections.Counter();merged=heapq.merge(*(Counted(g,counts) for g in groups))
  if mode=='unstarted':values=[];A=R=0
  elif mode=='full_exhaustion':values=list(merged);A=G+n;R=n
  else:
   requested=1 if mode=='prefix_one' else n
   values=list(itertools.islice(merged,requested));p=len(values)
   if requested==0:A=R=0
   elif requested>n:A=G+n;R=n
   else:
    A=G+p-1;R=k+sum(later[rank] for rank in flat[:p-1])
  assert values==flat[:len(values)]
  assert counts['attempts']==A and counts['reads']==R
  merged.close()
  records.append(dict(groups=groups,mode=mode,G=G,k=k,n=n,outputs=values,
   next_attempts=A,successful_reads=R,exhausted_attempts=A-R))
empty_full=next(r for r in records if r['groups']==[[],[],[]] and r['mode']=='full_exhaustion')
empty_prefix0=next(r for r in records if r['groups']==[[],[],[]] and r['mode']=='prefix_n')
assert empty_full['next_attempts']==3 and empty_prefix0['next_attempts']==0
pair=[r for r in records if r['groups']==[[0],[1],[]] and r['mode'] in ('prefix_n','full_exhaustion')]
assert [r['next_attempts'] for r in pair]==[4,5] and [r['successful_reads'] for r in pair]==[2,2]
out=dict(complete=True,python_version=sys.version.split()[0],
 heapq_merge_logical_source_sha256=hashlib.sha256(inspect.getsource(heapq.merge).encode()).hexdigest(),
 heapq_module_raw_sha256=hashlib.sha256(Path(heapq.__file__).read_bytes()).hexdigest(),
 original_derivation_sha256=hashlib.sha256((B.parent/'task038/DERIVATION.md').read_bytes()).hexdigest(),
 records=records,scope='20 fixed numeric cells, zero engine imports/calls; original Task038 success-read records retained',
 decision='Correct p0 prose to unstarted/islice0; started empty input and final exhaustion add next attempts. Do not treat reads as total cost or all-values prefix as EOF completion; caller DEFER unchanged.')
(B/'termination_work.json').write_bytes((json.dumps(out,indent=2)+'\n').encode())
print('termination accounting20cells pass; zero reads can have3attempts; same2outputs have4/5attempts')
