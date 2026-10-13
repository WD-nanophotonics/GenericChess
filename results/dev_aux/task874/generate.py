from pathlib import Path
import json,random,sys
R=Path.cwd();O=R/'results/dev_aux/task875';O.mkdir(exist_ok=False);plan=json.loads((R/'results/dev_aux/task874/plan.json').read_bytes())
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G
roots=[];failed=[];traces=[]
for i,seed in enumerate(plan['seeds']):
 rng=random.Random(seed);b=A.shogi.Board();b.clear();b.turn=0;b.move_number=1;used=set();spec=[]
 for color,row in [(0,6),(1,2)]:
  sq=row*9+rng.randrange(3,6);used.add(sq);spec.append((sq,8,color))
 for color,rs in [(0,range(4,8)),(1,range(1,5))]:
  for pt in [3,6]:
   legal=[r*9+c for r in rs for c in range(1,8) if r*9+c not in used];sq=rng.choice(legal);used.add(sq);spec.append((sq,pt,color))
 for sq,pt,c in spec:b.set_piece_at(sq,A.shogi.Piece(pt,c))
 initial=b.sfen();b.turn=0;blackcheck=b.is_check();b.turn=1;whitecheck=b.is_check();b.turn=0;failure=None;h=[];k=[G.key(b)];checks=[];movers=[];acts=[];phase='train' if i<16 else 'development' if i<24 else 'validation'
 if whitecheck:failure=dict(kind='initial_king_check',black=blackcheck,white=whitecheck)
 else:
  for ply in range(8):
   term=G.terminal(b,k,checks,movers)
   if term:failure=dict(kind='terminal_prefix',termination=term,ply=ply);break
   legal=sorted(m.usi() for m in b.legal_moves);ix=rng.randrange(len(legal));u=legal[ix];m=A.shogi.Move.from_usi(u);before=b.sfen();movers.append(b.turn);b.push(m);h.append(u);checks.append(b.is_check());k.append(G.key(b));acts.append(dict(legal=legal,index=ix,move=u,before_sfen=before,after_sfen=b.sfen()))
  if not failure and G.terminal(b,k,checks,movers):failure=dict(kind='terminal_prefix_end',termination=G.terminal(b,k,checks,movers))
 row=dict(seed=seed,source_family=seed,index=i,phase=phase,variant='NB',initial_sfen=initial,history=h,expected_sfen=b.sfen(),inventory=4)
 traces.append(dict(root=row,placement=spec,actions=acts,failure=failure))
 if failure:failed.append(dict(root=row,failure=failure))
 else:roots.append(row)
result=dict(status='ALL_DECLARED_REDUCED_INVENTORY_ROOTS_GENERATED',roots=roots,failed=failed,trace=traces,new_go=0,before_any_fit=True,scope=plan['variants']);(O/'roots_frozen.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('REDUCED_ROOTS',len(roots),'FAILED',len(failed));print([(v,p,sum(r['variant']==v and r['phase']==p for r in roots)) for v in ['NR','NRB'] for p in ['train','development','validation']])
