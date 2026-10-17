"""PRIMARY math-only forward eligibility/strict WDL accounting, no owner imports."""
import sys,json,time,math
from pathlib import Path
from collections import Counter
R=Path.cwd();sys.path.insert(0,str(R));from tools.local_agent.common import write_json
D=R/'.local_agent/paid-td-20261017';O=D/'exact/results/dev_aux/task2539';plan=json.loads((O/'plan.json').read_bytes());began=time.perf_counter();counts=Counter();max_error=0.;games={};max_weight=0.;negative_games=Counter();minimumP=float('inf');maximumP=-float('inf');errors=[]
queries=(json.loads(line)for line in (O/'queries.jsonl').open());q=next(queries,None)
for line in (O/'games.jsonl').open():
 e=json.loads(line);gid=e['gameid'];w=e['initial_weights'];trace=[0.]*6;delta=[0.]*6;last=None;observed=terms=0;localnodes=0
 if gid%128==0:
  assert time.perf_counter()-began<120,'FROZEN_MATH_CAP'
  for n in ('rollout','advisor','slack'):
   f=json.loads((R/'.local_agent'/(n+'.json')).read_bytes());assert not f.get('user_paused')and not f.get('stopped')
 minimumP=min(minimumP,w[0]);maximumP=max(maximumP,w[0]);max_weight=max(max_weight,*map(abs,w));negative_games[e['method']]+=w[0]<0
 while q is not None and q['gameid']==gid:
  counts['queries']+=1;localnodes+=q['nodes'];counts['paid_nodes']+=q['nodes'];counts['failed_queries']+=not q['complete'];max_weight=max(max_weight,*map(abs,q['weights']))
  assert q['weights']==(w if q['actor']==e['color']else plan['foe'])
  observe=e['method']=='TD'and q['actor']==e['color']and q['complete'];assert q['observed_by_TD']==observe
  if observe:
   v=math.tanh(q['value']/10);grad=[0.]*6 if q['pv_terminal']else[x*(1-v*v)/10 for x in q['pv_phi']]
   if last is not None:
    error=v-last;delta=[d+error*t for d,t in zip(delta,trace)];terms+=1
   trace=[plan['lam']*t+g for t,g in zip(trace,grad)];last=v;observed+=1
  q=next(queries,None)
 assert localnodes==e['nodes'];counts['games']+=1
 if e['method']=='TD':
  if last is not None and e['outcome']is not None:
   error=e['outcome']-last;delta=[d+error*t for d,t in zip(delta,trace)];terms+=1;counts['actual_endpoint_terms']+=1;counts['nonzero_actual_endpoint_terms']+=error!=0
  expected=[x+plan['eta']*d for x,d in zip(w,delta)];err=max(abs(a-b)for a,b in zip(expected,e['after_TD_weights']));max_error=max(max_error,err)
  assert all(math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12)for a,b in zip(expected,e['after_TD_weights']))
  assert observed==e['observed']and terms==e['stats']['samples'];counts['TD_observations']+=observed;counts['TD_terms']+=terms;counts['TD_episodes']+=1
 else:assert w==e['after_TD_weights']
 games[gid]={k:e[k]for k in ['generator_seed','method','seed','family','color','treatment','reward','initial_weights','total_nodes']}
assert q is None
for line in (O/'updates.jsonl').open():
 u=json.loads(line)
 if u['method']!='WDL':continue
 actual=[games[i]for i in u['gameids']];known=sum((1 if g['treatment']=='proposal'else -1)*g['reward']for g in actual if g['reward']is not None);radius=sum(g['reward']is None for g in actual)+u['missing'];den=2*plan['pairs_per_proposal'];bounds=[(known-radius)/den,(known+radius)/den]
 assert bounds==u['bounds']and u['changed']==(known-radius>0)
 assert u['after']==(u['proposal']if known-radius>0 else u['before']);assert u['proposal'][u['coordinate']]==u['before'][u['coordinate']]+u['delta']
 assert all(u['proposal'][j]==u['before'][j]for j in range(6)if j!=u['coordinate']);assert len(actual)==u['actual_games']and u['actual_games']+u['missing']==u['expected_games'];counts['WDL_proposals']+=1;counts['WDL_accepts']+=u['changed'];counts['missing_WDL_games_retained']+=u['missing']
assert counts['paid_nodes']==6400000 and counts['games']==7218 and counts['queries']==113660 and counts['WDL_proposals']==220
write_json(D/'independent-math.json',dict(status='PASS_PRIMARY_FORWARD_CREDIT_AND_INTERVAL_AGGREGATION',source_sha='3792d83068d5d0e61a0a33ebbf6850b414202c6f',counts=dict(counts),max_TD_episode_coordinate_error=max_error,min_actual_episode_P=minimumP,max_actual_episode_P=maximumP,negative_P_episode_counts=dict(negative_games),max_actual_query_coefficient_abs=max_weight,conditional14unit_material_upper_bound=14*max_weight,seconds=time.perf_counter()-began,scope='Independentmath-only: forwardeligibility ratherthanownerreversefutureerrors, directknownsum+UNKNOWNradius ratherthanownerpairedslotselector. Usesfrozenjournalphi/outcomes, NOT independentruleauthority/PVproof; separateownerCoreaudit/64unprunedcontrols retained. ActualnegativePepisodes distinguish92from91positivecone. 14unitbound is onlyconservativeinventoryassumption forfourlegacycapture/drop/promotionruleswithoutspawn, notgenericquantityconservation orbenefitofnegativeP. Missing84games neverzero/draw.'))
print('MATH_PASS',dict(counts),'maxerror',max_error,'minP',minimumP,'14unitbound',14*max_weight)
