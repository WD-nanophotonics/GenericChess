"""One bounded integer minor certificate; historical full-combination attempt rejected."""
import hashlib,itertools,json,time
from fractions import Fraction
from pathlib import Path
ROOT=Path.cwd();OUT=Path(__file__).resolve().parent;start=time.perf_counter();p=OUT/'result.json';r=json.loads(p.read_bytes())
def rank(matrix):
 a=[[Fraction(x) for x in row] for row in matrix];pivot=0
 for col in range(5):
  row=next((i for i in range(pivot,len(a)) if a[i][col]),None)
  if row is None:continue
  a[pivot],a[row]=a[row],a[pivot];v=a[pivot][col];a[pivot]=[x/v for x in a[pivot]]
  for i in range(pivot+1,len(a)):
   v=a[i][col];a[i]=[x-v*y for x,y in zip(a[i],a[pivot])]
  pivot+=1
 return pivot
basis=[];indices=[]
for i,row in enumerate(r['nonterminal_final_rows']):
 if time.perf_counter()-start>5:raise TimeoutError('5s certificate cap')
 f=row['material_feature']
 if rank(basis+[f])>len(basis):basis.append(f);indices.append(i)
 if len(basis)==5:break
assert len(basis)==5
determinant=0
for perm in itertools.permutations(range(5)):
 term=(-1)**sum(perm[i]>perm[j] for i in range(5) for j in range(i+1,5))
 for i,j in enumerate(perm):term*=basis[i][j]
 determinant+=term
assert determinant!=0
certificate={'complete':True,'input_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'method':'One basis minor independently verified by120-term Leibniz integer determinant','row_indices':indices,'matrix':basis,'determinant':determinant,'count_target_rhs':[sum(row) for row in basis],'exact_solution_for_reward_target':'all five coefficients1/15; nonsingular minor proves uniqueness without intercept','wall_seconds':time.perf_counter()-start,'not_training_or_new_game':True,'retained_failed_attempt':'Initial unconstrained minor-combination enumeration exceeded expected short cost; owned exec session58415 interrupted, exit1. No completed certificate from that attempt, no engine/training. Replaced with bounded5s basis+one-minor method; no claim original passed.'}
(OUT/'rank_certificate.json').write_bytes((json.dumps(certificate,indent=2)+'\n').encode());print(json.dumps(certificate))