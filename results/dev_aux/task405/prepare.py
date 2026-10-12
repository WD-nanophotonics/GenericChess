import sys,json,random,hashlib,math,time
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'results/dev_aux/task360'));sys.path.insert(0,str(R/'results/dev_aux/task364'));import adapter as A;import run as G;A.EXE=R/'.local_agent/yaneura26/yaneura-material1-cold-reuse.exe'
O=R/'results/dev_aux/task405';O.mkdir(exist_ok=True)
old=json.loads((R/'results/dev_aux/task364/declaration.json').read_text(encoding='utf-8'));axes=[2,3,4,5,6,7,9,10,11,12,13,14];roots=[]
for phase,seeds in [('train',range(2026102710,2026102714)),('development',range(2026102780,2026102784))]:
 for i,seed in enumerate(seeds):
  b=A.shogi.Board();initial=b.sfen();rng=random.Random(seed);h=[];keys=[G.key(b)];checks=[b.is_check()];movers=[]
  for _ in range(40):
   assert G.terminal(b,keys,checks,movers) is None,'No replacement roots allowed'
   legal=sorted(m.usi() for m in b.legal_moves);u=rng.choice(legal);h.append(u);movers.append(b.turn);b.push_usi(u);keys.append(G.key(b));checks.append(b.is_check())
  assert G.terminal(b,keys,checks,movers) is None
  f=dict(phase=phase,index=i,seed=seed,initial_sfen=initial,history=h,expected_sfen=b.sfen());G.full_root(f);roots.append(f)
rng=random.Random(2026102791);directions={p['name']:[[rng.choice([-1,1]) for a in axes] for _ in range(24)] for p in old['profiles']}
d=dict(roots=roots,initial_profiles=old['profiles'],axes=axes,directions=directions,direction_seed=2026102791,cap=24,nodes=1024,fixed_opponent=old['profiles'][0]['weights'],goal=old['goal'],coordinate=dict(max_rounds=2,proposal='base then axes half,double;tiesup;32..4096',selection='exact mean;firstmax base-firstties;strict gain else stop'),joint=dict(iterations=24,delta=.25,proposals='base,plus,minus eachiteration; roundcurrentinteger*exp(+/- .25*direction),clip32..4096',selection='exact rawmean,firstmax base-firstties, accept strictgain only; fixed24 noextra rounds ormodelchoice',vectors_per_start_max=49),source_sha=old['source_sha'],executable_sha256=hashlib.sha256(A.EXE.read_bytes()).hexdigest(),estimated_cost='singlecombined8-12min fromqualified5.25s/16control,1800secondfuse,about1584fit logical +train/developmentdiagnostics,1worker; actual cache/go/wall separate',scope='fresh seed prefixes fixed before probes, not broad independent validation; no human selection; no entering king; board-only SEE/fixed margins remain',freeze_time=time.time())
assert d['executable_sha256']=='80a43db8915073e68af43432f9bb4371507baef73f583de1d19cfde0e5700781'
(O/'declaration.json').write_text(json.dumps(d,indent=2),encoding='utf-8');print('FROZEN',len(roots),hashlib.sha256((O/'declaration.json').read_bytes()).hexdigest())