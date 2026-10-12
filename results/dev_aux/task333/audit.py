"""Independent endpoint-vs-search replay and fixed paired contrasts."""
import json,time,math,hashlib
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();O=R/'results/dev_aux/task333';assert not (O/'audit.json').exists();start=time.monotonic();D=json.loads((R/'results/dev_aux/task332/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task332/result.json').read_bytes());assert X['complete'];rows=X['calls'];nq=0
for z in rows:
 f=D['roots'][z['root']];b=chess.Board(f['initial_fen'])
 for u in f['history']:b.push_uci(u)
 assert b.fen()==f['expected_fen'];ss={q['ply']:q for q in z['search_records']};assert len(ss)==len(z['actions'])<=48
 for ply,u in enumerate(z['actions']):
  assert not b.is_game_over(claim_draw=False);q=ss[ply];assert q['player']==('candidate' if b.turn==z['color'] else 'unit');m=q['record'];assert m['root_fen']==f['initial_fen'] and m['full_history']==[a.uci() for a in b.move_stack];assert m['nodes_limit']==1024 and m['reported_nodes']>=0;parts=[s.split() for s in m['uci_info'] if ' pv ' in s];pv=parts[-1][parts[-1].index('pv')+1:];assert pv[0]==u;c=b.copy(stack=True)
  for t in pv:assert chess.Move.from_uci(t) in c.legal_moves;c.push_uci(t)
  assert chess.Move.from_uci(u) in b.legal_moves;b.push_uci(u);nq+=1
 oo=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF' if oo is None else oo.termination.name;sign=0 if kind!='CHECKMATE' else 1 if oo.winner==z['color'] else -1;fitness=F(49-len(z['actions']),48) if sign==1 else F(-1) if sign==-1 else F(0);cnt=lambda c:sum(len(b.pieces(k,c)) for k in range(1,6));assert (kind,sign,str(fitness),b.fen(),cnt(z['color'])-cnt(not z['color']))==(z['termination'],z['finite_mate_sign'],z['fitness'],z['final_fen'],z['quantity_difference'])
 for field,w in [('table_ack',z['weights']),('opponent_table_ack',D['opponent_weights'])]:assert z[field]['prices']=={str(i+1):[w[k]]*2 for i,k in enumerate('PNBRQ')}
 for field,w in [('leaf_probes',z['weights']),('opponent_leaf_probes',D['opponent_weights'])]:
  for pr in z[field]:assert math.isfinite(pr['measured_white_pawns']) and abs(pr['measured_white_pawns']-w[pr['type']]/208)<.011
assert nq==sum(json.loads(l).get('event')=='query' for l in (R/'results/dev_aux/task332/queries.jsonl').read_bytes().splitlines());assert len(rows)==20
summary=[];contrasts=[]
for name in D['unique_profiles']:
 zz=[z for z in rows if z['profile']==name];summary.append(dict(profile=name,games=len(zz),wins=sum(z['finite_mate_sign']==1 for z in zz),losses=sum(z['finite_mate_sign']==-1 for z in zz),terminations={k:sum(z['termination']==k for z in zz) for k in sorted({z['termination'] for z in zz})},speed=str(sum(F(z['fitness']) for z in zz)/4),quantity_mean=str(F(sum(z['quantity_difference'] for z in zz),4)),cells=[{k:z[k] for k in ('root','color','termination','finite_mate_sign','fitness','quantity_difference')} for z in zz]))
for family in ('unit','semantic','s703-base'):
 a=[z for z in rows if z['profile']==D['aliases']['initial-'+family]];b=[z for z in rows if z['profile']==D['aliases']['endpoint-'+family]];am={(z['root'],z['color']):z for z in a};bm={(z['root'],z['color']):z for z in b};assert set(am)==set(bm);contrasts.append(dict(family=family,speed_delta=str(sum(F(bm[k]['fitness'])-F(am[k]['fitness']) for k in am)/4),net_sign_delta=str(F(sum(bm[k]['finite_mate_sign']-am[k]['finite_mate_sign'] for k in am),4)),quantity_delta=str(F(sum(bm[k]['quantity_difference']-am[k]['quantity_difference'] for k in am),4)),same_trajectories=sum(am[k]['actions']==bm[k]['actions'] for k in am)))
out=dict(complete=True,games=20,queries=nq,summary=summary,contrasts=contrasts,source_result_sha256=hashlib.sha256((R/'results/dev_aux/task332/result.json').read_bytes()).hexdigest(),seconds=time.monotonic()-start,scope='Fixed all frozen endpoints; old exposed roots, four cells each; cold deterministic search, no statistical confidence or new training. Quantity is unweighted actor count, reported separately and not evidence for human price agreement.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))