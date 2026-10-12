"""Replay quantity pilot, H12/H24 sensitivity, separate mate and per-type counts."""
import json,time,math,hashlib,collections
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();O=R/'results/dev_aux/task336';assert not (O/'audit.json').exists();start=time.monotonic();D=json.loads((R/'results/dev_aux/task335/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task335/result.json').read_bytes());assert X['complete'];diagnostics=[];nq=0
for z in X['calls']:
 f=D['train_roots'][z['root']];b=chess.Board(f['initial_fen'])
 for u in f['history']:b.push_uci(u)
 assert b.fen()==f['expected_fen'];ss={q['ply']:q for q in z['search_records']};assert len(ss)==len(z['actions'])<=24;counters=collections.Counter();horizons={};initial={k:len(b.pieces(i+1,z['color']))-len(b.pieces(i+1,not z['color'])) for i,k in enumerate('PNBRQ')}
 def snapshot(h):
  oo=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;sign=0 if kind!='CHECKMATE' else 1 if oo.winner==z['color'] else -1;v={k:len(b.pieces(i+1,z['color']))-len(b.pieces(i+1,not z['color'])) for i,k in enumerate('PNBRQ')};quantity=sum(v.values());return dict(horizon=h,actual_plies=len(b.move_stack)-20,termination=kind,finite_mate_sign=sign,quantity_difference=quantity,per_type_difference=v,per_type_change={k:v[k]-initial[k] for k in v},mate_component=str(F(32*sign)),quantity_component=str(F(quantity,15) if not sign else F(0)),original_mixed=str(F(32*sign) if sign else F(quantity,15)),drawzero_mixed=str(F(32*sign) if sign else F(quantity,15) if oo is None else F(0)),captures=dict(counters))
 for ply,u in enumerate(z['actions']):
  assert not b.is_game_over(claim_draw=False);q=ss[ply];assert q['player']==('candidate' if b.turn==z['color'] else 'unit');meta=q['record'];assert meta['root_fen']==f['initial_fen'] and meta['full_history']==[a.uci() for a in b.move_stack] and meta['nodes_limit']==1024 and meta['reported_nodes']>=0;parts=[s.split() for s in meta['uci_info'] if ' pv ' in s];pv=parts[-1][parts[-1].index('pv')+1:];assert pv[0]==u;c=b.copy(stack=True)
  for t in pv:assert chess.Move.from_uci(t) in c.legal_moves;c.push_uci(t)
  m=chess.Move.from_uci(u);assert m in b.legal_moves
  if b.is_capture(m):victim='P' if b.is_en_passant(m) else chess.piece_symbol(b.piece_type_at(m.to_square)).upper();counters[q['player']+'_captures_'+victim]+=1
  if m.promotion:counters[q['player']+'_promotion_'+chess.piece_symbol(m.promotion).upper()]+=1
  b.push(m);nq+=1
  if ply+1==12:horizons['12']=snapshot(12)
 if '12' not in horizons:horizons['12']=snapshot(12)
 horizons['24']=snapshot(24);last=horizons['24'];assert (last['termination'],last['finite_mate_sign'],last['original_mixed'],last['quantity_difference'],b.fen())==(z['termination'],z['finite_mate_sign'],z['fitness'],z['quantity_difference'],z['final_fen'])
 for field,w in [('table_ack',z['weights']),('opponent_table_ack',D['unit'])]:assert z[field]['prices']=={str(i+1):[w[k]]*2 for i,k in enumerate('PNBRQ')}
 for field,w in [('leaf_probes',z['weights']),('opponent_leaf_probes',D['unit'])]:
  for pr in z[field]:assert abs(pr['measured_white_pawns']-w[pr['type']]/208)<.011
 diagnostics.append(dict(name=z['name'],root=z['root'],color=z['color'],initial_vector=initial,horizons=horizons))
assert len(diagnostics)==48 and nq==sum(json.loads(l).get('event')=='query' for l in (R/'results/dev_aux/task335/queries.jsonl').read_bytes().splitlines());summary=[]
for name in D['initials']:
 for h in ('12','24'):
  rr=[z['horizons'][h] for z in diagnostics if z['name']==name];summary.append(dict(profile=name,horizon=h,games=len(rr),mate_wins=sum(z['finite_mate_sign']==1 for z in rr),mate_losses=sum(z['finite_mate_sign']==-1 for z in rr),actual_draws=sum(z['termination'] not in ('CHECKMATE','UNKNOWN_CUTOFF') for z in rr),quantity_mean=str(F(sum(z['quantity_difference'] for z in rr),len(rr))),mate_component_mean=str(sum(F(z['mate_component']) for z in rr)/len(rr)),quantity_component_mean=str(sum(F(z['quantity_component']) for z in rr)/len(rr)),mixed_mean=str(sum(F(z['original_mixed']) for z in rr)/len(rr)),drawzero_mean=str(sum(F(z['drawzero_mixed']) for z in rr)/len(rr)),per_root_quantity={str(i):str(F(sum(z['horizons'][h]['quantity_difference'] for z in diagnostics if z['name']==name and z['root']==i),2)) for i in range(8)}))
out=dict(complete=True,games=48,queries=nq,new_queries=0,diagnostics=diagnostics,summary=summary,producer_seconds=X['seconds'],seconds=time.monotonic()-start,scope='Retrospective H12/H24 on identical recorded paths; no horizon choice/reselection/extension. Ordinary draw quantity was explicit335task; future drawzero task separatelydeclared. Per-type/capture changes describe trajectories, not proof of exchange bias causality. Unweighted quantity says Q-for-P and P-for-Q same one-for-one immediate count; longpolicy usefulness canstill differ.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='diagnostics'},indent=2))