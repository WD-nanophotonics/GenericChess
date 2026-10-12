import json,sys,hashlib,time
from pathlib import Path
import random,cshogi as C
from fractions import Fraction
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
O=R/'results/dev_aux/task426';d=json.loads((R/'results/dev_aux/task425/declaration.json').read_text(encoding='utf-8'));t0=time.perf_counter()
def random_audit(g):
 pv=0;expected=[];draws=0
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
 return pv,expected,draws

folder=R/'results/dev_aux/task425';games=[json.loads(x) for x in (folder/'games.jsonl').read_text(encoding='utf-8').splitlines()];raw=[json.loads(x) for x in (folder/'queries.jsonl').read_text(encoding='utf-8').splitlines()];expected=[];pv=0;draws=0
for g in games:
 if g['opponent_arm']=='unit':pv+=V.game(g);expected.extend(V.bare(q) for q in g['queries'])
 else:n,qs,nd=random_audit(g);pv+=n;draws+=nd;expected.extend(qs)
assert expected==raw
r=json.loads((folder/'result.json').read_text(encoding='utf-8'));seen=set();sourcechecks=0;cache={}
for row in r['rows']:
 src=row['source'];p=R/src['file']
 if src['file'] not in cache:cache[src['file']]=[json.loads(x) for x in p.read_text(encoding='utf-8').splitlines()]
 g=cache[src['file']][src['line']-1];assert g['root'] in d['roots'];assert g['weights']==row['weights'] and g['root']['index']==row['root_index'] and g['color']==row['color'];assert g['goal']==row['goal'] and g['raw_quantity']==row['quantity'] and g['termination']==row['termination'] and len(g['actions'])==row['plies'];assert row['weights'] in [p['weights'] for p in r['profiles']]
 if row['arm']=='unit':V.game(g)
 else:random_audit(g)
 key=(row['arm'],tuple(row['weights']),row['root_index'],row['color']);assert key not in seen;seen.add(key);sourcechecks+=1
assert len(seen)==len(r['profiles'])*4*2*2==96 and r['new_games']==len(games)==32 and r['new_go']==len(raw)==562 and r['cache_hits']==64
freeze=json.loads((R/'results/dev_aux/task417/all_endpoints_frozen.json').read_text(encoding='utf-8'))
for arm,task in [('unit',418),('random',419)]:assert hashlib.sha256((R/f'results/dev_aux/task{task}/endpoints.json').read_bytes()).hexdigest()==freeze['both_endpoints'][arm]
result=dict(status='PASS',newgames=len(games),actual_go=len(raw),new_PV_checks=pv,new_random_draws=draws,all_logical_source_checks=sourcechecks,exact_cache_hits=64,both_fit_endpoints_hash_match=True,scope='independent cshogi fullhistory/material/quantity/termination/PV/perturn RNG plusALL96 crossrows/source refs; no re-executed games',game_sha256=hashlib.sha256((folder/'games.jsonl').read_bytes()).hexdigest(),query_sha256=hashlib.sha256((folder/'queries.jsonl').read_bytes()).hexdigest(),seconds=time.perf_counter()-t0);(O/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result)
