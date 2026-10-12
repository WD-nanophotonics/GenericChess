import json,time,random,statistics,math,importlib.util
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task233';O.mkdir(exist_ok=True);D=json.loads((R/'results/dev_aux/task232/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task232/games.json').read_bytes());assert X['complete'] and len(X['calls'])==D['games'];started=time.monotonic()
s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);counts=dict(games=0,moves=0,agent_searches=0,unit_searches=0,unit_leaf_nodes=0,completed_D3=0,lower_completed=0,main_nodes=0,qnodes=0);depths={};times=[]
def value(b,col):
 out=b.outcome(claim_draw=False)
 if out:return 0 if out.winner is None else (1000000 if out.winner==col else -1000000)
 return 208*sum(len(b.pieces(t,col))-len(b.pieces(t,not col)) for t in range(1,6))
for c in X['calls']:
 r=c['result'];b=P.board(D['roots'][c['opening_index']]);assert r['opening_history']==D['roots'][c['opening_index']]['history'];color=r['agent_color'];rng=random.Random(c['random_seed']);si=oi=0
 for ply,text in enumerate(r['actions']):
  assert not b.is_game_over(claim_draw=False);move=chess.Move.from_uci(text);assert move in b.legal_moves
  if b.turn==color:
   m=r['search_records'][si];assert m['ply']==ply and m['root_fen']==b.fen() and m['full_history']==[z.uci() for z in b.move_stack];v=m['result'];a=v['action'];encoded=''.join(chr(97+a[k]['file'])+str(a[k]['rank']+1) for k in ('from_square','to_square'))+(a['promotion_target_id'].lower() if a['promotion_target_id'] else '');assert encoded==text;assert v['qnodes']==0 and not v['used_fallback'];depths[str(v['completed_depth'])]=depths.get(str(v['completed_depth']),0)+1;counts['completed_D3']+=v['completed_depth']==3;counts['lower_completed']+=v['completed_depth']<3;counts['main_nodes']+=v['nodes'];counts['qnodes']+=v['qnodes'];counts['agent_searches']+=1;times.append(m['wall_seconds']);si+=1
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
components=[]
for profile in D['profiles']:
 for opponent in D['opponents']:
  cs=[c for c in X['calls'] if c['profile']==profile and c['opponent']==opponent];base=[c for c in X['calls'] if c['profile']=='unit' and c['opponent']==opponent]
  def metrics(cs):
   return dict(original=statistics.mean(c['result']['reward'] for c in cs),quantity=statistics.mean(c['result']['score']['quantity_difference']/15 for c in cs),known_wins=sum(c['result']['score']['terminal'] and c['result']['score']['winner']==c['result']['agent_color'] for c in cs),unknown=sum(not c['result']['score']['terminal'] for c in cs))
  a=metrics(cs);bb=metrics(base);components.append(dict(profile=profile,opponent=opponent,metrics=a,delta_vs_unit={k:a[k]-bb[k] for k in ('original','quantity')},changed_action_pairs=sum(c['result']['actions']!=z['result']['actions'] for c,z in zip(cs,base))))
out=dict(complete=True,counts=counts,completed_depths=depths,search_wall=dict(min=min(times),mean=statistics.mean(times),max=max(times),sum=sum(times)),actual_game_batch_seconds=X['seconds'],audit_seconds=time.monotonic()-started,components=components,scope=D['scope']);(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
