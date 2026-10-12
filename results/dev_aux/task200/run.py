"""Predeclared short16/24plyresource curve, no newlearning or oldtestextension."""
import json,random,time,hashlib,importlib.util
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task200';sp=importlib.util.spec_from_file_location('P200',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);M=P.M;A=P.A;G=P.G

def execute():
 d=json.loads((O/'declaration.json').read_bytes());assert not (O/'games.json').exists();P.stop();binary=R/'.local_agent/alignment-order/fairy-order-toggle.exe';assert hashlib.sha256(binary.read_bytes()).hexdigest()==d['binary_sha256'];started=time.monotonic();deadline=started+d['deadline_seconds'];calls=[]
 for pi,(profile,w) in enumerate(d['profiles'].items()):
  for cap in (d['caps'] if pi%2==0 else d['caps'][::-1]):
   e=M.start(binary,3,deadline,P.stop)
   try:
    for oi,fixture in enumerate(d['roots']):
     for color in (True,False):
      probes,ack=M.configure(e,w,O/'variant.ini',deadline,P.stop);b=P.board(fixture);rng=random.Random(d['random_seeds'][oi]);moves=[];records=[];t=time.monotonic()
      for ply in range(cap):
       A.guard(deadline,P.stop)
       if b.is_game_over(claim_draw=False):break
       if b.turn==color:m,meta=M.M.search(e,b.copy(stack=True),deadline,P.stop);records.append(meta)
       else:m=rng.choice(sorted(b.legal_moves,key=lambda x:x.uci()))
       b.push(m);moves.append(m.uci())
      score=G.score(b,color,len(moves),cap);r=dict(root_fen=fixture['initial_fen'],opening_history=fixture['history'],opening_fen=fixture['expected_fen'],agent_color=color,actions=moves,search_records=records,opponent_records=[],final_fen=b.fen(),score=score,reward=score['reward'],candidate_leaf_probes=probes,table_ack=ack);calls.append(dict(name=f'{profile}-cap{cap}-o{oi}-c{int(color)}',cap=cap,profile=profile,opponent='random',opening_index=oi,random_seed=d['random_seeds'][oi],weights=w,result=r,play_seconds=time.monotonic()-t))
   finally:e.close()
 out=dict(complete=True,calls=calls,wall_seconds=time.monotonic()-started,binary_sha256=d['binary_sha256'],declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest());A.atomic_json(O/'games.json',out);print(json.dumps(dict(complete=True,games=len(calls),seconds=out['wall_seconds'])))
if __name__=='__main__':execute()
