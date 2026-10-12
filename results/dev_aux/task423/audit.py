import sys,json,random,time,hashlib
from pathlib import Path
from fractions import Fraction
import cshogi as C
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
O=R/'results/dev_aux/task423';O.mkdir(exist_ok=True);d=json.loads((R/'results/dev_aux/task417/declaration.json').read_text(encoding='utf-8'));t0=time.perf_counter()
unit=V.audit(418);folder=R/'results/dev_aux/task419';games=[json.loads(x) for x in (folder/'games.jsonl').read_text(encoding='utf-8').splitlines()];raw=[json.loads(x) for x in (folder/'queries.jsonl').read_text(encoding='utf-8').splitlines()];expected=[];pv=0;draws=0
for g in games:
 f=g['root'];assert f in d['roots'];b=C.Board(f['initial_sfen']);states=[' '.join(b.sfen().split()[:3])];movers=[];gave=[];h=[]
 for u in f['history']:
  assert V.terminal(b,states,movers,gave) is None;m=b.move_from_usi(u);assert b.is_legal(m);movers.append(b.turn);b.push(m);gave.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]));h.append(u)
 assert b.sfen().split()[:3]==f['expected_sfen'].split()[:3];qi=0;opp=0
 for ply,a in enumerate(g['actions']):
  assert V.terminal(b,states,movers,gave) is None;assert b.sfen().split()[:3]==a['before_sfen'].split()[:3];assert a['actor']==b.turn
  if b.turn==g['color']:
   q=g['queries'][qi];qi+=1;assert a['random_draw'] is None;assert q['history']==h and q['initial_sfen']==f['initial_sfen'];assert q['weights']==g['weights'] and q['nodes_limit']==d['nodes'] and q['cold_isready'];assert q['player']=='candidate' and q['ply']==ply and q['bestmove']==a['move'];pv+=V.query(q);expected.append(V.bare(q))
  else:
   x=a['random_draw'];legal=sorted(C.move_to_usi(m) for m in b.legal_moves);seed=(d['random_seed_base']+2*f['index']+g['color']+(100 if f['phase']=='development' else 0))*100+opp;assert x==dict(legal=legal,index=random.Random(seed).randrange(len(legal)),seed=seed,opponent_turn=opp);assert legal[x['index']]==a['move'];opp+=1;draws+=1
  m=b.move_from_usi(a['move']);assert b.is_legal(m);movers.append(b.turn);b.push(m);gave.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]));h.append(a['move']);assert b.sfen().split()[:3]==a['after_sfen'].split()[:3]
 assert qi==len(g['queries']);assert b.sfen().split()[:3]==g['final_sfen'].split()[:3];_,counts=V.literal(b.sfen(),g['weights']);qty=counts[g['color']]-counts[1-g['color']];assert qty==g['raw_quantity'];term=V.terminal(b,states,movers,gave);assert g['termination']==(term or {'kind':'cap24','winner':None});goal=Fraction(qty,19) if term is None else (Fraction(0) if term['winner'] is None else Fraction(32 if term['winner']==g['color'] else -32));assert str(goal)==g['goal']
assert expected==raw;assert len(games)>0
out=dict(status='PASS',unit=unit,random=dict(games=len(games),actual_go=len(raw),random_draws=draws,PV_move_checks=pv,game_sha256=hashlib.sha256((folder/'games.jsonl').read_bytes()).hexdigest(),query_sha256=hashlib.sha256((folder/'queries.jsonl').read_bytes()).hexdigest()),coverage='all418unit/419randomactualfit+diagnosticgames, independent cshogi fullhistory/terminal/legal lists/peropponentturn RNG/candidate realquery prices/PV/quantity/originalgoals; no fakego forrandom',seconds=time.perf_counter()-t0);(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)
