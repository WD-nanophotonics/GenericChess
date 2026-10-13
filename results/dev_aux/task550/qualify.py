import sys,json,time,copy,hashlib
from pathlib import Path
R=Path.cwd()
for n in [360,364,381,547]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V,controller as N
O=R/'results/dev_aux/task550';start=time.perf_counter();rows=[]
class Saved:
 def __init__(self,qs,w):self.qs=list(qs);self.w=w;self.calls=0
 def search(self,initial,history,nodes):
  q=copy.deepcopy(self.qs[self.calls]);self.calls+=1;assert q['initial_sfen']==initial and q['history']==history and q['nodes_limit']==nodes;return q
D=json.loads((R/'results/dev_aux/task518/declaration.json').read_bytes());print(D.keys(),flush=True)
games=[json.loads(x) for x in (R/'results/dev_aux/task521/games.jsonl').open()]
for g in games:
 ec=Saved([q for q in g['queries'] if q['player']=='candidate'],g['weights']);uq=[q for q in g['queries'] if q['player']=='unit'];eu=Saved(uq,uq[0]['weights']) if uq else None
 d=dict(cap=24,nodes=1024,seed_base=D['random_seed_base']);n=N.native_game(ec,eu,g['weights'],g['root'],g['color'],None,d)
 for k in ['weights','root','color','actions','queries','termination','final_sfen','raw_quantity','goal']:assert n[k]==g[k],(k,len(rows),n[k],g[k])
 assert ec.calls+ (eu.calls if eu else 0)==len(g['queries']);rows.append(dict(seed=g['root']['seed'],color=g['color'],opponent='unit' if eu else 'random',queries=ec.calls+(eu.calls if eu else 0)))
# Actual complete534 repetition path, not constructed longgame.
draw=next(json.loads(x) for x in (R/'results/dev_aux/task534/games.jsonl').open() if json.loads(x)['termination']['kind']=='fourfold_draw')
f=copy.deepcopy(draw['root']);f['history'] += [a['move'] for a in draw['actions']];f['expected_sfen']=draw['final_sfen'];b,keys,checks,movers=G.full_root(f);assert G.terminal(b,keys,checks,movers)==draw['termination']
e=Saved([],draw['weights']);ng=N.native_game(e,None,draw['weights'],f,1-b.turn,None,dict(cap=1,nodes=1024,seed_base=D['random_seed_base']));assert not ng['queries'] and not ng['actions'] and e.calls==0 and ng['termination']==draw['termination']
f2=copy.deepcopy(f);f2.update(initial_sfen=draw['final_sfen'],history=[]);py=A.shogi.Board(f2['initial_sfen']);cb=N.C.Board(f2['initial_sfen']);pl=sorted(m.usi() for m in py.legal_moves);cl=sorted(N.C.move_to_usi(m) for m in cb.legal_moves);assert pl==cl;assert G.terminal(py,[G.key(py)],[py.is_check()],[]) is None
ng2=N.native_game(e,None,draw['weights'],f2,1-cb.turn,None,dict(cap=1,nodes=1024,seed_base=D['random_seed_base']));assert len(ng2['actions'])==1 and not ng2['queries'];a=ng2['actions'][0];rd=a['random_draw'];import random
rng=random.Random(rd['seed']);before=rng.getstate();ix=rng.randrange(len(pl));after=rng.getstate();assert rd['legal']==pl and rd['index']==ix and a['move']==pl[ix] and before!=after
out=dict(status='PASS',saved_actual_games=len(rows),saved_actual_queries=sum(r['queries'] for r in rows),new_engine_queries=0,rows=rows,same_sfen_history_check=dict(full_history_termination=ng['termination'],full_history_go=0,full_history_draws=0,empty_history_go=0,empty_history_draws=1,ordered_legal_array=pl,selected_move=a['move'],rng_state_before_sha256=hashlib.sha256(repr(before).encode()).hexdigest(),rng_state_after_sha256=hashlib.sha256(repr(after).encode()).hexdigest(),source='closed534 actualfourfold path'),seconds=time.perf_counter()-start,scope='Replay storedactualPythoncontroller paths using storedactualqueries only. No newsearch or timinggain inference; finite standardShogi NoEnteringKing history/RNG/metadata qualification, not whole-generated-domain proof.')
(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print({k:v for k,v in out.items() if k not in ['rows','same_sfen_history_check']})
