from pathlib import Path
from collections import Counter
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_session_cached_phase_player import SessionCachedPhasePlayer
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_native_material import _load_transport
from scripts.generic_proof_rnb_bridge import actor_state
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2072.no_win_filter import CompleteGraphNoWinFilter
from results.dev_aux.task2100.campaign import evaluate
OUT=Path('results/dev_aux/task2116')
def run():
 if (OUT/'started.json').exists():raise RuntimeError('one frozen cap, no restart')
 start=time.perf_counter();p=json.loads((OUT/'plan.json').read_text());deadline=start+p['one_cap_seconds'];(OUT/'started.json').write_text(json.dumps(dict(started=True,source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())),encoding='utf-8')
 stop=_load_transport().stop_check
 def cancelled():stop(Path.cwd());return time.perf_counter()>=deadline
 g=json.loads(Path('results/dev_aux/task2100/games.jsonl').read_text().splitlines()[0]);roots=json.loads(Path('results/dev_aux/task2100/inputs.json').read_text())['roots'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(roots[g['family']]['rules']).read_text(encoding='utf-8')));record=deserialize_game_record(json.dumps(g['record']));s=GameSession(c);load=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2097','results/dev_aux/task2098','results/dev_aux/task2099');load=time.perf_counter()-load;provider=CompleteGraphNoWinFilter(teacher);rows=[]
 limits=PhaseLimits(proof_nodes=p['proof_nodes'],verification_nodes=p['verification_nodes'],proof_seconds=p['proof_seconds'],verification_seconds=p['verification_seconds'],normal_seconds=p['normal_seconds'])
 with (OUT/'queries.jsonl').open('x',encoding='utf-8')as f:
  for ply in p['prefix_plies']:
   side=s.state.position.side_to_move;targetrow=teacher.rows[teacher.key(actor_state(s.state))];v={'WIN':1,'DRAW':0,'LOSS':-1}[targetrow['label']];cases=[]
   for name in (p['providers']if ply%2==0 else list(reversed(p['providers']))):
    if cancelled():break
    player=SessionCachedPhasePlayer(c,evaluate(g['ratio']if side==g['candidate_side']else 1.),bank=SessionLogicalProofBank(provider if name=='NEGATIVE_FILTER'else prove_session_win_batch_pn,capacity=256),limits=limits,proof_enabled=True,max_depth=p['normal_depth'],proof_depth=p['proof_depth']);d=player.choose(s,max_nodes=p['normal_nodes'],seconds=p['total_seconds'],cancel=cancelled)
    row=dict(ply=ply,side=side,pieces=sum(x is not None for x in s.state.position.board),position_value_for_side_to_move=v,provider=name,full_record=json.loads(serialize_game_record(s.to_record())),choice=None if d.choice is None else action_to_dict(d.choice.action),source=d.source,proof_reason=d.proof_reason,logical_status=d.logical_status,proof_nodes=d.proof_nodes,proof_seconds=d.proof_seconds,normal_nodes=d.search_nodes,normal_seconds=d.normal_seconds,normal_depth=None if d.normal_receipt is None else d.normal_receipt.completed_depth,seconds=d.seconds,limits=dict(d.phase_limits));f.write(json.dumps(row)+'\n');f.flush();rows.append(row);cases.append(row)
   print(json.dumps(dict(ply=ply,paired=len(cases),seconds=time.perf_counter()-start)),flush=True)
   if len(cases)<2:break
   s.submit(record.actions[ply])
 result=dict(status='COMPLETE'if len(rows)==16 else'CAP_PARTIAL',queries=len(rows),teacher_load_seconds=load,teacher_prepaid_seconds=p['teacher_prepaid_seconds'],seconds=time.perf_counter()-start,by_provider={n:dict(queries=sum(r['provider']==n for r in rows),proof_nodes=sum(r['proof_nodes']for r in rows if r['provider']==n),proof_seconds=sum(r['proof_seconds']for r in rows if r['provider']==n),normal_nodes=sum(r['normal_nodes']for r in rows if r['provider']==n),normal_depths=dict(Counter(r['normal_depth']for r in rows if r['provider']==n)))for n in p['providers']})
 (OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':run()
