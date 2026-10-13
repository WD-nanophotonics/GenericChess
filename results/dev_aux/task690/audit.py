import json,sys,random,hashlib,time
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task690';d=json.loads((R/'results/dev_aux/task684/declaration.json').read_bytes());f=json.loads((R/'results/dev_aux/task684/roots_frozen.json').read_bytes());start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V,cshogi as C
seen=set();moves=0
for tr in f['trace']:
 seed=tr['seed'];b=C.Board();rng=random.Random(seed);states=[' '.join(b.sfen().split()[:3])];gave=[];movers=[]
 for a in tr['actions']:
  assert V.terminal(b,states,movers,gave) is None;legal=sorted(C.move_to_usi(m) for m in b.legal_moves if not b.piece(C.move_to(m)) and not C.move_is_promotion(m));ix=rng.randrange(len(legal));assert legal==a['legal'] and ix==a['index'] and legal[ix]==a['move'] and b.sfen()==a['before_sfen'];m=b.move_from_usi(a['move']);assert b.is_legal(m);movers.append(b.turn);b.push(m);gave.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]));assert b.sfen()==a['after_sfen'];moves+=1
 assert tr['failed'] is None and len(tr['actions'])==20;root=next(x for x in f['roots'] if x['seed']==seed);assert root['expected_sfen']==b.sfen() and root['history']==[a['move'] for a in tr['actions']];assert root['phase']==('train' if d['seeds'].index(seed)<16 else 'development');assert V.terminal(b,states,movers,gave) is None;assert all(sum(h)==0 for h in b.pieces_in_hand);assert sum(pc!=0 and pc%16!=8 for pc in b.pieces)==38;seen.add(seed)
assert seen==set(d['seeds']) and f['failed']==[] and f['before_any_fit'];out=dict(status='PASS_ALL_24_NEW_FULLARMY_ROOTS_NATIVE',actual_moves=moves,train=16,development=8,independent_rule_library='cshogi vsPython-shogi generator',source_sha256=hashlib.sha256((R/'results/dev_aux/task684/roots_frozen.json').read_bytes()).hexdigest(),new_go=0,seconds=time.perf_counter()-start,scope='ALL24preassignedfamilies/480actualquietpreludeactions uniformsortedlegalarrays/noncapture/nonpromotion/RNG/history/royalterminal/army38board/hand0 independentlyreplayed. No mate/pricelabel rootselection; finite20plyfullarmydistribution notallnaturalstates/generalrule-domainproof.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
