"""Scopedrootstudent frozen-searchbootstrap: correctsemigradient, no PVleaf assumption."""
import json,math,time,random,hashlib,datetime,importlib.util,sys
from pathlib import Path
import chess,numpy as np
R=Path.cwd();O=R/'results/dev_aux/task214';D=json.loads((O/'declaration.json').read_bytes())
s=importlib.util.spec_from_file_location('P214',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A;G=P.G
s=importlib.util.spec_from_file_location('E214',R/'results/dev_aux/task108/evolution.py');E=importlib.util.module_from_spec(s);s.loader.exec_module(E)
def read_value(meta):
 lines=[s for s in meta['uci_info'] if ' score ' in s and ' pv ' in s and 'lowerbound' not in s and 'upperbound' not in s]
 if not lines:return None
 f=lines[-1].split();i=f.index('score');kind=f[i+1];v=int(f[i+2]);
 if kind=='mate' and v==0:return None
 return dict(kind=kind,raw=v,bounded=math.tanh(v/400) if kind=='cp' else (1 if v>0 else -1),line=lines[-1])
def student(theta,phi):
 ratios=np.exp(theta);value=math.tanh((phi[0]+np.dot(phi[1:],ratios))/4);grad=(1-value*value)/4*np.asarray(phi[1:])*ratios;return value,grad

def execute():
 assert not (O/'events.jsonl').exists();P.stop();binary=R/'.local_agent/alignment-order/fairy-order-toggle.exe';assert hashlib.sha256(binary.read_bytes()).hexdigest()==D['binary_sha256'];start=time.monotonic();deadline=start+D['deadline_seconds'];j=A.Journal(O/'events.jsonl');calls=[];runs=[];training_freeze=None
 def block(w,seed,mode,round_,phase,opponent):
  roots=D['train_roots' if phase=='train' else 'heldout_roots'];games=[];e=M.start(binary,3,deadline,P.stop)
  try:
   for oi,fixture in enumerate(roots):
    for color in (True,False):
     A.guard(deadline,P.stop);probes,ack=M.configure(e,w,O/'variant.ini',deadline,P.stop);b=P.board(fixture);rs=D['train_random_seed_base']+round_*8+oi if phase=='train' else D['heldout_random_seed_base']+oi;rng=random.Random(rs);actions=[];searches=[];oppo=[];rootsmeta=[];name=f's{seed}-{mode}-{phase}-r{round_}-{opponent}-o{oi}-c{int(color)}';context=dict(name=name,seed=seed,mode=mode,round=round_,phase=phase,opponent=opponent,root_index=oi,agent_color=color,random_seed=rs);j.record('game_start',context=context,weights=w,price_probes=probes,table_ack=ack)
     for ply in range(D['cap']):
      A.guard(deadline,P.stop)
      if b.is_game_over(claim_draw=False):break
      if b.turn==color:m,record=M.M.search(e,b.copy(stack=True),deadline,P.stop);rootsmeta.append(dict(ply=ply,features_actor=[len(b.pieces(t,color))-len(b.pieces(t,not color)) for t in range(1,6)],root_fen=b.fen()));searches.append(record)
      elif opponent=='random':m=rng.choice(sorted(b.legal_moves,key=lambda z:z.uci()))
      else:m,record=P.P.unit2ply(b.copy(stack=True),deadline,P.stop);oppo.append(record)
      assert m in b.legal_moves;b.push(m);actions.append(m.uci());j.record('after_move',name=name,ply=ply,move=m.uci(),fen=b.fen())
     score=G.score(b,color,len(actions),D['cap']);r=dict(root_fen=fixture['initial_fen'],opening_history=fixture['history'],opening_fen=fixture['expected_fen'],agent_color=color,actions=actions,search_records=searches,opponent_records=oppo,root_features=rootsmeta,final_fen=b.fen(),score=score,reward=score['reward'],price_probes=probes,table_ack=ack);c=dict(context=context,weights=dict(w),result=r);calls.append(c);games.append(c);j.record('game_end',context=context,result=r)
  finally:e.close()
  return games
 def transitions(games):
  rows=[];excluded=[]
  for c in games:
   r=c['result'];col=r['agent_color'];b=chess.Board(r['root_fen'])
   for m in r['opening_history']:b.push_uci(m)
   states=[];ix=0
   for ply,text in enumerate(r['actions']):
    if b.turn==col:states.append((b.copy(stack=True),r['search_records'][ix],ply));ix+=1
    b.push_uci(text)
   for i,(s,meta,ply) in enumerate(states):
    after=s.copy(stack=True)
    for text in r['actions'][ply:ply+2]:after.push_uci(text)
    terminal=after.outcome(claim_draw=False);nxt=states[i+1][1] if i+1<len(states) else None
    if terminal:y=0 if terminal.winner is None else (1 if terminal.winner==col else -1);kind='true_terminal';v=None
    elif nxt:
     assert nxt['full_history']==[m.uci() for m in after.move_stack];v=read_value(nxt)
     if v is None:excluded.append(dict(game=c['context']['name'],index=i,reason='no_unbounded_successor_value'));continue
     y=v['bounded'];kind='search_bootstrap'
    else:excluded.append(dict(game=c['context']['name'],index=i,reason='unknown_cutoff_no_successor'));continue
    rows.append(dict(game=c['context']['name'],index=i,features=[len(s.pieces(t,col))-len(s.pieces(t,not col)) for t in range(1,6)],target=y,target_kind=kind,successor_value=v))
  return rows,excluded
 status='COMPLETE'
 try:
  for seed,mode in D['method_order']:
   theta=np.array(E.starts(seed));initial=E.weights(theta.tolist());run=dict(seed=seed,mode=mode,initial_weights=initial,initial_theta=theta.tolist(),rounds=[]);runs.append(run)
   for round_ in range(D['rounds']):
    teacher=initial if mode=='fixed_teacher' else E.weights(theta.tolist());before=theta.tolist();games=block(teacher,seed,mode,round_,'train','random');rows,excluded=transitions(games);updates=[]
    for row in rows:
     if mode=='terminal_only' and row['target_kind']!='true_terminal':continue
     oldtheta=theta.copy();v,grad=student(theta,row['features']);delta=row['target']-v;alpha=D['alpha']/max(1,float(grad@grad));theta=np.clip(theta+alpha*delta*grad,E.LOW,E.HIGH);newv,_=student(theta,row['features']);updates.append(dict(game=row['game'],index=row['index'],before=oldtheta.tolist(),value=v,target=row['target'],delta=delta,gradient=grad.tolist(),alpha=alpha,after=theta.tolist(),loss_before=delta**2,loss_after=(row['target']-newv)**2))
    run['rounds'].append(dict(round=round_,teacher_weights=teacher,student_before=before,student_after=theta.tolist(),all_transitions=rows,excluded=excluded,updates=updates));A.atomic_json(O/'progress.json',dict(actual_games=len(calls),seconds=time.monotonic()-start,current=[seed,mode,round_]));print(json.dumps(dict(games=len(calls),seconds=round(time.monotonic()-start,3),seed=seed,mode=mode,round=round_,updates=len(updates))),flush=True)
   run['final_weights']=E.weights(theta.tolist());run['final_theta']=theta.tolist();run['endpoint_frozen_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
  training_freeze=datetime.datetime.now(datetime.timezone.utc).isoformat();A.atomic_json(O/'endpoints.json',dict(complete=True,training_calls=len(calls),all_endpoints_frozen_at=training_freeze,ends=[{k:r[k] for k in ('seed','mode','initial_weights','final_weights','endpoint_frozen_at')} for r in runs]))
  # Onephysicalinitialbaselineperseed/opponent; referenced byallthree methods.
  for seed in D['start_seeds']:
   initial=next(r['initial_weights'] for r in runs if r['seed']==seed)
   for opponent in D['opponents_heldout']:block(initial,seed,'shared_initial',0,'heldout',opponent)
  for run in runs:
   for opponent in D['opponents_heldout']:block(run['final_weights'],run['seed'],run['mode'],0,'heldout',opponent)
 except BaseException as ex:status='INTERRUPTED';error=type(ex).__name__+': '+str(ex)
 finally:j.close()
 out=dict(complete=status=='COMPLETE',runs=runs,calls=calls,all_endpoints_frozen_at=training_freeze)
 if status!='COMPLETE':out['error']=error
 A.atomic_json(O/'controller.json',out);summary=dict(status=status,actual_games=len(calls),planned_unique_games=D['planned_unique_games'],train_games=sum(c['context']['phase']=='train' for c in calls),heldout_games=sum(c['context']['phase']=='heldout' for c in calls),seconds=time.monotonic()-start,allends_beforeheldout=training_freeze is not None,binary_sha256=D['binary_sha256'])
 if status!='COMPLETE':summary['error']=error
 A.atomic_json(O/'status.json',summary);print(json.dumps(summary));return 0 if status=='COMPLETE' else 3
if __name__=='__main__':sys.exit(execute())
