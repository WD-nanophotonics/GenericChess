"""Matchedcoveredking learning, fixedopponentdistribution, allendsbeforeheldout."""
import json,math,time,sys,importlib.util,hashlib,datetime
from pathlib import Path
import chess,random
R=Path.cwd();O=R/'results/dev_aux/task187'
s=importlib.util.spec_from_file_location('Pilot157for160',R/'results/dev_aux/task157/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A;G=P.G
s=importlib.util.spec_from_file_location('E160',R/'results/dev_aux/task108/evolution.py');E=importlib.util.module_from_spec(s);s.loader.exec_module(E)
D=json.loads((O/'declaration.json').read_bytes())
def execute():
 def stop():
  for root in (R,R.parent/'GenericChess 2'):
   for name in ('rollout','advisor','slack'):
    p=root/f'.local_agent/{name}.json'
    for attempt in range(3):
     try:
      v=json.loads(p.read_bytes())
      if v.get('user_paused') or v.get('stopped'):raise A.PersistentStop('persistentstop:'+str(p))
      break
     except (json.JSONDecodeError,OSError):
      if attempt==2:raise
      time.sleep(.05)
 stop();binary=R/'.local_agent/alignment-order/fairy-order-toggle.exe';assert hashlib.sha256(binary.read_bytes()).hexdigest()==D['binary_sha256']
 if (O/'events.jsonl').exists():raise FileExistsError('frozenbatchcannotrerun')
 started=time.monotonic();deadline=started+D['deadline_seconds'];j=A.Journal(O/'events.jsonl');calls=[];runs=[];e=None
 def block(w,seed,opponent,sweep,k,arm,phase):
  nonlocal e
  rewards=[];roots=D['train_roots' if phase=='train' else 'heldout_roots']
  try:
   e=M.start(binary,3,deadline,stop)
   for oi,fixture in enumerate(roots):
    for color in (True,False):
     A.guard(deadline,stop);probes,ack=M.configure(e,w,O/'variant.ini',deadline,stop)
     fen=fixture['initial_fen'];b=chess.Board(fen)
     for prelude in fixture['history']:b.push_uci(prelude)
     assert b.fen()==fixture['expected_fen'];random_seed=(2026500000+(sweep*4+k)*8+oi) if phase=='train' else 2026600000+oi;rng=random.Random(random_seed)
     name=f's{seed}-{opponent}-{phase}-g{sweep}-k{k}-a{arm}-o{oi}-c{int(color)}';context=dict(name=name,start_seed=seed,opponent=opponent,phase=phase,sweep=sweep,coordinate=k,arm=arm,root_index=oi,agent_color=color,random_seed=random_seed)
     moves=[];searches=[];oppo=[]
     j.record('game_start',context=context,root_fen=fen,weights=w,price_probes=probes,table_ack=ack)
     for ply in range(16):
      A.guard(deadline,stop)
      if b.is_game_over(claim_draw=False):break
      if b.turn==color:move,meta=M.M.search(e,b.copy(stack=True),deadline,stop);searches.append(meta)
      elif opponent.startswith('random'):move=rng.choice(sorted(b.legal_moves,key=lambda m:m.uci()))
      else:move,meta=P.unit2ply(b.copy(stack=True),deadline,stop);oppo.append(meta)
      assert move in b.legal_moves;b.push(move);moves.append(move.uci())
      j.record('after_move',name=name,ply=ply,move=move.uci(),fen=b.fen())
     score=G.score(b,color,len(moves),16); out=b.outcome(claim_draw=False); bounded=(0 if out.winner is None else (1 if out.winner==color else -1)) if out else score['quantity_difference']/15; reward=bounded if opponent.endswith('bounded') else score['reward']; result=dict(root_fen=fen,opening_history=fixture['history'],opening_fen=fixture['expected_fen'],actions=moves,search_records=searches,opponent_records=oppo,final_fen=b.fen(),score=score,original_reward=score['reward'],bounded_reward=bounded,objective=opponent,reward=reward,price_probes=probes,table_ack=ack)
     calls.append(dict(context=context,weights=dict(w),result=result));rewards.append(result['reward']);j.record('game_end',context=context,result=result)
     if len(calls)%48==0:
      A.atomic_json(O/'progress.json',dict(slots=len(calls),seconds=time.monotonic()-started,current=name))
      print(json.dumps(dict(slots=len(calls),seconds=round(time.monotonic()-started,3))),flush=True)
  finally:
   if e:e.close();e=None
  return rewards
 try:
  for seed,opponent in D['method_order']:
   theta=E.starts(seed);run=dict(seed=seed,opponent=opponent,initial_weights=E.weights(theta),updates=[],heldout=[]);runs.append(run)
   for sweep,step in enumerate(D['steps']):
    for k in range(4):
     candidates=[theta[:],theta[:],theta[:]];candidates[1][k]=min(E.HIGH,theta[k]+step);candidates[2][k]=max(E.LOW,theta[k]-step)
     groups=[block(E.weights(t),seed,opponent,sweep,k,a,'train') for a,t in enumerate(candidates)];means=[sum(z)/len(z) for z in groups];integer_sums=[sum(round(v*240) for v in group) for group in groups]; chosen=E.select(integer_sums);before=E.weights(theta);theta=candidates[chosen][:]
     run['updates'].append(dict(sweep=sweep,coordinate=E.TYPES[k],step=step,before=before,candidate_weights=[E.weights(t) for t in candidates],means=means,integer_sums_240=integer_sums,rewards=groups,selected=chosen,after=E.weights(theta)))
   run['final_weights']=E.weights(theta);run['endpoint_frozen_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
   A.atomic_json(O/'endpoints_partial.json',dict(complete=False,ends=[{k:r[k] for k in ('seed','opponent','initial_weights','final_weights','endpoint_frozen_at')} for r in runs if 'final_weights' in r]))
  frozen=datetime.datetime.now(datetime.timezone.utc).isoformat();A.atomic_json(O/'endpoints.json',dict(complete=True,all_endpoints_frozen_at=frozen,training_calls=len(calls),ends=[{k:r[k] for k in ('seed','opponent','initial_weights','final_weights','endpoint_frozen_at')} for r in runs]))
  for run in runs:
   for arm in ('initial','final'):
    rewards=block(run[arm+'_weights'],run['seed'],run['opponent'],0,0,arm,'heldout')
    run['heldout'] += [dict(arm=arm,opening_index=i//2,color=i%2==0,reward=value) for i,value in enumerate(rewards)]
  status='COMPLETE'
 except BaseException as ex:status='INTERRUPTED';error=type(ex).__name__+': '+str(ex)
 finally:
  if e:e.close()
  j.close()
 out=dict(completed=status=='COMPLETE',runs=runs,calls=calls,global_endpoint_freeze_at=locals().get('frozen'),scope='Matchedfixedagentbudget, changedobjective on fulllegal reachable roots; noequalcostsearchstrength oruniversalpriceclaim.')
 if status!='COMPLETE':out['error']=error
 A.atomic_json(O/'controller.json',out);summary=dict(status=status,slots=len(calls),actual_games=len(calls),train_games=sum(c['context']['phase']=='train' for c in calls),heldout_games=sum(c['context']['phase']=='heldout' for c in calls),wall_seconds=time.monotonic()-started,hard_seconds=D['deadline_seconds'],binary_sha256=D['binary_sha256'],cap=16,allends_beforeheldout=locals().get('frozen') is not None,nohumanfit=True)
 if status!='COMPLETE':summary['error']=error
 A.atomic_json(O/'status.json',summary);print(json.dumps(summary));return 0 if status=='COMPLETE' else 3
if __name__=='__main__':sys.exit(execute())
