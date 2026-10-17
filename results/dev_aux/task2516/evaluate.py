"""Common deployment; frozen fresh endpoint and midpoint panels, shared baseline."""
from pathlib import Path
import json,random,time,hashlib,datetime,sys
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2492.learning import Model
from results.dev_aux.task2492.adapters import ChessEnv
from results.dev_aux.task2392.reader import SharedDeleteStopReader
BASE=Path('results/dev_aux/task2516')
def run(panel):
 p=json.loads((BASE/'plan.json').read_text());cfg=p['panels'][panel];out=BASE/panel;out.mkdir(exist_ok=True);assert not(out/'started.json').exists()
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 train=json.loads(Path(p['training']).read_text());assert train['status']=='COMPLETE'and len(train['arms'])==8;arms={(a['seed'],a['method']):a for a in train['arms']};snapshots=[];weights={}
 for seed in p['seeds']:
  assert arms[(seed,'td')]['initial']==arms[(seed,'tree')]['initial'];weights[(seed,'initial')]=arms[(seed,'td')]['initial']
  for method in('td','tree'):
   a=arms[(seed,method)];w=a['weights'];actual=a['nodes'];game=a['checkpoints'][-1]['game']
   if cfg['checkpoint']<p['training_ceiling']:
    w=a['initial'];actual=0;game=None
    for c in a['checkpoints']:
     if c['nodes']<=cfg['checkpoint']:w=c['weights'];actual=c['nodes'];game=c['game']
   weights[(seed,method)]=w;snapshots.append(dict(seed=seed,method=method,weights=w,target_nodes=cfg['checkpoint'],actual_closed_episode_nodes=actual,game=game))
 (out/'weights.json').write_text(json.dumps(snapshots,indent=2));stop=SharedDeleteStopReader(Path.cwd());stop();start=time.perf_counter();rows=[];status='COMPLETE'
 (out/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=hashlib.sha256((BASE/'plan.json').read_bytes()).hexdigest(),training_sha=hashlib.sha256(Path(p['training']).read_bytes()).hexdigest(),weights_sha=hashlib.sha256((out/'weights.json').read_bytes()).hexdigest())))
 with(out/'games.jsonl').open('x')as gf,(out/'queries.jsonl').open('x')as qf:
  for slot in cfg['slots']:
   seed,family,color,treatment=slot;w=weights[(seed,treatment)];candidate=Model(w);foe=Model(p['foe_weights']);env=ChessEnv();rng=random.Random(family)
   for _ in range(p['opening_plies']):
    if env.terminal()is not None:break
    env.push(rng.choice(sorted(env.actions(),key=lambda a:a.uci())))
   prefix=env.record();nodes=0;outcome=None;reason='HORIZON_UNKNOWN';game_start=time.perf_counter();queries=0
   for ply in range(p['H']):
    stop();outcome=env.terminal()
    if outcome is not None:reason='ACTUAL_TERMINAL';break
    left=cfg['cap_seconds']-(time.perf_counter()-start)
    if left<=0:reason='GLOBAL_CAP_UNKNOWN';status='PARTIAL_CAP';break
    seconds=min(p['seconds_per_query'],left);model=candidate if env.player()==color else foe;r=TrainingSearch(p['depth'],quiet=False).search(env,model,nodes=p['nodes_per_query'],seconds=seconds,seed=family*10000+ply+p['ordering_seed_offset'],cancel=stop);nodes+=r.nodes;queries+=1
    qf.write(json.dumps(dict(slot=slot,ply=ply,root_fen=env.board.fen(),effective_node_limit=p['nodes_per_query'],effective_wall_limit=seconds,global_remaining_before_query=left,nodes=r.nodes,seconds=r.seconds,reason=r.reason,complete=r.complete,action=None if r.action is None else r.action.uci(),value=r.value),separators=(',',':'))+'\n');qf.flush()
    if not r.complete:reason='SEARCH_LIMIT_UNKNOWN';break
    assert r.action is not None;env.push(r.action)
   actual=env.terminal()
   if actual is not None:outcome=actual;reason='ACTUAL_TERMINAL'
   reward=None if outcome is None else outcome*(1 if color==0 else-1);row=dict(seed=seed,family=family,color=color,treatment=treatment,weights=w,initial_record=prefix,record=env.record(),reward=reward,ending=reason,nodes=nodes,queries=queries,seconds=time.perf_counter()-game_start);rows.append(row);gf.write(json.dumps(row,separators=(',',':'))+'\n');gf.flush()
   if len(rows)%32==0:print(json.dumps(dict(panel=panel,games=len(rows),seconds=time.perf_counter()-start)),flush=True)
   if status!='COMPLETE':break
 summaries=[]
 for seed in p['seeds']:
  tallies={}
  for t in('initial','td','tree'):
   rr=[r for r in rows if r['seed']==seed and r['treatment']==t];tallies[t]={k:sum(r['reward']==v for r in rr)for k,v in [('W',1),('L',-1),('D',0),('U',None)]}
  summaries.append(dict(seed=seed,tallies=tallies))
 result=dict(status=status,panel=panel,expected=len(cfg['slots']),actual=len(rows),nodes=sum(r['nodes']for r in rows),queries=sum(r['queries']for r in rows),seconds=time.perf_counter()-start,results=summaries,scope=p['scope']);(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run(sys.argv[1])
