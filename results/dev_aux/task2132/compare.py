from pathlib import Path
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_session_native_material import _load_transport
from scripts.generic_proof_player import ProofMaterialPlayer
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from results.dev_aux.task2100.campaign import evaluate
from results.dev_aux.task2131.stop_reader import ParsedStopReader
OUT=Path('results/dev_aux/task2132')
def run():
 if(OUT/'started.json').exists():raise RuntimeError('one120cap no restart')
 start=time.perf_counter();deadline=start+120;p=json.loads((OUT/'plan.json').read_text());(OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())),encoding='utf-8');legacy=_load_transport().stop_check;root=Path.cwd();g=json.loads(Path('results/dev_aux/task2100/games.jsonl').read_text().splitlines()[0]);inputs=json.loads(Path('results/dev_aux/task2100/inputs.json').read_text())['roots'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(inputs[g['family']]['rules']).read_text(encoding='utf-8')));s=GameSession(c);record=deserialize_game_record(json.dumps(g['record']));rows=[]
 for ply in range(8):
  for kind in('NORMAL','PN'):
   for arm in(p['arms']if(ply+(kind=='PN'))%2==0 else list(reversed(p['arms']))):
    reader=ParsedStopReader(root)if arm=='PARSED_BYTES_CACHE'else None;calls=0;callbacktime=0.
    def cancelled():
     nonlocal calls,callbacktime
     began=time.perf_counter()
     if reader is None:legacy(root)
     else:reader()
     calls+=1;callbacktime+=time.perf_counter()-began;return time.perf_counter()>=deadline
    began=time.perf_counter()
    r=ProofMaterialPlayer(c,evaluate(g['ratio']if s.state.position.side_to_move==g['candidate_side']else 1.),proof_enabled=False,max_depth=3).choose(s.state,max_nodes=4096,seconds=.1,cancel=cancelled)if kind=='NORMAL'else prove_session_win_batch_pn(s,max_nodes=1024,seconds=.2,max_depth=64,cancel=cancelled)
    elapsed=time.perf_counter()-began;rows.append(dict(ply=ply,kind=kind,arm=arm,callback_calls=calls,callback_seconds=callbacktime,seconds=elapsed,nodes=r.nodes,reason=r.exit_cause if kind=='NORMAL'else r.reason,completed_depth=r.completed_depth if kind=='NORMAL'else None,choice=action_to_dict(r.action)if kind=='NORMAL'and r.action is not None else None,status=r.status if kind=='PN'else r.source,actual_reads=reader.reads if reader else None,actual_parses=reader.parses if reader else None,bytes_read=reader.bytes_read if reader else None))
   if time.perf_counter()>=deadline:raise TimeoutError('one120cap')
  s.submit(record.actions[ply])
 summary={}
 for kind in('NORMAL','PN'):
  summary[kind]={}
  for arm in p['arms']:
   rr=[r for r in rows if r['kind']==kind and r['arm']==arm];summary[kind][arm]=dict(queries=len(rr),nodes=sum(r['nodes']for r in rr),seconds=sum(r['seconds']for r in rr),callback_calls=sum(r['callback_calls']for r in rr),callback_seconds=sum(r['callback_seconds']for r in rr),completed_depths=[r['completed_depth']for r in rr])
 result=dict(status='COMPLETE_FRESH_BYTES_SAME_BUDGET_STOP_PARSE_COMPARISON',queries=len(rows),summary=summary,seconds=time.perf_counter()-start,scope=p['scope'],no_stop_semantics_or_flag_change=True)
 (OUT/'queries.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
