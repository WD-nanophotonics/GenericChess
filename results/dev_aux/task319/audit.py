"""Enumerate all locally minimax-optimal PV paths and hierarchical tie moments."""
import json,time,hashlib,collections
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();O=R/'results/dev_aux/task319';O.mkdir(exist_ok=False);start=time.monotonic();T=json.loads((R/'results/dev_aux/task258/tree.json').read_bytes());D=json.loads((R/'results/dev_aux/task301/declaration.json').read_bytes());TAG='$dev_aux_constant_telemetry_v1'
def hook(z):
 if set(z)=={TAG}:v=z[TAG];return [v['value']]*v['count']
 return z
X=json.loads((R/'results/dev_aux/task301/result.json').read_bytes(),object_hook=hook);DD=json.loads((R/'results/dev_aux/task302/audit.json').read_bytes());details=[];allpaths=[]
def leafval(l,w):return l['terminal'] if 'terminal' in l else sum(w[k]*x for k,x in zip('PNBRQ',l['vector']))
def text(a):
 fr=a['from_square'];to=a['to_square'];return chess.square_name(chess.square(fr['file'],fr['rank']))+chess.square_name(chess.square(to['file'],to['rank']))+(a.get('promotion_target_id') or '').lower()
for case in X['cases']:
 tr=next(t for t in T['roots'] if t['root']==case['root']);w=case['weights'];acts=[]
 for a in tr['actions']:
  branches=[]
  for br in a['branches']:
   children=[dict(move=None,leaf=br['terminal'])] if 'terminal' in br else br['children'];best=max(leafval(c['leaf'],w) for c in children);cs=[c for c in children if leafval(c['leaf'],w)==best];branches.append((br,best,cs))
  av=min(v for _,v,_ in branches);acts.append((a,av,[(br,cs) for br,v,cs in branches if v==av]))
 best=max(v for _,v,_ in acts);optimal=[(a,bs) for a,v,bs in acts if v==best];pv=[text(a) for a in case['variants']['base']['result']['principal_variation']];paths=[];prob=[];vec=[]
 for a,bs in optimal:
  for br,cs in bs:
   for c in cs:
    path=[a['move'],br['reply']]+([] if c['move'] is None else [c['move']]);v=[0]*5 if 'terminal' in c['leaf'] else c['leaf']['vector'];p=F(1,len(optimal)*len(bs)*len(cs));paths.append(path);prob.append(p);vec.append(v);allpaths.append(dict(root=case['root'],profile=case['profile'],path=path,vector=v,probability=str(p)))
 assert sum(prob)==1 and pv in paths;mean=[sum(p*v[i] for p,v in zip(prob,vec)) for i in range(5)];variance=[sum(p*(F(v[i])-mean[i])**2 for p,v in zip(prob,vec)) for i in range(5)];old=next(z for z in DD['details'] if (z['root'],z['profile'])==(case['root'],case['profile']));assert best==old['base_score'];axes=[]
 for i,k in enumerate('PNBRQ'):
  x=old['axes'][i];axes.append(dict(piece=k,local_uniform_mean=str(mean[i]),variance=str(variance[i]),left=x['exact_negative_directional'],right=x['exact_positive_directional'],uniform_mean_matches_both=mean[i]==x['exact_negative_directional']==x['exact_positive_directional'],canonical_PV_slope=old['PV_slope'][i],support=sorted(set(v[i] for v in vec))))
 details.append(dict(root=case['root'],profile=case['profile'],root_score=best,optimal_root_actions=len(optimal),optimal_paths=len(paths),unique_vectors=len(set(map(tuple,vec))),canonical_path=pv,canonical_member=True,canonical_path_probability=str(prob[paths.index(pv)]),axes=axes))
(O/'paths.json').write_text(json.dumps(allpaths,separators=(',',':')),encoding='utf-8');out=dict(complete=True,new_engine_queries=0,points=len(details),all_optimal_paths=len(allpaths),all_canonical_paths_locally_optimal=True,nonzero_variance_axes=sum(F(a['variance'])>0 for d in details for a in d['axes']),uniform_mean_mismatch_axes=sum(not a['uniform_mean_matches_both'] for d in details for a in d['axes']),details=details,seconds=time.monotonic()-start,scope='Localuniformtie mean at everyoptimalnode is declared randomization only, not empirical engine probability or optimal response afterweightsperturb. Fullpathoptimality confirmed despiteboundTTordering. LocaluniformPVaveragingdoesnotgenerallymake validrootgradient; axisderivatives mayusemax/min overtimeactivebranches. No TDLeafuniversalrefutation/learning/adoption.',source_hashes={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [R/'results/dev_aux/task258/tree.json',R/'results/dev_aux/task301/result.json',R/'results/dev_aux/task302/audit.json']});(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k not in ('details','source_hashes')},indent=2))