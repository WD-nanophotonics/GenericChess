import json,hashlib,time,re,statistics,collections
from pathlib import Path
from fractions import Fraction as F
R=Path.cwd();O=R/'results/dev_aux/task616';O.mkdir(exist_ok=True);start=time.perf_counter();d=json.loads((R/'results/dev_aux/task614/declaration.json').read_bytes());r=json.loads((R/'results/dev_aux/task614/result.json').read_bytes());assert r['status']=='COMPLETE_ALL_CELLS';gs=[json.loads(x) for x in (R/'results/dev_aux/task614/games.jsonl').open(encoding='utf-8')];lookup={(g['profile'],g['mode'],g['root']['index'],g['color']):g for g in gs};assert len(lookup)==1152;rows=[];summ=[];cost=[];pmap=[]
for name in ['unit','random2514']:
 ip=next(i for i,p in enumerate(d['profiles']) if 'terminal-'+name+'-initial' in p['names']);ep=next(i for i,p in enumerate(d['profiles']) if 'terminal-'+name+'-endpoint' in p['names']);pmap.append(dict(start=name,initial=ip,endpoint=ep))
 def val(g,metric):return F(g['goal']) if metric=='mixed' else F(0) if g['termination']['winner'] is None else F(32 if g['termination']['winner']==g['color'] else -32)
 def status(g):return 'UNFINISHED' if g['termination']['kind']=='cap12' else 'DRAW' if g['termination']['winner'] is None else 'WIN' if g['termination']['winner']==g['color'] else 'LOSS'
 for metric in ['terminal','mixed']:
  rr=[]
  for f in d['roots']:
   for c in [0,1]:
    gg=[[lookup[(p,m,f['index'],c)] for p in [ip,ep]] for m in [0,1]];diff=[val(a[1],metric)-val(a[0],metric) for a in gg];I=diff[1]-diff[0];x=dict(start=name,metric=metric,phase=f['phase'],family=f['source_family'],root=f['index'],offset=f['offset'],color=c,mode0_gain=str(diff[0]),mode1_gain=str(diff[1]),interaction=str(I),mode0_initial=status(gg[0][0]),mode0_endpoint=status(gg[0][1]),mode1_initial=status(gg[1][0]),mode1_endpoint=status(gg[1][1]),scores=[[str(val(g,metric)) for g in a] for a in gg]);rr.append(x);rows.append(x)
  for phase in ['train','development']:
   a=[x for x in rr if x['phase']==phase];families=sorted({x['family'] for x in a})
   def avg(a):return dict(cells=len(a),mode0_gain=str(sum(F(x['mode0_gain']) for x in a)/len(a)),mode1_gain=str(sum(F(x['mode1_gain']) for x in a)/len(a)),interaction=str(sum(F(x['interaction']) for x in a)/len(a)),interaction_nonzero_cells=sum(F(x['interaction'])!=0 for x in a),positive_cells=sum(F(x['interaction'])>0 for x in a),negative_cells=sum(F(x['interaction'])<0 for x in a),all4unfinished=sum(all(x[k]=='UNFINISHED' for k in ['mode0_initial','mode0_endpoint','mode1_initial','mode1_endpoint']) for x in a))
   summ.append(dict(start=name,metric=metric,phase=phase,all=avg(a),by_family=[dict(family=f,**avg([x for x in a if x['family']==f])) for f in families],leave_one=[dict(omit=f,**avg([x for x in a if x['family']!=f])) for f in families]))
for pi in range(4):
 for mode in [0,1]:
  a=[g for g in gs if g['profile']==pi and g['mode']==mode];ns=[];ds=collections.Counter();diag=collections.Counter();sec=0
  for g in a:
   sec+=g['seconds']
   for q in g['queries']:
    info=[x for x in q['lines'] if re.search(r'\bnodes \d+',x)][-1];ns.append(int(re.search(r'\bnodes (\d+)',info)[1]));ds[int(re.search(r'\bdepth (\d+)',info)[1])]+=1;diag.update({k:v for k,v in q['capture_diag'].items() if k!='mode'})
  cost.append(dict(profile=pi,mode=mode,games=len(a),queries=len(ns),reported_nodes=sum(ns),node_min=min(ns),node_median=statistics.median(ns),node_max=max(ns),depth_distribution=ds,internal_game_seconds=sec,diagnostic=dict(diag),actual_mates=sum(g['termination']['kind']=='checkmate' for g in a),unfinished=sum(g['termination']['kind']=='cap12' for g in a)))
changed=[]
for pi in range(4):
 for f in d['roots']:
  for c in [0,1]:
   a,b=[lookup[(pi,m,f['index'],c)] for m in [0,1]];changed.append(dict(profile=pi,family=f['source_family'],root=f['index'],color=c,actions_equal=a['actions']==b['actions'],terminations_equal=a['termination']==b['termination'],mixed_equal=a['goal']==b['goal']))
out=dict(status='PASS_ALL_PRICE_MODE_INTERACTIONS',rows=rows,summaries=summ,resources=cost,price_map=pmap,paired_games=len(changed),paired_actions_changed=sum(not x['actions_equal'] for x in changed),paired_terminations_changed=sum(not x['terminations_equal'] for x in changed),paired_mixed_changed=sum(not x['mixed_equal'] for x in changed),all_path_comparisons=changed,source_sha256=hashlib.sha256((R/'results/dev_aux/task614/result.json').read_bytes()).hexdigest(),new_go=0,seconds=time.perf_counter()-start,scope=d['scope']+' ALLpairs preserved, Dotdifference-in-differences adoptedandbothsignsneutral. 8train/3eligibledevelopmentfamilies, original4thunavailable; rootweighted cellswithsamefamily grouped. Countertotals eachvisitedtree notmatchlatercontexts; no causalindividualharmfulprune or humanvaluelearning proof.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:out[k] for k in ['status','paired_games','paired_actions_changed','paired_terminations_changed','paired_mixed_changed','resources']}));print(json.dumps([dict(start=x['start'],phase=x['phase'],**x['all']) for x in summ if x['metric']=='terminal']))