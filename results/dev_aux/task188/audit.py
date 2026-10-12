"""Independentactualtrace and controller replay for fixedopponent learning."""
import json,math,random,time,sys,importlib.util,hashlib
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task188';O.mkdir(exist_ok=True)
for alias,path in [('E','results/dev_aux/task108/evolution.py'),('G','results/dev_aux/task104/short_game.py')]:
 s=importlib.util.spec_from_file_location(alias+'161',R/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);globals()[alias]=m
def unit(b,color):
 out=b.outcome(claim_draw=False)
 if out:return 0 if out.winner is None else (1000000 if out.winner==color else -1000000)
 return 208*sum(len(b.pieces(t,color))-len(b.pieces(t,not color)) for t in range(1,6))
def replay(task):
 P=R/f'results/dev_aux/task{task}';D=json.loads((R/'results/dev_aux/task187/declaration.json').read_bytes());C=json.loads((P/'controller.json').read_bytes());assert C['completed'];D.update(json.loads((P/'metadata_correction.json').read_bytes())['corrections']);calls=C['calls'];counts=dict(games=0,moves=0,engine_searches=0,opponent_searches=0,opponent_leaf_nodes=0,probes=0,table_acks=0);cache={};cache_hits=0;nodes=[];started=time.monotonic()
 for c in calls:
  r=c['result'];x=c['context'];w=c['weights'];roots=D['train_roots' if x['phase']=='train' else 'heldout_roots'];fixture=roots[x['root_index']];fen=fixture['initial_fen'];assert r['root_fen']==fen and r['opening_history']==fixture['history'];b=chess.Board(fen)
  for prelude in fixture['history']:b.push_uci(prelude)
  assert b.fen()==r['opening_fen']==fixture['expected_fen'];rng=random.Random(x['random_seed']);si=oi=0
  for text in r['actions']:
   assert not b.is_game_over(claim_draw=False);move=chess.Move.from_uci(text);assert move in b.legal_moves
   if b.turn==x['agent_color']:
    meta=r['search_records'][si];assert meta['root_fen']==fen and meta['full_history']==[m.uci() for m in b.move_stack] and meta['backend'].endswith(D['binary_sha256']) and meta['nodes_limit']==1024;assert isinstance(meta['reported_nodes'],int) and meta['reported_nodes']>0;nodes.append(meta['reported_nodes']);si+=1;counts['engine_searches']+=1
   elif x['opponent'].startswith('random'):assert move==rng.choice(sorted(b.legal_moves,key=lambda m:m.uci()))
   else:
    meta=r['opponent_records'][oi];assert meta['completed'] and meta['root_fen']==b.fen() and meta['full_history']==[m.uci() for m in b.move_stack]
    key=(fen,tuple(m.uci() for m in b.move_stack));opp=b.turn
    if key in cache:rows,nn=cache[key];cache_hits+=1
    else:
     rows=[];nn=0
     for candidate in sorted(b.legal_moves,key=lambda m:m.uci()):
      b.push(candidate)
      if b.is_game_over(claim_draw=False):vv=[unit(b,opp)];nn+=1
      else:
       vv=[]
       for reply in sorted(b.legal_moves,key=lambda m:m.uci()):
        b.push(reply);vv.append(unit(b,opp));nn+=1;b.pop()
      rows.append(dict(move=candidate.uci(),worst=min(vv),reply_count=len(vv)));b.pop()
     cache[key]=(rows,nn)
    assert rows==meta['rows'] and nn==meta['leaf_nodes'];best=max(row['worst'] for row in rows);assert meta['value']==best and move.uci()==next(row['move'] for row in rows if row['worst']==best)
    oi+=1;counts['opponent_searches']+=1;counts['opponent_leaf_nodes']+=nn
   b.push(move);counts['moves']+=1
  assert si==len(r['search_records']) and oi==len(r['opponent_records']) and b.fen()==r['final_fen'];assert G.score(b,x['agent_color'],len(r['actions']),16)==r['score'] and r['original_reward']==r['score']['reward'];out=b.outcome(claim_draw=False);bounded=(0 if out.winner is None else (1 if out.winner==x['agent_color'] else -1)) if out else r['score']['quantity_difference']/15; assert bounded==r['bounded_reward'] and r['reward']==(bounded if x['opponent'].endswith('bounded') else r['original_reward']);counts['games']+=1
  assert len(r['price_probes'])==5
  for p in r['price_probes']:assert math.isfinite(p['measured_white_pawns']) and abs(p['measured_white_pawns']-w[p['type']]/208)<=.011;counts['probes']+=1
  assert r['table_ack']['alignment']==3 and r['table_ack']['prices']=={str(i+1):[w[k],w[k]] for i,k in enumerate('PNBRQ')};counts['table_acks']+=1
 index=0;choices=0
 def block(w,seed,opponent,sweep,k,arm,phase):
  nonlocal index
  rewards=[]
  for oi in range(len(D['train_roots' if phase=='train' else 'heldout_roots'])):
   for color in (True,False):
    rs=(2026500000+(sweep*4+k)*8+oi) if phase=='train' else 2026600000+oi
    x=dict(name=f's{seed}-{opponent}-{phase}-g{sweep}-k{k}-a{arm}-o{oi}-c{int(color)}',start_seed=seed,opponent=opponent,phase=phase,sweep=sweep,coordinate=k,arm=arm,root_index=oi,agent_color=color,random_seed=rs)
    c=calls[index];assert c['context']==x and c['weights']==w;index+=1;rewards.append(c['result']['reward'])
  return rewards
 for seed,opponent in D['method_order']:
  theta=E.starts(seed);run=next(r for r in C['runs'] if r['seed']==seed and r['opponent']==opponent);assert run['initial_weights']==E.weights(theta)
  for sweep,step in enumerate(D['steps']):
   for k in range(4):
    candidate=[theta[:],theta[:],theta[:]];candidate[1][k]=min(E.HIGH,theta[k]+step);candidate[2][k]=max(E.LOW,theta[k]-step);groups=[block(E.weights(t),seed,opponent,sweep,k,a,'train') for a,t in enumerate(candidate)];means=[sum(z)/len(z) for z in groups];integer_sums=[sum(round(v*240) for v in group) for group in groups];selected=E.select(integer_sums)
    expected=dict(sweep=sweep,coordinate=E.TYPES[k],step=step,before=E.weights(theta),candidate_weights=[E.weights(t) for t in candidate],means=means,integer_sums_240=integer_sums,rewards=groups,selected=selected,after=E.weights(candidate[selected]));assert expected==run['updates'][sweep*4+k];theta=candidate[selected][:];choices+=1
  assert run['final_weights']==E.weights(theta)
 assert index==D['train_slots'];end=json.loads((P/'endpoints.json').read_bytes());assert end['complete'] and end['training_calls']==index and end['all_endpoints_frozen_at']==C['global_endpoint_freeze_at']
 for run in C['runs']:
  for arm in ('initial','final'):
   expected=block(run[arm+'_weights'],run['seed'],run['opponent'],0,0,arm,'heldout');assert expected==[x['reward'] for x in run['heldout'] if x['arm']==arm]
 assert index==len(calls)==D['total_slots']
 out=dict(complete=True,source_task=task,source_controller_sha256=hashlib.sha256((P/'controller.json').read_bytes()).hexdigest(),counts=counts,updates_verified=choices,allends_beforeheldout=True,reported_nodes_total=sum(nodes),reported_nodes_min=min(nodes),reported_nodes_max=max(nodes),opponent_unique_histories=len(cache),audit_cache_hits=cache_hits,seconds=time.monotonic()-started,scope='Exactauditcache keyedinitialFEN+fullhistory, preservesdraw/history; notgamecache/newphysicalevidence. Independentcompleteopponent/agent/legal/reward/table/schedule replay; noenginererun.')
 (O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
if __name__=='__main__':replay('187')
