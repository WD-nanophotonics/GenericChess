from pathlib import Path
import json,collections,importlib.util
R=Path.cwd();O=R/'results/dev_aux/task1705';O.mkdir(exist_ok=False);studies=[]
for task,planid in [(1678,1677),(1686,1685),(1696,1695),(1693,1692),(1699,1698)]:
 run=json.loads((R/f'results/dev_aux/task{task}/result.json').read_bytes());plan=json.loads((R/f'results/dev_aux/task{planid}/plan.json').read_bytes());selected=run['selected'];C=tuple(selected.get('POOLED',selected.get('PRIMARY',selected.get('FIXED_ON_TRAIN'))));families={f['family']:f for f in plan['families']};width=8 if task in(1693,1699) else 4;rows=[json.loads(l) for l in (R/f'results/dev_aux/task{task}/games.jsonl').open()];dev=[x for x in rows if x['phase']=='DEV'];means={}
 for p in [tuple(plan['baseline']),C]:
  dd=collections.defaultdict(list)
  for x in dev:
   if tuple(x['price'])==p:dd[x['family']].append(x['payoff'] or 0)
  means[p]={f:sum(a)/len(a) for f,a in dd.items()}
 strata=collections.defaultdict(list);demography=collections.Counter()
 for f in families.values():
  s=f['roots'][0];turn=s[-1];z=next(i for i,p in enumerate(s[:-1]) if p.upper()=='P');p=s[z];own=int(p.islower())==turn;distance=z//width if p.islower() else width-1-z//width;role=sum(p!='.' and int(p.islower())==turn for p in s[:-1])-1;demography[f['phase'],own,distance,role]+=1
  if f['phase']=='DEV':
   gain=means[C][f['family']]-means[tuple(plan['baseline'])][f['family']]
   for name,key in [('P_holder',own),('P_push_distance',distance),('own_nonkings',role),('P_holder_distance',(own,distance))]:strata[name,str(key)].append(gain)
 study={'task':task,'selected':C,'DEV_strata':[{'stratum':name,'key':key,'families':len(gg),'mean_gain':sum(gg)/len(gg)} for (name,key),gg in strata.items()],'root_demography':{str(k):v for k,v in demography.items()}}
 if run['TRAIN'] and len(C)==4:
  grid=collections.defaultdict(dict)
  for x in run['TRAIN']:grid[x['phase']][tuple(x['price'])]=x['finite_net']
  for phase,d in grid.items():
   if all(q in d for q in [(720,720,720,720),(1440,720,720,720),(720,720,720,360),(1440,720,720,360)]):
    v0=d[720,720,720,720];vr=d[1440,720,720,720];vp=d[720,720,720,360];vboth=d[1440,720,720,360];study.setdefault('TRAIN_fixed_factorial',[]).append({'phase':phase,'unit':v0,'R_only_gain':vr-v0,'P_only_gain':vp-v0,'combined_gain':vboth-v0,'R_P_interaction':vboth-vr-vp+v0,'R_SharedOrderAverage':((vr-v0)+(vboth-vp))/2,'P_SharedOrderAverage':((vp-v0)+(vboth-vr))/2})
 studies.append(study)
out={'status':'COMPLETED_ZERO_QUERY_ROOT_DISTANCE_ROLE_AND_FIXED_PRICE_PARAMETER_DIAGNOSTIC','studies':studies,'actual_go':0,'scope':'Postspecifieddescriptiverootstrata, notprespecifiedconfirmatorysubgrouptests/DEVpricechoice. No extraqueries/newholdout. TRAINsamegrid4corners only, attributiontwofactororderaverage notuniversalmechanicsprice.'};(O/'result.json').write_text(json.dumps(out,indent=2));print(json.dumps(studies,indent=2))
