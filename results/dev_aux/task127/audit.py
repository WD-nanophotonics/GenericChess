"""Replay the fixed64game deployment and separate bounded-return/policy evidence."""
import json,random,statistics,math,importlib.util,time,hashlib
from pathlib import Path
import chess
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux/task127';p=OUT/'games.json';D=json.loads(p.read_bytes());assert D['complete'] and len(D['calls'])==64
s=importlib.util.spec_from_file_location('score127audit',ROOT/'results/dev_aux/task104/short_game.py');G=importlib.util.module_from_spec(s);s.loader.exec_module(G)
by={c['context']['name']:c for c in D['calls']};assert len(by)==64;legal=0;searches=0;nodes=[];started=time.monotonic()
for c in D['calls']:
 r=c['result'];x=c['context'];w=c['weights'];op=int(x['name'].split('-')[0][1:]);assert r['opening']==G.opening(x['opening_seed'],plies=op)
 b=chess.Board();hist=[];si=0;rng=random.Random(x['random_seed'])
 for t in r['opening']:b.push_uci(t);hist.append(t)
 for t in r['actions']:
  assert not b.is_game_over(claim_draw=False);m=chess.Move.from_uci(t);assert m in b.legal_moves
  if b.turn==x['agent_color']:
   sr=r['search_records'][si];assert sr['full_history']==hist and sr['nodes_limit']==1024;nodes.append(sr['reported_nodes']);si+=1;searches+=1
  else:assert m==rng.choice(sorted(b.legal_moves,key=lambda z:z.uci()))
  b.push(m);hist.append(t);legal+=1
 assert b.fen()==r['final_fen'] and si==len(r['search_records']);assert G.score(b,x['agent_color'],len(r['actions']),16)==r['score']
 for pr in r['candidate_leaf_probes']:assert math.isfinite(pr['measured_white_pawns']) and abs(pr['measured_white_pawns']-w[pr['type']]/208)<=.011
 assert len(r['candidate_leaf_probes'])==5

def bounded(c):
 s=c['result']['score'];color=c['context']['agent_color']
 return (1 if s['winner']==color else -1) if s['terminal'] and s['winner'] is not None else 0 if s['terminal'] else s['quantity_difference']/15
rows=[]
for op in (6,24):
 arms={}
 for arm in ('unit','learned'):
  cs=[c for c in D['calls'] if c['context']['name'].startswith(f'p{op}-a{arm}-')]
  assert len(cs)==16
  arms[arm]=dict(games=16,bounded_return_mean=statistics.mean(bounded(c) for c in cs),original_reward_mean=statistics.mean(c['result']['reward'] for c in cs),cutoff_component_mean=statistics.mean(c['result']['score']['cutoff_quantity_component'] for c in cs),mates=sum(c['result']['score']['termination']=='CHECKMATE' for c in cs),wins=sum(c['result']['score']['winner']==c['context']['agent_color'] for c in cs))
 pairs=[]
 for oi in range(8):
  for color in (True,False):
   a=by[f'p{op}-aunit-o{oi}-c{int(color)}'];b=by[f'p{op}-alearned-o{oi}-c{int(color)}'];aa=a['result']['actions'];bb=b['result']['actions'];first=next((i for i,(x,y) in enumerate(zip(aa,bb)) if x!=y),None)
   pairs.append(dict(opening=oi,color=color,bounded_return_delta=bounded(b)-bounded(a),original_reward_delta=b['result']['reward']-a['result']['reward'],same_actions=aa==bb,first_divergence_ply=first))
 rows.append(dict(opening_plies=op,arms=arms,pairs=pairs,improved=sum(z['bounded_return_delta']>0 for z in pairs),worse=sum(z['bounded_return_delta']<0 for z in pairs),ties=sum(z['bounded_return_delta']==0 for z in pairs),paired_bounded_mean_delta=statistics.mean(z['bounded_return_delta'] for z in pairs)))
out=dict(complete=True,scope='Actual new-seed material deployment control, not training/human recovery',input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),legal_action_replays=legal,actual_search_calls=searches,leaf_probes_verified=320,reported_nodes_total=sum(nodes),reported_nodes_min=min(nodes),reported_nodes_max=max(nodes),all2regimes=rows,mean_paired_bounded_delta=statistics.mean(z['bounded_return_delta'] for r in rows for z in r['pairs']),metric_frozen=True,model_frozen=True,posthoc_selection=False,limits='32pairs over8opening seeds and2regimes. Conditionalmaturepriors, fixed16ply randomopponent. No Elo/standardratio/generalrule claim.',audit_seconds=time.monotonic()-started)
(OUT/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))