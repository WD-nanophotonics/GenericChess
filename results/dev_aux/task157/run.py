"""Actual64gamecoveredking pilot, oneengine and exactunit2ply opponent."""
import json,time,random,sys,importlib.util,hashlib,statistics
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task157';O.mkdir(exist_ok=True)
s=importlib.util.spec_from_file_location('M157',R/'results/dev_aux/task139/run.py');M=importlib.util.module_from_spec(s);s.loader.exec_module(M);A=M.A;G=M.M.G
def unit_value(b,color):
 out=b.outcome(claim_draw=False)
 if out is not None:return 0 if out.winner is None else (1000000 if out.winner==color else -1000000)
 return 208*sum(len(b.pieces(t,color))-len(b.pieces(t,not color)) for t in range(1,6))
def unit2ply(b,deadline,stop):
 color=b.turn;nodes=0;rows=[];started=time.monotonic();fen=b.fen();stack=[m.uci() for m in b.move_stack]
 for move in sorted(b.legal_moves,key=lambda m:m.uci()):
  A.guard(deadline,stop);b.push(move)
  try:
   if b.is_game_over(claim_draw=False):values=[unit_value(b,color)];nodes+=1
   else:
    values=[]
    for reply in sorted(b.legal_moves,key=lambda m:m.uci()):
     if nodes%64==0:A.guard(deadline,stop)
     b.push(reply)
     try:values.append(unit_value(b,color));nodes+=1
     finally:b.pop()
   rows.append(dict(move=move.uci(),worst=min(values),reply_count=len(values)))
  finally:b.pop()
 assert b.fen()==fen and [m.uci() for m in b.move_stack]==stack
 best=max(r['worst'] for r in rows);chosen=next(r['move'] for r in rows if r['worst']==best)
 return chess.Move.from_uci(chosen),dict(backend='PYTHON_STANDARDCHESS_FULL_LEGAL_2PLY_UNIT',leaf_nodes=nodes,completed=True,root_fen=fen,full_history=stack,rows=rows,value=best,wall_seconds=time.monotonic()-started)
def execute():
 d=json.loads((R/'results/dev_aux/task155/declaration.json').read_bytes());binary=R/'.local_agent/alignment-order/fairy-order-toggle.exe';digest=hashlib.sha256(binary.read_bytes()).hexdigest();assert digest=='c378f0b3fc9f99d48e3089294a7c6adf5d5215bcac070200424d0d24f4d4b460'
 if (O/'events.jsonl').exists():raise FileExistsError('frozenexecution')
 started=time.monotonic();deadline=started+d['deadline_seconds'];stop=lambda:A.stop_check(R);stop();j=A.Journal(O/'events.jsonl');calls=[];complete=False
 try:
  for profile,w in d['profiles'].items():
   for opponent in d['opponents']:
    e=M.start(binary,3,deadline,stop)
    try:
     for oi,fixture in enumerate(d['roots']):
      for color in (True,False):
       probes,ack=M.configure(e,w,O/'variant.ini',deadline,stop)
       fen=fixture['white_fen' if color else 'black_fen'];b=chess.Board(fen);rng=random.Random(d['random_seeds'][oi]);moves=[];searches=[];opponent_records=[];name=f'{profile}-{opponent}-o{oi}-c{int(color)}'
       j.record('game_start',name=name,root_fen=fen,weights=w,probes=probes,table_ack=ack)
       for ply in range(16):
        A.guard(deadline,stop)
        if b.is_game_over(claim_draw=False):break
        if b.turn==color:move,record=M.M.search(e,b.copy(stack=True),deadline,stop);searches.append(record)
        elif opponent=='random':move=rng.choice(sorted(b.legal_moves,key=lambda m:m.uci()))
        else:move,record=unit2ply(b.copy(stack=True),deadline,stop);opponent_records.append(record)
        assert move in b.legal_moves;b.push(move);moves.append(move.uci());j.record('after_move',name=name,ply=ply,move=move.uci(),fen=b.fen())
       score=G.score(b,color,len(moves),16);r=dict(root_fen=fen,agent_color=color,actions=moves,search_records=searches,opponent_records=opponent_records,final_fen=b.fen(),reward=score['reward'],score=score,candidate_leaf_probes=probes,table_ack=ack)
       c=dict(name=name,profile=profile,opponent=opponent,opening_index=oi,random_seed=d['random_seeds'][oi],weights=w,result=r);calls.append(c);j.record('game_end',name=name,result=r)
    finally:e.close()
  complete=True
 except BaseException as ex:error=type(ex).__name__+': '+str(ex)
 finally:j.close()
 out=dict(complete=complete,calls=calls,wall_seconds=time.monotonic()-started,binary_sha256=digest,declaration_sha256=hashlib.sha256((R/'results/dev_aux/task155/declaration.json').read_bytes()).hexdigest(),scope='Differentfixedopponentcompute/distribution withsameagentbudget; notequalresourcestrengthcomparison orhumanpricelearning.')
 if not complete:out['error']=error
 A.atomic_json(O/'games.json',out)
 summary=dict(complete=complete,games=len(calls),seconds=out['wall_seconds'],groups=[],profile_pairs=[])
 if complete:
  for opponent in d['opponents']:
   for profile in d['profiles']:
    rows=[c for c in calls if c['opponent']==opponent and c['profile']==profile]
    summary['groups'].append(dict(profile=profile,opponent=opponent,games=len(rows),mate_wins=sum(c['result']['score']['termination']=='CHECKMATE' and c['result']['score']['winner']==c['result']['agent_color'] for c in rows),mate_losses=sum(c['result']['score']['termination']=='CHECKMATE' and c['result']['score']['winner']!=c['result']['agent_color'] for c in rows),cutoffs=sum(not c['result']['score']['terminal'] for c in rows),original_reward_mean=statistics.mean(c['result']['reward'] for c in rows),opponent_leaf_nodes=sum(r['leaf_nodes'] for c in rows for r in c['result']['opponent_records']),opponent_compute_seconds=sum(r['wall_seconds'] for c in rows for r in c['result']['opponent_records'])))
   for oi in range(8):
    for color in (True,False):
     pair=[next(c['result'] for c in calls if c['name']==f'{profile}-{opponent}-o{oi}-c{int(color)}') for profile in ('unit','learned')]
     summary['profile_pairs'].append(dict(opponent=opponent,opening=oi,color=color,reward_delta=pair[1]['reward']-pair[0]['reward'],same_actions=pair[0]['actions']==pair[1]['actions'],terminal=[r['score']['termination'] for r in pair]))
 A.atomic_json(O/'summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='profile_pairs'},indent=2));return 0 if complete else 3
if __name__=='__main__':sys.exit(execute())
