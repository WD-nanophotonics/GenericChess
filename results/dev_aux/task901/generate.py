from pathlib import Path
import json,random,sys
R=Path.cwd();O=R/'results/dev_aux/task902';O.mkdir(exist_ok=False);plan=json.loads((R/'results/dev_aux/task901/plan.json').read_bytes())
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G
roots=[];failed=[];traces=[]
for i,seed in enumerate(plan['seeds']):
 for geometry in ['center','edge']:
  rng=random.Random(seed);used=set();spec=[];kr=[5,3] if geometry=='center' else [1,3];columns=range(3,6) if geometry=='center' else range(1,4)
  for color,row in enumerate(kr):
   sq=row*9+rng.choice(columns);used.add(sq);spec.append((sq,8,color,-1))
  for color,rs in [(0,range(3,7) if geometry=='center' else range(2,6)),(1,range(2,6) if geometry=='center' else range(0,4))]:
   for j,pt in enumerate([3,3,6,6]):
    legal=[r*9+c for r in rs for c in range(1,8) if r*9+c not in used];sq=rng.choice(legal);used.add(sq);spec.append((sq,pt,color,j))
  for inventory in [4,8]:
   subset=[x for x in spec if inventory==8 or x[3] in [-1,0,2]];b=A.shogi.Board();b.clear();b.turn=0;b.move_number=1
   for sq,pt,c,j in subset:b.set_piece_at(sq,A.shogi.Piece(pt,c))
   initial=b.sfen();bc=b.is_check();b.turn=1;wc=b.is_check();b.turn=0;term=G.terminal(b,[G.key(b)],[],[]);actions=sorted(m.usi() for m in b.legal_moves);failure=dict(kind='initial_white_check',black=bc,white=wc) if wc else dict(kind='initial_terminal',termination=term) if term else dict(kind='too_few_actions',count=len(actions)) if len(actions)<2 else None
   row=dict(seed=seed,source_family=seed,index=i,phase='train' if i<16 else 'development' if i<32 else 'validation',variant=geometry+str(inventory),initial_sfen=initial,history=[],expected_sfen=initial,inventory=inventory)
   tr=dict(root=row,placement=subset,full_placement=spec,black_check=bc,white_check=wc,initial_legal=actions,failure=failure);traces.append(tr)
   if failure:failed.append(dict(root=row,failure=failure))
   else:roots.append(row)
result=dict(status='ALL192_PROSPECTIVE_COOPERATION_ROOTS_FROZEN',roots=roots,failed=failed,trace=traces,new_go=0,before_any_fit=True);(O/'roots_frozen.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print('COOP_ROOTS',len(roots),'FAIL',len(failed));print([(v,p,sum(r['variant']==v and r['phase']==p for r in roots)) for v in plan['variants'] for p in ['train','development','validation']])
