"""Independent fixed endpoint deployment replay forRootTD."""
import json,time,math
from pathlib import Path
from fractions import Fraction as F
import chess
R=Path.cwd();O=R/'results/dev_aux/task353';assert not (O/'audit.json').exists();start=time.monotonic();D=json.loads((R/'results/dev_aux/task352/declaration.json').read_bytes());X=json.loads((R/'results/dev_aux/task352/result.json').read_bytes());assert X['complete'];nq=newq=games=0;summary=[];contrasts=[]
for z in X['calls']:
 f=D['roots'][z['phase']][z['root']];b=chess.Board(f['initial_fen'])
 for u in f['history']:b.push_uci(u)
 ss={q['ply']:q for q in z['search_records']};assert len(ss)==len(z['actions'])<=24
 for ply,u in enumerate(z['actions']):
  assert not b.is_game_over(claim_draw=False);q=ss[ply];assert q['player']==('candidate'if b.turn==z['color']else'unit');meta=q['record'];assert meta['root_fen']==f['initial_fen'] and meta['full_history']==[m.uci() for m in b.move_stack] and meta['nodes_limit']==1024 and meta['reported_nodes']>=0;parts=[s.split() for s in meta['uci_info']if' pv 'in s];pv=parts[-1][parts[-1].index('pv')+1:];assert pv[0]==u;c=b.copy(stack=True)
  for t in pv:assert chess.Move.from_uci(t)in c.legal_moves;c.push_uci(t)
  assert chess.Move.from_uci(u)in b.legal_moves;b.push_uci(u);nq+=1;newq+=z['source']=='352'
 oo=b.outcome(claim_draw=False);kind='UNKNOWN_CUTOFF'if oo is None else oo.termination.name;sign=0 if kind!='CHECKMATE'else 1 if oo.winner==z['color']else-1;cnt=lambda co:sum(len(b.pieces(k,co)) for k in range(1,6));quantity=cnt(z['color'])-cnt(not z['color']);goal=F(32*sign)if sign else F(quantity,15)if oo is None else F(0);assert (str(goal),quantity,kind,sign,b.fen())==(z['fitness'],z['quantity_difference'],z['termination'],z['finite_mate_sign'],z['final_fen'])
 for field,w in [('table_ack',z['weights']),('opponent_table_ack',D['unit'])]:assert z[field]['prices']=={str(i+1):[w[k]]*2 for i,k in enumerate('PNBRQ')}
 for field,w in [('leaf_probes',z['weights']),('opponent_leaf_probes',D['unit'])]:
  for p in z[field]:assert abs(p['measured_white_pawns']-w[p['type']]/208)<.011
 if z['source']in('335','342'):
  old=json.loads((R/f"results/dev_aux/task{z['source']}/result.json").read_bytes())['calls'];wmatch=lambda r:tuple(r['weights'][k] for k in'PNBRQK')==tuple(z['weights'][k] for k in'PNBRQK');r=next(r for r in old if wmatch(r)and r['root']==z['root']and r['color']==z['color']);assert all(r[k]==z[k]for k in r if k not in('name','source','phase'))
 games+=1
assert games==192 and X['actual_games']==96 and X['reused_cases']==96 and newq==X['actual_queries']==sum(json.loads(l).get('event')=='query'for l in (R/'results/dev_aux/task352/queries.jsonl').read_bytes().splitlines())
for phase in('train','development'):
 rr=[z for z in X['calls']if z['phase']==phase]
 for name in D['profiles']:
  zz=[z for z in rr if z['name']==name];assert len(zz)==16;summary.append(dict(phase=phase,profile=name,fitness=str(sum(F(z['fitness'])for z in zz)/16),wins=sum(z['finite_mate_sign']==1 for z in zz),losses=sum(z['finite_mate_sign']==-1 for z in zz),quantity_mean=str(F(sum(z['quantity_difference']for z in zz),16))))
 for family in('unit','semantic','s703-base'):
  a={(z['root'],z['color']):z for z in rr if z['name']=='initial-'+family};b={(z['root'],z['color']):z for z in rr if z['name']=='endpoint-'+family};assert set(a)==set(b);d={k:F(b[k]['fitness'])-F(a[k]['fitness'])for k in a};contrasts.append(dict(phase=phase,family=family,fitness_delta=str(sum(d.values())/16),net_mate_delta=str(F(sum(b[k]['finite_mate_sign']-a[k]['finite_mate_sign']for k in a),16)),quantity_delta=str(F(sum(b[k]['quantity_difference']-a[k]['quantity_difference']for k in a),16)),positive_cells=sum(v>0 for v in d.values()),negative_cells=sum(v<0 for v in d.values()),same_trajectories=sum(a[k]['actions']==b[k]['actions']for k in a),root_deltas=[str(sum(v for k,v in d.items()if k[0]==ri)/2)for ri in range(8)]))
out=dict(complete=True,logical_cases=192,new_games=96,reused_cases=96,new_queries=newq,total_query_checks_including_reuse=nq,summary=summary,contrasts=contrasts,producer_seconds=X['seconds'],seconds=time.monotonic()-start,scope='FrozenRootTDendpoints independentpolicyvalue evaluation, exactinitialcase reuse sourcequalified. No furtherfit/epoch/human selection. Training-root labels exposed; development roots already342/345exposed butnotused350updates.96TDsamples differcostfrom1008coordinategames: compare resource/result, not unfairclaimsamebudgetwinner. No ultimateWDL/coherenthumanprice success.')
(O/'audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items()if k not in('summary','scope')},indent=2))