"""Independent replay of the declared Task124 schedule and physical games."""
import hashlib,importlib.util,json,math,random,statistics,time
from pathlib import Path
import chess
ROOT=Path.cwd();OUT=ROOT/'results/dev_aux/task125'
def load(n,p):
 s=importlib.util.spec_from_file_location(n,ROOT/p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
G=load('g104for125','results/dev_aux/task104/short_game.py');E=load('e108for125','results/dev_aux/task108/evolution.py')
p=ROOT/'results/dev_aux/task124/controller.json';D=json.loads(p.read_bytes());calls=D['calls'];assert D['completed'] and len(calls)==1920 and len(D['runs'])==6
assert sum(x['context']['phase']=='train' for x in calls)==1728
by={c['context']['name']:c for c in calls};assert len(by)==1920
started=time.monotonic();nodes=[];moves=0;searches=0
for c in calls:
 x=c['context'];r=c['result'];w=c['weights'];op=int(x['name'].split('-p')[1].split('-')[0]);assert op in (6,24)
 assert r['opening']==G.opening(x['opening_seed'],plies=op)
 b=chess.Board();hist=[];si=0;rng=random.Random(x['random_seed'])
 for text in r['opening']:
  m=chess.Move.from_uci(text);assert m in b.legal_moves;b.push(m);hist.append(text)
 for text in r['actions']:
  assert not b.is_game_over(claim_draw=False);m=chess.Move.from_uci(text);assert m in b.legal_moves
  if b.turn==x['agent_color']:
   sr=r['search_records'][si];assert sr['full_history']==hist and sr['nodes_limit']==1024
   assert sr['backend']=='QUALIFIED_FAIRY_MATERIAL:477628ae141c6e5fb7dcb562e31e3bc40eab95b20c8b966ece131a1dbf090999'
   assert isinstance(sr['reported_nodes'],int) and sr['reported_nodes']>=0;nodes.append(sr['reported_nodes']);si+=1;searches+=1
  else:assert m==rng.choice(sorted(b.legal_moves,key=lambda z:z.uci()))
  b.push(m);hist.append(text);moves+=1
 assert si==len(r['search_records']) and b.fen()==r['final_fen']
 assert len(r['actions'])==16 or b.is_game_over(claim_draw=False)
 s=G.score(b,x['agent_color'],len(r['actions']),16);assert s==r['score'] and s['reward']==r['reward']
 assert [z['type'] for z in r['candidate_leaf_probes']]==list('PNBRQ')
 for pr in r['candidate_leaf_probes']:
  assert pr['expected_white_pawns']==w[pr['type']]/208 and math.isfinite(pr['measured_white_pawns']) and abs(pr['measured_white_pawns']-w[pr['type']]/208)<=.011
seen=[];summary=[];reference={'N':3,'B':3,'R':5,'Q':9}
def distance(w):return statistics.mean(abs(math.log(w[k]/208/reference[k])) for k in 'NBRQ')
for run in D['runs']:
 seed=run['seed'];op=run['opening_plies'];theta=E.starts(seed);rng=random.Random(seed+900000);assert run['initial_weights']==E.weights(theta);assert len(run['iterations'])==6
 for g,iteration in enumerate(run['iterations']):
  delta=[rng.choice((-1,1)) for _ in E.TYPES];candidates=[theta[:]]+[[max(E.LOW,min(E.HIGH,t+sgn*.4*z)) for t,z in zip(theta,delta)] for sgn in (1,-1)]
  groups=[]
  for a,t in enumerate(candidates):
   rewards=[]
   for oi in range(8):
    for color in (True,False):
     name=f's{seed}-p{op}-train-g{g}-a{a}-o{oi}-c{int(color)}';seen.append(name);c=by[name]
     assert c['weights']==E.weights(t) and c['context']['opening_seed']==83000+g*8+oi and c['context']['random_seed']==93000+g*8+oi
     rewards.append(c['result']['reward'])
   groups.append(rewards)
  means=[sum(z)/16 for z in groups];chosen=max(range(3),key=lambda a:means[a]);assert means[chosen]>=means[0]
  before=E.weights(theta);theta=candidates[chosen][:]
  expected=dict(generation=g,before=before,delta=delta,means=means,rewards=groups,selected=chosen,after=E.weights(theta));assert expected==iteration
 assert E.weights(theta)==run['final_weights']
 heldout=[];arms={}
 for arm in ('initial','final'):
  games=[]
  for oi in range(8):
   for color in (True,False):
    name=f's{seed}-p{op}-heldout-g0-a{arm}-o{oi}-c{int(color)}';seen.append(name);c=by[name];assert c['weights']==run[arm+'_weights'];assert c['context']['opening_seed']==85000+oi and c['context']['random_seed']==95000+oi
    heldout.append(dict(arm=arm,opening_index=oi,color=color,reward=c['result']['reward']));games.append(c)
  scores=[c['result']['score'] for c in games];arms[arm]=dict(games=16,reward_mean=statistics.mean(z['reward'] for z in scores),cutoff_component_mean=statistics.mean(z['cutoff_quantity_component'] for z in scores),terminal_component_mean=statistics.mean(z['terminal_component'] for z in scores),speed_component_mean=statistics.mean(z['mate_speed_component'] for z in scores),mates=sum(z['termination']=='CHECKMATE' for z in scores),wins=sum(c['result']['score']['winner']==c['context']['agent_color'] for c in games),losses=sum(c['result']['score']['winner'] is not None and c['result']['score']['winner']!=c['context']['agent_color'] for c in games))
 assert heldout==run['heldout']
 pairs=[]
 for oi in range(8):
  for color in (True,False):
   a=by[f's{seed}-p{op}-heldout-g0-ainitial-o{oi}-c{int(color)}']['result']['score'];b=by[f's{seed}-p{op}-heldout-g0-afinal-o{oi}-c{int(color)}']['result']['score']
   pairs.append(dict(opening=oi,color=color,reward_delta=b['reward']-a['reward'],both_nonterminal=not(a['terminal'] or b['terminal']),quantity_delta_if_both_nonterminal=(b['quantity_difference']-a['quantity_difference'])/15 if not(a['terminal'] or b['terminal']) else None))
 summary.append(dict(seed=seed,opening_plies=op,initial_ratios={k:run['initial_weights'][k]/208 for k in 'NBRQ'},final_ratios={k:run['final_weights'][k]/208 for k in 'NBRQ'},updates=sum(z['selected']!=0 for z in run['iterations']),human_reference_initial_distance=distance(run['initial_weights']),human_reference_final_distance=distance(run['final_weights']),heldout=arms,paired=pairs))
assert seen==[c['context']['name'] for c in calls]
assert {(r['seed'],r['opening_plies']) for r in D['runs']}=={(s,o) for s in (103,104,105) for o in (6,24)}
result=dict(complete=True,scope='Actual frozen Task124 replay and all6endpoint descriptive assessment',input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),physical_games=1920,legal_actions_replayed=moves,search_calls=searches,leaf_probes_verified=9600,exact_schedule_selection_and_call_order=True,reported_nodes_min=min(nodes),reported_nodes_max=max(nodes),reported_nodes_total=sum(nodes),all6rows=summary,reference_fixed_before_this_run=True,metric_and_reference_used_only_after_selection=True,independent_human_recovery_test=False,limits='Three starts reused; mixed mature priors, random opponent and16ply objective; exploratory changed-distribution control, not genericrules/Elo/convergence. All outcomes retained.',audit_seconds=time.monotonic()-started)
(OUT/'task124_audit.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='all6rows'}));print(json.dumps(summary))