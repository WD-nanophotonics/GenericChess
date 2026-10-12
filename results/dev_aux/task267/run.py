import json,time,sys,importlib.util,hashlib,math
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task267';D=json.loads((O/'declaration.json').read_bytes());assert not (O/'result.json').exists();s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);P.stop();binary=R/D['binary_relative'];assert hashlib.sha256(binary.read_bytes()).hexdigest()==D['binary_sha256'];start=time.monotonic();deadline=start+600;env=dict(P=P,O=O,deadline=deadline,math=math);exec(compile((O/'configure.py').read_text(),str(O/'configure.py'),'exec'),env);configure=env['configure'];calls=[];out=dict(complete=False,calls=calls)
def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'result.json',out)
try:
 for op in D['opponents']:
  engines={name:P.M.start(binary,3,deadline,P.stop) for name in ('semantic',op)}
  try:
   for limit in D['node_limits']:
    for fi,f in enumerate(D['roots']):
     for color in (True,False):
      P.A.guard(deadline,P.stop);probes={};ack={}
      for name,e in engines.items():probes[name],ack[name]=configure(e,D['profiles'][name])
      b=P.board(f);actor=color;actions=[];records=[];ts=time.monotonic()
      for ply in range(D['cap']):
       P.A.guard(deadline,P.stop)
       if b.is_game_over(claim_draw=False):break
       name='semantic' if b.turn==actor else op;m,rec=P.M.M.search(engines[name],b.copy(stack=True),deadline,P.stop,limit=limit);records.append(dict(ply=ply,player=name,record=rec));assert m in b.legal_moves;b.push(m);actions.append(m.uci())
      outcome=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if outcome is None else outcome.termination.name;sign=0 if outcome is None or outcome.winner is None else 1 if outcome.winner==actor else -1;quantity=sum(len(b.pieces(t,actor))-len(b.pieces(t,not actor)) for t in range(1,6));calls.append(dict(opponent=op,node_limit=limit,root=fi,phase=f['phase'],color=color,opening_history=f['history'],actions=actions,search_records=records,final_fen=b.fen(),termination=kind,winner=None if outcome is None else outcome.winner,terminal=outcome is not None,finite_mate_goal=sign if kind=='CHECKMATE' else 0,actual_terminal_result=None if outcome is None else sign,quantity_at_cap=quantity,ply_count=len(actions),seconds=time.monotonic()-ts,leaf_probes=probes,table_ack=ack));save()
  finally:
   for e in engines.values():e.close()
  print(op,len(calls),round(time.monotonic()-start,3),flush=True)
 out['complete']=True;save();print('COMPLETE',len(calls),out['seconds'])
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
