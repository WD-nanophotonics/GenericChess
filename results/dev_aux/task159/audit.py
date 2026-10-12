"""Independentreplay of64actualpilot games and completeopponent2ply selections."""
import json,random,sys,importlib.util,statistics
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task159';O.mkdir(exist_ok=True)
s=importlib.util.spec_from_file_location('G159',R/'results/dev_aux/task104/short_game.py');G=importlib.util.module_from_spec(s);s.loader.exec_module(G)
D=json.loads((R/'results/dev_aux/task155/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task157/games.json').read_bytes());assert X['complete'] and len(X['calls'])==64
counts=dict(games=0,moves=0,engine_searches=0,unit_opponent_searches=0,unit_opponent_leaf_nodes=0,price_probes=0)
def value(b,color):
 out=b.outcome(claim_draw=False)
 if out:return 0 if out.winner is None else (1000000 if out.winner==color else -1000000)
 return 208*sum(len(b.pieces(t,color))-len(b.pieces(t,not color)) for t in range(1,6))
for c in X['calls']:
 r=c['result'];b=chess.Board(r['root_fen']);color=r['agent_color'];rng=random.Random(c['random_seed']);si=oi=0
 assert b.is_valid() and not b.is_game_over(claim_draw=False)
 for text in r['actions']:
  assert not b.is_game_over(claim_draw=False);move=chess.Move.from_uci(text);assert move in b.legal_moves
  if b.turn==color:
   meta=r['search_records'][si];assert meta['root_fen']==r['root_fen'] and meta['full_history']==[m.uci() for m in b.move_stack] and meta['backend'].endswith(X['binary_sha256']);si+=1;counts['engine_searches']+=1
  elif c['opponent']=='random':assert move==rng.choice(sorted(b.legal_moves,key=lambda m:m.uci()))
  else:
   meta=r['opponent_records'][oi];assert meta['completed'] and meta['root_fen']==b.fen() and meta['full_history']==[m.uci() for m in b.move_stack];opp=b.turn;rows=[];nodes=0
   for candidate in sorted(b.legal_moves,key=lambda m:m.uci()):
    b.push(candidate)
    if b.is_game_over(claim_draw=False):vv=[value(b,opp)];nodes+=1
    else:
     vv=[]
     for reply in sorted(b.legal_moves,key=lambda m:m.uci()):
      b.push(reply);vv.append(value(b,opp));nodes+=1;b.pop()
    rows.append(dict(move=candidate.uci(),worst=min(vv),reply_count=len(vv)));b.pop()
   assert rows==meta['rows'] and nodes==meta['leaf_nodes']
   best=max(x['worst'] for x in rows);assert best==meta['value'];assert move.uci()==next(x['move'] for x in rows if x['worst']==best);oi+=1;counts['unit_opponent_searches']+=1;counts['unit_opponent_leaf_nodes']+=nodes
  b.push(move);counts['moves']+=1
 assert si==len(r['search_records']) and oi==len(r['opponent_records']);assert b.fen()==r['final_fen'];assert G.score(b,color,len(r['actions']),16)==r['score'] and r['reward']==r['score']['reward'];counts['games']+=1
 assert len(r['candidate_leaf_probes'])==5
 for p in r['candidate_leaf_probes']:assert abs(p['measured_white_pawns']-c['weights'][p['type']]/208)<=.011;counts['price_probes']+=1
 assert r['table_ack']['alignment']==3 and r['table_ack']['prices']=={str(i+1):[c['weights'][k],c['weights'][k]] for i,k in enumerate('PNBRQ')}
summary=json.loads((R/'results/dev_aux/task157/summary.json').read_bytes())
paired={}
for opponent in D['opponents']:
 pairs=[p for p in summary['profile_pairs'] if p['opponent']==opponent]
 paired[opponent]=dict(profile_reward_difference_mean=statistics.mean(p['reward_delta'] for p in pairs),nonzero_paired_deltas=sum(p['reward_delta']!=0 for p in pairs),changed_action_pairs=sum(not p['same_actions'] for p in pairs),scope='Same16matchedroot/color pairs, fixedtwoexposedprofiles; not generallearning/strength.')
out=dict(complete=True,counts=counts,paired=paired,scope='Independentactualtrace/fullopponentsearch replay, notengine rerun. Noextraengineworker orallgame-ruleclaim.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
