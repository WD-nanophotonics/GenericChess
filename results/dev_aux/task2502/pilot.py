"""Price-independent TRAIN prefix admission; resource gate uses completion only."""
from pathlib import Path
import json,random,time,hashlib,datetime,math
from results.dev_aux.task2501.search import TrainingSearch
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2502')
def run():
 p=json.loads((OUT/'plan.json').read_text());assert not(OUT/'started.json').exists();stop=SharedDeleteStopReader(Path.cwd());stop();start=time.perf_counter();(OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest())));allrows=[];gate='UNKNOWN';selected=None;status='COMPLETE'
 with(OUT/'queries.jsonl').open('x')as f:
  for phase,node_limit in enumerate(p['node_limits']):
   phase_rows=[]
   for seed in p['initial_seeds']:
    rng=random.Random(seed);weights=[1.]+[rng.uniform(.5,1.5)for _ in range(4)]
    for family in range(p['families']):
     env=ChessEnv();rng=random.Random(p['opening_seed_base']+family)
     for _ in range(p['opening_plies']):
      if env.terminal()is not None:break
      env.push(rng.choice(sorted(env.actions(),key=lambda a:a.uci())))
     record=env.record()
     for quiet in (False,True):
      stop();left=p['cap_seconds']-(time.perf_counter()-start)
      if left<=0:status='PARTIAL_CAP';break
      search=TrainingSearch(p['depth'],quiet=quiet,qstack=p['qstack']);r=search.search(env,Model(weights),nodes=node_limit,seconds=min(p['seconds_per_query'],left),seed=seed*100000+family,cancel=stop)
      assert env.record()==record
      row=dict(phase=phase,node_limit=node_limit,seed=seed,family=family,quiet=quiet,initial=weights,record=record,complete=r.complete,value=r.value,pv_phi=r.pv_phi,pv_terminal=r.pv_terminal,action=None if r.action is None else r.action.uci(),nodes=r.nodes,seconds=r.seconds,reason=r.reason,stats=search.last_stats);phase_rows.append(row);allrows.append(row);f.write(json.dumps(row)+'\n');f.flush()
     if status!='COMPLETE':break
    if status!='COMPLETE':break
   if status!='COMPLETE':break
   q=[r for r in phase_rows if r['quiet']];assert len(q)==len(p['initial_seeds'])*p['families']
   completed=sum(r['complete']for r in q);required=math.ceil(p['completion_fraction']*len(q))
   if completed>=required:selected=node_limit;gate='RESOURCE_FEASIBLE_COMPLETION_ONLY';break
  if gate=='UNKNOWN'and status=='COMPLETE':gate='RESOURCE_GATE_NOT_MET'
 result=dict(status=status,gate=gate,selected_search_nodes=selected,queries=len(allrows),nodes=sum(r['nodes']for r in allrows),seconds=time.perf_counter()-start,phases=[dict(node_limit=n,plain_complete=sum(r['complete']for r in allrows if r['node_limit']==n and not r['quiet']),quiet_complete=sum(r['complete']for r in allrows if r['node_limit']==n and r['quiet']),quiet_expected=len(p['initial_seeds'])*p['families'])for n in p['node_limits']if any(r['node_limit']==n for r in allrows)],scope='AllTRAIN roots/initials retained; gate uses query completion ONLY before training WDL, no action/score/root selection. New full qsearch labels bounded by nodes/time/qstack: aborted means UNKNOWN, never static label. No game outcome or holdout queried.')
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
