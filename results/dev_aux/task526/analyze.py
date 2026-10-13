import json,sys,time,hashlib,collections
from pathlib import Path
from fractions import Fraction
import cshogi as C
import numpy as np
R=Path.cwd();O=R/'results/dev_aux/task526';O.mkdir(exist_ok=True);assert not (O/'result.json').exists();sys.path.insert(0,str(R/'results/dev_aux/task390'));from analyze import features
sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
AX=[2,3,4,5,6,7,9,10,11,12,13,14]
class Basis:
 def __init__(self):self.rows={};self.witness=[]
 def add(self,v,label):
  row=list(map(Fraction,v))
  for p,b in sorted(self.rows.items()):
   if row[p]:row=[a-row[p]*z for a,z in zip(row,b)]
  piv=next((i for i,x in enumerate(row) if x),None)
  if piv is None:return
  row=[x/row[piv] for x in row]
  for p,b in list(self.rows.items()):
   if b[piv]:self.rows[p]=[x-b[piv]*z for x,z in zip(b,row)]
  self.rows[piv]=row;self.witness.append(dict(label=label,vector=v))
 def result(self):
  free=[i for i in range(len(AX)) if i not in self.rows];null=[]
  for f in free:
   x=[Fraction(0)]*len(AX);x[f]=1
   for p,b in self.rows.items():x[p]=-b[f]
   assert all(sum(a*b for a,b in zip(x,w['vector']))==0 for w in self.witness);null.append(list(map(str,x)))
  return dict(rank=len(self.rows),pivot_axes=[AX[p] for p in sorted(self.rows)],nullspace_axes=AX,nullspace=null,rref={str(AX[p]):list(map(str,b)) for p,b in sorted(self.rows.items())},basis_witness=self.witness)
def newstats():return dict(bases={k:Basis() for k in ['played','played_delta','PV','PV_delta','move_delta']},counts=collections.Counter(),presence={k:[0]*16 for k in ['played','PV']},observed_types=collections.Counter(),q=0,games=0,material_dot_checks=0)
def addstate(st,key,s,rootv,label):
 v,t=features(s);vec=[v[a] for a in AX];st['bases'][key].add(vec,label);st['bases'][key+'_delta'].add([v[a]-rootv[a] for a in AX],label);st['counts'][key+'_states']+=1;st['presence'][key]=[x+int(y>0) for x,y in zip(st['presence'][key],t)];return v
rows={};t0=time.perf_counter();sources=[];dev=json.loads((R/'results/dev_aux/task521/result.json').read_bytes());profile_names={tuple(p['weights']):p['names'] for p in dev['profiles']}
f=R/'results/dev_aux/task521/games.jsonl';sources.append(dict(path=f.relative_to(R).as_posix(),sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
for line,text in enumerate(f.open(encoding='utf-8'),1):
 g=json.loads(text);key=(tuple(g['weights']),g['opponent_arm']);st=rows.setdefault(key,newstats());st['games']+=1;root=g['root']['expected_sfen'];rv,_=features(root);label=dict(source_line=line,root_seed=g['root']['seed'],color=g['color']);previous=addstate(st,'played',root,rv,dict(**label,ply=0))
 for i,a in enumerate(g['actions']):
  v=addstate(st,'played',a['after_sfen'],rv,dict(**label,ply=i+1));delta=[v[x]-previous[x] for x in AX];st['bases']['move_delta'].add(delta,dict(**label,ply=i+1,move=a['move']));st['counts']['actions']+=1;st['counts']['price_feature_invariant_actions']+=not any(delta);st['counts']['drop_actions']+=bool(a['drop']);st['counts']['promotion_actions']+=bool(a['promotion']);st['counts']['capture_actions']+=bool(a['captured']);st['counts']['quiet_no_capture_no_promotion']+=not a['captured'] and not a['promotion'];score0,_=V.literal(a['before_sfen'],g['weights']);score1,_=V.literal(a['after_sfen'],g['weights']);assert sum((v[x]-previous[x])*g['weights'][x] for x in range(16))==score1-score0;st['material_dot_checks']+=1;previous=v
 for qi,q in enumerate(g['queries']):
  st['q']+=1;b=C.Board(q['initial_sfen'])
  for u in q['history']:
   m=b.move_from_usi(u);assert b.is_legal(m);b.push(m)
  for li,text in enumerate(q['lines']):
   if ' pv ' not in text:continue
   p=b.copy()
   for pi,u in enumerate(text.split(' pv ',1)[1].split()):
    m=p.move_from_usi(u);assert p.is_legal(m);p.push(m);addstate(st,'PV',p.sfen(),rv,dict(**label,query=qi,info_line=li,PV_ply=pi+1))
result=[]
for (w,opp),st in rows.items():
 result.append(dict(weights=list(w),profile_names=profile_names[w],opponent=opp,games=st['games'],queries=st['q'],counts=dict(st['counts']),presence={k:{str(a):v[a] for a in AX} for k,v in st['presence'].items()},exact_feature_geometry={k:v.result() for k,v in st['bases'].items()},material_dot_checks=st['material_dot_checks']))
out=dict(status='PASS_FEATURE_GEOMETRY',axes=AX,sources=sources,rows=result,new_go=0,seconds=time.perf_counter()-t0,scope='ALL80actualdevelopment games/ALL5unique prices (allinitial+endpoints)/bothopponents, actualplayed andALLreturnedPV states with exactrationalrank/nullspace/basis witness. RepeatedPVprefixes not independent samples. Rank ofsigned board+hand pricefeatures only, notsearchfrontier, gradients, reward identifiability, genericdomain orhumanprices. Physicalquiet/drop may befeatureinvariant evenwhen resulting tactics differ; no positionalpatch orlabel fitting.')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(dict(status=out['status'],rows=len(result),games=sum(r['games'] for r in result),queries=sum(r['queries'] for r in result),seconds=out['seconds'],ranks=[dict(names=r['profile_names'],opponent=r['opponent'],rank={k:v['rank'] for k,v in r['exact_feature_geometry'].items()}) for r in result])))
