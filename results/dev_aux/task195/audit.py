"""Independentreplay of256actualdeploymentgames and completeopponent2ply selections."""
import json,random,sys,importlib.util,statistics
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task195';O.mkdir(exist_ok=True)
s=importlib.util.spec_from_file_location('G159',R/'results/dev_aux/task104/short_game.py');G=importlib.util.module_from_spec(s);s.loader.exec_module(G)
D=json.loads((R/'results/dev_aux/task193/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task193/games.json').read_bytes());assert X['complete'] and len(X['calls'])==D['games']
# Independently reproduce all fixed construction seeds, including the excluded checked root.
for fixture in D['roots']+D['excluded_roots']:
 b=chess.Board();rng=random.Random(fixture['seed']);built=[]
 for ply in range(20):
  choices=sorted(b.legal_moves,key=lambda m:m.uci())
  if not choices or b.is_game_over(claim_draw=False):break
  m=rng.choice(choices);b.push(m);built.append(m.uci())
 assert built==fixture['history'] and b.fen()==fixture['expected_fen']
 if fixture.get('failure'):assert len(built)<20 and (not choices or b.is_game_over(claim_draw=False))
 else:assert len(built)==20 and b.is_valid() and not b.is_game_over(claim_draw=False)
assert D['excluded_slots']==2*len(D['opponents'])*len(D['profiles'])*len(D['excluded_roots']) and D['games']==2*len(D['opponents'])*len(D['profiles'])*len(D['roots'])
counts=dict(games=0,moves=0,engine_searches=0,unit_opponent_searches=0,unit_opponent_leaf_nodes=0,price_probes=0)
def value(b,color):
 out=b.outcome(claim_draw=False)
 if out:return 0 if out.winner is None else (1000000 if out.winner==color else -1000000)
 return 208*sum(len(b.pieces(t,color))-len(b.pieces(t,not color)) for t in range(1,6))
for c in X['calls']:
 r=c['result'];b=chess.Board(r['root_fen'])
 for text in r['opening_history']:b.push_uci(text)
 assert b.fen()==r['opening_fen']==D['roots'][c['opening_index']]['expected_fen']
 color=r['agent_color'];rng=random.Random(c['random_seed']);si=oi=0
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
summary=json.loads((R/'results/dev_aux/task193/summary.json').read_bytes())
paired={}
for opponent in D['opponents']:
 for profile in (p for p in D['profiles'] if p!='unit'):
  pairs=[p for p in summary['profile_pairs'] if p['opponent']==opponent and p['profile']==profile]
  paired[opponent+'-'+profile]=dict(profile_reward_difference_mean=statistics.mean(p['reward_delta'] for p in pairs),nonzero_paired_deltas=sum(p['reward_delta']!=0 for p in pairs),changed_action_pairs=sum(not p['same_actions'] for p in pairs),scope='Same16matchedfreshreachable-root/color pairs, allmechanicallyeligibletraining-onlymodelprofiles; not generallearning/strength.')
components=[]
def bounded(c):
 sc=c['result']['score'];color=c['result']['agent_color']
 return (0 if sc['winner'] is None else (1 if sc['winner']==color else -1)) if sc['terminal'] else sc['quantity_difference']/15
for opponent in D['opponents']:
 for profile in D['profiles']:
  group=[c for c in X['calls'] if c['opponent']==opponent and c['profile']==profile]
  components.append(dict(opponent=opponent,profile=profile,original_mean=statistics.mean(c['result']['reward'] for c in group),bounded_mean=statistics.mean(bounded(c) for c in group),final_quantity_mean=statistics.mean(c['result']['score']['quantity_difference']/15 for c in group),mate_wins=sum(c['result']['score']['termination']=='CHECKMATE' and c['result']['score']['winner']==c['result']['agent_color'] for c in group),mate_losses=sum(c['result']['score']['termination']=='CHECKMATE' and c['result']['score']['winner']!=c['result']['agent_color'] for c in group)))
out=dict(complete=True,counts=counts,paired=paired,components=components,scope='Independentactualtrace/fullpreludehistory/fullopponentsearch replay, notengine rerun. Noextraengineworker orallgame-ruleclaim.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
