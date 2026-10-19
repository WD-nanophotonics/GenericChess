"""Paid Chess TD reset-distribution comparison; research only, all-history rules."""
from pathlib import Path
import json,random,time,hashlib,datetime,sys
from collections import Counter
from math import exp,log
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2566.tc import TCEpisode
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2565.train import prefix,restore
from results.dev_aux.task2392.reader import SharedDeleteStopReader

def initial(seed):
 r=random.Random(seed);return [1.]+[r.uniform(.5,1.5)for _ in range(4)]
def proposal(weights,seed,index):
 r=random.Random(seed*100000+index+972568000);w=list(weights);j=1+index%4;w[j]*=exp(r.uniform(-log(2),log(2)));return w

def improvement(rows):
 # Two common-root/color pairs. Missing or UNKNOWN spans [-1,1], never0.
 if len(rows)!=4:return None
 scores={}
 for r in rows:
  z=r['outcome'];v=None if z is None else z*(1 if r['color']==0 else -1)
  scores[r['variant'],r['color']]=(-1,1)if v is None else(v,v)
 lo=sum(scores['proposal',c][0]-scores['incumbent',c][1]for c in(0,1))
 hi=sum(scores['proposal',c][1]-scores['incumbent',c][0]for c in(0,1))
 return [lo/2,hi/2]

def run(directory):
 d=Path(directory);p=json.loads((d/'plan.json').read_text());s=json.loads(Path('.local_agent/session.json').read_text());assert s['id']==p['session_id']and s['state']=='active';assert not(d/'started.json').exists()
 for name,h in p['pins'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h,name
 stop=SharedDeleteStopReader(Path.cwd());stop();began=time.perf_counter();(d/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=hashlib.sha256((d/'plan.json').read_bytes()).hexdigest())));arms=[];counts=Counter();gid=0
 with(d/'queries.jsonl').open('x')as qf,(d/'games.jsonl').open('x')as gf,(d/'comparisons.jsonl').open('x')as cf:
  for seed,method in p['arms_order']:
   m=Model(initial(seed));foe=Model(p['foes']['uniform']);td=TCEpisode(5,p['eta'],p['lambda'])if method=='TC'else TDLeafEpisode(p['eta'],p['lambda']);used=0;index=0;roundindex=0;updates=0;terms=0;snapshots=[];ab=time.perf_counter();pending=[];before_round=None;candidate=None
   while used<p['nodes_per_arm']and index<p['max_games']and time.perf_counter()-began<p['cap_seconds']:
    foe_name=p['foe_cycle'][index%len(p['foe_cycle'])];foe=Model(p['foes'][foe_name])
    if method=='WDL':
     if not pending:before_round=list(m.weights);candidate=proposal(before_round,seed,roundindex)
     variant=('incumbent','proposal','proposal','incumbent')[len(pending)];color=(0,0,1,1)[len(pending)];family=p['training_family_offset']+roundindex;current_w=before_round if variant=='incumbent'else candidate
    else:variant='learner';color=index%2;family=p['training_family_offset']+index//2;current_w=list(m.weights)
    reset_plies=8 if method=='TD_early'else p['mixed_prefix_cycle'][index%len(p['mixed_prefix_cycle'])]
    gid+=1;e=ChessEnv();prefix(e,0,family,reset_plies);first=e.record();w_before=list(m.weights);player=Model(current_w);game_start=used;nq=0;observed=0;ending='HORIZON_UNKNOWN'
    for ply in range(p['H']):
     stop()
     if e.terminal()is not None:ending='ACTUAL_TERMINAL';break
     remaining=min(p['nodes_per_arm']-used,p['nodes_per_game']-(used-game_start));wall=p['cap_seconds']-(time.perf_counter()-began)
     if remaining<=0 or wall<=0:ending='AGGREGATE_OR_GAME_CAP_UNKNOWN';break
     actor=e.player();model=player if actor==color else foe;old=e.record();limit=min(remaining,p['nodes_per_query']);seconds=min(wall,p['seconds_per_query']);order=family*1000+ply+p['ordering_seed_offset'];search=TrainingSearch(p['depth'],quiet=(actor==color and method=='TD_q2'),q_limit=2);r=search.search(e,model,nodes=limit,seconds=seconds,seed=order,cancel=stop);assert old==e.record();used+=r.nodes;nq+=1;obs=method!='WDL'and actor==color and r.complete
     if obs:td.observe(m,r);observed+=1
     if r.complete:e.push(r.action)
     q=dict(gameid=gid,seed=seed,method=method,index=index,round_index=roundindex,variant=variant,foe_name=foe_name,family=family,prefix_plies=reset_plies,color=color,ply=ply,actor=actor,observed=obs,weights=list(model.weights),record_before=old,record_after=e.record(),complete=r.complete,value=r.value,pv_phi=r.pv_phi,pv_terminal=r.pv_terminal,nodes=r.nodes,total_nodes=used,seconds=r.seconds,effective_nodes=limit,effective_seconds=seconds,ordering_seed=order,reason=r.reason,search_stats=search.last_stats,candidate_q2=(actor==color and method=='TD_q2'))
     qf.write(json.dumps(q,separators=(',',':'))+'\n');qf.flush()
     if not r.complete:ending='SEARCH_RESOURCE_UNKNOWN';break
    z=e.terminal()
    if z is not None:ending='ACTUAL_TERMINAL'
    assert restore(0,None,e.record()).terminal()==z
    stats=dict(samples=0,loss=None,changed=False,censored=z is None)if method=='WDL'else td.finish(m,z);terms+=stats['samples'];updates+=int(w_before!=m.weights)
    row=dict(gameid=gid,seed=seed,method=method,index=index,round_index=roundindex,variant=variant,foe_name=foe_name,family=family,prefix_plies=reset_plies,color=color,initial_weights=w_before,played_weights=current_w,weights=list(m.weights),stats=stats,initial_record=first,record=e.record(),outcome=z,ending=ending,nodes=used-game_start,total_nodes=used,queries=nq,observed=observed)
    gf.write(json.dumps(row,separators=(',',':'))+'\n');gf.flush();counts.update(dict(games=1,actual_terminal=z is not None,unknown=z is None,nodes=row['nodes'],queries=nq,observed=observed,terms=stats['samples']));index+=1
    if method=='WDL':
     pending.append(row)
     if len(pending)==4:
      interval=improvement(pending);accepted=interval[0]>0
      if accepted:m=Model(candidate);updates+=1
      cf.write(json.dumps(dict(seed=seed,round_index=roundindex,gameids=[x['gameid']for x in pending],incumbent=before_round,proposal=candidate,interval=interval,accepted=accepted,after=list(m.weights),nodes=used))+'\n');cf.flush();pending=[];roundindex+=1
    for boundary in p['snapshot_nodes']:
     if used<=boundary:
      snapshots=[x for x in snapshots if x['boundary']!=boundary];snapshots.append(dict(boundary=boundary,nodes=used,index=index,weights=list(m.weights)))
   if method=='WDL'and pending:cf.write(json.dumps(dict(seed=seed,round_index=roundindex,gameids=[x['gameid']for x in pending],incumbent=before_round,proposal=candidate,interval=None,accepted=False,after=list(m.weights),nodes=used,incomplete=True))+'\n');cf.flush()
   a=dict(generator_seed=0,seed=seed,method=method,initial=initial(seed),weights=list(m.weights),nodes=used,games=index,updates=updates,terms=terms,snapshots=snapshots,seconds=time.perf_counter()-ab,cause='TOTAL_NODES'if used==p['nodes_per_arm']else'GLOBAL_CAP_OR_MAX_GAMES');arms.append(a);print(json.dumps(a),flush=True)
   if time.perf_counter()-began>=p['cap_seconds']:break
 result=dict(status='COMPLETE'if len(arms)==len(p['arms_order'])and all(x['nodes']==p['nodes_per_arm']for x in arms)else'PARTIAL_CAP',arms=arms,expected_arms=len(p['arms_order']),nodes=sum(a['nodes']for a in arms),counts=dict(counts),seconds=time.perf_counter()-began);(d/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='arms'}),flush=True)
if __name__=='__main__':run(sys.argv[1])
