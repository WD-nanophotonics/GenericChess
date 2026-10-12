"""Independentactualtrace and controller replay for fixedopponent learning."""
import json,math,random,time,sys,importlib.util,hashlib
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task215';O.mkdir(exist_ok=True)
for alias,path in [('E','results/dev_aux/task108/evolution.py'),('G','results/dev_aux/task104/short_game.py')]:
 s=importlib.util.spec_from_file_location(alias+'161',R/path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);globals()[alias]=m
def unit(b,color):
 out=b.outcome(claim_draw=False)
 if out:return 0 if out.winner is None else (1000000 if out.winner==color else -1000000)
 return 208*sum(len(b.pieces(t,color))-len(b.pieces(t,not color)) for t in range(1,6))
def replay(task):
 P=R/f'results/dev_aux/task{task}';D=json.loads((R/'results/dev_aux/task214/declaration.json').read_bytes());C=json.loads((P/'controller.json').read_bytes());assert C['complete'];calls=C['calls'];counts=dict(games=0,moves=0,engine_searches=0,opponent_searches=0,opponent_leaf_nodes=0,probes=0,table_acks=0);cache={};cache_hits=0;nodes=[];started=time.monotonic()
 for c in calls:
  r=c['result'];x=c['context'];w=c['weights'];roots=D['train_roots' if x['phase']=='train' else 'heldout_roots'];fixture=roots[x['root_index']];fen=fixture['initial_fen'];assert r['root_fen']==fen and r['opening_history']==fixture['history'];b=chess.Board(fen)
  for prelude in fixture['history']:b.push_uci(prelude)
  assert b.fen()==r['opening_fen']==fixture['expected_fen'];rng=random.Random(x['random_seed']);si=oi=0
  for counts_local,text in enumerate(r['actions']):
   assert not b.is_game_over(claim_draw=False);move=chess.Move.from_uci(text);assert move in b.legal_moves
   if b.turn==x['agent_color']:
    meta=r['search_records'][si];assert meta['root_fen']==fen and meta['full_history']==[m.uci() for m in b.move_stack] and meta['backend'].endswith(D['binary_sha256']) and meta['nodes_limit']==1024;assert isinstance(meta['reported_nodes'],int) and meta['reported_nodes']>0;nodes.append(meta['reported_nodes']);assert r['root_features'][si]==dict(ply=counts_local,features_actor=[len(b.pieces(t,x['agent_color']))-len(b.pieces(t,not x['agent_color'])) for t in range(1,6)],root_fen=b.fen());si+=1;counts['engine_searches']+=1
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
  assert si==len(r['search_records']) and oi==len(r['opponent_records']) and b.fen()==r['final_fen'];assert G.score(b,x['agent_color'],len(r['actions']),D['cap'])==r['score'] and r['reward']==r['score']['reward'];counts['games']+=1
  assert len(r['price_probes'])==5
  for p in r['price_probes']:assert math.isfinite(p['measured_white_pawns']) and abs(p['measured_white_pawns']-w[p['type']]/208)<=.011;counts['probes']+=1
  assert r['table_ack']['alignment']==3 and r['table_ack']['prices']=={str(i+1):[w[k],w[k]] for i,k in enumerate('PNBRQ')};counts['table_acks']+=1

 def read_value(meta):
  lines=[z for z in meta['uci_info'] if ' score ' in z and ' pv ' in z and 'lowerbound' not in z and 'upperbound' not in z]
  if not lines:return None
  f=lines[-1].split();k=f.index('score');kind=f[k+1];n=int(f[k+2])
  if kind=='mate' and n==0:return None
  return dict(kind=kind,raw=n,bounded=math.tanh(n/400) if kind=='cp' else (1 if n>0 else -1),line=lines[-1])
 def rows_for(games):
  rows=[];excluded=[]
  for c in games:
   r=c['result'];col=r['agent_color'];b=chess.Board(r['root_fen'])
   for m in r['opening_history']:b.push_uci(m)
   states=[];ix=0
   for ply,m in enumerate(r['actions']):
    if b.turn==col:states.append((b.copy(stack=True),r['search_records'][ix],ply));ix+=1
    b.push_uci(m)
   for i,(board,meta,ply) in enumerate(states):
    after=board.copy(stack=True)
    for m in r['actions'][ply:ply+2]:after.push_uci(m)
    outcome=after.outcome(claim_draw=False)
    if outcome:y=0 if outcome.winner is None else (1 if outcome.winner==col else -1);kind='true_terminal';v=None
    elif i+1<len(states):
     nxt=states[i+1][1];assert nxt['full_history']==[m.uci() for m in after.move_stack];v=read_value(nxt)
     if v is None:excluded.append(dict(game=c['context']['name'],index=i,reason='no_unbounded_successor_value'));continue
     y=v['bounded'];kind='search_bootstrap'
    else:excluded.append(dict(game=c['context']['name'],index=i,reason='unknown_cutoff_no_successor'));continue
    phi=[len(board.pieces(t,col))-len(board.pieces(t,not col)) for t in range(1,6)];rows.append(dict(game=c['context']['name'],index=i,features=phi,target=y,target_kind=kind,successor_value=v))
  return rows,excluded
 index=0;updates=0;loss_increases=0
 def block(w,seed,mode,round_,phase,opponent):
  nonlocal index
  games=[]
  for oi in range(len(D['train_roots' if phase=='train' else 'heldout_roots'])):
   for color in (True,False):
    rs=D['train_random_seed_base']+round_*8+oi if phase=='train' else D['heldout_random_seed_base']+oi;name=f's{seed}-{mode}-{phase}-r{round_}-{opponent}-o{oi}-c{int(color)}';context=dict(name=name,seed=seed,mode=mode,round=round_,phase=phase,opponent=opponent,root_index=oi,agent_color=color,random_seed=rs);c=calls[index];assert c['context']==context and c['weights']==w;games.append(c);index+=1
  return games
 for seed,mode in D['method_order']:
  theta=E.starts(seed);run=next(r for r in C['runs'] if r['seed']==seed and r['mode']==mode);initial=E.weights(theta);assert run['initial_weights']==initial and run['initial_theta']==theta
  for round_ in range(D['rounds']):
   z=run['rounds'][round_];teacher=initial if mode=='fixed_teacher' else E.weights(theta);assert z['teacher_weights']==teacher and max(abs(a-b) for a,b in zip(theta,z['student_before']))<1e-12;games=block(teacher,seed,mode,round_,'train','random');rows,excluded=rows_for(games);assert rows==z['all_transitions'] and excluded==z['excluded'];ui=0
   for row in rows:
    if mode=='terminal_only' and row['target_kind']!='true_terminal':continue
    phi=row['features'];ratios=list(map(math.exp,theta));v=math.tanh((phi[0]+sum(p*r for p,r in zip(phi[1:],ratios)))/4);grad=[(1-v*v)/4*p*r for p,r in zip(phi[1:],ratios)];delta=row['target']-v;alpha=D['alpha']/max(1,sum(g*g for g in grad));after=[max(E.LOW,min(E.HIGH,t+alpha*delta*g)) for t,g in zip(theta,grad)];vv=math.tanh((phi[0]+sum(p*math.exp(t) for p,t in zip(phi[1:],after)))/4);u=z['updates'][ui];assert u['game']==row['game'] and u['index']==row['index'];assert max(abs(a-b) for a,b in zip(u['before'],theta))<1e-12 and max(abs(a-b) for a,b in zip(u['after'],after))<1e-12 and max(abs(a-b) for a,b in zip(u['gradient'],grad))<1e-12;assert abs(u['value']-v)<1e-12 and abs(u['delta']-delta)<1e-12 and abs(u['alpha']-alpha)<1e-12 and u['target']==row['target'];assert abs(u['loss_before']-delta*delta)<1e-12 and abs(u['loss_after']-(row['target']-vv)**2)<1e-12
    # With actor/white signs bothnegated forblack, delta*gradient isidentical.
    sign=1 if games[0]['result']['agent_color'] else -1
    assert all(abs(delta*g-(-delta)*(-g))<1e-12 for g in grad)
    loss_increases+=u['loss_after']>u['loss_before']+1e-12;theta=after;updates+=1;ui+=1
   assert ui==len(z['updates']) and max(abs(a-b) for a,b in zip(theta,z['student_after']))<1e-12
  assert E.weights(theta)==run['final_weights']
 assert index==D['planned_train_games'];end=json.loads((P/'endpoints.json').read_bytes());assert end['complete'] and end['training_calls']==index and end['all_endpoints_frozen_at']==C['all_endpoints_frozen_at'] and len(end['ends'])==9
 for seed in D['start_seeds']:
  initial=next(r['initial_weights'] for r in C['runs'] if r['seed']==seed)
  for opponent in D['opponents_heldout']:block(initial,seed,'shared_initial',0,'heldout',opponent)
 for r in C['runs']:
  for opponent in D['opponents_heldout']:block(r['final_weights'],r['seed'],r['mode'],0,'heldout',opponent)
 assert index==len(calls)==D['planned_unique_games']
 out=dict(complete=True,source_task=task,source_controller_sha256=hashlib.sha256((P/'controller.json').read_bytes()).hexdigest(),counts=counts,updates_verified=updates,individual_loss_increases=loss_increases,all9ends_beforeheldout=True,reported_nodes_total=sum(nodes),reported_nodes_min=min(nodes),reported_nodes_max=max(nodes),opponent_unique_histories=len(cache),audit_cache_hits=cache_hits,seconds=time.monotonic()-started,scope='Completeactuallegality/history/RNG/opponenttree/probes/tables/targets/fixedteacher boundaries/semigradient/control schedule replay. Sharedinitialbaselinecountedoncephysical, all9pairedmethodsuseit; no independentreplicationclaim/newgames.')
 (O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
if __name__=='__main__':replay('214')
