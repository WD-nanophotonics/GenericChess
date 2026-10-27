"""Diagnose one fixed action-representation mismatch within its original cap."""
from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from hashlib import sha256
from collections import Counter
from datetime import datetime
import json,sys
from time import perf_counter,process_time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.actions import BoardMove,SemanticBoardMove
from generic_chess.core.search_runtime import _plain_leaper_hash_patterns
from generic_chess.rules.compiler import compile_ruleset_for_execution,compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record,serialize_game_record
from generic_chess.learning.incremental import FixedScaleSessionEnv
from scripts.replay_leaper_first_history import physical,digest

def main():
 out=ROOT/'docs/research/data/aux_one_full_history_20261027'
 plan=json.loads((out/'plan.json').read_bytes())
 raw=(out/'input.json').read_bytes();x=json.loads(raw)
 assert sha256(raw).hexdigest()=='62541ed42c093b8ce420131f364ef40c863a80cd8b3058e6da5e85e66b24a2aa'
 first=(out/'result.json').read_bytes()
 amendment=(ROOT/'.local_agent/one-history-942bc7a8-diagnostic-plan.json').read_bytes()
 assert json.loads(amendment)['original_result_sha256']==sha256(first).hexdigest()
 (out/'diagnostic-plan.json').write_bytes(amendment)
 (out/'diagnostic-driver.py').write_bytes(Path(__file__).read_bytes())
 began,cpu=perf_counter(),process_time();attempts=1;rows=[];failure=None;summary={}
 def guard():
  for n in ['rollout','advisor','slack']:
   f=json.loads((ROOT/'.local_agent'/(n+'.json')).read_bytes())
   if f.get('user_paused') or f.get('stopped'):raise RuntimeError('STOPPED_USER')
  if (datetime.now().astimezone()-datetime.fromisoformat(plan['origin'])).total_seconds()>=plan['whole_minutes']*60:
   raise RuntimeError('ORIGINAL_WHOLE_CAP')
 try:
  guard();rule=ruleset_from_dict(x['rule'])
  old=compile_ruleset_for_execution(rule);semantic=compile_legacy_ruleset_for_semantic_execution(rule)
  assert _plain_leaper_hash_patterns(semantic)
  # Unique visible endpoints within each actor/mode/owner/source certify only
  # that this original plain-atom rule does not have coordinate aliases.
  geometry_checks=0
  for tid in old.types_by_id:
   for mode in ['target_empty','target_enemy']:
    for owner in ['0','1']:
     for source in range(old.board_size**2):
      destinations=[]
      for pattern in semantic.ir.patterns:
       if tid not in pattern.type_ids or pattern.target.kind!=mode:continue
       for gid in pattern.geometry_ids:
        g=semantic.ir.geometry[gid]
        assert g.kind=='leap' and g.atom_source[0]==tid
        path=g.paths[owner][source]
        if path:destinations.append(path[0])
      assert len(destinations)==len(set(destinations))
      geometry_checks+=1
  full=deserialize_game_record(json.dumps(x['final_record']))
  assert all(type(a) is SemanticBoardMove and a.promotion_target_id is None for a in full.actions)
  prefix=replace(full,actions=full.actions[:-1])
  projected=replace(full,actions=tuple(BoardMove(a.from_square,a.to_square,a.promotion_target_id) for a in full.actions))
  (out/'projected-legacy-record.json').write_text(serialize_game_record(projected),encoding='utf-8')
  states={}
  for name,compiled,record in [('semantic_full',semantic,full),('semantic_prefix',semantic,prefix),('projected_legacy_full',old,projected)]:
   guard()
   assert attempts<4
   attempts+=1;t,c=perf_counter(),process_time();s=GameSession.replay(compiled,record);guard()
   counts=dict(s.state.repetition_counts)
   row=dict(case=name,actions=len(record.actions),Core_status=s.state.terminal_status.status.value,Core_winner=s.state.terminal_status.winner,Session_status=s.result.status.value,learner_terminal=FixedScaleSessionEnv(s,unit_type='A').terminal(),record_matches_its_own_input=s.to_record()==record,ply=s.state.ply_count,history_entries=len(s.state.history),repetition_entries=len(counts),maximum_repetition_count=max(counts.values()),current_repetition_count=counts[s.state.history[-1].position_key],wall=perf_counter()-t,cpu=process_time()-c)
   rows.append(row);states[name]=s
  a,b=states['projected_legacy_full'],states['semantic_full']
  assert len(a._search_witnesses)==len(b._search_witnesses)==129
  equal_positions=sum(p==q for p,q in zip(a._search_witnesses,b._search_witnesses))
  assert equal_positions==129
  mapping={};inverse={}
  for h,k in zip(a.state.history,b.state.history):
   assert (h.actor,h.gave_check)==(k.actor,k.gave_check)
   assert h.position_key not in mapping or mapping[h.position_key]==k.position_key
   assert k.position_key not in inverse or inverse[k.position_key]==h.position_key
   mapping[h.position_key]=k.position_key;inverse[k.position_key]=h.position_key
  mapped={mapping[k]:v for k,v in a.state.repetition_counts}
  assert mapped==dict(b.state.repetition_counts)
  summary=dict(geometry_uniqueness_checks=geometry_checks,source_action_types=dict(Counter(type(a).__name__ for a in full.actions)),physical_final_equal=physical(a)==physical(b),all129_positions_equal=equal_positions,original_vs_projected_record_equal=full==projected,raw_repetition_maps_equal=a.state.repetition_counts==b.state.repetition_counts,observed_rekey_map_size=len(mapping),observed_rekeyed_counts_equal=True,namespace_map_scope='Only the129observed positions of this one trace, not a general key converter/TT quotient',position_witness_api='Core-owned GameSession._search_witnesses readonly verifier use; not new learning/runtime API')
  (out/'observed-key-map.json').write_text(json.dumps(mapping,sort_keys=True,indent=2)+'\n',encoding='utf-8')
 except Exception as e:failure=dict(type=type(e).__name__,message=str(e))
 result=dict(first_rawlegacy_attempt='FAILED/retained result.json; no original hypothesis pass',total_replay_attempts_including_failure=attempts,maximum_original_attempts=4,original_cap_reset=False,input_sha256=sha256(raw).hexdigest(),driver_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),wall=perf_counter()-began,cpu=process_time()-cpu,rows=rows,summary=summary,failure=failure)
 (out/'diagnostic.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
