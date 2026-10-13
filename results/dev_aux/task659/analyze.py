import json,hashlib,time,collections,statistics,re
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task659';d=json.loads((R/'results/dev_aux/task656/declaration.json').read_bytes());start=time.perf_counter();roots=d['roots'];families=sorted({r['source_family'] for r in roots});data={};work=collections.defaultdict(lambda:dict(go=0,nodes=0,game_seconds=0,games=0))
def val(g,m):
 if m=='quantity':return F(g['raw_quantity'],19)
 if m=='mixed':return F(g['goal'])
 t=g['termination'];w=t['winner']
 if w is None:return F(0)
 if m=='terminal':return F(32 if w==g['color'] else -32)
 return F(13-len(g['actions'])) if w==g['color'] else F(-13)
for text in (R/'results/dev_aux/task657/games.jsonl').open(encoding='utf-8'):
 g=json.loads(text);key=(g['replica'],g['profile'],g['root']['index'],g['color']);assert key not in data;data[key]={m:val(g,m) for m in ['quantity','fast','terminal','mixed']};w=work[(g['replica'],g['profile'])];w['games']+=1;w['go']+=len(g['queries']);w['game_seconds']+=g['seconds']
 for q in g['queries']:a=[x for x in q['lines'] if re.search(r'\bnodes \d+',x)][-1];w['nodes']+=int(re.search(r'\bnodes (\d+)',a)[1])
assert len(data)==d['expected_physical_games'];rows=[];curves=[]
for pair in d['pairs']:
 for metric in ['quantity','fast','terminal','mixed']:
  draw=[]
  for replica in range(8):
   dif=[data[(replica,pair['endpoint_profile'],r['index'],c)][metric]-data[(replica,pair['initial_profile'],r['index'],c)][metric] for r in roots for c in [0,1]];cells=[(r,c) for r in roots for c in [0,1]];rr=dict(route=pair['route'],start=pair['start'],metric=metric,replica=replica,gain=str(sum(dif)/88),by_family=[dict(family=f,gain=str(sum(dif[i] for i,(r,c) in enumerate(cells) if r['source_family']==f)/sum(r['source_family']==f for r,c in cells))) for f in families],leave_one=[dict(omit=f,gain=str(sum(dif[i] for i,(r,c) in enumerate(cells) if r['source_family']!=f)/sum(r['source_family']!=f for r,c in cells))) for f in families]);rows.append(rr);draw.append((rr,dif))
  for n in [1,2,4,8]:
   df=[sum(x[1][i] for x in draw[:n])/n for i in range(88)];lo=[sum(df[i] for i,(r,c) in enumerate(cells) if r['source_family']!=f)/sum(r['source_family']!=f for r,c in cells) for f in families];curves.append(dict(route=pair['route'],start=pair['start'],metric=metric,predeclared_rng_prefix=n,gain=str(sum(df)/88),min_leave_one_gain=str(min(lo)),positive_individual_draws=sum(F(x[0]['gain'])>0 for x in draw[:n]),negative_individual_draws=sum(F(x[0]['gain'])<0 for x in draw[:n]),draw_means=[x[0]['gain'] for x in draw[:n]],by_generator=[dict(generator=k,gain=str(sum(df[i] for i,(r,c) in enumerate(cells) if r['generator']==k)/sum(r['generator']==k for r,c in cells))) for k in [0,1]],by_offset=[dict(offset=k,gain=str(sum(df[i] for i,(r,c) in enumerate(cells) if r['offset']==k)/sum(r['offset']==k for r,c in cells))) for k in [2,4,8,12]],empirical_draw_mean_sd=statistics.stdev(float(F(x[0]['gain'])) for x in draw[:n]) if n>1 else None))
res=[dict(replica=ri,profile=pi,**v) for (ri,pi),v in sorted(work.items())];out=dict(status='ALL_FIXED_ENDPOINT_SAMPLING_COST_SCORES_FROZEN',curves=curves,individual_draw_family_rows=rows,resources=res,actual_games=len(data),new_go=0,seconds=time.perf_counter()-start,scope=d['scope']+' Empiricaldrawspread isdescriptive conditionalfixedroots, notIIDgeometryconfidence/populationWDL. Prefix1/2/4/8 frozeninadvance, no favorablebudget ormodelselection. Independent658fullphysicalaudit requiredbeforevalidatedclaim.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([x for x in curves if x['metric'] in ['quantity','fast'] and x['predeclared_rng_prefix']==8]))
