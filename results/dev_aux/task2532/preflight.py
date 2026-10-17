"""Real recorded-episode six-coordinate preflight; no newfitness/trainingcampaign."""
from pathlib import Path
from math import tanh,isclose
import json,hashlib,time,datetime
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2492.learning import Model,Receipt
from results.dev_aux.task2492.episode import TDLeafEpisode
from results.dev_aux.task2504.search import TrainingSearch
from results.dev_aux.task2525.run import RecordedSessionEnv
from results.dev_aux.task2529.training_audit import terminal
from results.dev_aux.task2532.free_model import FreeModel
from results.dev_aux.task2392.reader import SharedDeleteStopReader
D=Path('results/dev_aux/task2532');O=Path('results/dev_aux/task2529');T=Path('results/dev_aux/task2527')
def near(x,y):return isclose(x,y,rel_tol=1e-8,abs_tol=1e-9)
def run(*,replay=False,stop_root=None):
 began=time.perf_counter();p=json.loads((D/'preflight-plan.json').read_text());stop=SharedDeleteStopReader(Path.cwd()if stop_root is None else Path(stop_root));stop()
 for n,h in p['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 marker=D/'preflight-started.json'
 if not replay:
  assert not marker.exists();marker.write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha256=hashlib.sha256((D/'preflight-plan.json').read_bytes()).hexdigest())))
 else:assert json.loads(marker.read_text())['plan_sha256']==hashlib.sha256((D/'preflight-plan.json').read_bytes()).hexdigest()
 def queries():
  with(T/'queries.jsonl').open()as f:
   for line in f:yield json.loads(line)
 it=iter(queries());q=next(it,None);selected=None
 for line in(T/'episodes.jsonl').open():
  e=json.loads(line);key=e['generator_seed'],e['seed'],e['game'];rr=[]
  while q is not None and(q['generator_seed'],q['seed'],q['game'])==key:rr.append(q);q=next(it,None)
  if e['outcome']is not None and any(r['complete']and not r['pv_terminal']and r['pv_phi'][0]!=0 for r in rr):selected=e,rr;break
 assert selected is not None;e,rr=selected;gs=e['generator_seed'];cc=compile_ruleset(ruleset_from_dict(json.loads((T/f'rules-{gs}.json').read_text())));w=e['initial_weights'];free=FreeModel(w);fixed=Model(w);assert free.weights==fixed.weights==w
 chosen=next(r for r in rr if r['complete']and not r['pv_terminal']and r['pv_phi'][0]!=0);phi=chosen['pv_phi'];analytic=free.gradient(phi);numerical=[]
 for j in range(6):
  plus=list(w);minus=list(w);plus[j]+=p['gradient_h'];minus[j]-=p['gradient_h'];numeric=(FreeModel(plus).prediction(phi)-FreeModel(minus).prediction(phi))/(2*p['gradient_h']);assert near(numeric,analytic[j]);numerical.append(numeric)
 assert analytic[0]!=0 and fixed.gradient(phi)[0]==0
 clone=FreeModel(w);clone.apply([.125,0,0,0,0,0]);assert clone.weights==[w[0]+.125]+w[1:]
 tp=json.loads((T/'registration.json').read_text());a=TDLeafEpisode(tp['eta'],tp['lambda']);b=TDLeafEpisode(tp['eta'],tp['lambda']);preds=[];grads=[];previous=e['initial_record'];session=GameSession.replay(cc,deserialize_game_record(json.dumps(previous)))
 for r in rr:
  assert r['record_before']==previous and r['weights']==w and r['complete'];record=deserialize_game_record(json.dumps(r['record_after']));assert record.actions[:-1]==session.to_record().actions;session.submit(record.actions[-1]);assert session.to_record()==record;previous=r['record_after'];v=tanh(r['value']/10);g=[0.]*6 if r['pv_terminal']else[x*(1-v*v)/10 for x in r['pv_phi']];receipt=Receipt(record.actions[-1],r['value'],None if r['pv_phi']is None else tuple(r['pv_phi']),r['pv_terminal'],(),r['nodes'],True,0,0.,'complete');a.observe(free,receipt);b.observe(fixed,receipt);preds.append(v);grads.append(g)
 actual=terminal(session);assert actual==e['outcome']and previous==e['record'];public=GameSession.replay(cc,deserialize_game_record(json.dumps(e['record'])));assert public.state==session.state and public.result==session.result
 stats=a.finish(free,actual);fixedstats=b.finish(fixed,actual);errors=[preds[i+1]-preds[i]for i in range(len(preds)-1)]+[actual-preds[-1]];future=0.;delta=[0.]*6
 for i in reversed(range(len(preds))):
  future=errors[i]+tp['lambda']*future;delta=[x+future*y for x,y in zip(delta,grads[i])]
 assert all(near(x,y+tp['eta']*z)for x,y,z in zip(free.weights,w,delta));assert fixed.weights==e['weights']and all(near(x,y)for x,y in zip(free.weights[1:],fixed.weights[1:]))
 root=GameSession.replay(cc,deserialize_game_record(json.dumps(rr[0]['record_before'])));env=RecordedSessionEnv(root,e['channels']);before=env.record();seed=gs*100000000+e['seed']+e['game']*1000+rr[0]['ply']+90100000;search=TrainingSearch(2,quiet=False);one=search.search(env,Model(w),nodes=p['search_nodes'],seconds=p['search_seconds'],seed=seed,cancel=stop);two=search.search(env,FreeModel(w),nodes=p['search_nodes'],seconds=p['search_seconds'],seed=seed,cancel=stop);assert one.complete and two.complete and env.record()==before;assert(one.action,one.value,one.pv_phi,one.pv_terminal,one.nodes)==(two.action,two.value,two.pv_phi,two.pv_terminal,two.nodes);env.push(one.action);assert env.record()==rr[0]['record_after']
 out=dict(status='PASS_REAL_EPISODE_ALL6_GRADIENT_APPLY_CREDIT_AND_IDENTICAL_INITIAL_SEARCH',source_episode=dict(generator_seed=gs,seed=e['seed'],game=e['game'],queries=len(rr),actual_terminal=actual,fullrecord_sha256=hashlib.sha256(json.dumps(e['record'],sort_keys=True).encode()).hexdigest()),all6_finite_difference=dict(phi=phi,analytic=list(analytic),numerical=numerical,old_fixed_P_gradient=0.),old_fixed_update_exact=True,raw_P_before=w[0],raw_P_after_free_episode=free.weights[0],P_changed=free.weights[0]!=w[0],new_free_weights=free.weights,actual_search_queries=2,actual_search_nodes=one.nodes+two.nodes,source_record_replay_plies=len(session.to_record().actions),scope=p['scope']+' Oldrecordedtargets/selectedPV/contiguousactualoutcome are re-differentiated withSAMEweights; NOTnewselfplayrollouts ornewfitness. AdditionaltwoD2queries areAPIcompatibility ONLY. No sign-benefit/wholetraining/controlwinner claim.',seconds=time.perf_counter()-began);(O/'free-model-preflight.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
