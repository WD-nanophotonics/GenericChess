"""Fixed-profile matched policy control, no training/selection."""
import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,importlib.util,ast,re,time,collections
R=Path.cwd();sp=importlib.util.spec_from_file_location('D',R/'results/dev_aux/task1720/driver.py');D=importlib.util.module_from_spec(sp);sp.loader.exec_module(D)
p=json.loads((R/sys.argv[1]).read_bytes());d=D.Driver(p,R/sys.argv[2]);records=[];dev=[];error=None
tree=ast.parse((R/'results/dev_aux/task1688/qualify_literal_fixed.py').read_text(encoding='utf-8-sig'));fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='ref');ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'independentactors','exec'),ns);ref=ns['ref']
try:
 for f in p['families']:
  for root in f['roots']:
   s=tuple(root);assert ref(s)==d.T.moves(s)
 d.start_engine()
 for price in sorted(map(tuple,p['fixed_profiles'])):
  for f in p['families'][:4]:
   s=tuple(f['roots'][0]);d.choose(s,price,64);d.e.send('position fen '+d.T.fen(s));d.e.send('go perft 1');raw=d.e.until(lambda z:z.startswith('Nodes searched:'));actual={m.group(1):int(m.group(2)) for z in raw if (m:=re.fullmatch(r'([a-h][1-8][a-h][1-8][rnb]?): (\d+)',z))};assert actual=={u:1 for u,t in ref(s)};records.append(dict(price=price,state=s,raw=raw))
 (d.O/'qualification.json').write_text(json.dumps(dict(status='PASS',literal_roots=2*len(p['families']),actual_perft=len(records),records=records)))
 for price in sorted(set(map(tuple,p['fixed_profiles']))):
  for phase in sorted({f['phase'] for f in p['families']}):dev.append(d.evaluate(price,phase))
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:d.close()
out=dict(status='COMPLETE' if error is None else 'PARTIAL_PRESERVED',error=error,actual_go=d.queries,cache_hits=d.hits,actual_reported_nodes=d.newnodes,seconds=time.perf_counter()-d.start,exit_code=d.e.p.poll() if d.e else None,TRAIN=[],DEV=dev,selected={},actual_games=len(d.rows),perft=len(records),source_sha256=D.sha('results/dev_aux/task1720/fixed.py'))
(d.O/'result.json').write_text(json.dumps(out,indent=2));print('FINAL', {k:v for k,v in out.items() if k not in ('TRAIN','DEV')})

