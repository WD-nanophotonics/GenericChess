import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,importlib.util,ast,re,time,collections
R=Path.cwd();sp=importlib.util.spec_from_file_location('D',R/'results/dev_aux/task1720/driver.py');D=importlib.util.module_from_spec(sp);sp.loader.exec_module(D)
p=json.loads((R/'results/dev_aux/task1727/plan.json').read_bytes());d=D.Driver(p,R/'results/dev_aux/task1728');records=[];dev=[];error=None
tree=ast.parse((R/'results/dev_aux/task1688/qualify_literal_fixed.py').read_text(encoding='utf-8-sig'));fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='ref');ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'independentactors','exec'),ns);ref=ns['ref']
try:
 for f in p['families']:
  for root in f['roots']:
   s=tuple(root);assert ref(s)==d.T.moves(s)
   for u,t in ref(s):assert ref(t)==d.T.moves(t)
 d.start_engine()
 for i,root in enumerate([s for f in p['families'] for s in f['roots']]):
  s=tuple(root);d.choose(s,p['baseline'],64)
  for depth in (1,2) if i<8 else (1,):
   d.e.send('position fen '+d.T.fen(s));d.e.send('go perft '+str(depth));raw=d.e.until(lambda z:z.startswith('Nodes searched:'));actual={m.group(1):int(m.group(2)) for z in raw if (m:=re.fullmatch(r'([a-h][1-8][a-h][1-8][rnb]?): (\d+)',z))};expect={u:1 if depth==1 else len(ref(t)) for u,t in ref(s)}
   assert actual==expect;records.append(dict(depth=depth,state=s,raw=raw))
 (d.O/'qualification.json').write_text(json.dumps(dict(status='PASS',literal_roots=32,all_children=True,actual_perft=len(records),perft_records=records)))
 for price in sorted(set(map(tuple,p['fixed_profiles']))):dev.append(d.evaluate(price,'PILOT'))
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:d.close()
cc=collections.Counter(z['category'] for z in d.rows);phy=sum(cc[k] for k in ('PHYSICAL_MATE','PHYSICAL_STALE'));ng=len(d.rows)
out=dict(status='COMPLETE' if error is None else 'PARTIAL_PRESERVED',error=error,actual_go=d.queries,cache_hits=d.hits,actual_reported_nodes=d.newnodes,seconds=time.perf_counter()-d.start,exit_code=d.e.p.poll() if d.e else None,TRAIN=[],DEV=dev,selected=dict(FIXED53=p['fixed_profiles'][1],FIXED52=p['fixed_profiles'][2]),actual_games=ng,perft=len(records),categories=dict(cc),physical_fraction=phy/ng if ng else None,UNKNOWN_fraction=cc['UNRESOLVED']/ng if ng else None,go_per_game=d.queries/ng if ng else None,advance_predeclared_feasibility=(error is None and phy/ng>=.25 and cc['UNRESOLVED']/ng<=.10 and d.queries/ng<=100))
(d.O/'result.json').write_text(json.dumps(out,indent=2));print(out)

