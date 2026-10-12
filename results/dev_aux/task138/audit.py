"""Replay actualcompositionpilot and diagnose terminal/feature signal; no newgames."""
import json,hashlib,random,time,sys,importlib.util
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();O=R/'results/dev_aux/task138';O.mkdir(exist_ok=True)
d=json.loads((R/'results/dev_aux/task135/declaration.json').read_bytes());games=json.loads((R/'results/dev_aux/task136/games.json').read_bytes());assert games['complete']
spec=importlib.util.spec_from_file_location('score138',R/'results/dev_aux/task104/short_game.py');G=importlib.util.module_from_spec(spec);spec.loader.exec_module(G)
def vec(b,color):return [len(b.pieces(t,color))-len(b.pieces(t,not color)) for t in range(1,6)]
def rank(vectors):
 rows=[[F(x) for x in row] for row in vectors];pivot=0
 for k in range(len(rows[0])):
  i=next((i for i in range(pivot,len(rows)) if rows[i][k]),None)
  if i is None:continue
  rows[pivot],rows[i]=rows[i],rows[pivot];q=rows[pivot][k];rows[pivot]=[x/q for x in rows[pivot]]
  for i in range(pivot+1,len(rows)):
   q=rows[i][k]
   if q:rows[i]=[a-q*b for a,b in zip(rows[i],rows[pivot])]
  pivot+=1
 return pivot
moves=searches=0;terminals=[];started=time.monotonic()
for c in games['calls']:
 r=c['result'];b=chess.Board(r['root_fen']);assert b.is_valid() and not b.is_game_over(claim_draw=False);color=b.turn;rng=random.Random(r['random_seed']);si=0
 for text in r['actions']:
  assert not b.is_game_over(claim_draw=False)
  m=chess.Move.from_uci(text);assert m in b.legal_moves
  if b.turn==color:
   meta=r['search_records'][si];assert meta['root_fen']==r['root_fen'] and meta['full_history']==[m.uci() for m in b.move_stack];assert meta['backend'].endswith(games['binary_sha256']);assert meta['nodes_limit']==1024 and isinstance(meta['reported_nodes'],int) and meta['reported_nodes']>0;si+=1;searches+=1
  else:assert m==rng.choice(sorted(b.legal_moves,key=lambda m:m.uci()))
  b.push(m);moves+=1
 assert si==len(r['search_records']) and b.fen()==r['final_fen'];assert G.score(b,color,len(r['actions']),16)==r['score'];assert r['reward']==r['score']['reward']
 assert len(r['candidate_leaf_probes'])==5
 for probe in r['candidate_leaf_probes']:assert abs(probe['measured_white_pawns']-c['weights'][probe['type']]/208)<=.011
 terminals.append(dict(name=c['name'],win=r['score']['winner']==color,mate=r['score']['termination']=='CHECKMATE',plies=len(r['actions']),reward=r['reward']))
roots=[];deltas=[]
for fixture in d['train']:
 for color in (True,False):
  b=chess.Board(fixture['white_fen' if color else 'black_fen']);base=vec(b,color);mate1=[];checks=0;captures=0
  for m in list(b.legal_moves):
   captures+=b.is_capture(m);b.push(m)
   if b.is_check():checks+=1
   if b.is_checkmate():mate1.append(m.uci())
   deltas.append([v-v0 for v,v0 in zip(vec(b,color),base)])
   if not b.is_game_over(claim_draw=False):
    for reply in list(b.legal_moves):
     b.push(reply);deltas.append([v-v0 for v,v0 in zip(vec(b,color),base)]);b.pop()
   b.pop()
  roots.append(dict(seed=fixture['seed'],color=color,mate_in_one_actions=mate1,legal_actions=b.legal_moves.count(),checks=checks,captures=captures))
unique=sorted(set(map(tuple,deltas)));r5=rank(unique);r4=rank([v[1:] for v in unique])
out=dict(complete=True,actual_games=len(games['calls']),actual_legal_moves=moves,actual_searches=searches,leaf_probes=5*len(games['calls']),pilot_declaration_error='Prose32games contradicted fixedfirst4roots2turns2profiles=16; actual16. Preservedoriginaldeclaration, no retrospectiveexpansion.',allmatewins=all(x['mate'] and x['win'] for x in terminals),terminals=terminals,training_root_geometry=roots,complete_two_ply_feature_unique_rows=len(unique),feature_rank5=r5,feature_rank4_afterPfixed=r4,seconds=time.monotonic()-started,scope='Featurefullrank proves possiblelinearprice contrasts on declaredfinitechildren, not feedbackidentifiability orhumanpricelearning. Allpilotwins leave onlymatespeedfeedback. Heldoutgeometrynotplayed.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:out[k] for k in ('complete','actual_games','actual_legal_moves','actual_searches','leaf_probes','allmatewins','complete_two_ply_feature_unique_rows','feature_rank5','feature_rank4_afterPfixed','seconds')},indent=2))
