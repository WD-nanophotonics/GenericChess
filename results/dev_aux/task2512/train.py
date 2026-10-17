"""Frozen single-process learning-method contrast; no product defaults."""
from pathlib import Path
import json,random,time,hashlib,datetime
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2492.learning import Model,transformed,TreeStrap
from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2392.reader import SharedDeleteStopReader
OUT=Path('results/dev_aux/task2512')
def run():
 p=json.loads((OUT/'plan.json').read_text());assert not(OUT/'started.json').exists()
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 stop=SharedDeleteStopReader(Path.cwd());stop();began=time.perf_counter();results=[];status='COMPLETE'
 (OUT/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest())))
 with(OUT/'decisions.jsonl').open('x')as df,(OUT/'episodes.jsonl').open('x')as gf:
  for slot in p['arms']:
   seed,method=slot['seed'],slot['method'];rng=random.Random(seed);initial=[1.]+[rng.uniform(.5,1.5)for _ in range(4)];m=Model(initial);td=TDLeafEpisode(p['eta'],p['lambda']);tree=TreeStrap(p['eta']);used=0;searches=0;start=time.perf_counter();totals={};games=[];checkpoints=[]
   for game in range(p['max_games']):
    if used>=p['nodes_per_arm']:break
    env=ChessEnv();rng=random.Random(p['opening_seed_base']+game)
    for _ in range(p['opening_plies']):
     if env.terminal()is not None:break
     env.push(rng.choice(sorted(env.actions(),key=lambda a:a.uci())))
    prefix=env.record();before=list(m.weights);td.reset();reason='HORIZON_UNKNOWN';outcome=None;begin_nodes=used;decision_start=searches;sample_count=active_count=changes=0;loss_sum=0.
    for ply in range(p['H']):
     stop();outcome=env.terminal()
     if outcome is not None:reason='ACTUAL_TERMINAL';break
     left=p['nodes_per_arm']-used;seconds=p['cap_seconds']-(time.perf_counter()-began)
     if left<=0:reason='TOTAL_NODE_UNKNOWN';break
     if seconds<=0:reason='GLOBAL_CAP_UNKNOWN';status='PARTIAL_GLOBAL_CAP';break
     node_limit=min(p['nodes_per_query'],left);wall_limit=min(p['seconds_per_query'],seconds);snapshot=list(m.weights);engine=TrainingSearch(p['depth'],quiet=False)
     r=engine.search(env,m,nodes=node_limit,seconds=wall_limit,seed=seed*100000+game*1000+ply,cancel=stop);used+=r.nodes;searches+=1
     pred=None if not r.complete else transformed(r.value,m.scale);grad=None if not r.complete else [0.]*5 if r.pv_terminal else list(m.gradient(r.pv_phi));samples=[];stats=dict(samples=0,loss=None,changed=False)
     if r.complete:
      if not r.pv_terminal:assert m.raw(r.pv_phi)==r.value
      if method=='td':td.observe(m,r)
      else:
       samples=[[list(s.phi),None if s.lower==float('-inf')else s.lower,None if s.upper==float('inf')else s.upper,s.depth]for s in r.samples]
       stats=tree.update(m,r);sample_count+=stats['samples'];active_count+=stats.get('active',0);changes+=snapshot!=m.weights;loss_sum+=(stats['loss']or 0.)*stats['samples']
     row=dict(seed=seed,method=method,game=game,ply=ply,root_fen=env.board.fen(),weights_before=snapshot,weights_after=list(m.weights),complete=r.complete,action=None if r.action is None else r.action.uci(),value=r.value,pv_phi=r.pv_phi,pv_terminal=r.pv_terminal,prediction=pred,gradient=grad,samples=samples,update=stats,nodes=r.nodes,total_nodes=used,seconds=r.seconds,reason=r.reason,effective_node_limit=node_limit,effective_wall_limit=wall_limit,global_remaining_before_query=seconds)
     df.write(json.dumps(row,separators=(',',':'))+'\n');df.flush()
     if not r.complete:reason='SEARCH_RESOURCE_UNKNOWN';break
     assert r.action is not None;env.push(r.action)
    actual=env.terminal()
    if actual is not None:outcome=actual;reason='ACTUAL_TERMINAL'
    stats=td.finish(m,outcome)if method=='td'else dict(samples=sample_count,active=active_count,loss=loss_sum/max(1,sample_count),changed=bool(changes),query_updates=changes,censored=outcome is None)
    label='U'if outcome is None else'D'if outcome==0 else'W'if outcome==1 else'L';totals[label]=totals.get(label,0)+1
    row=dict(seed=seed,method=method,game=game,initial_weights=before,weights=list(m.weights),initial_record=prefix,record=env.record(),outcome=outcome,ending=reason,nodes=used-begin_nodes,total_nodes=used,searches=searches-decision_start,stats=stats,seconds=time.perf_counter()-start);games.append(row);gf.write(json.dumps(row,separators=(',',':'))+'\n');gf.flush()
    checkpoints.append(dict(nodes=used,game=game,weights=list(m.weights),seconds=row['seconds']))
    if status!='COMPLETE':break
   result=dict(seed=seed,method=method,initial=initial,weights=list(m.weights),nodes=used,searches=searches,games=len(games),outcomes=totals,samples=sum(g['stats']['samples']for g in games),nonzero_episode_updates=sum(g['stats']['changed']for g in games),seconds=time.perf_counter()-start,checkpoints=checkpoints,cause='GLOBAL_CAP'if status!='COMPLETE'else'TOTAL_NODES'if used==p['nodes_per_arm']else'MAX_GAMES');results.append(result);print(json.dumps({k:v for k,v in result.items()if k!='checkpoints'}),flush=True)
   if status!='COMPLETE':break
 result=dict(status=status,arms=results,expected_arms=len(p['arms']),seconds=time.perf_counter()-began,nodes=sum(a['nodes']for a in results),scope=p['scope']);(OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='arms'}))
if __name__=='__main__':run()
