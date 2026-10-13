import json,random,time,sys,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task662';seeds=list(range(2026109000,2026109024));plan=dict(question='Doesordinaryfullarmygeometry avoidterminal-curriculum pricingbias atcheapH12quantitycost?',seeds=seeds,split='First16seeds train last8development assignedBEFOREgeneration',prelude_plies=20,filter='Uniformsortedlegalnoncapture/nonpromotion actions only; allfailedterminal/noeligiblemoves preserved, noresampling',cap=12,nodes=1024,seed_base=2026110002,scope='NEWgeometrygenerator premise; orthodoxfullarmy standardopening20quietlegalmoves, no engine/mature/humanprices ormateconditioning inrootselection. Familiesoriginalseed; roots fixedbeforefit, development neverfitness/axis/epoch/rootselector. Quantityforallterminations goal no terminalbonus; twoarbitraryoriginalinitials/12samejointdirections free12axes/P90K0. No source-referencefitness/longgames/newworkers/default/UI change. Small16train/8dev feasibility, notuniversalnaturaldistribution proof.');(O/'declaration.json').write_text(json.dumps(plan,indent=2),encoding='utf-8');start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
roots=[];failed=[];trace=[]
for i,seed in enumerate(seeds):
 b=A.shogi.Board();initial=b.sfen();h=[];k=[G.key(b)];checks=[];movers=[];rng=random.Random(seed);acts=[];failure=None
 for ply in range(20):
  term=G.terminal(b,k,checks,movers)
  if term:failure=dict(kind='terminal_duringquietprelude',termination=term,ply=ply);break
  legal=sorted(m.usi() for m in b.legal_moves if b.piece_at(m.to_square) is None and not m.promotion)
  if not legal:failure=dict(kind='noquietlegalaction',ply=ply);break
  idx=rng.randrange(len(legal));u=legal[idx];m=A.shogi.Move.from_usi(u);before=b.sfen();movers.append(b.turn);b.push(m);h.append(u);checks.append(b.is_check());k.append(G.key(b));acts.append(dict(ply=ply,legal=legal,index=idx,move=u,before_sfen=before,after_sfen=b.sfen()))
 phase='train' if i<16 else 'development'
 if failure:failed.append(dict(seed=seed,phase=phase,history=h,expected_sfen=b.sfen(),failure=failure));trace.append(dict(seed=seed,actions=acts,failed=failure));continue
 assert G.quantity(b,0)==0 and G.quantity(b,1)==0;assert G.terminal(b,k,checks,movers) is None
 roots.append(dict(index=len(roots),seed=seed,source_family=seed,phase=phase,initial_sfen=initial,history=h,expected_sfen=b.sfen()));trace.append(dict(seed=seed,actions=acts,failed=None))
out=dict(status='ALL_DECLARED_QUIET_ROOTS_GENERATED',before_any_fit=True,roots=roots,failed=failed,trace=trace,train=sum(r['phase']=='train' for r in roots),development=sum(r['phase']=='development' for r in roots),new_go=0,seconds=time.perf_counter()-start,declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest(),scope=plan['scope']);(O/'roots_frozen.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print('QUIET_ROOTS',out['train'],out['development'],len(failed))
