from pathlib import Path
from collections import Counter,defaultdict
import json,time,hashlib
from generic_chess.rules.serialization import deserialize_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import serialize_game_record
from generic_chess.core.actions import action_to_dict
from scripts.generic_proof_rnb_bridge import actor_state,uci
from results.dev_aux.task2068.teacher import CanonicalTeacher
from results.dev_aux.task2100.campaign import sha_state
OUT=Path('results/dev_aux/task2144')
def run():
 start=time.perf_counter();root=Path('results/dev_aux/task2139');p=json.loads((root/'plan.json').read_text(encoding='utf-8'));inputs=json.loads((root/'inputs.json').read_text(encoding='utf-8'))['roots'];games=[json.loads(x)for x in(root/'games.jsonl').read_text(encoding='utf-8').splitlines()];by=defaultdict(list)
 for r in map(json.loads,(root/'decisions.jsonl').read_text(encoding='utf-8').splitlines()):by[r['physical_id']].append(r)
 teacher=CanonicalTeacher('results/dev_aux/task2093','results/dev_aux/task2094','results/dev_aux/task2095');counts=Counter();analyses={};trace={};first=[]
 for g in games:
  if g['reused_from']is not None:continue
  c=compile_ruleset_for_execution(deserialize_ruleset(Path(inputs[g['family']]['rules']).read_text(encoding='utf-8')));s=GameSession(c);dd=by[g['physical_id']];assert len(dd)==g['moves'];steps=[]
  for ply,d in enumerate(dd):
   assert d['physical_id']==g['physical_id']and d['logical_slot']==g['logical_slot']and d['ply']==ply
   assert d['root_record']==json.loads(serialize_game_record(s.to_record()))and d['ruleset_fingerprint']==c.ruleset_fingerprint and d['root_state_sha']==sha_state(s.state)
   assert d['side']==s.state.position.side_to_move and d['is_candidate']==(d['side']==g['candidate_side'])and d['choice']is not None
   assert all(d['requested_limits'][k]==p[k]for k in d['requested_limits'])
   assert d['actual_phase_limits']['total_seconds']==p['step_seconds']and d['actual_phase_limits']['fallback_admission_seconds']>=0
   nr=d['normal_receipt']
   if nr is not None:
    assert nr['nodes']==d['search_nodes']and nr['seconds']==d['normal_seconds']
    assert nr['action']==d['choice']['action'];counts['normal_depth_'+str(nr['completed_depth'])]+=1
   counts['source_'+d['source']]+=1;counts['exit_'+d['exit_cause']]+=1
   a=next(a for a in s.legal_actions()if action_to_dict(a)==d['choice']['action']);before=teacher.rows[teacher.key(actor_state(s.state))];v={'WIN':1,'DRAW':0,'LOSS':-1}[before['label']];v=v if d['side']==g['candidate_side']else-v
   s.submit(a);after=teacher.rows[teacher.key(actor_state(s.state))];v2={'WIN':1,'DRAW':0,'LOSS':-1}[after['label']];v2=v2 if s.state.position.side_to_move==g['candidate_side']else-v2
   steps.append(dict(ply=ply,side=d['side'],source=d['source'],action=uci(a),before_position_candidate_value=v,after_position_candidate_value=v2,normal_depth=None if nr is None else nr['completed_depth'],root_state_sha=d['root_state_sha']))
  trace[g['physical_id']]=steps
  analyses[g['physical_id']]=dict(family=g['family'],role=g['candidate_side'],ratio=g['ratio'],phase=g['phase'],outcome=g['outcome'],candidate_positional_declines=sum(x['after_position_candidate_value']<x['before_position_candidate_value']and x['side']==g['candidate_side']for x in steps),opponent_positional_gifts=sum(x['after_position_candidate_value']>x['before_position_candidate_value']and x['side']!=g['candidate_side']for x in steps),first_initial_position_value=steps[0]['before_position_candidate_value'])
  counts['decisions']+=len(dd)
 assert counts['decisions']==6045
 for family in range(32,48):
  for role in(0,1):
   baseline=next(g for g in games if g['family']==family and g['candidate_side']==role and g['ratio']==1.)
   for price in(.5,2.):
    learned=next(g for g in games if g['family']==family and g['candidate_side']==role and g['ratio']==price)
    if learned['score']==baseline['score']:continue
    a,b=trace[baseline['physical_id']],trace[learned['physical_id']];different=next((i for i in range(min(len(a),len(b)))if a[i]['action']!=b[i]['action']),None)
    assert different is not None and a[different]['root_state_sha']==b[different]['root_state_sha']
    first.append(dict(family=family,role=role,price=price,baseline=baseline['score'],learned=learned['score'],first_different_ply=different,baseline_decision=a[different],learned_decision=b[different],baseline_physical=baseline['physical_id'],learned_physical=learned['physical_id']))
 lock=json.loads((root/'selector-lock.json').read_text(encoding='utf-8'));means=lock['selected'][0]['TRAIN_means'];mx=max(means.values());maxima=[r for r,v in means.items()if v==mx]
 out=dict(status='PASS_EVERY_RETURNED_DECISION_PRECOMMIT_ROOT_AND_NORMAL_RECEIPT',counts=dict(counts),outcome_changed_DEV_pairs=first,posthoc_TRAIN_global_best=maxima,TRAIN_global_best_mean=mx,posthoc_optimizer_diagnosis='Strict adjacent updates halt on equal neighboring fitness, though nonadjacent ratio1 has higher TRAIN mean. This is an optimizer limitation. Globalargmax is NOT retroactively selected/validated; no reusing DEV for selection.',scope='Position label changes on played histories are posthoc diagnostics ONLY; never claim arbitraryhistoryexactWDL or use asreward. Allactualoutcomes audited separately. No newquery/game/fit.',original_completion_scope_erratum='Inherited study string INPUT_ONLY described previous planning phase, notactualrunstatus. started.json and COMPLETE544/496 counters establish actualexecution; rawcompletion unaltered.',seconds=time.perf_counter()-start)
 (OUT/'result.json').write_text(json.dumps(out,indent=2),encoding='utf-8');(OUT/'physical-attribution.json').write_text(json.dumps(analyses,indent=2),encoding='utf-8');print(json.dumps(out),flush=True)
if __name__=='__main__':run()
