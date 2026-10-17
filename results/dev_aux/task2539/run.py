"""Paid fixed-opponent operational TD/WDL comparison; full typed rule authority."""
from pathlib import Path
from collections import Counter
import json,random,time,hashlib,datetime
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from results.dev_aux.task2525.run import RecordedSessionEnv,replay_bound
from results.dev_aux.task2532.free_model import FreeModel
from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2392.reader import SharedDeleteStopReader
D=Path('results/dev_aux/task2539')
CHANNELS=(('board','P'),('board','A'),('board','X'),('hand','A'),('hand','P'),('hand','X'))
def interval(row):
 return(-1,1)if row is None or row['reward']is None else(row['reward'],row['reward'])
def proposal(index,seed,p):
 cycle,slot=divmod(index,12);moves=[(j,sign*p['grid_step'])for j in range(6)for sign in(-1,1)];random.Random(p['proposal_order_seed']+seed+cycle*1000000).shuffle(moves);return moves[slot]
def run():
 assert not(D/'started.json').exists();p=json.loads((D/'plan.json').read_text());s=json.loads(Path('.local_agent/session.json').read_text());assert s['id']==p['session_id']and s['state']=='active'
 paths=[D/'run.py',D/'plan.json',Path('results/dev_aux/task2492/episode.py'),Path('results/dev_aux/task2492/learning.py'),Path('results/dev_aux/task2532/free_model.py'),Path('results/dev_aux/task2504/search.py'),Path('results/dev_aux/task2525/run.py'),Path('results/dev_aux/task2511/generic.py')]+[Path(f'results/dev_aux/task2525/rules-{g}.json')for g in p['generator_seeds']]
 (D/'pins.json').write_text(json.dumps(dict(pins={x.as_posix():hashlib.sha256(x.read_bytes()).hexdigest()for x in paths}),indent=2));(D/'started.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=hashlib.sha256((D/'plan.json').read_bytes()).hexdigest())))
 stop=SharedDeleteStopReader(Path.cwd());stop();began=time.perf_counter();arms=[];counts=Counter();status='COMPLETE';gid=0
 with(D/'queries.jsonl').open('x')as qf,(D/'games.jsonl').open('x')as gf,(D/'updates.jsonl').open('x')as uf:
  for gs in p['generator_seeds']:
   cc=compile_ruleset(ruleset_from_dict(json.loads(Path(f'results/dev_aux/task2525/rules-{gs}.json').read_text())))
   for method,seed in p['arms_order']:
    if time.perf_counter()-began>=p['cap_seconds']:status='PARTIAL_CAP';break
    rng=random.Random(seed);initial=[1.]+[rng.uniform(.5,1.5)for _ in range(5)];model=FreeModel(initial);used=0;games=0;updates=0;blocks=0;armbegan=time.perf_counter();foe=FreeModel(p['foe'])
    def play(weights,family,color,treatment,block):
     nonlocal used,games,gid
     gid+=1;gameid=gid;gamebegan=time.perf_counter();m=FreeModel(weights);env=RecordedSessionEnv(GameSession(cc),CHANNELS);rr=random.Random(gs*1000000+family)
     for _ in range(p['prefix_plies']):
      if env.terminal()is not None:break
      env.push(rr.choice(sorted(env.actions(),key=repr)))
     prefix=env.record();td=TDLeafEpisode(p['eta'],p['lam']);before_nodes=used;nq=0;ending='HORIZON_UNKNOWN';observed=0
     for ply in range(p['H']):
      stop()
      if env.terminal()is not None:ending='ACTUAL_TERMINAL';break
      left=p['nodes_per_arm']-used;wall=p['cap_seconds']-(time.perf_counter()-began)
      if left<=0 or wall<=0:ending='AGGREGATE_CAP_UNKNOWN';break
      actor=env.player();current=m if actor==color else foe;record=env.record();state=env.session.state;limit=min(left,p['nodes_per_query']);seconds=min(wall,p['seconds_per_query']);orderseed=gs*100000000+family*1000+ply+p['ordering_seed_offset']
      r=TrainingSearch(p['depth'],quiet=False).search(env,current,nodes=limit,seconds=seconds,seed=orderseed,cancel=stop);used+=r.nodes;nq+=1;assert env.record()==record and env.session.state==state
      observe=method=='TD'and actor==color and r.complete
      if observe:td.observe(m,r);observed+=1
      if r.complete:env.push(r.action)
      q=dict(gameid=gameid,generator_seed=gs,method=method,seed=seed,family=family,color=color,treatment=treatment,block=block,ply=ply,actor=actor,weights=list(current.weights),record_before=record,record_after=env.record(),complete=r.complete,observed_by_TD=observe,value=r.value,pv_phi=r.pv_phi,pv_terminal=r.pv_terminal,nodes=r.nodes,total_nodes=used,seconds=r.seconds,effective_nodes=limit,effective_seconds=seconds,reason=r.reason,ordering_seed=orderseed)
      qf.write(json.dumps(q,separators=(',',':'))+'\n');qf.flush()
      if not r.complete:ending='SEARCH_RESOURCE_UNKNOWN';break
     actual=env.terminal()
     if actual is not None:ending='ACTUAL_TERMINAL'
     replay_bound(env);stats=td.finish(m,actual)if method=='TD'else None
     row=dict(gameid=gameid,generator_seed=gs,method=method,seed=seed,family=family,color=color,treatment=treatment,block=block,initial_weights=list(weights),after_TD_weights=list(m.weights),stats=stats,initial_record=prefix,record=env.record(),channels=CHANNELS,outcome=actual,reward=None if actual is None else actual*(1 if color==0 else-1),ending=ending,nodes=used-before_nodes,total_nodes=used,queries=nq,observed=observed,seconds=time.perf_counter()-gamebegan)
     gf.write(json.dumps(row,separators=(',',':'))+'\n');gf.flush();games+=1;counts['games']+=1;counts['actual_terminal']+=actual is not None;counts['unknown']+=actual is None;counts['queries']+=nq;counts['observed']+=observed
     return row
    if method=='TD':
     for i in range(p['max_games']):
      if used>=p['nodes_per_arm']or time.perf_counter()-began>=p['cap_seconds']:break
      before=list(model.weights);row=play(before,p['training_family_offset']+i//2,i%2,'TD',i);model=FreeModel(row['after_TD_weights']);updates+=before!=model.weights
      uf.write(json.dumps(dict(generator_seed=gs,method=method,seed=seed,index=i,nodes=used,before=before,after=list(model.weights),gameids=[row['gameid']],changed=before!=model.weights),separators=(',',':'))+'\n');uf.flush()
    else:
     for block in range(p['max_blocks']):
      if used>=p['nodes_per_arm']or time.perf_counter()-began>=p['cap_seconds']:break
      before=list(model.weights);j,delta=proposal(block,seed,p);candidate=list(before);candidate[j]+=delta;rows={};slots=[]
      for f in range(p['pairs_per_proposal']):
       for color in(0,1):
        for treatment in(('current','proposal')if(block+f+color)%2==0 else('proposal','current')):slots.append((p['training_family_offset']+block*p['pairs_per_proposal']+f,color,treatment))
      for family,color,treatment in slots:
       if used>=p['nodes_per_arm']or time.perf_counter()-began>=p['cap_seconds']:break
       rows[family,color,treatment]=play(before if treatment=='current'else candidate,family,color,treatment,block)
      lo=hi=0
      for f in range(p['pairs_per_proposal']):
       family=p['training_family_offset']+block*p['pairs_per_proposal']+f
       for color in(0,1):
        aa=interval(rows.get((family,color,'current')));bb=interval(rows.get((family,color,'proposal')));lo+=bb[0]-aa[1];hi+=bb[1]-aa[0]
      den=2*p['pairs_per_proposal'];accepted=lo>0
      if accepted:model=FreeModel(candidate);updates+=1
      rec=dict(generator_seed=gs,method=method,seed=seed,index=block,nodes=used,before=before,proposal=candidate,coordinate=j,delta=delta,after=list(model.weights),gameids=[r['gameid']for r in rows.values()],expected_games=len(slots),actual_games=len(rows),missing=len(slots)-len(rows),bounds=[lo/den,hi/den],changed=accepted)
      uf.write(json.dumps(rec,separators=(',',':'))+'\n');uf.flush();blocks+=1
    arm=dict(generator_seed=gs,method=method,seed=seed,channels=CHANNELS,initial=initial,weights=list(model.weights),nodes=used,games=games,updates=updates,blocks=blocks,seconds=time.perf_counter()-armbegan,cause='TOTAL_NODES'if used==p['nodes_per_arm']else'GLOBAL_CAP'if time.perf_counter()-began>=p['cap_seconds']else'MAX_GAMES_OR_BLOCKS');arms.append(arm);print(json.dumps(arm),flush=True)
    if time.perf_counter()-began>=p['cap_seconds']:status='PARTIAL_CAP';break
   if status!='COMPLETE':break
 result=dict(status=status,expected_arms=32,arms=arms,nodes=sum(a['nodes']for a in arms),seconds=time.perf_counter()-began,counts=dict(counts),scope=p['scope']);(D/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='arms'}))
if __name__=='__main__':run()
