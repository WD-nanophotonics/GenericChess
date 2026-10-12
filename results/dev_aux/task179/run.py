"""Actual reachable full-army short pilot; retains the initial prelude history."""
import json,time,random,sys,importlib.util,hashlib,statistics
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task179'
s=importlib.util.spec_from_file_location('P166',R/'results/dev_aux/task157/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);M=P.M;A=P.A;G=P.G
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
def board(root):
 b=chess.Board(root['initial_fen'])
 for move in root['history']:b.push_uci(move)
 assert b.fen()==root['expected_fen']
 return b
def execute():
 assert json.loads((R/'results/dev_aux/task175/status.json').read_bytes())['status']=='COMPLETE'
 d=json.loads((O/'declaration.json').read_bytes());binary=R/'.local_agent/alignment-order/fairy-order-toggle.exe';assert hashlib.sha256(binary.read_bytes()).hexdigest()==d['binary_sha256']
 if (O/'events.jsonl').exists():raise FileExistsError('frozenexecution')
 started=time.monotonic();deadline=started+d['deadline_seconds'];stop();j=A.Journal(O/'events.jsonl');calls=[];complete=False
 try:
  for profile,w in d['profiles'].items():
   for opponent in d['opponents']:
    e=M.start(binary,3,deadline,stop)
    try:
     for oi,fixture in enumerate(d['roots']):
      for color in (True,False):
       probes,ack=M.configure(e,w,O/'variant.ini',deadline,stop);b=board(fixture);rng=random.Random(d['random_seeds'][oi]);moves=[];searches=[];oppo=[];name=f'{profile}-{opponent}-o{oi}-c{int(color)}'
       j.record('game_start',name=name,fixture=fixture,weights=w,probes=probes,table_ack=ack)
       for ply in range(16):
        A.guard(deadline,stop)
        if b.is_game_over(claim_draw=False):break
        if b.turn==color:move,record=M.M.search(e,b.copy(stack=True),deadline,stop);searches.append(record)
        elif opponent=='random':move=rng.choice(sorted(b.legal_moves,key=lambda m:m.uci()))
        else:move,record=P.unit2ply(b.copy(stack=True),deadline,stop);oppo.append(record)
        assert move in b.legal_moves;b.push(move);moves.append(move.uci());j.record('after_move',name=name,ply=ply,move=move.uci(),fen=b.fen())
       score=G.score(b,color,len(moves),16);r=dict(root_fen=fixture['initial_fen'],opening_history=fixture['history'],opening_fen=fixture['expected_fen'],agent_color=color,actions=moves,search_records=searches,opponent_records=oppo,final_fen=b.fen(),reward=score['reward'],score=score,candidate_leaf_probes=probes,table_ack=ack)
       c=dict(name=name,profile=profile,opponent=opponent,opening_index=oi,random_seed=d['random_seeds'][oi],weights=w,result=r);calls.append(c);j.record('game_end',name=name,result=r)
    finally:e.close()
  complete=True
 except BaseException as ex:error=type(ex).__name__+': '+str(ex)
 finally:j.close()
 out=dict(complete=complete,calls=calls,wall_seconds=time.monotonic()-started,binary_sha256=d['binary_sha256'],declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest())
 if not complete:out['error']=error
 A.atomic_json(O/'games.json',out);summary=dict(complete=complete,games=len(calls),seconds=out['wall_seconds'],groups=[],profile_pairs=[])
 if complete:
  for opponent in d['opponents']:
   for profile in d['profiles']:
    rows=[c for c in calls if c['opponent']==opponent and c['profile']==profile]
    summary['groups'].append(dict(profile=profile,opponent=opponent,games=len(rows),mate_wins=sum(c['result']['score']['termination']=='CHECKMATE' and c['result']['score']['winner']==c['result']['agent_color'] for c in rows),mate_losses=sum(c['result']['score']['termination']=='CHECKMATE' and c['result']['score']['winner']!=c['result']['agent_color'] for c in rows),cutoffs=sum(not c['result']['score']['terminal'] for c in rows),original_reward_mean=statistics.mean(c['result']['reward'] for c in rows),opponent_leaf_nodes=sum(r['leaf_nodes'] for c in rows for r in c['result']['opponent_records'])))
   for profile in (p for p in d['profiles'] if p!='unit'):
    for oi in range(len(d['roots'])):
     for color in (True,False):
      pair=[next(c['result'] for c in calls if c['name']==f'{p}-{opponent}-o{oi}-c{int(color)}') for p in ('unit',profile)]
      summary['profile_pairs'].append(dict(profile=profile,opponent=opponent,opening=oi,color=color,reward_delta=pair[1]['reward']-pair[0]['reward'],same_actions=pair[0]['actions']==pair[1]['actions'],terminal=[r['score']['termination'] for r in pair]))
 A.atomic_json(O/'summary.json',summary);print(json.dumps({k:v for k,v in summary.items() if k!='profile_pairs'},indent=2));return 0 if complete else 3
if __name__=='__main__':sys.exit(execute())
