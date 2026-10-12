"""Actual32rootqualification onnew mode0/3 binary before learning."""
import json,time,hashlib,sys,importlib.util,chess
from pathlib import Path
R=Path.cwd();O=R/'results/dev_aux/task152'
spec=importlib.util.spec_from_file_location('M152qual',R/'results/dev_aux/task139/run.py');M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M);A=M.A
D=json.loads((O/'declaration.json').read_bytes());binary=R/D['binary_relative'];assert hashlib.sha256(binary.read_bytes()).hexdigest()==D['binary_sha256']
old=json.loads((R/'results/dev_aux/task133/declaration.json').read_bytes());started=time.monotonic();deadline=started+120;stop=lambda:A.stop_check(R);rows=[]
if (O/'qualification.json').exists():raise FileExistsError('frozenqualification')
for profile,w in old['profiles'].items():
 for mode in (0,3):
  e=M.start(binary,mode,deadline,stop)
  try:
   for root in old['roots']:
    probes,ack=M.configure(e,w,O/'qual-variant.ini',deadline,stop);b=chess.Board()
    for m in root['history']:b.push_uci(m)
    move,meta=M.M.search(e,b.copy(stack=True),deadline,stop)
    assert move in b.legal_moves
    rows.append(dict(profile=profile,weights=w,mode=mode,root=root,move=move.uci(),metadata=meta,leaf_probes=probes,table_ack=ack))
  finally:e.close()
A.atomic_json(O/'qualification.json',dict(complete=True,binary_sha256=D['binary_sha256'],searches=len(rows),rows=rows,wall_seconds=time.monotonic()-started,scope='Samebinaryactual0/3parameter/legalityqualification onexposedroots; notlearningorstrengthproof'))
print(json.dumps(dict(qualified=True,actualsearches=len(rows),leafprobes=5*len(rows),seconds=time.monotonic()-started)))
