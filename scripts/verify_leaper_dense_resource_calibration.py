"""Verify saved dense resource outcomes without Player or solver execution."""
from __future__ import annotations
import argparse,json,hashlib
from collections import Counter,defaultdict
from pathlib import Path
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value,write_record
from scripts.verify_leaper_pvs_quality_pilot import action,full_digest,fixed_bounds

def load(p):return json.loads(Path(p).read_text(encoding='utf8'))
def score(g):
 if g['status']!='TERMINAL':return None
 t=g['Core_terminal'];w=t['winner']
 if w is None:
  assert t['status'] in ('max_ply','repetition','stalemate');return .5
 assert w in (0,1);return float(w==g['long_seat'])
def summarize(games):
 assert len(games)==12 and {g['game_id'] for g in games}==set(range(12))
 rows=[]
 for f in range(6):
  gs=[g for g in games if g['family']==f];assert len(gs)==2 and {g['long_seat'] for g in gs}=={0,1}
  actual=[score(g) for g in gs];eligible=all(g['status']=='TERMINAL' and g['timing_eligible'] for g in gs)
  values=actual if eligible else [None,None]
  rows.append(dict(family=f,actual=fixed_bounds(actual,2),timing_pair=fixed_bounds(values,2),long_net_actual=None if None in actual else 2*sum(actual)-2,eligible_pair=eligible,Core_reasons=dict(Counter(g.get('Core_terminal',{}).get('status',g['status']) for g in gs))))
 actual=fixed_bounds([score(g) for g in games],12)
 valid=[score(g) if g['status']=='TERMINAL' and g['timing_eligible'] else None for g in games]
 all_valid=all(r['eligible_pair'] for r in rows)
 positive=sum(r['eligible_pair'] and r['long_net_actual']>0 for r in rows)
 return dict(families=rows,actual=actual,timing_games=fixed_bounds(valid,12),positive_eligible_families=positive,all12eligible=all_valid,screen_pass=all_valid and positive>=3 and sum(valid)>6,protocol='Originalall12gate remainsfailed duepreservedslot0;actualpoints not timingqualification;fixed12denominator.')

def verify(prepared,original,continuation,out):
 roots={r['id']:r for r in load(prepared/'inputs.json')['rows']}
 games=load(continuation/'games.json');observed=set();pvs=0;transitions=0;orphans=[];details=[]
 original_ids={p.stem for p in (original/'returns').glob('*.json')}
 continuation_ids={p.stem for p in (continuation/'returns').glob('*.json')}
 assert not original_ids&continuation_ids
 for g in games:
  root=roots[g['case_id']];assert root['family']==g['family'] and root['fingerprint']==g['fingerprint'] and root['record']==g['initial_record']
  rules=ruleset_from_dict(root['RuleSet']);assert compute_fingerprint(rules)==root['fingerprint']
  c=compile_legacy_ruleset_for_semantic_execution(rules);s=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
  counts=Counter();dists=defaultdict(Counter)
  qs=list(g['queries'])
  # Third actual return exists despite losing the bookkeeping tail. Validate it
  # as a raw orphan against the exact preceding record; do not promote game0.
  if g['game_id']==0:
   assert g['status']=='FAILED' and len(qs)==2
   orphan=load(original/'returns/g0002.json');qs.append(orphan);orphans.append('g0002')
  for q in qs:
   qid=q['query_id'];assert qid not in observed;observed.add(qid)
   folder=original if qid in original_ids else continuation;raw=load(folder/'returns'/f'{qid}.json')
   assert all(q[k]==v for k,v in raw.items())
   assert full_digest(s.to_record())==q['record_before_sha256']
   d=q['decision'];chosen=action(d['action'],s);before=s.to_record();pv=GameSession.replay(c,before)
   for a in d['principal_variation']:pv.submit(action(a,pv));pvs+=1
   assert d['runtime_depth_balanced'] and q['provider_present']
   assert d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
   assert q['provider_delta']['availability'].get('declines',0)==0
   assert 0<q['actual_limits']['max_time_seconds']<=q['requested_service_seconds']
   assert q['actual_limits']['max_nodes']==500000 and q['actual_limits']['max_depth']==64
   assert q['actual_limits']['quiescence_max_depth']==4 and q['actual_limits']['quiescence_hard_max_depth']==8
   assert q['timing_eligible']==(q['service_wall_seconds']<=q['requested_service_seconds']*1.1)
   if 'seat' in q:assert q['seat']==s.state.position.side_to_move
   seat=s.state.position.side_to_move;policy='long' if seat==g['long_seat'] else 'short'
   assert q['requested_service_seconds']==(2 if policy=='long' else .5)
   counts[d['termination_reason']]+=1;dists[policy].update(calls=1,wall=q['service_wall_seconds'],cpu=q['cpu_seconds'],nodes=d['nodes'],qnodes=d['qnodes'],packing=q['construction_packing_seconds'],overtime=not q['timing_eligible'],depth64=d['completed_depth']==64)
   s.submit(chosen);transitions+=1
   if 'record_after_sha256' in q:assert full_digest(s.to_record())==q['record_after_sha256']
  if g['status']=='TERMINAL':
   assert s.state.terminal_status.is_terminal
   assert record_value(s.to_record())==g['final_record'] and record_value(s.state.terminal_status)==g['Core_terminal']
   assert record_value(s.result)==g['Session_result']
   assert g['timing_eligible']==all(q['timing_eligible'] for q in qs)
  details.append(dict(game_id=g['game_id'],family=g['family'],status=g['status'],queries=len(qs),by_policy={k:dict(v) for k,v in dists.items()},reasons=dict(counts),last_validated_record=record_value(s.to_record())))
 assert observed==original_ids|continuation_ids
 r=dict(summary=summarize(games),details=details,original_returns=len(original_ids),continuation_returns=len(continuation_ids),replayed_transitions=transitions,literal_PV_plies=pvs,orphan_raw_returns_validated_not_promoted=orphans,new_Player=0,new_solver=0,limitations='Saved actualCore/action/PV replay only. No counterfactual actionWDL,nearstrength or algorithmbenefit. Onefailedpreservedslot0 andprotocolamendment preventoriginalPASS evenifotherfamiliespositive;all6exposed,neverholdout.')
 write_record(out,r);print(json.dumps({k:r[k] for k in ['original_returns','continuation_returns','replayed_transitions','literal_PV_plies']}));print(json.dumps(r['summary']))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--original',type=Path,required=True);p.add_argument('--continuation',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.prepared,a.original,a.continuation,a.output)
