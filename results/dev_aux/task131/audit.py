"""Replay changed terminal-input contract with bound actual cached prefix."""
import json,hashlib,importlib.util,random,math,statistics,time
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task131';p=O/'controller.json';D=json.loads(p.read_bytes());decl=json.loads((O/'declaration.json').read_bytes());F=json.loads((O/'opening_contract.json').read_bytes());oldpath=R/'results/dev_aux/task129/controller.json';old=json.loads(oldpath.read_bytes());assert hashlib.sha256(oldpath.read_bytes()).hexdigest()==decl['source_controller_sha256'];assert not old['completed']
s=importlib.util.spec_from_file_location('g131audit',R/'results/dev_aux/task104/short_game.py');G=importlib.util.module_from_spec(s);s.loader.exec_module(G)
s=importlib.util.spec_from_file_location('e131audit',R/'results/dev_aux/task108/evolution.py');E=importlib.util.module_from_spec(s);s.loader.exec_module(E)
assert D['completed'] and len(D['calls'])==3552 and len(D['runs'])==3;calls=D['calls'];by={c['context']['name']:c for c in calls};assert len(by)==3552
counts=dict(cached=0,new=0,excluded=0,moves=0,searches=0,leaf_probes=0);nodes=[];started=time.monotonic()
for c in calls:
 x=c['context'];fixture=F[str(x['opening_seed'])]
 if c.get('status')=='EXCLUDED_INPUT':
  assert fixture['terminal'] and c['result'] is None and c['selection_contribution']==0 and c['opening']==fixture['moves'];assert chess.Board(fixture['fen']).is_game_over(claim_draw=False);counts['excluded']+=1;continue
 assert not fixture['terminal'];r=c['result'];w=c['weights'];assert r['opening']==fixture['moves']
 if c['provenance']=='CACHED_ACTUAL_TASK129':
  i=c['source_call_index'];assert i==counts['cached'];assert {k:c[k] for k in ('context','weights','result')}==old['calls'][i];counts['cached']+=1
 else:assert c['provenance']=='NEW_ACTUAL_TASK131';counts['new']+=1
 b=chess.Board();hist=[];si=0;rng=random.Random(x['random_seed'])
 for u in r['opening']:
  m=chess.Move.from_uci(u);assert m in b.legal_moves;b.push(m);hist.append(u)
 for u in r['actions']:
  assert not b.is_game_over(claim_draw=False);m=chess.Move.from_uci(u);assert m in b.legal_moves
  if b.turn==x['agent_color']:
   sr=r['search_records'][si];assert sr['full_history']==hist and sr['nodes_limit']==1024 and sr['backend']=='QUALIFIED_FAIRY_MATERIAL:477628ae141c6e5fb7dcb562e31e3bc40eab95b20c8b966ece131a1dbf090999';nodes.append(sr['reported_nodes']);si+=1;counts['searches']+=1
  else:assert m==rng.choice(sorted(b.legal_moves,key=lambda z:z.uci()))
  b.push(m);hist.append(u);counts['moves']+=1
 assert b.fen()==r['final_fen'] and si==len(r['search_records']);assert len(r['actions'])==16 or b.is_game_over(claim_draw=False)
 assert G.score(b,x['agent_color'],len(r['actions']),16)==r['score'] and r['score']['reward']==r['reward']
 assert [z['type'] for z in r['candidate_leaf_probes']]==list('PNBRQ')
 for z in r['candidate_leaf_probes']:assert math.isfinite(z['measured_white_pawns']) and abs(z['measured_white_pawns']-w[z['type']]/208)<=.011;counts['leaf_probes']+=1
assert counts['cached']==816 and counts['new']==2718 and counts['excluded']==18
seen=[];summary=[];steps=[(E.HIGH-E.LOW)/2**(i+1) for i in range(6)];ref=dict(N=3,B=3,R=5,Q=9)
def dist(w):return statistics.mean(abs(math.log(w[k]/208/ref[k])) for k in 'NBRQ')
for run in D['runs']:
 seed=run['seed'];theta=E.starts(seed);assert run['initial_weights']==E.weights(theta) and len(run['updates'])==24
 for sweep,step in enumerate(steps):
  for k in range(4):
   candidates=[theta[:],theta[:],theta[:]];candidates[1][k]=min(E.HIGH,theta[k]+step);candidates[2][k]=max(E.LOW,theta[k]-step);groups=[]
   for arm,t in enumerate(candidates):
    rewards=[]
    for oi in range(8):
     for color in (True,False):
      name=f's{seed}-train-sweep{sweep}-k{k}-a{arm}-o{oi}-c{int(color)}';seen.append(name);c=by[name]
      assert c['weights']==E.weights(t) and c['context']['opening_seed']==87000+(sweep*4+k)*8+oi and c['context']['random_seed']==97000+(sweep*4+k)*8+oi
      rewards.append(c['selection_contribution'] if c.get('status')=='EXCLUDED_INPUT' else c['result']['reward'])
    groups.append(rewards)
   means=[sum(z)/16 for z in groups];choice=max(range(3),key=lambda i:means[i]);before=E.weights(theta);theta=candidates[choice][:]
   expected=dict(sweep=sweep,coordinate=E.TYPES[k],step=step,before=before,candidate_weights=[E.weights(t) for t in candidates],means=means,rewards=groups,selected=choice,after=E.weights(theta));assert expected==run['updates'][sweep*4+k]
 assert E.weights(theta)==run['final_weights'];h=[];arms={}
 for arm in ('initial','final'):
  games=[]
  for oi in range(8):
   for color in (True,False):
    name=f's{seed}-heldout-sweep0-k0-a{arm}-o{oi}-c{int(color)}';seen.append(name);c=by[name];assert c['weights']==run[arm+'_weights'] and c['context']['opening_seed']==89000+oi and c['context']['random_seed']==99000+oi
    assert c.get('status')!='EXCLUDED_INPUT';games.append(c);h.append(dict(arm=arm,opening_index=oi,color=color,reward=c['result']['reward']))
  arms[arm]=dict(games=16,reward_mean=statistics.mean(c['result']['reward'] for c in games),quantity_component_mean=statistics.mean(c['result']['score']['cutoff_quantity_component'] for c in games),terminal_component_mean=statistics.mean(c['result']['score']['terminal_component'] for c in games),speed_component_mean=statistics.mean(c['result']['score']['mate_speed_component'] for c in games),mates=sum(c['result']['score']['termination']=='CHECKMATE' for c in games),wins=sum(c['result']['score']['winner']==c['context']['agent_color'] for c in games))
 assert h==run['heldout']
 pairs=[]
 for oi in range(8):
  for color in (True,False):
   a=by[f's{seed}-heldout-sweep0-k0-ainitial-o{oi}-c{int(color)}']['result']['score'];b=by[f's{seed}-heldout-sweep0-k0-afinal-o{oi}-c{int(color)}']['result']['score']
   pairs.append(dict(opening=oi,color=color,reward_delta=b['reward']-a['reward'],both_nonterminal=not(a['terminal'] or b['terminal']),quantity_delta_if_both_nonterminal=(b['quantity_difference']-a['quantity_difference'])/15 if not(a['terminal'] or b['terminal']) else None))
 summary.append(dict(seed=seed,initial_ratios={k:run['initial_weights'][k]/208 for k in 'NBRQ'},final_ratios={k:run['final_weights'][k]/208 for k in 'NBRQ'},accepted_updates=sum(z['selected']!=0 for z in run['updates']),reference_initial_distance=dist(run['initial_weights']),reference_final_distance=dist(run['final_weights']),heldout=arms,paired=pairs,paired_reward_mean_delta=statistics.mean(z['reward_delta'] for z in pairs),paired_reward_median_delta=statistics.median(z['reward_delta'] for z in pairs)))
assert seen==[c['context']['name'] for c in calls]
out=dict(complete=True,input_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),scope='Changed terminal-input contract exploratory coordinate control; cached prefix is not an independent fresh trial',trial_slots=3552,unique_actual_games=3534,counts=counts,actual_training_games=3438,actual_heldout_games=96,all3rows=summary,exact_schedule_and_selection=True,excluded_root_seed=87136,excluded_slots_symmetrically18=True,old_task129_stays_failed=True,per_seed_freeze_then_heldout_no_crossseed_feedback=True,reported_nodes_total=sum(nodes),reported_nodes_min=min(nodes),reported_nodes_max=max(nodes),audit_seconds=time.monotonic()-started)
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='all3rows'}));print(json.dumps([{k:v for k,v in r.items() if k!='paired'} for r in summary]))