import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import importlib.util,json,time,re,hashlib
R=Path.cwd();O=R/'results/dev_aux/task1676';O.mkdir(exist_ok=False)
def module(n,path):
 sp=importlib.util.spec_from_file_location(n,R/path);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);return m
T=module('T','results/dev_aux/task1675/rules.py');P=module('P','results/dev_aux/task166/run.py');cases=json.loads((R/'results/dev_aux/task1675/literal_cases.json').read_bytes());selected=list(range(512));more=[i for i,x in enumerate(cases) if any(len(u)==5 for u,t in x['moves']) or any(tuple(t)[:16].count('R')>1 or tuple(t)[:16].count('r')>1 for u,t in x['moves'])];selected=sorted(set(selected+more));start=time.monotonic();deadline=start+180;e=None;error=None;records=[]
(O/'frozen_indices.json').write_text(json.dumps({'indices':selected,'D2_first':64,'seconds_cap':180,'priceblind':True}))
try:
 e=P.M.start(R/'.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe',3,deadline,P.stop)
 for name,val in [('Threads',1),('Hash',16),('Use NNUE','false'),('SyzygyPath','<empty>'),('VariantPath',str(R/'results/dev_aux/task1675/variant.ini')),('UCI_Variant','aux_pawn')]:
  e.send(f'setoption name {name} value {val}');ack=e.ready()
  if name=='UCI_Variant':(O/'variant_ack.json').write_text(json.dumps(ack));assert any(l.startswith('info string variant aux_pawn files 4 ranks 4 ') for l in ack),ack
 with (O/'native.jsonl').open('w') as f:
  for i in selected:
   P.stop();assert time.monotonic()<deadline;s=tuple(cases[i]['state']);expected=dict(T.moves(s));e.send('position fen '+T.fen(s));e.send('go perft 1');raw=e.until(lambda l:'Nodes searched:' in l,max_lines=300);got={m.group(1):int(m.group(2)) for l in raw if (m:=re.fullmatch(r'([a-d][1-4][a-d][1-4][rnb]?):\s*(\d+)',l.strip()))};assert sorted(got)==sorted(expected),(i,T.fen(s),got,sorted(expected));r={'index':i,'depth':1,'state':s,'raw':raw};records.append(r);f.write(json.dumps(r)+'\n')
   if i<64:
    e.send('position fen '+T.fen(s));e.send('go perft 2');raw=e.until(lambda l:'Nodes searched:' in l,max_lines=300);got={m.group(1):int(m.group(2)) for l in raw if (m:=re.fullmatch(r'([a-d][1-4][a-d][1-4][rnb]?):\s*(\d+)',l.strip()))};assert got=={u:len(T.moves(t)) for u,t in expected.items()},(i,got);r={'index':i,'depth':2,'state':s,'raw':raw};records.append(r);f.write(json.dumps(r)+'\n')
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:
 if e:e.close()
out={'status':'PASS_NATIVE_PAWN_PROMOTION_DUPLICATE_FRONTIERS' if error is None else 'FAIL_PRESERVED','error':error,'actual_perft':len(records),'D1':sum(x['depth']==1 for x in records),'D2':sum(x['depth']==2 for x in records),'seconds':time.monotonic()-start,'exit_code':e.p.poll() if e else None,'binary_sha256':hashlib.sha256((R/'.local_agent/leaf-rnbp-46/fairy-leaf-rnb.exe').read_bytes()).hexdigest(),'model_sha256':hashlib.sha256((R/'results/dev_aux/task1675/rules.py').read_bytes()).hexdigest()};(O/'result.json').write_text(json.dumps(out,indent=2));print(out)
