import json,hashlib,time,re,statistics,collections
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task626';O.mkdir(exist_ok=True);start=time.perf_counter();d=json.loads((R/'results/dev_aux/task624/declaration.json').read_bytes());r=json.loads((R/'results/dev_aux/task624/result.json').read_bytes());assert r['status']=='COMPLETE_ALL_BUDGET_CELLS';gs={}
for task in [614,624]:gs[task]=[json.loads(x) for x in (R/f'results/dev_aux/task{task}/games.jsonl').open(encoding='utf-8')]
lookup={}
for x in r['rows']:
 task=614 if x['reused'] else 624;g=gs[task][x['source']['line']-1];lookup[(x['profile'],x['nodes'],x['root'],x['color'])]=g
assert len(lookup)==1728
rows=[];summ=[];cost=[]
def status(g):return 'UNFINISHED' if g['termination']['kind']=='cap12' else 'DRAW' if g['termination']['winner'] is None else 'WIN' if g['termination']['winner']==g['color'] else 'LOSS'
def value(g,metric):
 t=g['termination'];winner=t['winner']
 if metric=='mixed':return F(g['goal'])
 if winner is None:return F(0)
 if metric=='terminal':return F(32 if winner==g['color'] else -32)
 return F(13-len(g['actions'])) if winner==g['color'] else F(-13)
for route in ['terminal_and_mixed','fast']:
 for st in ['unit','random2514']:
  ip=next(i for i,p in enumerate(d['profiles']) if 'terminal-'+st+'-initial' in p['names']);ep=next(i for i,p in enumerate(d['profiles']) if ('terminal-'+st+'-endpoint' if route=='terminal_and_mixed' else 'fast-'+st+'-endpoint') in p['names'])
  for metric in ['fast','terminal','mixed']:
   rr=[]
   for f in d['roots']:
    for c in [0,1]:
     g=[[lookup[(p,b,f['index'],c)] for p in [ip,ep]] for b in [1024,8192]];diff=[value(x[1],metric)-value(x[0],metric) for x in g];rr.append(dict(route=route,start=st,metric=metric,phase=f['phase'],family=f['source_family'],root=f['index'],color=c,low_gain=str(diff[0]),high_gain=str(diff[1]),interaction=str(diff[1]-diff[0]),all4unfinished=all(status(a)=='UNFINISHED' for x in g for a in x),statuses=[[status(a) for a in x] for x in g]))
   rows+=rr
   for phase in ['train','development']:
    a=[x for x in rr if x['phase']==phase];families=sorted({x['family'] for x in a})
    def mean(a):return dict(cells=len(a),low_gain=str(sum(F(x['low_gain']) for x in a)/len(a)),high_gain=str(sum(F(x['high_gain']) for x in a)/len(a)),interaction=str(sum(F(x['interaction']) for x in a)/len(a)),positive_cells=sum(F(x['interaction'])>0 for x in a),negative_cells=sum(F(x['interaction'])<0 for x in a),nonzero_cells=sum(F(x['interaction'])!=0 for x in a),all4unfinished=sum(x['all4unfinished'] for x in a))
    summ.append(dict(route=route,start=st,metric=metric,phase=phase,all=mean(a),by_family=[dict(family=f,**mean([x for x in a if x['family']==f])) for f in families],leave_one=[dict(omit=f,**mean([x for x in a if x['family']!=f])) for f in families]))
for pi in range(6):
 for budget in [1024,8192]:
  a=[lookup[(pi,budget,f['index'],c)] for f in d['roots'] for c in [0,1]];ns=[];depth=collections.Counter();diag=collections.Counter()
  for g in a:
   for q in g['queries']:
    info=[s for s in q['lines'] if re.search(r'\bnodes \d+',s)][-1];ns.append(int(re.search(r'\bnodes (\d+)',info)[1]));depth[int(re.search(r'\bdepth (\d+)',info)[1])]+=1;diag.update({k:v for k,v in q['capture_diag'].items() if k!='mode'})
  cost.append(dict(profile=pi,requested_nodes=budget,games=len(a),actual_queries=len(ns),reported_nodes=sum(ns),node_min=min(ns),node_median=statistics.median(ns),node_max=max(ns),depth_distribution=depth,internal_game_seconds=sum(g['seconds'] for g in a),counter_totals=diag,actual_mates=sum(g['termination']['kind']=='checkmate' for g in a),unfinished=sum(status(g)=='UNFINISHED' for g in a)))
out=dict(status='ALL_BUDGET_INTERACTIONS_FROZEN',rows=rows,summaries=summ,resources=cost,logical_games=1728,new_go=0,seconds=time.perf_counter()-start,source_sha256=hashlib.sha256((R/'results/dev_aux/task624/result.json').read_bytes()).hexdigest(),scope=d['scope']+' ALL24 route/start/metric/phase contrasts withALL8train/3eligibledev family omissions. Resource-request policy effect, not equalactualwork oruniformdepthproof. No result-based filtering orreferencefit. Independent625physical/cached-source check required forfinalclaim.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps([dict(route=x['route'],start=x['start'],phase=x['phase'],metric=x['metric'],**x['all']) for x in summ if x['phase']=='development']));print(json.dumps([dict(profile=x['profile'],budget=x['requested_nodes'],go=x['actual_queries'],nodes=x['reported_nodes'],mates=x['actual_mates']) for x in cost]))