from pathlib import Path
import json,random,sys,hashlib
import cshogi as C
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
O=R/'results/dev_aux/task467';d=json.loads((O/'declaration.json').read_text(encoding='utf-8'));checks=[]
for f in d['roots']:
 b=C.Board(f['initial_sfen']);rng=random.Random(f['seed']);states=[' '.join(b.sfen().split()[:3])];movers=[];gave=[]
 for u in f['history']:
  assert V.terminal(b,states,movers,gave) is None;legal=sorted(C.move_to_usi(m) for m in b.legal_moves);assert rng.choice(legal)==u;m=b.move_from_usi(u);assert b.is_legal(m);movers.append(b.turn);b.push(m);gave.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]))
 assert b.sfen()==f['expected_sfen'] and V.terminal(b,states,movers,gave) is None;checks.append(dict(seed=f['seed'],phase=f['phase'],prefix_plies=len(f['history'])))
rng=random.Random(d['direction_seed']);assert d['directions']=={p['name']:[[rng.choice([-1,1]) for a in d['axes']] for _ in range(24)] for p in d['initial_profiles']}
(O/'input_audit.json').write_text(json.dumps(dict(status='PASS_INPUTS',roots=checks,directions=48,new_go=0,declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest()),indent=2),encoding='utf-8');print('independent467inputs PASS')
