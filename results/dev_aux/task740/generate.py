import json,random,time,sys,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task740';plan=json.loads((R/'results/dev_aux/task739/declaration.json').read_bytes());seeds=plan['seeds'];start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
roots=[];failed=[];trace=[]
for i,seed in enumerate(seeds):
 b=A.shogi.Board();initial=b.sfen();h=[];k=[G.key(b)];checks=[];movers=[];rng=random.Random(seed);acts=[];failure=None
 for ply in range(plan['prelude_plies']):
  term=G.terminal(b,k,checks,movers)
  if term:failure=dict(kind='terminal_duringalllegalprelude',termination=term,ply=ply);break
  legal=sorted(m.usi() for m in b.legal_moves)
  if not legal:failure=dict(kind='nolegalaction',ply=ply);break
  idx=rng.randrange(len(legal));u=legal[idx];m=A.shogi.Move.from_usi(u);before=b.sfen();movers.append(b.turn);b.push(m);h.append(u);checks.append(b.is_check());k.append(G.key(b));acts.append(dict(ply=ply,legal=legal,index=idx,move=u,before_sfen=before,after_sfen=b.sfen()))
 if failure is None and G.terminal(b,k,checks,movers) is not None:failure=dict(kind='terminal_at_prelude_end',termination=G.terminal(b,k,checks,movers),ply=len(h))
 phase='train' if i<16 else 'development'
 if failure:failed.append(dict(seed=seed,phase=phase,history=h,expected_sfen=b.sfen(),failure=failure));trace.append(dict(seed=seed,actions=acts,failed=failure));continue
 assert G.terminal(b,k,checks,movers) is None
 roots.append(dict(index=len(roots),seed=seed,source_family=seed,phase=phase,initial_sfen=initial,history=h,expected_sfen=b.sfen()));trace.append(dict(seed=seed,actions=acts,failed=None))
out=dict(status='ALL_DECLARED_ALLLEGAL_ROOTS_GENERATED',before_any_fit=True,roots=roots,failed=failed,trace=trace,train=sum(r['phase']=='train' for r in roots),development=sum(r['phase']=='development' for r in roots),new_go=0,seconds=time.perf_counter()-start,declaration_sha256=hashlib.sha256((R/'results/dev_aux/task739/declaration.json').read_bytes()).hexdigest(),scope=plan['scope']);(O/'roots_frozen.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('ALLLEGAL_ROOTS',out['train'],out['development'],len(failed))
