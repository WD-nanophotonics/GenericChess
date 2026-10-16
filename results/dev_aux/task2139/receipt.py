"""Public complete decision journal, including unsuccessful choices, before commit."""
from dataclasses import fields
import json
from generic_chess.core.actions import action_to_dict
from generic_chess.session.serialization import serialize_game_record
from results.dev_aux.task2100.campaign import sha_state

def choice_value(choice):
 if choice is None:return None
 return {f.name:(action_to_dict(v) if f.name=='action' and v is not None else v) for f in fields(choice) for v in [getattr(choice,f.name)]}

def decision_receipt(session,d,*,physical_id,logical_slot,ply,candidate,limits):
 normal=None
 if d.normal_receipt is not None:
  normal={f.name:(action_to_dict(v) if f.name=='action' and v is not None else v) for f in fields(d.normal_receipt) for v in [getattr(d.normal_receipt,f.name)]}
 return dict(physical_id=physical_id,logical_slot=logical_slot,ply=ply,side=session.state.position.side_to_move,is_candidate=session.state.position.side_to_move==candidate,ruleset_fingerprint=session.compiled.ruleset_fingerprint,root_record=json.loads(serialize_game_record(session.to_record())),root_state_sha=sha_state(session.state),root_result=dict(status=session.result.status.value,winner=session.result.winner),requested_limits={k:limits[k] for k in ('normal_nodes','normal_depth','normal_seconds','proof_nodes','proof_seconds','proof_depth','verification_nodes','verification_seconds','step_seconds','H')},actual_phase_limits=dict(d.phase_limits),choice=choice_value(d.choice),normal_receipt=normal,**{k:getattr(d,k) for k in ('source','proof_reason','logical_status','exit_cause','seconds','admission_seconds','proof_nodes','verification_nodes','fill_verification_nodes','search_nodes','proof_seconds','verification_seconds','fill_verification_seconds','normal_seconds','proof_rank')})
