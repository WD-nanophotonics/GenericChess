"""Verify physical/history and actual feature aliasing across new rule clocks."""
from pathlib import Path
from dataclasses import replace
import json
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.schema import ruleset_from_dict,ruleset_to_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.ai.evaluation.semantic import build_semantic_opportunity_profile
from generic_chess.ai.evaluation.semantic_attacks import SemanticAttackEvaluator
from scripts.price_regions import CONFIG
from scripts.research_record import write_record,record_value
base=Path('artifacts/price-regions-20261021');report=json.loads((base/'rule-clock-counterfactual.json').read_text());sources={k:json.loads((base/v).read_text()) for k,v in (('source3x3','goal-census.json'),('emptyrow3x4','empty-row-census.json'))};output=base/'rule-clock-feature-alias.json'
if output.exists():raise FileExistsError(output)
rows=[]
for w in report['worlds']:
 old=sources[w['label']];oldc=compile_ruleset_for_execution(ruleset_from_dict(old['rule']));newc=compile_ruleset_for_execution(ruleset_from_dict(w['rule']));expected=dict(old['rule']);expected['max_ply']=w['max_ply'];assert expected==w['rule']
 assert not oldc.automatic_adjudications and not newc.automatic_adjudications
 cfg=replace(CONFIG,dynamic_mobility_weight=2);evaluators=[]
 for c in (oldc,newc):
  profile,_=build_semantic_opportunity_profile(c,cfg);profile=replace(profile,board_value_by_type={'K':0,'H':1000,'B':1000},hand_value_by_base_type={'K':0,'H':0,'B':0},promotion_gain_by_type={'K':0,'H':0,'B':0});evaluators.append(SemanticAttackEvaluator(c,profile,cfg,backend='core'))
 for x in w['roots']:
  before=GameSession.replay(oldc,deserialize_game_record(json.dumps(old['roots'][x['index']]['record'])));after=GameSession.replay(newc,deserialize_game_record(json.dumps(x['record'])))
  assert replace(before.state.position,ruleset_fingerprint=newc.ruleset_fingerprint)==after.state.position
  keys={a.position_key:b.position_key for a,b in zip(before.state.history,after.state.history)}
  assert len(set(keys.values()))==len(keys)
  assert [(a.actor,a.action_signature,a.gave_check) for a in before.state.history]==[(a.actor,a.action_signature,a.gave_check) for a in after.state.history]
  assert sorted((keys[k],n) for k,n in before.state.repetition_counts)==sorted(after.state.repetition_counts)
  attacks=[ev._attack_maps(s.state) for ev,s in zip(evaluators,(before,after))];assert attacks[0]==attacks[1]
  scores=[ev.evaluate(s.state) for ev,s in zip(evaluators,(before,after))];assert scores[0]==scores[1]
  rows.append(dict(world=w['label'],max_ply=w['max_ply'],index=x['index'],same_physical_state_and_events=True,
   same_attack_maps=True,same_actual_material_plus_coverage_score=scores[0],goal_values_changed=x.get('goal_values_changed',False)))
write_record(output,dict(scope='New actual-rule max_ply5/7/8 vs6 only, no automatic PENDING in these scoped worlds; no claim a bare remaining-ply count captures all generic adjudication.',rows=rows))
print('validated',len(rows),'goal-changing',sum(x['goal_values_changed'] for x in rows))
