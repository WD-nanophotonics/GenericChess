import json,time,hashlib
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task631';O.mkdir(exist_ok=True);d=json.loads((R/'results/dev_aux/task627/declaration.json').read_bytes());r=json.loads((R/'results/dev_aux/task629/result.json').read_bytes());freeze=json.loads((R/'results/dev_aux/task627/roots_frozen.json').read_bytes());assert r['status']=='ALL_PROBES_COMPLETE';gs=[json.loads(x) for x in (R/'results/dev_aux/task629/games.jsonl').open(encoding='utf-8')];lookup={(g['profile'],g['root']['index'],g['color']):g for g in gs};rows=[];summ=[]
def val(g,m):
 winner=g['termination']['winner']
 if m=='mixed':return F(g['goal'])
 if winner is None:return F(0)
 if m=='terminal':return F(32 if winner==g['color'] else -32)
 return F(13-len(g['actions'])) if winner==g['color'] else F(-13)
for route in ['terminal_and_mixed','fast']:
 for st in ['unit','random2514']:
  ip=next(i for i,p in enumerate(d['probe_profiles']) if 'terminal-'+st+'-initial' in p['names']);ep=next(i for i,p in enumerate(d['probe_profiles']) if ('terminal-'+st+'-endpoint' if route=='terminal_and_mixed' else 'fast-'+st+'-endpoint') in p['names'])
  for metric in ['fast','terminal','mixed']:
   a=[]
   for f in freeze['roots']:
    for c in [0,1]:
     x,y=[lookup[(p,f['index'],c)] for p in [ip,ep]];a.append(dict(route=route,start=st,metric=metric,family=f['seed'],generator=f['generator'],root=f['index'],offset=f['offset'],color=c,gain=str(val(y,metric)-val(x,metric)),initial_term=x['termination'],endpoint_term=y['termination'],initial_plies=len(x['actions']),endpoint_plies=len(y['actions'])))
   rows+=a;families=sorted({x['family'] for x in a})
   def mean(a):return dict(cells=len(a),gain=str(sum(F(x['gain']) for x in a)/len(a)),positive_cells=sum(F(x['gain'])>0 for x in a),negative_cells=sum(F(x['gain'])<0 for x in a),both_unfinished=sum(x['initial_term']['kind']==x['endpoint_term']['kind']=='cap12' for x in a))
   summ.append(dict(route=route,start=st,metric=metric,all=mean(a),by_family=[dict(family=f,**mean([x for x in a if x['family']==f])) for f in families],leave_one=[dict(omit=f,**mean([x for x in a if x['family']!=f])) for f in families],by_generator=[dict(generator=p,**mean([x for x in a if x['generator']==p])) for p in [0,1] if any(x['generator']==p for x in a)]))
profile_stats=[dict(profile=pi,games=sum(g['profile']==pi for g in gs),mates=sum(g['profile']==pi and g['termination']['kind']=='checkmate' for g in gs),unfinished=sum(g['profile']==pi and g['termination']['kind']=='cap12' for g in gs)) for pi in range(6)]
out=dict(status='ALL_NEW_BALANCED_TRANSFER_SCORES_FROZEN',rows=rows,summaries=summ,profiles=profile_stats,original_families=8,eligible_families=freeze['eligible_families'],unavailable=freeze['unavailable'],setup_mates=freeze['setup_mates'],roots=len(freeze['roots']),actual_probe_games=r['actual_games'],actual_probe_go=r['actual_go'],seconds=r['seconds'],new_go=0,source_sha256=hashlib.sha256((R/'results/dev_aux/task629/result.json').read_bytes()).hexdigest(),scope=d['scope']+' ALL4learnedendpoint owninitial contrasts, all3scores, all7eligiblefamily omissions; generationpolicies exposure/conditionalmate notnaturalWDL distribution. Positive/negative transfer doesnotestablishhumanvalues oruniversaloptimum. Independent630physicalaudit required beforefinalclaim.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([dict(route=x['route'],start=x['start'],metric=x['metric'],**x['all']) for x in summ]));print(json.dumps(profile_stats))