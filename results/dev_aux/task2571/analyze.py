"""All fixed snapshots, paired W-L curves, censoring and actual cost accounting."""
from pathlib import Path
from collections import defaultdict, Counter
import json, hashlib, itertools, sys
from results.dev_aux.task2568.summary import contrast
D=Path('results/dev_aux/task2571');T=Path('results/dev_aux/task2568')
METHODS=('TD','TC','WDL');B=(250000,500000,750000,1000000)
def label(m,b):return m if b==1000000 else m+'@'+str(b)
def load(p):return json.loads(Path(p).read_text())
def rows(p):return list(map(json.loads,Path(p).open()))
def bindings():
 p=load(D/'eval-plan.json');f=load(D/'freeze.json');t=load(T/'result.json');bound=load(D/'result.json');started=load(D/'eval-started.json')
 assert started['utc']>f['registered_at'] and f['registered_at']==p['registered_at']
 for n,h in f['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 assert bound['source_sha']==hashlib.sha256((T/'result.json').read_bytes()).hexdigest()
 expected=set(itertools.product([0],[1977,8173,27182,31415],range(441001,441005),[0,1],['initial']+[label(m,b)for m in METHODS for b in B],p['foes']))
 assert set(map(tuple,p['slots']))==expected and len(p['slots'])==832
 gg=rows(T/'games.jsonl');cc=rows(T/'comparisons.jsonl');checks=[]
 for a in bound['arms']:
  src=next(x for x in t['arms']if x['seed']==a['seed']and x['method']==a['original_method']);b=a['nominal_boundary'];games=[g for g in gg if g['seed']==a['seed']and g['method']==a['original_method']and g['total_nodes']<=b];assert games;g=games[-1];w=g['weights']
  if a['original_method']=='WDL':
   closed=[c for c in cc if c['seed']==a['seed']and c['nodes']<=g['total_nodes']];w=closed[-1]['after']if closed else src['initial']
  assert w==a['weights'] and g['total_nodes']==a['nodes']
  if b<1000000:
   ss=next(s for s in src['snapshots']if s['boundary']==b);assert ss['weights']==w and ss['nodes']==g['total_nodes'] and ss['index']==g['index']+1 and a['source_episode']==ss['index']
  else:assert a['weights']==src['weights']and a['source_episode']==g['index']
  checks.append(dict(seed=a['seed'],method=a['method'],nominal=b,actual_nodes=a['nodes'],closed_episodes=g['index']+1,source_last_index=g['index']))
 r=dict(status='PASS_ALL48_INDEPENDENT_EPISODE_BINDINGS',checks=checks,scope='Legacy source_episode field copies raw snapshot index=closedcount for intermediate snapshots, but endpoint uses0basedlastindex. This auditor records both explicitly; no coefficient/cost/cap changed. WDL accepted-round decisions applied before binding; incomplete comparisons do not accept.')
 (D/'binding-audit.json').write_text(json.dumps(r,indent=2));print(json.dumps(dict(status=r['status'],models=len(checks))))
def panel(d):
 d=Path(d);p=load(d/'eval-plan.json');ev=load(d/'eval-result.json');rr={tuple(r['slot']):r for r in rows(d/'eval-games.jsonl')};assert len(rr)==ev['actual'];return p,ev,rr

def summarize():
 p,ev,rr=panel(D);out={};increments={};matched={}
 for m in METHODS:
  out[m]={};increments[m]={}
  for i,b in enumerate(B):
   l=label(m,b);old='initial'if i==0 else label(m,B[i-1]);out[m][str(b)]={f:contrast(rr,[s for s in p['slots']if s[5]==f],l,'initial')for f in p['foes']};increments[m][str(b)]={f:contrast(rr,[s for s in p['slots']if s[5]==f],l,old)for f in p['foes']}
 for left,right in [('TC','TD'),('TD','WDL'),('TC','WDL')]:matched[left+'-'+right]={str(b):{f:contrast(rr,[s for s in p['slots']if s[5]==f],label(left,b),label(right,b))for f in p['foes']}for b in B}
 seedcurves={str(seed):{m:{str(b):{f:contrast(rr,[s for s in p['slots']if s[1]==seed and s[5]==f],label(m,b),'initial')for f in p['foes']}for b in B}for m in METHODS}for seed in [1977,8173,27182,31415]}
 rolecurves={str(c):{m:{str(b):{f:contrast(rr,[s for s in p['slots']if s[3]==c and s[5]==f],label(m,b),'initial')for f in p['foes']}for b in B}for m in METHODS}for c in [0,1]}
 familycurves={str(fam):{m:{str(b):{f:contrast(rr,[s for s in p['slots']if s[2]==fam and s[5]==f],label(m,b),'initial')for f in p['foes']}for b in B}for m in METHODS}for fam in range(441001,441005)}
 costs=defaultdict(Counter)
 for g in rr.values():costs[g['slot'][4]].update(dict(games=1,nodes=g['nodes'],queries=g['queries'],actual_terminal=g['outcome']is not None,unknown=g['outcome']is None))
 trainroots={json.dumps(g['initial_record'],sort_keys=True)for g in rows(T/'games.jsonl')};oldroots=set()
 for task in (2568,2570):oldroots.update(json.dumps(g['initial_record'],sort_keys=True)for g in rows(Path('results/dev_aux/task'+str(task))/'eval-games.jsonl'))
 roots={json.dumps(g['initial_record'],sort_keys=True)for g in rr.values()};controls=0;uncertain=0
 for g in rr.values():
  for h in rr.values():
   if tuple(g['slot'])>=tuple(h['slot'])or g['slot'][:4]!=h['slot'][:4]or g['slot'][5]!=h['slot'][5]or g['weights']!=h['weights']:continue
   if g['outcome']is None or h['outcome']is None:uncertain+=1;continue
   assert all(g[k]==h[k]for k in('record','reward','nodes','queries'));controls+=1
 source=load(T/'result.json');r=dict(status='ALL_REGISTERED_COST_POINTS_RETAINED',EVAL=ev,gain_vs_initial=out,adjacent_gain=increments,matched_method_gain=matched,all_seed_curves=seedcurves,all_role_curves=rolecurves,all_family_curves=familycurves,EVAL_cost_by_label=dict(costs),inherited_training_nodes=source['nodes'],inherited_training_seconds=source['seconds'],new_training_nodes=0,new_eval_nodes=ev['nodes'],new_eval_seconds=ev['seconds'],training_plus_this_panel_nodes=source['nodes']+ev['nodes'],snapshot_model_costs=load(D/'binding-audit.json')['checks'],same_weight_terminal_controls=controls,unresolved_same_weight_controls=uncertain,exposure=dict(roots=len(roots),currentTRAINoverlap=len(roots&trainroots),previous97EVALoverlap=len(roots&oldroots)),scope='Finitepanel pairedW-L[-2,2], unknown/missing[-1,1] reward bounds, NOTconfidenceintervals. ALLseeds/roles/families/costpoints, no checkpoint selection or newTRAIN. Lastclosedepisodes lag nominalbudgets; BOTHnodeaxes retained. InheritedTRAINpaidonce, allnewfoe/baseline/failedquerywork paid; audits/engineeringoutsideproducerwall.')
 (D/'summary.json').write_text(json.dumps(r,indent=2));print(json.dumps(dict(eval=ev,curves={m:{b:{f:z['bounds']for f,z in zz.items()}for b,zz in q.items()}for m,q in out.items()},adjacent={m:{b:{f:z['bounds']for f,z in zz.items()}for b,zz in q.items()}for m,q in increments.items()},exposure=r['exposure'],controls=controls)))
if __name__=='__main__':globals()[sys.argv[1]]()
