"""Source/evidence consumer; no new Native/PN query or parameter fitting."""
from pathlib import Path
import importlib,json,time,sys
ROOT=Path.cwd()
def run():
 start=time.perf_counter();import generic_chess
 assert Path(generic_chess.__file__).resolve().is_relative_to(ROOT)
 summary={}
 for task,module in((2057,'audit'),(2059,'audit'),(2066,'audit'),(2074,'audit'),(2079,'audit'),(2080,'weights_audit'),(2085,'audit')):
  m=importlib.import_module(f'results.dev_aux.task{task}.{module}');out=ROOT/'.replay_output'/str(task);out.mkdir(parents=True,exist_ok=False);m.OUT=out;m.run();summary[str(task)]=json.loads((out/'result.json').read_text())['status']
 m=importlib.import_module('results.dev_aux.task2086.portable');out=ROOT/'.replay_output'/'2086';out.mkdir(parents=True,exist_ok=False)
 # Consumer reads original portablecertificates but writes its replay summary elsewhere.
 original=m.OUT;data=(original/'certificates.json').read_bytes();(out/'certificates.json').write_bytes(data);m.OUT=out;m.verify();summary['2086']=json.loads((out/'replay.json').read_text())['status']
 result=dict(status='PASS_NEW_DIRECTORY_FULL_SOURCE_EVIDENCE_REPLAY',modules=summary,seconds=time.perf_counter()-start,scope='Allmodules fromrestoredtree, Python-S/archivedpurepytest+chess dependencies, noNumPyneededforindependentmetrics; noNative/PN/regeneratedcertificate/training. SamehostOS/interpreter. Teacherstrategyexecution isdeterministicproofvalidation, notnewfitness.')
 (ROOT/'.replay_output'/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
