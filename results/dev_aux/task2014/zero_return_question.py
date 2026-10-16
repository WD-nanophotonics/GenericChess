"""Scoped future zero-return question; current actual-terminal rewards unchanged."""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.session.session import GameSession
from scripts.generic_inventory_proof_transport import SetupTransportedNoWinFilter
BASE=Path('results/dev_aux');OUT=BASE/'task2014'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def lines(p):return[json.loads(x)for x in Path(p).read_text().splitlines()]
def run():
 assert read(BASE/'task2012/result.json')['status']=='PASS_PREDECLARED_ACTUAL_RULE_COMPLETION'
 p=read(BASE/'task1997/run-plan.json');c=compile_ruleset_for_execution(deserialize_ruleset(Path(p['rules']).read_text()));roots=read(p['roots'])['roots'];filt=SetupTransportedNoWinFilter(BASE/'task1895',BASE/'task1896/coverage.json',c)
 full=lines(BASE/'task2011/games.jsonl');mid={g['slot']:g for g in lines(BASE/'task2005/games.jsonl')};early={g['slot']:g for g in lines(BASE/'task1997/games.jsonl')};steps={}
 for task in(1997,2005,2011):
  group=defaultdict(list)
  for m in lines(BASE/f'task{task}/moves.jsonl'):group[m['slot']].append(m)
  steps[task]=group
 hits=[];counterexample=None;all_terminal=Counter()
 for g in full:
  parent=mid[g['parent_slot']];origin=early[parent['parent_slot']];trace=steps[1997][origin['slot']]+steps[2005][parent['slot']]+steps[2011][g['slot']];record=deserialize_game_record(json.dumps(g['record']));assert len(trace)==len(record.actions)
  s=GameSession(c,roots[g['family']]['setup']);entry=None
  for i,action in enumerate(record.actions):
   assert trace[i]['ply']==i and hashlib.sha256(repr(s.state).encode()).hexdigest()==trace[i]['before_state_sha']
   if entry is None and filt.eligible(s):
    entry=i
    if counterexample is None:
     prefix=s.to_record();probe=GameSession.replay(c,prefix);side=probe.state.position.side_to_move;result=probe.resign()
     assert result.winner==1-side
     counterexample=dict(mode='REAL_SESSION_API_COUNTEREXAMPLE_NOT_STUDY_REWARD',case_slot=g['slot'],prefix_record=json.loads(serialize_game_record(prefix)),resigned_record=json.loads(serialize_game_record(probe.to_record())),winner=result.winner,status=result.status.value,claim_refuted='No possible winner across ALL GameSession choices. Voluntaryresignation cancreateWIN despite no winning boardterminal.',scope='Fixed implemented policy omitsresignation; a future utilityzero certificate must bind that policy restriction, notclaim arbitrarySessionDRAW.')
   s.submit(action)
  assert hashlib.sha256(repr(s.state).encode()).hexdigest()==g['final_state_sha'];all_terminal[s.result.status.value]+=1
  if entry is not None:
   assert g['outcome']=='DRAW' and g['finite_event_score']==0
   hits.append(dict(case_slot=g['slot'],first_eligible_ply=entry,actual_terminal_ply=len(record.actions),actual_terminal_status=s.result.status.value,remaining_actual_moves=len(trace)-entry,remaining_actual_proof_visits=sum(x['proof_nodes']for x in trace[entry:]),remaining_recorded_decision_seconds=sum(x['seconds']for x in trace[entry:])))
 assert counterexample is not None
 result=dict(status='PROPOSAL_CHECKED_NOT_ADOPTED',parent_cases=256,eligible_zero_suffix_cases=len(hits),all_eligible_suffixes_actual_DRAW=True,observed_suffix_moves=sum(x['remaining_actual_moves']for x in hits),observed_suffix_proof_visits=sum(x['remaining_actual_proof_visits']for x in hits),observed_suffix_decision_seconds=sum(x['remaining_recorded_decision_seconds']for x in hits),hits=hits,actual_terminal_statuses=dict(all_terminal),proof_argument='For exact compiled no-drop/no-promotion/remove-only/draw-history/declarationfree rules, complete closed KK/KKN admissible board census contains no WIN terminals. Any no-resign board-action continuation stays in closure. Finite maxply96 forces eventual ruleterminal; hence fixed nonresigning policy fullgame utilityW-L is identically0 on this closure. Thisis stronger than lackofaforcedWIN and doesnotextend to arbitraryGameSessionchoices.',counterexample=counterexample,proposed_interface='SeparateCERTIFIED_POLICY_RETURN_ZERO with census/rule/history/policy binding; doNOT mutate SessionStatus, report actualDRAW withoutplay, or treat budgetUNKNOWNasDRAW. Actualterminal evaluation remains baseline. Not implemented or used in any67training/reward.',scope='One genuine legalresignationbranch shows overbroad formulation false. Corpus agreement256sharedcases is not a generic mathematicalproof or newindependentvalidation. Observed suffixwork is not prospective guaranteed savings. No humanfit/labelrewrite/newNativeorprover.')
 with(OUT/'result.json').open('x',encoding='utf-8')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k not in ('hits','counterexample')}))
if __name__=='__main__':run()
