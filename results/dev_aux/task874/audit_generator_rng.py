import json,random,sys,time
from pathlib import Path
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task878';O.mkdir(exist_ok=False);sys.path.insert(0,str(R/'results/dev_aux/task360'));import adapter as A;start=time.perf_counter();count=0;prefix=0
for task in [850,870,875]:
 data=json.loads((R/f'results/dev_aux/task{task}/roots_frozen.json').read_bytes())
 for i,tr in enumerate(data['trace']):
  r=tr['root'];rng=random.Random(r['seed']);used=set();spec=[]
  for color,row in [(0,6),(1,2)]:sq=row*9+rng.randrange(3,6);used.add(sq);spec.append([sq,8,color])
  for color,rs in [(0,range(4,8)),(1,range(1,5))]:
   for pt in ([3,6] if task==875 else [3,7]+([6] if i%2 else [])):
    legal=[row*9+col for row in rs for col in range(1,8) if row*9+col not in used];sq=rng.choice(legal);used.add(sq);spec.append([sq,pt,color])
  assert spec==tr['placement'];b=C.Board(r['initial_sfen']);assert b.turn==0;assert r['phase']==('train' if i<16 else 'development' if i<24 else 'validation');expectedvar='NB' if task==875 else 'NRB' if i%2 else 'NR';assert r['variant']==expectedvar
  for sq,pt,color in spec:
   cs=C.SQUARE_NAMES.index(A.shogi.SQUARE_NAMES[sq]);assert b.piece(cs)==A.MAP[pt]+16*color,(task,sq,pt,color,b.sfen())
  assert sum(pc!=0 for pc in b.pieces)==len(spec)
  for action in tr['actions']:
   legal=sorted(C.move_to_usi(m) for m in b.legal_moves);ix=rng.randrange(len(legal));assert action['legal']==legal and action['index']==ix and action['move']==legal[ix];b.push_usi(action['move']);prefix+=1
  assert b.sfen()==r['expected_sfen'];count+=1
out=dict(status='PASS_ALL120_REDUCED_GRAMMAR_SEED_PLACEMENT_PREFIX_RNG',roots=count,prefix_moves=prefix,new_go=0,seconds=time.perf_counter()-start,scope='Additionalexactseed/placement/prefixRNGqualification for850/870/875, independentC legalfrontiers and coordinate mapping. Bothfailed andeligible roots retained, no regenerated scientificdata/newgames. Earlierphysicalaudits already fulllegal/terminal/actualrandomopponent checks; thisaddsgeneratorRNGbinding notnewoutcomeclaim.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)
