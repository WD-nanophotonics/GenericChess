"""Independent forward-view TD credit and actual move-event replay; no search."""
from pathlib import Path
from collections import defaultdict,Counter
from math import tanh,isclose,isfinite
import json,hashlib,random,chess
OUT=Path('results/dev_aux/task2508')
def rows(p):return[json.loads(x)for x in Path(p).read_text().splitlines()]
def run():
 base=Path('results/dev_aux/task2506');plan=json.loads((base/'plan.json').read_text());done=json.loads((base/'result.json').read_text());episodes=rows(base/'episodes.jsonl');decisions=rows(base/'decisions.jsonl');events=rows(base/'events.jsonl');by=defaultdict(list);evs=defaultdict(list);counts=Counter();arms=defaultdict(list);curves=[]
 for n,h in plan['pins'].items():assert hashlib.sha256(Path(n).read_bytes()).hexdigest()==h,n
 for d in decisions:by[(d['seed'],d['quiet'],d['game'])].append(d)
 for e in events:evs[(e['seed'],e['quiet'],e['game'])].append(e)
 current={};node_total=Counter()
 for ep in episodes:
  key=(ep['seed'],ep['quiet'],ep['game']);arm=key[:2];rr=by[key];ee=evs[key];assert ee[0]['kind']=='START'and ee[-1]['kind']=='END';assert ee[0]['initial_record']==ep['initial_record']and ee[0]['weights']==ep['initial_weights'];assert ee[-1]['outcome']==ep['outcome']and ee[-1]['ending']==ep['ending']
  if arm not in current:
   rng=random.Random(arm[0]);current[arm]=[1.]+[rng.uniform(.5,1.5)for _ in range(4)]
  assert current[arm]==ep['initial_weights'];weights=current[arm];b=chess.Board(ep['initial_record']['initial'])
  for u in ep['initial_record']['moves']:
   m=chess.Move.from_uci(u);assert m in b.legal_moves;b.push(m);counts['legal_prefix_moves']+=1
  moves=[e for e in ee if e['kind']=='MOVE'];assert len(rr)==ep['searches'];assert len(moves)==sum(d['complete']for d in rr)
  predictions=[];gradients=[]
  for i,d in enumerate(rr):
   assert d['ply']==i and d['root_fen']==b.fen();assert d['nodes']<=8192;node_total[arm]+=d['nodes'];assert node_total[arm]==d['total_nodes'];counts['queries']+=1
   if not d['complete']:
    assert i==len(rr)-1 and all(d[k]is None for k in('action','value','pv_phi','prediction','gradient'));counts['failed_queries']+=1;continue
   value=d['value'];terminal=d['pv_terminal'];phi=d['pv_phi'];assert isfinite(value)
   if terminal:assert phi is None and value in(-1000000.,0.,1000000.);grad=[0.]*5;counts['terminal_search_targets']+=1
   else:
    assert value==sum(x*w for x,w in zip(phi,weights));v=tanh(value/10.);grad=[0. if j==0 else x*(1-v*v)/10. for j,x in enumerate(phi)]
   pred=tanh(value/10.);assert pred==d['prediction'];assert all(isclose(x,y,rel_tol=1e-12,abs_tol=1e-13)for x,y in zip(grad,d['gradient']));predictions.append(pred);gradients.append(grad)
   me=moves[i];assert me['ply']==i and me['action']==d['action'];m=chess.Move.from_uci(me['action']);assert m in b.legal_moves;b.push(m);assert me['after_fen']==b.fen();counts['legal_training_moves']+=1
   if d['stats']['q_truncated_leaf_labels']:counts['queries_with_explicit_qcut']+=1
  assert b.fen()==ep['record']['fen']and[m.uci()for m in b.move_stack]==ep['record']['moves'];o=b.outcome(claim_draw=True);outcome=None if o is None else 0 if o.winner is None else 1 if o.winner else-1
  assert outcome==ep['outcome'];counts['episodes']+=1;counts['censored_episodes']+=outcome is None;counts['actual_terminal_episodes']+=outcome is not None
  n=len(predictions);errors=[predictions[i+1]-predictions[i]for i in range(max(0,n-1))]
  if n and outcome is not None:errors.append(float(outcome)-predictions[-1])
  # Independent FORWARD lambda-return sum, via backward scalar recurrence;
  # production uses accumulated vector eligibility. Same fixed game snapshot.
  credit=[0.]*5;future=0.
  for i in reversed(range(n)):
   error=errors[i]if i<len(errors)else 0.;future=error+plan['lambda']*future
   for j,g in enumerate(gradients[i]):credit[j]+=g*future
  expected=[w+plan['eta']*d for w,d in zip(weights,credit)];expected[0]=1.
  assert all(isclose(a,b,rel_tol=1e-11,abs_tol=1e-12)for a,b in zip(expected,ep['weights']));assert ep['weights'][0]==1.
  assert ep['stats']['samples']==len(errors);loss=sum(e*e/2 for e in errors)/max(1,len(errors));assert isclose(loss,ep['stats']['loss'],rel_tol=1e-12,abs_tol=1e-14)
  assert ep['stats']['censored']==(outcome is None);counts['td_terms']+=len(errors);counts['nonzero_episode_updates']+=ep['stats']['changed'];counts['nonzero_TD_errors']+=sum(e!=0 for e in errors);counts['TD_errors_abs_gt_1e_8']+=sum(abs(e)>1e-8 for e in errors);counts['actual_parameter_change_steps']+=any(a!=b for a,b in zip(weights,ep['weights']))
  current[arm]=ep['weights'];arms[arm].append(ep);curves.append(dict(seed=arm[0],quiet=arm[1],game=ep['game'],nodes=node_total[arm],weights=ep['weights'],loss=loss,td_terms=len(errors),nonzero_errors=sum(e!=0 for e in errors),actual_outcome=outcome,changed=ep['stats']['changed']))
 assert set(by)==set(evs)=={(e['seed'],e['quiet'],e['game'])for e in episodes}
 summary=[]
 for a in done['arms']:
  key=(a['seed'],a['quiet']);assert node_total[key]==a['nodes']<=plan['nodes_per_arm'];assert current[key]==a['weights'];assert len(arms[key])==a['games'];ds=[d for d in decisions if(d['seed'],d['quiet'])==key]
  summary.append(dict(**a,failed_queries=sum(not d['complete']for d in ds),failed_query_nodes=sum(d['nodes']for d in ds if not d['complete']),qcut_leaf_targets=sum(d['stats']['q_truncated_leaf_labels']for d in ds),qcap_still_tactical=sum(d['stats'].get('q_cap_still_tactical',0)for d in ds),terminal_search_targets=sum(d['stats']['actual_terminal_nodes']for d in ds),mean_nodes_per_query=a['nodes']/max(1,len(ds))))
 result=dict(status='PASS_INDEPENDENT_FORWARD_TD_AND_ALL_ACTUAL_TRAINING_EVENTS',counts=dict(counts),arms=summary,curves=curves,scope='Everycompleted episode weight update recomputed by independent forward lambda sum of saved PV gradients/predictions, legalactual moves/events reconstructed with python-chess. Searchleafvalue/gradient match saved receipt, not all internal hypothetical branches replayed. Same library rules, not independent engine strength. All U/failednodes retained.')
 (OUT/'training-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('arms','curves')}))
if __name__=='__main__':run()
