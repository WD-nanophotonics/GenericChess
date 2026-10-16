"""One bounded intrusive cost profile of the observed expensive TRAIN LOW entry."""
from pathlib import Path
import json,time,hashlib,cProfile,pstats,uuid,datetime
from dataclasses import fields
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from results.dev_aux.task2273.incremental_adapted import prove_incremental_graph
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2377')
def run():
 assert Path('results/dev_aux/task2362/completion.json').exists(),'No secondproofproducer whileactualvalidationactive'
 p=json.loads((OUT/'plan.json').read_text());assert not(OUT/'result.json').exists()and not(OUT/'started.json').exists();f=Path('results/dev_aux/task2358');plan=json.loads((f/'plan.json').read_text());roots={r['index']:r for r in json.loads(Path(plan['input']).read_text())};d=next(d for d in map(json.loads,(f/'decisions.jsonl').read_text().splitlines())if(d['slot'],d['ply'])==(p['matrix_slot'],p['ply']));r=roots[p['family']];s=GameSession.replay(compile_ruleset_for_execution(deserialize_ruleset(Path(r['rules']).read_text())),deserialize_game_record(json.dumps(d['root_record'])));assert hashlib.sha256(repr(s.state).encode()).hexdigest()==p['root_state_sha'];stop=EvidenceStopReader(Path.cwd());stop();before=stop.reads;before_bytes=stop.bytes_read;tick=time.perf_counter();prof=cProfile.Profile()
 def cancel():stop();return False
 private=Path('.local_agent')/('profile82-'+uuid.uuid4().hex);private.mkdir();result=None
 with(OUT/'started.json').open('x')as fp:json.dump(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),plan_sha=hashlib.sha256((OUT/'plan.json').read_bytes()).hexdigest(),one_attempt=True),fp)
 try:
  prof.enable();result=prove_incremental_graph(s,max_nodes=65536,max_edges=524288,seconds=p['seconds'],max_depth=96,cancel=cancel)
 except BaseException as error:
  with(OUT/'failure.json').open('x')as fp:json.dump(dict(error_type=type(error).__name__,action='FAIL_CLOSED_NO_RETRY',raw_private_profile_retained=True),fp)
  raise
 finally:
  prof.disable();prof.dump_stats(str(private/'raw.prof'))
 wall=time.perf_counter()-tick;stats=pstats.Stats(prof).stats;root=Path.cwd().resolve();rows=[];stop_cumulative=0.
 for (filename,line,name),(primitive,calls,exclusive,cumulative,callers)in stats.items():
  path=Path(filename)
  if filename.startswith('~')or filename.startswith('<'):safe='python-runtime'
  elif path.resolve().is_relative_to(root):safe=path.resolve().relative_to(root).as_posix()
  else:safe='external/'+path.name
  if safe.endswith('stop_evidence.py')and name=='__call__':stop_cumulative+=cumulative
  rows.append(dict(file=safe,line=line,function=name,primitive_calls=primitive,calls=calls,exclusive_seconds=exclusive,cumulative_seconds=cumulative))
 rows.sort(key=lambda r:r['exclusive_seconds'],reverse=True);simple={field.name:getattr(result,field.name)for field in fields(result)if field.name!='certificate'and isinstance(getattr(result,field.name),(str,int,float,bool,type(None)))}
 public=dict(status='ONE_BOUNDED_INTRUSIVE_COST_PROFILE',context={k:p[k]for k in('family','matrix_slot','ply','root_state_sha')},requested_seconds=p['seconds'],measured_seconds=wall,result_fields=simple,unverified_candidate_returned=getattr(result,'certificate',None)is not None,stop_reads=stop.reads-before,stop_bytes=stop.bytes_read-before_bytes,profile_reported_total_exclusive=sum(r['exclusive_seconds']for r in rows),stop_reader_reported_cumulative_seconds=stop_cumulative,top_exclusive_functions=rows[:25],raw_private_profile_retained=True,scope=p['scope'])
 with(OUT/'result.json').open('x')as fp:json.dump(public,fp,indent=2)
 print(json.dumps({k:v for k,v in public.items()if k!='top_exclusive_functions'}));print(json.dumps(rows[:8]))
if __name__=='__main__':run()
