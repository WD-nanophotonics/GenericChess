import json,sys,hashlib,time
from pathlib import Path
from fractions import Fraction
import cshogi as C
import numpy as np
R=Path.cwd();O=R/'results/dev_aux/task527';O.mkdir(exist_ok=True);sys.path.insert(0,str(R/'results/dev_aux/task390'));from analyze import features
geometry=json.loads((R/'results/dev_aux/task526/result.json').read_bytes());AX=geometry['axes'];groups={(tuple(x['weights']),x['opponent']):x for x in geometry['rows']};observed={k:{n:[] for n in ['played','played_delta','PV','PV_delta','move_delta']} for k in groups};checks=0;t0=time.perf_counter()
def native(b):
 v=[0]*16;types=[0]*16
 for pc in b.pieces:
  if pc:pt=pc%16;v[pt]+=1 if pc<16 else -1;types[pt]+=1
 for color,hand in enumerate(b.pieces_in_hand):
  for pt,n in zip([1,2,3,4,7,5,6],hand):v[pt]+=(1 if color==0 else -1)*n;types[pt]+=n
 assert sum(types)-types[8]==38;return v,types
def record(key,kind,b,rv):
 global checks
 v,types=native(b);assert (v,types)==features(b.sfen());checks+=1;observed[key][kind].append([v[a] for a in AX]);observed[key][kind+'_delta'].append([v[a]-rv[a] for a in AX]);return v
for text in (R/'results/dev_aux/task521/games.jsonl').open(encoding='utf-8'):
 g=json.loads(text);key=(tuple(g['weights']),g['opponent_arm']);b=C.Board(g['root']['expected_sfen']);rv,_=native(b);prev=record(key,'played',b,rv)
 for a in g['actions']:
  m=b.move_from_usi(a['move']);assert b.is_legal(m);b.push(m);assert b.sfen().split()[:3]==a['after_sfen'].split()[:3];v=record(key,'played',b,rv);observed[key]['move_delta'].append([v[a]-prev[a] for a in AX]);prev=v
 for q in g['queries']:
  b=C.Board(q['initial_sfen'])
  for u in q['history']:b.push(b.move_from_usi(u))
  for line in q['lines']:
   if ' pv ' not in line:continue
   p=b.copy()
   for u in line.split(' pv ',1)[1].split():m=p.move_from_usi(u);assert p.is_legal(m);p.push(m);record(key,'PV',p,rv)
def forward_rank(mat):
 a=[list(map(Fraction,row)) for row in mat];rank=0
 for j in range(len(AX)):
  pivot=next((i for i in range(rank,len(a)) if a[i][j]),None)
  if pivot is None:continue
  a[rank],a[pivot]=a[pivot],a[rank];p=a[rank]
  for i in range(rank+1,len(a)):
   if a[i][j]:factor=a[i][j]/p[j];a[i]=[x-factor*y for x,y in zip(a[i],p)]
  rank+=1
 return rank
rows=[];nulltests=0
for key,data in observed.items():
 src=groups[key];row=dict(profile_names=src['profile_names'],opponent=key[1],verified={})
 for kind,mat in data.items():
  cert=src['exact_feature_geometry'][kind];witness=[w['vector'] for w in cert['basis_witness']];assert all(v in mat for v in witness);assert forward_rank(witness)==cert['rank'];assert int(np.linalg.matrix_rank(np.asarray(mat,dtype=float)))==cert['rank']
  for null in cert['nullspace']:
   v=list(map(Fraction,null));assert all(sum(a*b for a,b in zip(v,x))==0 for x in mat);nulltests+=len(mat)
  row['verified'][kind]=dict(rank=cert['rank'],vectors=len(mat),independent_exact_witness_rank=forward_rank(witness),all_native_nullvectors_verified=True)
 rows.append(row)
out=dict(status='PASS_NATIVE_GEOMETRY',source_sha256=hashlib.sha256((R/'results/dev_aux/task526/result.json').read_bytes()).hexdigest(),native_literal_state_vector_checks=checks,all_null_vector_dot_checks=nulltests,rows=rows,new_go=0,seconds=time.perf_counter()-t0,scope='Nativepieces/nativehands independentlyagreeALLsignedvector/typecounts; exactforwardelimination confirms each witnessrank andALLobservednull orthogonality; float rank additionalcrosscheck only. Freepriceaxesexclude fixedP90: featureinvariant may includeP-onlycapturing, NOTallmaterialscoreinvariant. RepeatedPVstates notindependent samples; rank notrewardidentification.')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='rows'}))
