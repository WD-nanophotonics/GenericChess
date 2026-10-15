import sys
from pathlib import Path
sys.path=[p for p in sys.path if Path(p).resolve()!=Path(__file__).resolve().parent]
import json,ast,importlib.util,re,time
R=Path.cwd();sp=importlib.util.spec_from_file_location('D',R/'results/dev_aux/task1720/driver.py');D=importlib.util.module_from_spec(sp);sp.loader.exec_module(D)
p=json.loads((R/'results/dev_aux/task1719/plan.json').read_bytes());p['seconds_cap']=180;p['max_go']=96;d=D.Driver(p,R/'results/dev_aux/task1722')
tree=ast.parse((R/'results/dev_aux/task1688/qualify_literal_fixed.py').read_text(encoding='utf-8-sig'));fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='ref');ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'ref','exec'),ns);ref=ns['ref']
records=[];error=None;replay=[];perft=[]
clean=lambda raw:[re.sub(r'\b(?:time|nps) \d+','TIME_OR_NPS',z) for z in raw]
try:
 for f in p['families']:
  for root in f['roots']:
   s=tuple(root);assert ref(s)==d.T.moves(s)
   for u,t in ref(s):assert ref(t)==d.T.moves(t)
 d.start_engine()
 for i,price in enumerate(map(tuple,p['prices'])):
  for f in p['families'][:4]:
   s=tuple(f['roots'][i%2]);d.choose(s,price,64)
   d.e.send('position fen '+d.T.fen(s));d.e.send('go perft 1');raw=d.e.until(lambda z:z.startswith('Nodes searched:'));native={m.group(1):int(m.group(2)) for z in raw if (m:=re.fullmatch(r'([a-h][1-8][a-h][1-8][rnb]?): (\d+)',z))}
   assert native=={u:1 for u,t in ref(s)};perft.append(dict(price=price,state=s,raw=raw))
 # Direct saved 1-clear vs original2-clear; selected roots, ALL 12 global aligned prices.
 for i,x in enumerate([json.loads(l) for l in (d.O/'choices.jsonl').open()][::2]):
  price=tuple(x['price']);d.e.send('setoption name UCI_Variant value '+p['variant_names'][str(price)]);va=d.e.ready()
  d.e.send('devauxleafrnbp '+' '.join(map(str,price)));ack=d.e.ready();d.e.send('ucinewgame');d.e.ready()
  d.e.send('position fen '+x['fen']);d.e.send(x['command']);raw=d.e.until(lambda z:z.startswith('bestmove '));d.e.ready()
  assert raw[-1].split()[1]==x['move'] and clean(raw[:-1])==clean(x['uci_info']);replay.append(dict(source=x,raw=raw,ack=ack,variant_ack=va,explicit_clear_commands=2))
except BaseException as ex:error=type(ex).__name__+':'+str(ex)
finally:d.close()
(d.O/'perft.json').write_text(json.dumps(perft));(d.O/'replay.json').write_text(json.dumps(replay))
out=dict(status='PASS' if error is None else 'PARTIAL_PRESERVED',error=error,actual_go=d.queries+len(replay),newdriver_go=d.queries,original_replay_go=len(replay),perft=len(perft),literal_roots=224,exit_code=d.e.p.poll() if d.e else None,seconds=time.perf_counter()-d.start,scope='All new112paired roots and all children independently agree, all12 global profiles actual48 perft, 24 newdriver1clear vsoriginal2clear rawmatches excludingtime/nps. No wall ratio claim.')
(d.O/'result.json').write_text(json.dumps(out,indent=2));print(out)
assert error is None

