import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,time,importlib.util,re,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1746';O.mkdir(exist_ok=False);ini='';models={4:'results/dev_aux/task1675/rules.py',8:'results/dev_aux/task1688/rules.py'}
for w,task in ((4,1675),(8,1688)):ini+=(R/f'results/dev_aux/task{task}/variant.ini').read_text()+'\n'
(O/'variant.ini').write_text(ini,encoding='ascii');(O/'plan.json').write_text(json.dumps(dict(status='FROZEN_COMPLETE_KRK_NATIVE_RULE_QUALIFICATION',widths=[4,8],literal_cases='First32 of alreadyfrozen1741literal1024 eachwidth, bothcolorframes; D1all64/D2first16 perboard=160perft. IncludesRcapturebarechildren asphysicalmoves, nottableterminal.',max_seconds=180,actual_go_search=0),indent=2))
sp=importlib.util.spec_from_file_location('P',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P);deadline=time.monotonic()+180;start=time.perf_counter();e=None;error=None;records=[]
try:
 e=P.M.start(R/'.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe',3,deadline,P.stop)
 for n,v in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(O/'variant.ini'))]:e.send(f'setoption name {n} value {v}');e.ready()
 for W in (4,8):
  sp=importlib.util.spec_from_file_location('T',R/models[W]);T=importlib.util.module_from_spec(sp);sp.loader.exec_module(T);name='aux_pawn' if W==4 else 'aux_pawn8';e.send('setoption name UCI_Variant value '+name);va=e.ready();assert any(z.startswith(f'info string variant {name} files {W} ranks {W} ') for z in va);e.send('devauxleafrnbp 720 720 720 720');ack=e.ready();assert 'info string DEV_AUX leafRNBP 720 720 720 720 nativeP 720 nativeR 720 nativeN 720 nativeB 720 captureP 720 captureR 720 captureN 720 captureB 720' in ack
  cases=json.loads((R/f'results/dev_aux/task1741/literal{W}.json').read_bytes())[:32]
  for i,x in enumerate(cases):
   s=tuple(x['state'])
   for swapped in (0,1):
    state=tuple(p.swapcase() for p in s[:-1])+(1-s[-1],) if swapped else s
    for depth in ((1,2) if i<8 else (1,)):
     P.stop();assert time.monotonic()<deadline;e.send('position fen '+T.fen(state));e.send('go perft '+str(depth));raw=e.until(lambda z:z.startswith('Nodes searched:'));actual={m.group(1):int(m.group(2)) for z in raw if(m:=re.fullmatch(r'([a-h][1-8][a-h][1-8][rnb]?): (\d+)',z))};expected={u:1 if depth==1 else len(T.moves(t)) for u,t in T.moves(state)};assert actual==expected;records.append(dict(width=W,source_id=x['id'],swapped=swapped,state=state,depth=depth,raw=raw))
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:
 if e:e.close()
(O/'records.json').write_text(json.dumps(records));out=dict(status='PASS' if error is None else 'PARTIAL_PRESERVED',error=error,actual_perft=len(records),actual_native_go=0,seconds=time.perf_counter()-start,exit_code=e.p.poll() if e else None);(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
assert error is None

