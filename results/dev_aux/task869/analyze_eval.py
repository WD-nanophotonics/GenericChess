import json,collections
from fractions import Fraction as F
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task873';O.mkdir(exist_ok=False);assert json.loads((R/'results/dev_aux/task872/result.json').read_bytes())['status']=='PASS_ALL40_CHECKED_GRAMMAR_ROOTS_AND232_TRANSFER_GAMES';gs=[json.loads(l) for l in (R/'results/dev_aux/task871/games.jsonl').open(encoding='utf-8')];eps=json.loads((R/'results/dev_aux/task855/endpoints.json').read_bytes())['endpoints'];eps=[e for e in eps if e['start']=='unit'];rows=[]
def metric(g):
 t=g['termination'];royal=not t['kind'].startswith('cap');real=F(1 if t['winner']==g['color'] else -1 if t['winner'] is not None else 0) if royal else F(0);return dict(real=real,fast=F(25-len(g['actions']),25) if real>0 else F(-1) if real<0 else F(0),censored=F(not royal))
for e in eps:
 for pool in ['train','development','validation']:
  for opp in ['unit_search','uniform_random']:
   rr=[g for g in gs if g['root']['variant']==e['variant'] and g['pool']==pool and g['opponent']==opp];table={(g['profile'],g['root']['seed'],g['color']):g for g in rr};seeds=sorted(set(g['root']['seed'] for g in rr));base=e['variant']+'_initial_'+e['start'];families=[];negative=[];trans=collections.Counter();candidate_total=collections.Counter();initial_total=collections.Counter()
   for seed in seeds:
    mm=dict(real=F(0),fast=F(0),censored=F(0))
    for color in [0,1]:
     a,b=table[e['name'],seed,color],table[base,seed,color];ma,mb=metric(a),metric(b);delta={k:ma[k]-mb[k] for k in mm};mm={k:mm[k]+delta[k]/2 for k in mm};trans[str(mb['real'])+'->'+str(ma['real'])]+=1;candidate_total['win' if ma['real']>0 else 'loss' if ma['real']<0 else 'censored' if ma['censored'] else 'draw']+=1;initial_total['win' if mb['real']>0 else 'loss' if mb['real']<0 else 'censored' if mb['censored'] else 'draw']+=1
     if delta['real']<0 or delta['fast']<0:negative.append(dict(seed=seed,color=color,delta={k:str(v) for k,v in delta.items()},candidate=a['termination'],initial=b['termination']))
    families.append(dict(seed=seed,delta={k:str(v) for k,v in mm.items()}))
   mean={k:sum(F(f['delta'][k]) for f in families)/len(families) for k in mm};loo={k:min((sum(F(f['delta'][k]) for f in families if f['seed']!=seed)/(len(families)-1),seed) for seed in seeds) if len(seeds)>1 else None for k in mm};row=dict(candidate=e['name'],baseline=base,variant=e['variant'],pool=pool,opponent=opp,families=len(seeds),mean_delta={k:str(v) for k,v in mean.items()},family_deletion_min={k:dict(value=str(v[0]),removed=v[1]) if v else None for k,v in loo.items()},by_family=families,negative_cells=negative,real_transitions=dict(trans),candidate_counts=dict(candidate_total),initial_counts=dict(initial_total),rook_to_knight=e['endpoint'][6]/90,bishop_to_knight=e['endpoint'][5]/90);rows.append(row);print(e['name'],pool,opp,row['mean_delta'],dict(candidate_total),dict(initial_total))
out=dict(status='ALL_CHECKED_NEW_GRAMMAR_FROZEN_UNIT_PRICE_TRANSFER',rows=rows,new_go=0,scope='Frozen2unitendpoints 2opponents29neweligiblefamilies2colors/H24/256. New grammarpermitslegallycheckedmovingside butnotnonmovingsidecheck. Failed11seeds kept/noresampling. Old855price endpointsunchanged, newdistributionpostmethodselection notrestoredunexposedholdout. Noquantityfitness/modelreselection/resultdirectedextension/wholegameuniversalpriceproof.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
