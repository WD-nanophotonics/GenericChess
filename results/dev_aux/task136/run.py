"""Scoped synthetic-root adapter; actualownedFairy process and fullpostroot history."""
import json,time,random,sys,importlib.util,hashlib
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task136';O.mkdir(exist_ok=True)
s=importlib.util.spec_from_file_location('cached127composition',R/'results/dev_aux/task127/run.py');M=importlib.util.module_from_spec(s);s.loader.exec_module(M);A=M.adapter;G=M.G
def search(e,b,deadline,stop,limit=1024):
 A.guard(deadline,stop);root=b.root();history=[m.uci() for m in b.move_stack]
 e.send('position fen '+root.fen()+(' moves '+' '.join(history) if history else ''))
 e.send('go nodes '+str(limit));lines=e.until(lambda x:x.startswith('bestmove '));m=chess.Move.from_uci(lines[-1].split()[1]);assert m in b.legal_moves;e.ready();A.guard(deadline,stop)
 n=None;depth=None
 for line in lines[:-1]:
  f=line.split()
  if f and f[0]=='info':
   if 'nodes' in f:n=int(f[f.index('nodes')+1])
   if 'depth' in f:depth=int(f[f.index('depth')+1])
 return m,dict(root_fen=root.fen(),full_history=history,reported_nodes=n,reported_depth=depth,nodes_limit=limit,backend=e.backend,uci_info=lines[:-1])
def play(e,w,root_fen,seed,deadline,stop,name,journal,config,cap=16):
 A.guard(deadline,stop);A.validate_weights(w)
 probes=A.configure(e,w,config,deadline,stop);b=chess.Board(root_fen)
 if not b.is_valid() or b.is_game_over(claim_draw=False):raise ValueError('invalidfrozeninput')
 color=b.turn;rng=random.Random(seed);moves=[];records=[]
 if journal:journal.record('game_start',name=name,weights=w,root_fen=root_fen,random_seed=seed,probes=probes)
 for ply in range(cap):
  A.guard(deadline,stop)
  if b.is_game_over(claim_draw=False):break
  if b.turn==color:m,meta=search(e,b.copy(stack=True),deadline,stop);records.append(meta)
  else:m=rng.choice(sorted(b.legal_moves,key=lambda m:m.uci()))
  assert m in b.legal_moves;b.push(m);moves.append(m.uci())
  if journal:journal.record('after_move',name=name,ply=ply,move=m.uci(),fen=b.fen())
 result=dict(root_fen=root_fen,agent_color=color,random_seed=seed,actions=moves,search_records=records,final_fen=b.fen(),score=G.score(b,color,len(moves),cap),candidate_leaf_probes=probes)
 result['reward']=result['score']['reward']
 if journal:journal.record('game_end',name=name,result=result)
 return result
def execute():
 d=json.loads((R/'results/dev_aux/task135/declaration.json').read_bytes());started=time.monotonic();deadline=started+120;stop=lambda:A.stop_check(R);stop();binary,digest,_=A.validated_entry(R/'.local_agent/material-selfplay/fairy-material.exe',R/'results/dev_aux/task120/qualification.json')
 if (O/'events.jsonl').exists():raise FileExistsError('nor erun')
 j=A.Journal(O/'events.jsonl');calls=[];complete=False
 try:
  for arm,w in d['profiles'].items():
   e=A.UCI(binary,R,deadline,stop);e.backend='QUALIFIED_FAIRY_MATERIAL:'+digest
   try:
    for i,fixture in enumerate(d['train'][:4]):
     for color in (True,False):
      name=f'{arm}-o{i}-c{int(color)}';fen=fixture['white_fen' if color else 'black_fen'];result=play(e,w,fen,2026110000+i,deadline,stop,name,j,O/'variant.ini')
      calls.append(dict(name=name,arm=arm,root_index=i,weights=w,result=result))
   finally:e.close()
  complete=True
 except BaseException as ex:error=type(ex).__name__+': '+str(ex)
 finally:j.close()
 out=dict(complete=complete,calls=calls,wall_seconds=time.monotonic()-started,fixture_sha256=hashlib.sha256((R/'results/dev_aux/task135/declaration.json').read_bytes()).hexdigest(),binary_sha256=digest)
 if not complete:out['error']=error
 A.atomic_json(O/'games.json',out)
 pairs=[]
 for i in range(4):
  for color in (True,False):
   pair=[next(c['result'] for c in calls if c['name']==f'{arm}-o{i}-c{int(color)}') for arm in ('unit','learned')]
   pairs.append(dict(root=i,color=color,delta=pair[1]['reward']-pair[0]['reward'],same_actions=pair[0]['actions']==pair[1]['actions'],termination=[x['score']['termination'] for x in pair]))
 summary=dict(complete=complete,games=len(calls),wall_seconds=out['wall_seconds'],pairs=pairs,informative=any(p['delta']!=0 for p in pairs),scope='Syntheticbalanced16ply pilot; nohumanrecovery or generalstrength evidence')
 A.atomic_json(O/'summary.json',summary);print(json.dumps(summary,indent=2));return 0 if complete else 3
if __name__=='__main__':sys.exit(execute())
