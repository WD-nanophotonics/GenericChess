"""Replay frozen actual Task121; no engine or training callbacks here."""
import json,math,random,sys,importlib.util,hashlib,time,statistics
from pathlib import Path
import chess
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux/task122';OUT.mkdir(exist_ok=True)
def load(n,p):
 s=importlib.util.spec_from_file_location(n,ROOT/p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
G=load('g104audit','results/dev_aux/task104/short_game.py');E=load('e108audit','results/dev_aux/task108/evolution.py')
p=ROOT/'results/dev_aux/task121/controller.json';d=json.loads(p.read_bytes());calls=d['calls']; assert d['completed'] and len(calls)==480
byname={c['context']['name']:c for c in calls};assert len(byname)==480
nodes=[];nsearch=0;nmoves=0;summaries=[];started=time.monotonic()
for c in calls:
 x=c['context'];r=c['result'];w=c['weights'];b=chess.Board();hist=[];si=0; rng=random.Random(x['random_seed'])
 assert r['opening']==G.opening(x['opening_seed'])
 for u in r['opening']:
  m=chess.Move.from_uci(u);assert m in b.legal_moves;b.push(m);hist.append(u)
 for u in r['actions']:
  assert not b.is_game_over(claim_draw=False)
  m=chess.Move.from_uci(u);assert m in b.legal_moves
  if b.turn==x['agent_color']:
   sr=r['search_records'][si];assert sr['full_history']==hist and sr['nodes_limit']==1024
   assert sr['backend']=='QUALIFIED_FAIRY_MATERIAL:477628ae141c6e5fb7dcb562e31e3bc40eab95b20c8b966ece131a1dbf090999'
   nodes.append(sr['reported_nodes']);si+=1;nsearch+=1
  else:assert m==rng.choice(sorted(b.legal_moves,key=lambda z:z.uci()))
  b.push(m);hist.append(u);nmoves+=1
 assert si==len(r['search_records']);assert b.fen()==r['final_fen']
 assert len(r['actions'])==16 or b.is_game_over(claim_draw=False)
 score=G.score(b,x['agent_color'],len(r['actions']),16);assert score==r['score'] and score['reward']==r['reward']
 assert len(r['candidate_leaf_probes'])==5
 for pr in r['candidate_leaf_probes']:
  assert pr['expected_white_pawns']==w[pr['type']]/208
  assert abs(pr['measured_white_pawns']-w[pr['type']]/208)<=.011
 summaries.append(dict(name=x['name'],phase=x['phase'],weights=w,score=score,plies=len(r['actions'])))
# Reconstruct exact frozen scheduler and all choices from logged callbacks.
def replay(w,x,deadline):
 c=byname[x['name']];assert c['context']==x and c['weights']==w;return c['result']
ctrl=E.Experiment(replay,budget_seconds=900);rec=ctrl.run(json.loads((ROOT/'results/dev_aux/task120/pilot16/pilot.json').read_bytes())['rows'])
assert rec['runs']==d['runs'] and rec['calls']==calls
# Explicitly posthoc: endpoints were already exposed before this reference/distance choice.
ref={'N':3,'B':3,'R':5,'Q':9}
def ratios(w):return {k:w[k]/w['P'] for k in E.TYPES}
def distance(w):return sum(abs(math.log(w[k]/w['P']/ref[k])) for k in E.TYPES)/4
rows=[]
for run in d['runs']:
 seed=run['seed'];h=[c for c in calls if c['context']['phase']=='heldout' and c['context']['name'].startswith('s'+str(seed)+'-')]
 arms={}
 for arm in ('initial','final'):
  a=[c['result']['score'] for c in h if '-a'+arm+'-' in c['context']['name']]
  arms[arm]=dict(games=len(a),reward_mean=statistics.mean(z['reward'] for z in a),cutoff_quantity_component_mean=statistics.mean(z['cutoff_quantity_component'] for z in a),cutoff_mean_among_nonterminal=statistics.mean(z['cutoff_quantity_component'] for z in a if not z['terminal']),wins=sum(z['winner']==chess.WHITE if c['context']['agent_color'] else z['winner']==chess.BLACK for c,z in zip([c for c in h if '-a'+arm+'-' in c['context']['name']],a)),mates=sum(z['termination']=='CHECKMATE' for z in a),terminal_games=sum(z['terminal'] for z in a))
 pairs=[]
 for oi in range(4):
  for color in (True,False):
   a=byname[f's{seed}-heldout-ainitial-o{oi}-c{int(color)}']['result']['score'];b=byname[f's{seed}-heldout-afinal-o{oi}-c{int(color)}']['result']['score']
   pairs.append(dict(opening_index=oi,color=color,reward_delta=b['reward']-a['reward'],cutoff_component_delta=b['cutoff_quantity_component']-a['cutoff_quantity_component'],both_nonterminal=not(a['terminal'] or b['terminal']),both_nonterminal_quantity_delta=b['quantity_difference']/15-a['quantity_difference']/15 if not(a['terminal'] or b['terminal']) else None))
 rows.append(dict(seed=seed,initial_ratios=ratios(run['initial_weights']),final_ratios=ratios(run['final_weights']),updates=sum(z['selected']!=0 for z in run['iterations']),heldout=arms,paired=pairs,posthoc_initial_log_distance=distance(run['initial_weights']),posthoc_final_log_distance=distance(run['final_weights'])))
result=dict(scope='Replay of already exposed frozen Task121; no new games',input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),complete=True,games=480,legal_action_replays=nmoves,actual_search_calls=nsearch,leaf_probes_verified=2400,exact_controller_and_selection_replayed=True,reported_nodes_min=min(nodes),reported_nodes_max=max(nodes),reported_nodes_total=sum(nodes),nodes_over_configured=sum(n>1024 for n in nodes),training_terminal_count=sum(s['score']['terminal'] for s in summaries if s['phase']=='train'),heldout_terminal_count=sum(s['score']['terminal'] for s in summaries if s['phase']=='heldout'),all_three_rows=rows,traditional_reference=ref,reference_source='https://www.chess.com/terms/chess-piece-value',distance_definition='mean absolute log((piece/P)/traditional_reference) over NBRQ',reference_and_distance_selected_after_endpoint_exposure=True,human_description_status='EXPLORATORY_POSTHOC_NOT_INDEPENDENT_RECOVERY_TEST',audit_seconds=time.monotonic()-started)
(OUT/'audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');(OUT/'game_summary.json').write_text(json.dumps(summaries,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))