import json,collections,re,math
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task864';O.mkdir(exist_ok=False);assert json.loads((R/'results/dev_aux/task863/result.json').read_bytes())['status']=='PASS_ALL608_LEAF_NATIVE_FACTORIAL_GAMES';gs=[json.loads(l) for l in (R/'results/dev_aux/task862/games.jsonl').open(encoding='utf-8')];rows=[];inventory=[]
def metric(g):
 t=g['termination'];royal=not t['kind'].startswith('cap');v=F(1 if t['winner']==g['color'] else -1 if t['winner'] is not None else 0) if royal else F(0);return dict(real=v,fast=F(25-len(g['actions']),25) if v>0 else F(-1) if v<0 else F(0),censored=F(not royal))
for endpoint in list(dict.fromkeys(g['endpoint'] for g in gs)):
 for pool in ['train','development','validation']:
  for opp in ['unit_search','uniform_random']:
   rr=[g for g in gs if g['endpoint']==endpoint and g['pool']==pool and g['opponent']==opp];table={(g['mode'],g['root']['seed'],g['color']):g for g in rr};seeds=sorted(set(g['root']['seed'] for g in rr));family=[]
   for seed in seeds:
    mean={mode:{k:F(0) for k in ['real','fast','censored']} for mode in ['II','IL','LI','LL']}
    for c in [0,1]:
     mm={mode:metric(table[mode,seed,c]) for mode in mean};inventory.append(dict(endpoint=endpoint,pool=pool,opponent=opp,seed=seed,color=c,metrics={m:{k:str(v) for k,v in a.items()} for m,a in mm.items()}))
     for m in mean:
      for k in mean[m]:mean[m][k]+=mm[m][k]/2
    family.append(dict(seed=seed,means={m:{k:str(v) for k,v in a.items()} for m,a in mean.items()}))
   means={m:{k:sum(F(f['means'][m][k]) for f in family)/len(family) for k in ['real','fast','censored']} for m in ['II','IL','LI','LL']};effects={label:{k:str(means[a][k]-means[b][k]) for k in means[a]} for label,a,b in [('leaf_only','IL','II'),('other_native_only','LI','II'),('both','LL','II')]};effects['interaction']={k:str(means['LL'][k]-means['LI'][k]-means['IL'][k]+means['II'][k]) for k in means['II']};rows.append(dict(endpoint=endpoint,pool=pool,opponent=opp,families=len(seeds),means={m:{k:str(v) for k,v in a.items()} for m,a in means.items()},effects=effects,by_family=family));print(endpoint,pool,opp,{k:v['real'] for k,v in effects.items()})
# Verify deployment-equivalent controls against qualifiedoriginals, allactions/queryscores, notwall.
old=[]
for n in [853,855,857]:old.extend(json.loads(l) for l in (R/f'results/dev_aux/task{n}/games.jsonl').open(encoding='utf-8'))
lookup={}
for g in old:lookup.setdefault((tuple(g['weights']),g['opponent'],g['root']['seed'],g['color']),g)
cp=lambda q:[re.search(r' score (?:cp|mate) (-?\d+)',l).group(0) for l in q['lines'] if ' score ' in l]
control=dict(cases=0,actions_equal=0,terminal_equal=0,query_final_scores_equal=0,query_bestmoves_equal=0,query_count_equal=0,missing_original=0)
for g in gs:
 if g['mode'] not in ['II','LL']:continue
 key=(tuple(g['weights']),g['opponent'],g['root']['seed'],g['color']);a=lookup.get(key)
 if a is None:control['missing_original']+=1;continue
 control['cases']+=1;control['actions_equal']+=a['actions']==g['actions'];control['terminal_equal']+=a['termination']==g['termination'];control['query_count_equal']+=len(a['queries'])==len(g['queries']);control['query_final_scores_equal']+=[cp(q)[-1] for q in a['queries']]==[cp(q)[-1] for q in g['queries']];control['query_bestmoves_equal']+=[q['bestmove'] for q in a['queries']]==[q['bestmove'] for q in g['queries']]
out=dict(status='ALL_2X2_LEAF_VS_OTHER_NATIVE_PRICE_EFFECTS',rows=rows,cell_inventory=inventory,deployment_equivalent_original_controls=control,new_go=0,scope='Leafoverride actualreadbacks fully863qualified. OthernativeincludesSEE/cachedmaterial/nonPawnMaterial/remainingheuristics, notpureorderingorSEE-only. Allalreadyexposedroots/negative/censored preserved, no newholdout orfit. Effects arefinite diagnostics notuniversalcausalWDL; ordinaryconcurrentmachine/nodesworkvaries.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('ORIGINAL_CONTROLS',control)
