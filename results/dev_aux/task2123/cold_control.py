from pathlib import Path
import json,time,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_session_cached_phase_player import SessionCachedPhasePlayer
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from results.dev_aux.task2105.provider import TriggerProvider
from results.dev_aux.task2100.campaign import evaluate
from results.dev_aux.task2068.teacher import CanonicalTeacher
OUT=Path('results/dev_aux/task2123')
def run(teacher=None):
 if(OUT/'started.json').exists():raise RuntimeError('single90cap/no rerun')
 start=time.perf_counter();deadline=start+90;p=json.loads((OUT/'plan.json').read_text());(OUT/'started.json').write_text(json.dumps(dict(source_sha=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())),encoding='utf-8');load=time.perf_counter();teacher=teacher or CanonicalTeacher('results/dev_aux/task2097','results/dev_aux/task2098','results/dev_aux/task2099');load=time.perf_counter()-load;case=json.loads(Path('results/dev_aux/task2117/cases-frozen-before-labels.json').read_text())['cases'][40];assert case['family']==11;roots=json.loads(Path('results/dev_aux/task2100/inputs.json').read_text())['roots'];c=compile_ruleset_for_execution(deserialize_ruleset(Path(roots[11]['rules']).read_text(encoding='utf-8')));s=GameSession.replay(c,deserialize_game_record(json.dumps(case['record'])));limits=PhaseLimits(proof_nodes=1024,verification_nodes=16384,proof_seconds=.2,verification_seconds=.2,normal_seconds=.25);rows=[]
 for ratio in p['ratios']:
  player=SessionCachedPhasePlayer(c,evaluate(ratio),bank=SessionLogicalProofBank(TriggerProvider(teacher),capacity=256),limits=limits,proof_enabled=True,max_depth=2,proof_depth=64);d=player.choose(s,max_nodes=512,seconds=.75,cancel=lambda:time.perf_counter()>=deadline);rows.append(dict(ratio=ratio,choice=None if d.choice is None else action_to_dict(d.choice.action),source=d.source,proof_reason=d.proof_reason,proof_nodes=d.proof_nodes,proof_seconds=d.proof_seconds,completed_depth=None if d.normal_receipt is None else d.normal_receipt.completed_depth,nodes=d.search_nodes,seconds=d.seconds,limits=dict(d.phase_limits)))
 assert all(r['completed_depth']==2 and r['source']=='MATERIAL_SEARCH'and r['proof_reason']=='certified_complete_graph_no_win'for r in rows);assert all(rows[i]['choice']==rows[5-i]['choice']for i in range(3));assert rows[0]['choice']!=rows[2]['choice']
 result=dict(status='PASS_ACTUAL_COLD_FULL_POLICY_POSTTRIGGER_PRICE_DEPENDENCE',queries=6,case=40,family=11,teacher_load_seconds=load,seconds=time.perf_counter()-start,scope=p['scope'],all_completed_depth2=True,reverse_order_stable=True,actual_ACTION_divergence=True,all_child_positional_WDL=0,no_WDL_gain_claim=True,no_game_or_policy_change=True)
 (OUT/'queries.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)
if __name__=='__main__':run()
