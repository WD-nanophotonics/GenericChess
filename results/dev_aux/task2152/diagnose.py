from pathlib import Path
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from results.dev_aux.task2131.stop_reader import ParsedStopReader
from results.dev_aux.task2152.debug_batch import prove_session_win_batch_pn,DIAGNOSTIC_ERRORS
OUT=Path('results/dev_aux/task2152')
def run():
 if(OUT/'started.json').exists():raise RuntimeError('one30cap diagnosis, nofillingpanel')
 start=time.perf_counter();deadline=start+30;reader=ParsedStopReader(Path.cwd());failures=[]
 def cancel():
  try:reader()
  except Exception as e:
   failures.append(dict(type=type(e).__name__,message=str(e)));raise
  return time.perf_counter()>=deadline
 (OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),cap_seconds=30)),encoding='utf-8')
 inp=json.loads(Path('results/dev_aux/task2139/inputs.json').read_text(encoding='utf-8'))['roots'][25];c=compile_ruleset_for_execution(deserialize_ruleset(Path(inp['rules']).read_text(encoding='utf-8')));s=GameSession(c)
 r=prove_session_win_batch_pn(s,target=1,max_nodes=65536,seconds=6.,max_depth=96,cancel=cancel)
 errors=[dict(e,trace=e['trace'].replace(str(Path.cwd()),'<PROJECT>'))for e in DIAGNOSTIC_ERRORS]
 out=dict(status='SINGLE_CHANGED_OBSERVABILITY_DIAGNOSTIC',original_case=[25,1,65536,6.],result=dict(status=r.status,reason=r.reason,nodes=r.nodes,seconds=r.seconds),caught_prover_errors=errors,cancel_errors=failures,read_count=reader.reads,parse_count=reader.parses,seconds=time.perf_counter()-start,scope='DoesNOTreplaceoriginalunsupported event. CapturedonlyNEWdiagnostic; ifnotreproduced originalcauseunidentified, no guessedCPU/JSONattribution.')
 (OUT/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out),flush=True)
if __name__=='__main__':run()
