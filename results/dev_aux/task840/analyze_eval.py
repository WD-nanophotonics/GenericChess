import json,collections
from fractions import Fraction as F
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task848';O.mkdir(exist_ok=False);assert json.loads((R/'results/dev_aux/task847/result.json').read_bytes())['status']=='PASS_ALL672_MC_PROBES_ACTUAL';gs=[json.loads(l) for l in (R/'results/dev_aux/task846/games.jsonl').open(encoding='utf-8')];rows=[]
def metrics(g):
 t=g['termination'];royal=not t['kind'].startswith('cap');z=F(1 if t['winner']==g['color'] else -1 if t['winner'] is not None else 0) if royal else F(0);q=F(g['raw_quantity'],19);return dict(real=z,quantity=q,literal=z if royal else q,censored=F(not royal),fast=(F(25-len(g['actions']),25) if z>0 else F(-1) if z<0 else F(0)))
profiles=list(dict.fromkeys(g['profile'] for g in gs));pairs=[(n,'original_unit' if n.endswith('_unit') else 'original_random2514') for n in profiles if not n.startswith('original_')]+[('rook_bishop_superset_projection_unit','free_logprices_unit'),('rook_bishop_superset_projection_random2514','free_logprices_random2514'),('rook_bishop_superset_projection_random2514','projection_only_random2514')]
for pool in ['development','validation']:
 for opp in ['unit','random2514']:
  subset=[g for g in gs if g['pool']==pool and g['opponent']==opp];families=sorted(set(g['root']['seed'] for g in subset));table={(g['profile'],g['root']['seed'],g['color']):g for g in subset};basecounts={p:dict(collections.Counter(g['termination']['kind'] for g in subset if g['profile']==p)) for p in profiles}
  for name,base in pairs:
   fam=[];negative=[];trans=collections.Counter()
   for seed in families:
    mm={k:F(0) for k in metrics(next(iter(table.values())))}
    for c in [0,1]:
     a,b=table[name,seed,c],table[base,seed,c];ma,mb=metrics(a),metrics(b);delta={k:ma[k]-mb[k] for k in mm};mm={k:mm[k]+delta[k]/2 for k in mm};trans[str(mb['real'])+'->'+str(ma['real'])]+=1
     if delta['real']<0 or delta['literal']<0:negative.append(dict(seed=seed,color=c,delta={k:str(v) for k,v in delta.items()},candidate=a['termination'],baseline=b['termination']))
    fam.append(dict(seed=seed,delta={k:str(v) for k,v in mm.items()}))
   mean={k:sum(F(f['delta'][k]) for f in fam)/len(fam) for k in mm};loo={k:min((sum(F(f['delta'][k]) for f in fam if f['seed']!=seed)/(len(fam)-1),seed) for seed in families) for k in mm};rows.append(dict(pool=pool,opponent=opp,candidate=name,baseline=base,mean_delta={k:str(v) for k,v in mean.items()},family_deletion_min={k:dict(value=str(v[0]),removed_family=v[1]) for k,v in loo.items()},families=fam,negative_cells=negative,real_transitions=dict(trans),actual_counts=basecounts))
  print(pool,opp,[(r['candidate'],r['mean_delta']['real'],r['mean_delta']['literal']) for r in rows if r['pool']==pool and r['opponent']==opp],flush=True)
(O/'result.json').write_text(json.dumps(dict(status='ALL_FIXED_H24_MC_PAIRED_METRICS_FAMILY_DELETION',rows=rows,new_go=0,scope='All7profiles2opponents24families bothcolors/keepcensoreddenominator. Real contribution zero forunfinished NOTdrawclaim; quantityseparate/fastterminal/literal. No selectedlayer/endpoint/H extension. Sourceprice notfitness.'),indent=2),encoding='utf-8')
