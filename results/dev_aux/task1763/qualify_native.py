"""Post-run Native perft qualification of BOTH exact pilot price profiles."""
import json,time,re,importlib.util
from pathlib import Path
from scripts.generic_proof_rnb_bridge import compile_rnb,from_actor,uci
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
p=Path('results/dev_aux/task1763');plan=json.loads((p/'plan.json').read_text());c=compile_rnb()
sp=importlib.util.spec_from_file_location('P54','results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(sp);sp.loader.exec_module(P)
Tspec=importlib.util.spec_from_file_location('T54',plan['model']);T=importlib.util.module_from_spec(Tspec);Tspec.loader.exec_module(T)
start=time.perf_counter();e=P.M.start(Path(plan['binary']).resolve(),3,time.monotonic()+180,P.stop);records=[]
try:
 for name,value in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(Path(plan['variant_ini']).resolve()))]:e.send(f'setoption name {name} value {value}');e.ready()
 for price in plan['prices']:
  name=plan['variant_names'][str(tuple(price))];e.send('setoption name UCI_Variant value '+name);va=e.ready();e.send('devauxleafrnbp '+' '.join(map(str,price)));ack=e.ready()
  for f in plan['families']:
   for color,raw in enumerate(f['roots']):
    s=from_actor(c,raw)
    for depth in (1,2):
     P.stop();e.send('position fen '+T.fen(raw));e.send('go perft '+str(depth));out=e.until(lambda z:z.startswith('Nodes searched:'))
     native={m.group(1):int(m.group(2)) for row in out if(m:=re.fullmatch(r'([a-h][1-8][a-h][1-8][rnb]?): (\d+)',row))}
     expected={uci(a):1 if depth==1 else len(legal_actions(apply_action(s,a,c),c)) for a in legal_actions(s,c)}
     assert native==expected,(f['family'],color,depth,native,expected)
     records.append(dict(family=f['family'],color=color,price=price,depth=depth,raw=out))
finally:e.close()
(p/'native_perft_records.json').write_text(json.dumps(records));out=dict(status='PASS_ALL_ROOTS_BOTH_PROFILES_D1_D2',actual_perft=len(records),seconds=time.perf_counter()-start,qualification_timing='After pilot, retained honestly; no games repeated or relabeled.',exit_code=e.p.poll())
(p/'native_qualification.json').write_text(json.dumps(out,indent=2));print(out)
