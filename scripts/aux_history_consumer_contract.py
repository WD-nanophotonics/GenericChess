"""Consume the fixed historic alias in real learner/proof-bank interfaces.

No rule sampler, new solver, Player, training or replacement certificate framework.
"""
from pathlib import Path
from copy import deepcopy
from dataclasses import replace
from time import perf_counter
from unittest.mock import patch
import json,gzip,hashlib
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.transition import legal_successors
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model
from scripts.generic_session_certificate_json import decode_session_certificate
from scripts.generic_session_win_proof import verify_session_certificate,SessionProofResult
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from scripts.leaper_clock_rebinding import verify_history_draw_safety
from scripts.leaper_truth_compatibility import bind_context,compare_contexts,action_coverage
from scripts.research_record import record_value

def sha(b):return hashlib.sha256(b).hexdigest()
def run(folder,output):
    folder=Path(folder);proto_raw=(folder/"protocol.json").read_bytes();proto=json.loads(proto_raw)
    if Path(output).exists():raise RuntimeError("existing completed consumer; no automatic rerun")
    start=perf_counter()
    for x in proto["source_bindings"]:
        b=(folder/Path(x["path"]).name).read_bytes();assert sha(b)==x["sha256"] and len(b)==x["bytes"]
    f=json.loads((folder/"repeat4-counterexample.json").read_bytes())
    domain=json.loads(gzip.decompress((folder/"mask5-domain.json.gz").read_bytes()))
    c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(f["rule"]))
    rows=sorted(f["rows"],key=lambda r:r["value"]);draw,win=rows
    submits=0
    original=GameSession.submit
    def counted(s,a):
        nonlocal submits
        submits+=1
        return original(s,a)
    with patch.object(GameSession,"submit",counted):
        sessions=[GameSession.replay(c,deserialize_game_record(json.dumps(r["record"])))for r in rows]
        a,b=sessions
        assert a.state.position==b.state.position and a.state.ply_count==b.state.ply_count==11
        assert a.legal_actions()==b.legal_actions()
        assert not a.state.terminal_status.is_terminal and not b.state.terminal_status.is_terminal
        key=repetition_identity_key(a.state.position,c)
        assert dict(a.state.repetition_counts)[key]==dict(b.state.repetition_counts)[key]==1
        assert a.state.repetition_counts!=b.state.repetition_counts
        envs=[FixedScaleSessionEnv(s,unit_type="A")for s in sessions]
        model=Model([1.,0.],fixed=0,scale=10.)
        feats=[e.features()for e in envs]
        assert envs[0].names==envs[1].names==(("board","A"),("hand","A"))
        assert feats[0]==feats[1]==(1,0)
        assert [e.terminal()for e in envs]==[None,None]
        assert all(model.gradient(phi)==(0.,0.)for phi in feats)
        decoded,cert=decode_session_certificate(c,win["win_certificate"],max_nodes=8192)
        assert decoded.state==b.state and cert.target==0
        actual_win=verify_session_certificate(b,cert,max_nodes=8192,seconds=5.)
        assert actual_win["verified"]
        actual_draw=verify_history_draw_safety(domain,f["rule"],draw["record"],draw["draw_safety"],seconds=5.)
        assert actual_draw["verified"] and actual_draw["value_for0"]==0
        source_cert_reject=verify_session_certificate(a,cert,max_nodes=8192,seconds=5.)
        assert not source_cert_reject["verified"]
        rebound=replace(cert,root_record=a.to_record(),root_state=a.state)
        rebound_reject=verify_session_certificate(a,rebound,max_nodes=8192,seconds=5.)
        assert not rebound_reject["verified"]
        imports=[]
        def source_import(session,**kw):
            imports.append(dict(record=record_value(session.to_record()),target=kw["target"]))
            if session.to_record()==b.to_record() and kw["target"]==0:
                return SessionProofResult("PROVEN_WIN",cert,"SAVED_CERTIFICATE_IMPORT_NO_SOLVER",0,0.,12)
            return SessionProofResult("UNKNOWN",None,"no_saved_certificate_for_exact_history",0,0.,0)
        bank=SessionLogicalProofBank(source_import,capacity=4)
        queries=[bank.query(s,target=0,max_nodes=4096,seconds=1.,max_depth=12,
                    verification_max_nodes=8192,verification_seconds=5.)for s in(b,b,a)]
        assert [(q.hit,q.stored,q.logical_result.status)for q in queries]==[(False,True,"PROVEN_WIN"),(True,False,"PROVEN_WIN"),(False,False,"UNKNOWN")]
        assert len(imports)==2 and queries[1].actual_proof_nodes==queries[1].actual_verification_nodes==0
        assert queries[0].key!=queries[2].key
        # The actual draw safety decision is an original legal-successor index.
        safety=draw["draw_safety"]
        sr=next(x for x in safety["vertices"]if x["index"]==safety["root"])
        assert sr["actor"]==1 and len(sr["selected_action_indices"])==1
        choices=list(legal_successors(a.state,c));safe=choices[sr["selected_action_indices"][0]][0]
        assert safe in a.legal_actions()
        # A full all-defense WIN certificate at actor1 covers every root action.
        root_actions=[choice.action for choice,node in cert.tree.edges]
        assert set(root_actions)==set(b.legal_actions()) and safe in root_actions
        # At WIN root all actor1 actions have seat0 value+1; at DRAW root the
        # safety action has value0. Same literal action can be optimal in both.
        from generic_chess.core.actions import action_to_dict
        safe_wire=action_to_dict(safe)
        contexts=[bind_context(f["rule"],r["record"],compiled=c)for r in rows]
        win_labels=[dict(action=action_to_dict(x),wdl_bounds=[1,1],value_seat=0)for x in root_actions]
        draw_labels=[dict(action=safe_wire,wdl_bounds=[0,0],value_seat=0)]
        coverage=[action_coverage(contexts[0],draw_labels,[0,0],value_seat=0),
                  action_coverage(contexts[1],win_labels,[1,1],value_seat=0)]
        assert all(next(x for x in cv["rows"]if x["action"]==safe_wire)["regret_bounds"]==[0,0]for cv in coverage)
        before=submits
    if perf_counter()-start>proto["budget"]["whole_consumer_seconds"]:raise RuntimeError("whole consumer cap exceeded; evidence saved separately, no refill")
    value=model.prediction(feats[0])
    out=dict(protocol_sha256=sha(proto_raw),source_bindings=proto["source_bindings"],
        root_summary=dict(ply=11,remaining_plies=53,actor=1,current_repetition_count=1,root_terminal_statuses=["ongoing","ongoing"],
            same_full_Position=True,same_legal_actions=True,full_repetition_maps_differ=True),
        source_values_for0=[0,1],actual_WIN_verification=record_value(actual_win),actual_DRAW_verification=actual_draw,
        learner=dict(channels=envs[0].names,features=feats,predictions=[value,value],gradients=[model.gradient(x)for x in feats],model_updates=0,
            equal_weight_truth_MSE=((value-0)**2+(value-1)**2)/2,unrestricted_common_prediction_minimum_MSE=.25),
        source_certificate_reject=record_value(source_cert_reject),root_rebound_certificate_reject=record_value(rebound_reject),
        proof_bank=dict(queries=[dict(hit=q.hit,stored=q.stored,status=q.logical_result.status,
            actual_proof_nodes=q.actual_proof_nodes,actual_verification_nodes=q.actual_verification_nodes,verification_scope=q.verification_scope)for q in queries],
            saved_certificate_import_callbacks=len(imports),new_proof_solver_calls=0),
        matched_root_policy=dict(common_certified_optimal_action=safe_wire,coverage=coverage,
            inference="Valuealias doesnotprove disjointoptimalrootactions;thisactualsafeactionhaszeroregretinboth completehistories,withoutmergingtheirvalues."),
        context_comparison=compare_contexts(contexts[0],contexts[1]),
        actual_GameSession_submit_calls=before,whole_wall_seconds=perf_counter()-start,
        new_Player_calls=0,new_solver_calls=0,new_games=0,new_training=0,
        limitations="Oldexposedproofpair,notnewheldoutorqualitytrial. ExistingcheckerCoreenumerationsandoldcertificateimportareverificationcost. No activelearner/cache defectfound. A sharedrootoptimalaction doesnotcertifyone universalhistoryblindstrategy.")
    Path(output).write_bytes((json.dumps(record_value(out),indent=2)+"\n").encode())
    return out
