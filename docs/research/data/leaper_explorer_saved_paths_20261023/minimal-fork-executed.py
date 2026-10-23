from pathlib import Path
import hashlib
from scripts.leaper_saved_child_bounds import current_truth,propagate
from scripts.leaper_saved_suffix_transfer import apply as suffix_apply
from scripts.leaper_observed_path_proofs import apply as observed_apply
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_cooperative_certificate import root_session
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from scripts.generic_session_win_proof import prove_session_win,verify_session_certificate
from scripts.generic_session_certificate_json import export_session_certificate
from scripts.leaper_microgames import role_stop_requested

p=Path('artifacts/saved-child-bounds-d19a')
t=current_truth('docs/research/data/leaper_explorer_truth_20261023','docs/research/data/leaper_explorer_followup_20261023')
local=load(p/'edges.json.gz');u,_=propagate(t,local);v=suffix_apply(u,load(p/'shortened-proofs.json.gz'));w=observed_apply(v,load(p/'observed-proofs.json.gz'))
root=next(r for r in w['roots']if r['id'].startswith('f5b740cd2f'))
assert root['ply']==0 and root['wdl_bounds']==[0,1] and root['wdl_fork']is None
nonwin=[a for a in root['action_bounds']if a['wdl_bounds']==[-1,0]];assert len(nonwin)==1
edge=next(e for q in local['rows']if q['id']==root['id']for e in q['children']if e['action']==nonwin[0]['action'])
child=next(r for r in w['roots']if r['id']==edge['child_id'])
assert child['wdl_bounds']==[0,1]and child['ply']==1
old=load('docs/research/data/leaper_explorer_truth_20261023/critical.json')
assert child['id']!=old['child_id'] and child['fingerprint']!=old['child_record']['ruleset_fingerprint']
spec=dict(question='Can a shallow forced WIN for the next mover certify that the original initial alternative loses, while another first action is exactDRAW, thereby proving an initial fork?',
    input_digest=digest(w),root_id=root['id'],child_id=child['id'],fingerprint=child['fingerprint'],action=nonwin[0]['action'],
    target=1,caps=dict(max_depth=3,max_nodes=2048,seconds=30),
    changed_premise='Unique remaining knownnonwin alternative at a newly nonloss initial. Different saved full history and rule from closed50kquery. Existing optional Session WIN entry reused, not new solver development.',
    alternative='Wait for actual E0/target freeze; retain initialforkUNKNOWN. This single minimal diagnostic closes on failure, no depth/node/time extension or batch.',
    source_sha='c7e7b84101ee286a4d3bc98a19a33463afd2809d',proof_source_sha256=hashlib.sha256(Path('scripts/generic_session_win_proof.py').read_bytes()).hexdigest(),
    stop='One query at saved ply1 history, no newrule/layout/game/TRAINroot; UNKNOWN remains UNKNOWN. No oldcaprefill.')
save(p/'minimal-fork-spec.json',spec)
c=compile_rule(ruleset_from_dict(w['rules'][child['fingerprint']]))
_,s=root_session(w,child['id'],c)
assert s.state.position.side_to_move==spec['target']
proof=prove_session_win(s,target=spec['target'],max_nodes=2048,seconds=30,max_depth=3,cancel=role_stop_requested)
result=dict(spec=spec,status=proof.status,reason=proof.reason,nodes=proof.nodes,seconds=proof.seconds,completed_depth=proof.completed_depth,certificate=None,verification=None,
    initial_fork=True if proof.certificate is not None else None,scope='A positive would decide this single initial fork through a literal all-defense certificate. A failed shallow query is not DRAW, no-WIN or no-fork truth. No further query or cap refill.')
if proof.certificate is not None:
    result['certificate']=export_session_certificate(proof.certificate,max_nodes=4096)
    result['verification']=verify_session_certificate(s,proof.certificate,max_nodes=4096,seconds=30,cancel=role_stop_requested)
    assert result['verification']['verified']
save(p/'minimal-fork-result.json',result);print(result)
