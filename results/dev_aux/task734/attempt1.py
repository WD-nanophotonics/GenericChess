import json,time,sys,copy,hashlib
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task734';start=time.perf_counter()
for n in [360,364,381]:sys.path.insert(0,str(R/f'results/dev_aux/task{n}'))
import adapter as A,run as G,audit as V
roots=json.loads((R/'results/dev_aux/task717/roots_frozen.json').read_bytes())['roots'];cached={};checks=[]
# Validate every full root first with the original complete constructor. Cache only exact root payloads.
for f in roots:
 x=G.full_root(f);assert x[0].sfen()==f['expected_sfen'];cached[f['index']]=x
 for repeat in range(2):
  b=copy.deepcopy(x[0]);k=list(x[1]);ch=list(x[2]);mo=list(x[3]);fresh=G.full_root(f);assert b.sfen()==fresh[0].sfen() and k==fresh[1] and ch==fresh[2] and mo==fresh[3];legal=sorted(m.usi() for m in b.legal_moves);assert legal==sorted(m.usi() for m in fresh[0].legal_moves);assert G.terminal(b,k,ch,mo)==G.terminal(*fresh)
  for u in legal[:1]:
   for board,kk,cc,mm in [(b,k,ch,mo),fresh]:
    m=A.shogi.Move.from_usi(u);mm.append(board.turn);board.push(m);cc.append(board.is_check());kk.append(G.key(board))
   assert b.sfen()==fresh[0].sfen() and k==fresh[1] and ch==fresh[2] and mo==fresh[3] and G.terminal(b,k,ch,mo)==G.terminal(*fresh)
  assert x[0].sfen()==f['expected_sfen'] and len(x[1])==61 and len(x[2])==len(x[3])==60
  checks.append(dict(root=f['index'],repeat=repeat,history_key_check_mover_legal_and_one_transition_equal=True,cache_unchanged=True))
# Two short counterbalanced observations; only this observed initial construction cost, not total audit speedup.
trials=[]
for order in [('full','clone'),('clone','full')]:
 times={}
 for mode in order:
  t=time.perf_counter();count=0
  for rep in range(8):
   for f in roots:
    if mode=='full':z=G.full_root(f)
    else:
     x=cached[f['index']];z=(copy.deepcopy(x[0]),list(x[1]),list(x[2]),list(x[3]))
    assert z[0].sfen()==f['expected_sfen'];count+=1
  times[mode]=time.perf_counter()-t
 trials.append(dict(order=list(order),constructions_per_mode=count,seconds=times))
out=dict(status='ALL24_ROOT_CLONE_OWNERSHIP_AND_HISTORY_PASS',checks=checks,trials=trials,new_games=0,new_go=0,seconds=time.perf_counter()-start,source_sha256=hashlib.sha256((R/'results/dev_aux/task717/roots_frozen.json').read_bytes()).hexdigest(),scope='Observed723fullPythonaudit root-history work costly; fulloriginalconstruction first and48fresh-vs-deepclone states/key/check/mover/legal/terminal/oneaction equal, originalcache notmutated. Shortcounterbalanced microobservations underordinaryconcurrentload, nottotalaudit orengine speedup. NOrunning723audit mutation/restart, no physicalfitting/defaults/primarychange. Futureaudit optimization needsfullactualsame-input output equivalence, notskip independent rules/PV/rawquery/material/RNG/ACK/selection verification.');(O/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in out.items() if k!='checks'}))
