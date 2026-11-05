"""Saved runner-up allocation acceptance;no Player/producer/proof search."""
from pathlib import Path
from collections import Counter
import json,hashlib
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.research_record import record_value,write_record
from scripts.verify_leaper_pvs_quality_pilot import action

def verify(base,out):
 b=Path(base);f=json.loads((b/'frozen.json').read_text());assert hashlib.sha256((b/'inputs.json').read_bytes()).hexdigest()==f['input_sha256'];rows=json.loads((b/'inputs.json').read_text())['rows'];rs=[json.loads(p.read_text()) for p in sorted(b.glob('return-*.json'))];assert len(rs)==32 and {r['slot'] for r in rs}==set(range(32))
 pairs=[];pvplies=0;diagnosis=Counter();case=[]
 for ri,row in enumerate(rows):
  rules=ruleset_from_dict(row['RuleSet']);assert compute_fingerprint(rules)==row['fingerprint'];c=compile_legacy_ruleset_for_semantic_execution(rules);s=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
  legal=[record_value(a) for a in s.legal_actions()];off,on=[next(r for r in rs if r['root']==ri and r['on']==v) for v in (False,True)]
  for r in (off,on):
   d=r['decision'];assert r['record_before']==record_value(s.to_record()) and r['wall_seconds']<=1.1 and r['timing_eligible'];assert d['runtime_depth_balanced'] and not d['native_legality_fallbacks'] and not d['native_legality_operational_failures'];action(d['action'],s)
   pv=GameSession.replay(c,s.to_record())
   for raw in d['principal_variation']:pv.submit(action(raw,pv));pvplies+=1
   assert d['runner_up_interventions']<=1
   if not r['on']:assert not d['runner_up_trace'] and d['runner_up_interventions']==0
   for e in d['runner_up_trace']:
    seen=[]
    for x in e['rows']:
     assert x['action'] in legal and x['action'] not in seen;seen.append(x['action'])
     expected='UPPER' if x['score']<=x['alpha'] else 'LOWER' if x['score']>=x['beta'] else 'EXACT'
     assert x['bound']==expected and x['child_depth']==e['depth']-1
    if e['completed']:assert len(seen)==len(legal)
  d=on['decision'];events=[e for e in d['runner_up_trace'] if e['intervention']];assert len(events)==d['runner_up_interventions']==1
  grant=events[0];assert grant['first_child_window']==[-10**12,10**12]
  assert grant['rows'] and grant['rows'][0]['action']==grant['planned_action']
  seed=next(e for e in d['runner_up_trace'] if e['depth']==grant['seed_depth']);assert seed['completed'] and seed['ordinary_phase'] and seed['depth']>=2 and not seed['intervention']
  alternatives=[x for x in seed['rows'] if x['action']!=seed['best_action']];nominee=max(alternatives,key=lambda x:x['score']);assert nominee['action']==grant['planned_action']
  initial=next(x for x in seed['rows'] if x['action']==seed['best_action']);diagnosis['seed_alternative_bound_'+nominee['bound']]+=1;diagnosis['seed_reported_tie' if nominee['score']==initial['score'] else 'seed_reported_gap']+=1
  # Compare follow-up returned bounds at the SAME actual root depth,not previous scores.
  runner=grant['rows'][0];inc=next((x for x in grant['rows'] if x['action']==seed['best_action']),None)
  if inc and inc['bound'] in ('EXACT','LOWER') and inc['score']>runner['score']:diagnosis['incumbent_finitely_dominates_followup']+=1
  elif inc and inc['bound'] in ('EXACT','UPPER') and runner['score']>inc['score']:diagnosis['followup_finitely_dominates_incumbent']+=1
  else:diagnosis['followup_rank_unknown_or_tied']+=1
  same=(off['decision']['choice_kind'],off['decision']['action'],off['decision']['declaration'])==(d['choice_kind'],d['action'],d['declaration']);pairs.append(dict(root=ri,family=row['family'],layout=row['layout'],same_complete_choice=same,actual=True,Q4=off['decision']['result_ordinary_qdepth']==d['result_ordinary_qdepth']==4,relative_action_value_interval=[0,0] if same else [-2,2]))
  case.append(dict(root=ri,OFF_depth=off['decision']['completed_depth'],ON_depth=d['completed_depth'],OFF_score=off['decision']['score'],ON_score=d['score'],same_choice=same))
 stable=[family for family in range(8) if sum(p['family']==family and not p['same_complete_choice'] and p['actual'] and p['Q4'] for p in pairs)==2]
 summary=json.loads((b/'summary.json').read_text());assert summary['stable_two_layout_families']==stable
 result=dict(status='PASS_SAVED_FINITE_ACCEPTANCE',returns=32,pairs=pairs,cases=case,Core_PV_plies=pvplies,mechanism_diagnosis=dict(diagnosis),stable_two_layout_families=stable,paired_panel_mean_action_difference_bounds=[sum(p['relative_action_value_interval'][0] for p in pairs)/16,sum(p['relative_action_value_interval'][1] for p in pairs)/16],newPlayer=0,newPN=0,limits='sharedCoreliteralreplay;reportedboundsnottrueWDL;panelintervalnotpopulationCI;norepeatedsameroottimingorperformancecausalityclaim')
 write_record(out,result);return result
if __name__=='__main__':
 import sys;print(json.dumps(verify(sys.argv[1],sys.argv[2])))
