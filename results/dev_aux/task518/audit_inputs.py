import json,random,sys,hashlib
from pathlib import Path
import cshogi as C
R=Path.cwd();O=R/'results/dev_aux/task518';sys.path.insert(0,str(R/'results/dev_aux/task381'));import audit as V
d=json.loads((O/'declaration.json').read_text(encoding='utf-8'));checks=[]
for f,expected_terminal in [(f,None) for f in d['roots']]+[(x['root'],x['terminal']) for x in d['unavailable']]:
 b=C.Board(f['initial_sfen']);rng=random.Random(f['seed']);states=[' '.join(b.sfen().split()[:3])];movers=[];gave=[]
 for u in f['history']:
  assert V.terminal(b,states,movers,gave) is None;legal=sorted(C.move_to_usi(m) for m in b.legal_moves);assert rng.choice(legal)==u;m=b.move_from_usi(u);assert b.is_legal(m);movers.append(b.turn);b.push(m);gave.append(bool(b.is_check()));states.append(' '.join(b.sfen().split()[:3]))
 assert b.sfen()==f['expected_sfen'];term=V.terminal(b,states,movers,gave);assert term==expected_terminal,(term,expected_terminal);checks.append(dict(seed=f['seed'],phase=f['phase'],prefix_plies=len(f['history']),terminal=term,available=term is None))
rng=random.Random(d['direction_seed']);assert d['directions']=={p['name']:[[rng.choice([-1,1]) for _ in d['axes']] for _ in range(24)] for p in d['initial_profiles']};allseeds={x['seed'] for x in checks};assert allseeds==set(d['input_policy']['seeds']['train']+d['input_policy']['seeds']['development']);out=dict(status='PASS_INPUTS',roots=checks,native_prefix_plies=sum(x['prefix_plies'] for x in checks),directions=48,new_go=0,all8seeds_retained=True,declaration_sha256=hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest(),scope='Newpolicybeforegeneration, all8seeds retained includingunavailable ifany; no replacement. No development queries yet.');(O/'input_audit.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)
