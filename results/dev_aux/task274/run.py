import json,time,math,hashlib,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task274';D=json.loads((O/'declaration.json').read_bytes());assert not (O/'result.json').exists();s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);P.stop();binary=R/D['binary_relative'];assert hashlib.sha256(binary.read_bytes()).hexdigest()==D['binary_sha256'];start=time.monotonic();deadline=start+180;env=dict(P=P,O=O,deadline=deadline,math=math);exec(compile((O/'configure.py').read_text(),str(O/'configure.py'),'exec'),env);configure=env['configure'];calls=[];out=dict(complete=False,calls=calls)
def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'result.json',out)
try:
 for scale in D['scales']:
  weights={side:D['profiles'][side+'-c'+scale]['weights'] for side in ('semantic','unit')};engines={side:P.M.start(binary,3,deadline,P.stop) for side in weights}
  try:
   for limit in D['node_limits']:
    for oi,f in enumerate(D['roots']):
     for color in (True,False):
      probes={};ack={}
      for side,e in engines.items():probes[side],ack[side]=configure(e,weights[side])
      b=P.board(f);actions=[];searches=[];ts=time.monotonic()
      for ply in range(48):
       P.A.guard(deadline,P.stop)
       if b.is_game_over(claim_draw=False):break
       side='semantic' if b.turn==color else 'unit';m,v=P.M.M.search(engines[side],b.copy(stack=True),deadline,P.stop,limit=limit);searches.append(dict(ply=ply,player=side,record=v));assert m in b.legal_moves;b.push(m);actions.append(m.uci())
      oo=b.outcome(claim_draw=False);term='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;sign=0 if oo is None or oo.winner is None else 1 if oo.winner==color else -1;calls.append(dict(scale=scale,node_limit=limit,root=oi,color=color,weights=weights,actions=actions,search_records=searches,final_fen=b.fen(),termination=term,terminal=oo is not None,finite_mate_goal=sign if term=='CHECKMATE' else 0,actual_terminal_result=None if oo is None else sign,quantity_at_cap=sum(len(b.pieces(t,color))-len(b.pieces(t,not color)) for t in range(1,6)),seconds=time.monotonic()-ts,leaf_probes=probes,table_ack=ack));save()
  finally:
   for e in engines.values():e.close()
  print(scale,len(calls),round(time.monotonic()-start,3),flush=True)
 out['complete']=True;save();print('COMPLETE',len(calls),out['seconds'])
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
