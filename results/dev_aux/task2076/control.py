"""Prospective paired opt-in proof-cost decisions on frozen actual histories."""
from pathlib import Path
import json,hashlib,time
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_session_cached_phase_player import SessionCachedPhasePlayer
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from scripts.generic_inventory_proof_transport import SetupTransportedNoWinFilter
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2072.no_win_filter import CompleteGraphNoWinFilter
from results.dev_aux.task2063.campaign import evaluator
OUT=Path('results/dev_aux/task2076')
def run():
 p=json.loads((OUT/'plan.json').read_text());assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in p['source_sha'].items());beg=time.perf_counter();init=time.perf_counter();teacher=CanonicalTeacher('results/dev_aux/task2056','results/dev_aux/task2058','results/dev_aux/task2059');new=CompleteGraphNoWinFilter(teacher);newinit=time.perf_counter()-init;rows=[];baseinit=0.
 weights=json.loads(Path('results/dev_aux/task2060/models.json').read_text())['material'];limits=PhaseLimits(proof_nodes=p['proof_nodes'],verification_nodes=p['verification_nodes'],proof_seconds=p['proof_seconds'],verification_seconds=p['verification_seconds'],normal_seconds=p['normal_seconds'])
 with(OUT/'decisions.jsonl').open('x')as f:
  for case in p['cases']:
   c=compile_ruleset_for_execution(deserialize_ruleset(Path(case['rules']).read_text()));s=GameSession.replay(c,deserialize_game_record(json.dumps(case['record'])));assert hashlib.sha256(repr(s.state).encode()).hexdigest()==case['state_sha'];before=s.to_record();init=time.perf_counter();old=SetupTransportedNoWinFilter('results/dev_aux/task2044','results/dev_aux/task2045/coverage.json',c);baseinit+=time.perf_counter()-init
   for arm in(p['arms']if case['index']%2==0 else p['arms'][::-1]):
    player=SessionCachedPhasePlayer(c,evaluator(weights),bank=SessionLogicalProofBank(old if arm==p['arms'][0]else new,capacity=256),limits=limits,proof_enabled=True,max_depth=p['normal_depth'],proof_depth=p['proof_depth']);d=player.choose(s,max_nodes=p['normal_nodes'],seconds=p['step_seconds'],cancel=lambda:time.perf_counter()-beg>=p['seconds_cap']);assert s.to_record()==before and d.choice is not None
    row=dict(case=case['index'],arm=arm,source=d.source,choice=action_to_dict(d.choice.action),proof_reason=d.proof_reason,proof_nodes=d.proof_nodes,normal_nodes=d.search_nodes,completed_depth=None if d.normal_receipt is None else d.normal_receipt.completed_depth,seconds=d.seconds,proof_seconds=d.proof_seconds,normal_seconds=d.normal_seconds,verification_nodes=d.verification_nodes,bank_hit=d.bank_hit);f.write(json.dumps(row)+'\n');f.flush();rows.append(row)
   assert time.perf_counter()-beg<p['seconds_cap']
 old=[r for r in rows if r['arm']==p['arms'][0]];newrows=[r for r in rows if r['arm']==p['arms'][1]];olds={r['case']:r for r in old};news={r['case']:r for r in newrows};saving=sum(r['seconds']for r in old)-sum(r['seconds']for r in newrows)
 result=dict(status='COMPLETE_FROZEN_PAIRED_FULL_HISTORY_DECISIONS',cases=16,decisions=len(rows),same_actions=sum(olds[i]['choice']==news[i]['choice']for i in olds),same_normal_nodes=sum(olds[i]['normal_nodes']==news[i]['normal_nodes']for i in olds),same_completed_depth=sum(olds[i]['completed_depth']==news[i]['completed_depth']for i in olds),old_proof_nodes=sum(r['proof_nodes']for r in old),new_proof_nodes=sum(r['proof_nodes']for r in newrows),old_decision_seconds=sum(r['seconds']for r in old),new_decision_seconds=sum(r['seconds']for r in newrows),new_teacher_load_seconds=newinit,baseline_filter_initialization_seconds=baseinit,new_teacher_build_seconds=p['teacher_build_cost_seconds'],estimated_calls_to_pay_teacher_build_and_load=None if saving<=0 else(p['teacher_build_cost_seconds']+newinit)/(saving/16),seconds=time.perf_counter()-beg,scope=p['sampling'])
 (OUT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':run()
