import json,time,sys,importlib.util,hashlib,random,datetime
from pathlib import Path
import chess
R=Path.cwd();O=R/'results/dev_aux/task263';assert not (O/'result.json').exists();base=json.loads((R/'results/dev_aux/task258/declaration.json').read_bytes());native=json.loads((R/'results/dev_aux/task259/declaration.json').read_bytes());semantic=json.loads((R/'results/dev_aux/task261/profile.json').read_bytes());profiles={'unit':base['unit'],'semantic':semantic['normalized_P208'],**{k:v for k,v in native['profiles'].items() if k.endswith('-base')}}
# Four fixedcyclic rotations PNBRQ, preserveactualsemanticnumericmultiset andK0.
keys='PNBRQ';vec=[profiles['semantic'][k] for k in keys]
for shift in (1,2,3,4):profiles[f'semantic-permutation-{shift}']=dict(zip(keys,vec[shift:]+vec[:shift]),K=0)
D=dict(task_id='263',question='Can actualmature1thread material-only backend use samefullhistorycapture roots cheaply; semantic/random/permutedprice controls andnodecostcurve?',roots=base['roots'],profiles=profiles,node_limits=[1024,16384,262144],binary_relative='.local_agent/alignment-order/fairy-order-toggle.exe',binary_sha256='c378f0b3fc9f99d48e3089294a7c6adf5d5215bcac070200424d0d24f4d4b460',alignment=3,deadline_seconds=600,created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='108freshcoldactualmatureUCIqueries; unchanged1thread/16MiB fixedmargins/pruning/order hooks. Reportactualnodes/depth/overshoot; q/selectivity differsfiniteq0Native, notmatchedD3/humanlearning/standardStockfishproof. Pricepermutationspreservemultiset/K0 butPvaries, nohumanlabel orbesttable selection. Estimated<=90s actualqueries; fixedcurve noresultdrivenextensions.')
(O/'declaration.json').write_text(json.dumps(D,indent=2),encoding='utf-8');s=importlib.util.spec_from_file_location('p',R/'results/dev_aux/task166/run.py');P=importlib.util.module_from_spec(s);s.loader.exec_module(P);P.stop();binary=R/D['binary_relative'];assert hashlib.sha256(binary.read_bytes()).hexdigest()==D['binary_sha256'];start=time.monotonic();deadline=start+600;rows=[];out=dict(complete=False,rows=rows)
def save():out['seconds']=time.monotonic()-start;P.A.atomic_json(O/'result.json',out)
try:
 for name,w in profiles.items():
  e=P.M.start(binary,3,deadline,P.stop)
  try:
   for f in D['roots']:
    b=chess.Board(f['initial_fen'])
    for text in f['history']:b.push_uci(text)
    assert b.fen()==f['fen']
    for limit in (D['node_limits'] if len(rows)//3%2==0 else list(reversed(D['node_limits']))):
     probes,ack=P.M.configure(e,w,O/'variant.ini',deadline,P.stop);ts=time.monotonic();move,meta=P.M.M.search(e,b.copy(stack=True),deadline,P.stop,limit=limit);rows.append(dict(profile=name,weights=w,root=f['id'],move=move.uci(),metadata=meta,wall_seconds=time.monotonic()-ts,leaf_probes=probes,table_ack=ack));save()
  finally:e.close()
  print(name,len(rows),round(time.monotonic()-start,3),flush=True)
 out['complete']=True;save();print('COMPLETE',len(rows),out['seconds'])
except BaseException as ex:out['failure']=dict(type=type(ex).__name__,message=str(ex));save();raise
