import json,time,random,statistics,math,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task237';O.mkdir(exist_ok=True);D=json.loads((R/'results/dev_aux/task236/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task236/games.json').read_bytes());assert X['complete'] and len(X['calls'])==128;started=time.monotonic()
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);counts=dict(games=0,moves=0,agent_searches=0,unit_searches=0,unit_leaf_nodes=0,completed_D2=0,lower_completed=0,main_nodes=0,qnodes=0);depths={};times=[]
def value(b,col):
 out=b.outcome(claim_draw=False)
 if out:return 0 if out.winner is None else (1000000 if out.winner==col else -1000000)
 return 208*sum(len(b.pieces(t,col))-len(b.pieces(t,not col)) for t in range(1,6))
for c in X['calls']:
 r=c['result'];b=P.board(D['roots'][c['phase']][c['opening_index']]);assert r['opening_history']==D['roots'][c['phase']][c['opening_index']]['history'];color=r['agent_color'];rng=random.Random(c['random_seed']);si=oi=0
 for ply,text in enumerate(r['actions']):
  assert not b.is_game_over(claim_draw=False);move=chess.Move.from_uci(text);assert move in b.legal_moves
  if b.turn==color:
   m=r['search_records'][si];assert m['ply']==ply and m['root_fen']==b.fen() and m['full_history']==[z.uci() for z in b.move_stack];v=m['result'];a=v['action'];encoded=''.join(chr(97+a[k]['file'])+str(a[k]['rank']+1) for k in ('from_square','to_square'))+(a['promotion_target_id'].lower() if a['promotion_target_id'] else '');assert encoded==text;assert v['qnodes']==0 and not v['used_fallback'];depths[str(v['completed_depth'])]=depths.get(str(v['completed_depth']),0)+1;counts['completed_D2']+=v['completed_depth']==2;counts['lower_completed']+=v['completed_depth']<2;counts['main_nodes']+=v['nodes'];counts['qnodes']+=v['qnodes'];counts['agent_searches']+=1;times.append(m['wall_seconds']);si+=1
  elif c['opponent']=='random':assert move==rng.choice(sorted(b.legal_moves,key=lambda z:z.uci()))
  else:
   meta=r['opponent_records'][oi];assert meta['full_history']==[z.uci() for z in b.move_stack] and meta['root_fen']==b.fen();col=b.turn;rows=[];nodes=0
   for cand in sorted(b.legal_moves,key=lambda z:z.uci()):
    b.push(cand)
    if b.is_game_over(claim_draw=False):vv=[value(b,col)];nodes+=1
    else:
     vv=[]
     for reply in sorted(b.legal_moves,key=lambda z:z.uci()):b.push(reply);vv.append(value(b,col));nodes+=1;b.pop()
    b.pop();rows.append(dict(move=cand.uci(),worst=min(vv),reply_count=len(vv)))
   assert rows==meta['rows'] and nodes==meta['leaf_nodes'];best=max(z['worst'] for z in rows);assert text==next(z['move'] for z in rows if z['worst']==best);counts['unit_searches']+=1;counts['unit_leaf_nodes']+=nodes;oi+=1
  b.push(move);counts['moves']+=1
 assert si==len(r['search_records']) and oi==len(r['opponent_records']) and b.fen()==r['final_fen'];assert P.G.score(b,color,len(r['actions']),8)==r['score'];counts['games']+=1

assert all(c['phase']=='train' for c in X['calls'][:72]) and all(c['phase']=='heldout' for c in X['calls'][72:])
E=json.loads((R/'results/dev_aux/task236/endpoints.json').read_bytes());assert E==X['endpoints'] and E['training_games']==72
means={}
for seed,names in D['seed_profiles'].items():
 vals={name:statistics.mean(c['result']['score']['quantity_difference']/15 for c in X['calls'] if c['phase']=='train' and c['profile']==name) for name in names};means[seed]=vals;assert vals==E['training_means'][seed];assert max(names,key=lambda x:vals[x])==E['selected'][seed];assert E['weights'][seed]==D['profiles'][E['selected'][seed]]
components=[]
def metric(cs):
 a=[c['result']['score'] for c in cs];return dict(original=statistics.mean(c['result']['reward'] for c in cs),quantity=statistics.mean(s['quantity_difference']/15 for s in a),wins=sum(s['terminal'] and s['winner']==c['result']['agent_color'] for c,s in zip(cs,a)),losses=sum(s['terminal'] and s['winner'] is not None and s['winner']!=c['result']['agent_color'] for c,s in zip(cs,a)),unknown=sum(not s['terminal'] for s in a))
for seed in E['selected']:
 for opponent in D['opponents']:
  a=[c for c in X['calls'] if c['phase']=='heldout' and c['profile']==f'initial-s{seed}' and c['opponent']==opponent];b=[c for c in X['calls'] if c['phase']=='heldout' and c['profile']==f'selected-s{seed}' and c['opponent']==opponent];unit=[c for c in X['calls'] if c['phase']=='heldout' and c['profile']=='unit' and c['opponent']==opponent];ma=metric(a);mb=metric(b);mu=metric(unit);components.append(dict(seed=seed,selected=E['selected'][seed],opponent=opponent,initial=ma,final=mb,unit=mu,delta_vs_initial={k:mb[k]-ma[k] for k in ('original','quantity')},delta_vs_unit={k:mb[k]-mu[k] for k in ('original','quantity')},changed_action_pairs=sum(x['result']['actions']!=y['result']['actions'] for x,y in zip(a,b))))
out=dict(complete=True,counts=counts,completed_depths=depths,search_wall=dict(min=min(times),mean=statistics.mean(times),max=max(times),sum=sum(times)),actual_game_batch_seconds=X['seconds'],audit_seconds=time.monotonic()-started,selection_train_only=True,all_endpoints_before_heldout=True,selection=E,components=components,queries=[dict(seed=q['seed'],label=q['label'],root=q['root'],completed_depth=q['decision']['completed_depth'],action=q['action_uci'],score=q['decision']['score'],seconds=q['wall_seconds']) for q in X['queries']],scope=D['scope']);(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
