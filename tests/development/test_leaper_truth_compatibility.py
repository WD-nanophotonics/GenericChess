"""Semantic controls for source-bound truth reuse; no search is performed."""
from copy import deepcopy
from dataclasses import replace
import gzip
import json
from pathlib import Path
import pytest
from scripts.leaper_truth_compatibility import (
    bind_context, compare_contexts, action_coverage, qualify, digest, Context,
)

DATA=Path("docs/research/data/leaper_h6_initial_truth_20261023")

@pytest.fixture(scope="module")
def sample():
    source=json.loads(gzip.decompress((DATA/"inputs.json.gz").read_bytes()))
    family=next(f for f in source["families"] if f.get("rule") is not None)
    row=next(r for r in source["rows"] if r["family"]==family["family"])
    return family,row,bind_context(family["rule"],row["full_record"])


def test_exact_full_context_matches(sample):
    f,r,c=sample
    actual=bind_context(f["rule"],r["full_record"],compiled=c.session.compiled)
    assert compare_contexts(c,actual)["status"]=="COMPATIBLE"
    assert c.identity["state_sha256"]==r["state_sha256"]
    assert c.identity["ply"]==0 and c.identity["max_ply"]==6


def test_metadata_does_not_invent_semantic_difference(sample):
    f,r,c=sample
    rule=deepcopy(f["rule"]);rule["metadata"]={"description":"different prose"}
    actual=bind_context(rule,r["full_record"],compiled=c.session.compiled)
    assert compare_contexts(c,actual)["status"]=="COMPATIBLE"


def test_changed_clock_cannot_take_h6_truth(sample):
    f,r,c=sample
    rule=deepcopy(f["rule"]);rule["max_ply"]=128
    from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
    record=deepcopy(r["full_record"]);record["ruleset_fingerprint"]=compute_fingerprint(ruleset_from_dict(rule))
    actual=bind_context(rule,record)
    out=qualify(actual,c,[],[0,0])
    assert out["compatibility"]["status"]=="INCOMPATIBLE"
    assert out["coverage"] is None and out["quality"]=="UNKNOWN_CONTEXT_MISMATCH"


def test_wrong_compiled_scope_is_rejected(sample):
    f,r,c=sample
    rule=deepcopy(f["rule"]);rule["repetition_limit"]=4
    with pytest.raises(ValueError,match="compiled rules differ"):
        bind_context(rule,r["full_record"],compiled=c.session.compiled)


def test_resignation_is_not_same_outcome_even_with_same_gamestate(sample):
    f,r,c=sample
    record=deepcopy(r["full_record"]);record["resigned_by"]=0
    actual=bind_context(f["rule"],record,compiled=c.session.compiled)
    assert c.identity["state_sha256"]==actual.identity["state_sha256"]
    assert compare_contexts(c,actual)["status"]=="INCOMPATIBLE"
    assert not actual.legal_actions


def test_missing_action_labels_are_unknown(sample):
    _,_,c=sample
    labels=[dict(action=c.legal_actions[0],wdl_bounds=[0,0])]
    out=action_coverage(c,labels,[0,0])
    assert out["labelled_actions"]==1
    assert out["unlabelled_actions"]==len(c.legal_actions)-1
    assert out["rows"][0]["classification"]=="OPTIMAL_SOURCE_CLAIM"
    assert all(x["classification"]=="UNKNOWN" for x in out["rows"][1:])
    assert action_coverage(c,labels)["source_root_bounds"] is None


def test_empty_coverage_does_not_become_draw(sample):
    _,_,c=sample
    out=action_coverage(c,[])
    assert out["frontier_bounds"]==[-1,1]
    assert out["source_root_bounds"] is None
    assert out["label_authority"]=="SOURCE_CLAIM_NOT_RESOLVED_HERE"


@pytest.mark.parametrize("bounds",[[True,True],[1,-1],[0.0,0.0],[0],[0,2]])
def test_malformed_bounds_rejected(sample,bounds):
    _,_,c=sample
    with pytest.raises(ValueError,match="WDL bounds"):
        action_coverage(c,[dict(action=c.legal_actions[0],wdl_bounds=bounds)])


def test_duplicate_or_foreign_action_rejected(sample):
    _,_,c=sample
    label=dict(action=c.legal_actions[0],wdl_bounds=[0,0])
    with pytest.raises(ValueError,match="duplicate"):
        action_coverage(c,[label,label])
    foreign=deepcopy(label);foreign["action"]["pattern_id"]="not-declared"
    with pytest.raises(ValueError,match="outside"):
        action_coverage(c,[foreign])


def test_root_action_contradiction_rejected(sample):
    _,_,c=sample
    with pytest.raises(ValueError,match="inconsistent"):
        action_coverage(c,[dict(action=a,wdl_bounds=[-1,-1]) for a in c.legal_actions],[0,0])


def test_value_seat_changes_optimization_direction(sample):
    _,_,c=sample
    # Physical turn0; values relative to seat1 must be minimized.
    labels=[dict(action=a,wdl_bounds=[i%2,i%2]) for i,a in enumerate(c.legal_actions)]
    out=action_coverage(c,labels,[0,0],value_seat=1)
    assert out["rows"][0]["classification"]=="OPTIMAL_SOURCE_CLAIM"
    assert out["rows"][1]["classification"]=="SUBOPTIMAL_SOURCE_CLAIM"


def test_unknown_selected_action_not_scored(sample):
    _,_,c=sample
    out=qualify(c,c)
    assert all(r["classification"]=="UNKNOWN" for r in out["coverage"]["rows"])


def abstract_context(side=0, count=3):
    # Algebra-only control: labels are synthetic intervals, never game truth.
    actions=tuple(dict(kind="abstract",index=i) for i in range(count))
    return Context(None,dict(side_to_move=side,terminal=dict(status="ongoing",winner=None)),actions)


def test_partial_win_certificate_can_reach_wdl_ceiling():
    c=abstract_context()
    out=action_coverage(c,[dict(action=c.legal_actions[0],wdl_bounds=[1,1])])
    assert out["rows"][0]["classification"]=="OPTIMAL_SOURCE_CLAIM"
    assert all(r["classification"]=="UNKNOWN" for r in out["rows"][1:])


def test_nonloss_bound_is_not_exact_draw_or_optimal():
    c=abstract_context()
    labels=[dict(action=c.legal_actions[0],wdl_bounds=[0,1])]
    out=action_coverage(c,labels)
    assert out["rows"][0]["classification"]=="UNKNOWN"
    assert out["rows"][0]["wdl_bounds"]==[0,1]
    out=action_coverage(c,labels,[0,0])
    assert out["rows"][0]["classification"]=="OPTIMAL_SOURCE_CLAIM"
    assert out["rows"][0]["feasible_wdl_bounds"]==[0,0]


def test_all_losing_root_does_not_make_selected_loss_wrong():
    c=abstract_context()
    out=action_coverage(c,[],[-1,-1])
    assert all(r["classification"]=="OPTIMAL_SOURCE_CLAIM" for r in out["rows"])
    assert out["labelled_actions"]==0 and out["unlabelled_actions"]==3


def test_interval_dominance_without_root_label():
    c=abstract_context()
    out=action_coverage(c,[dict(action=c.legal_actions[0],wdl_bounds=[0,1]),
                           dict(action=c.legal_actions[1],wdl_bounds=[-1,-1])])
    assert out["rows"][1]["classification"]=="SUBOPTIMAL_SOURCE_CLAIM"
    assert out["rows"][1]["regret_bounds"]==[1,2]


def test_only_action_is_optimal_without_claiming_its_value():
    c=abstract_context(count=1)
    row=action_coverage(c,[])["rows"][0]
    assert row["classification"]=="OPTIMAL_SOURCE_CLAIM"
    assert row["feasible_wdl_bounds"]==[-1,1]


def test_terminal_bounds_must_include_actual_result(sample):
    f,r,c=sample
    record=deepcopy(r["full_record"]);record["resigned_by"]=0
    terminal=bind_context(f["rule"],record,compiled=c.session.compiled)
    with pytest.raises(ValueError,match="actual Session terminal"):
        action_coverage(terminal,[],[0,0])
    assert action_coverage(terminal,[],[-1,-1])["actual_terminal_value"]==-1


def test_all_small_interval_frontiers_against_literal_assignments():
    from itertools import product
    intervals=[(-1,-1),(-1,0),(-1,1),(0,0),(0,1),(1,1)]
    roots=[None,*intervals]
    cases=0
    # Exhaustive small frontier check, independent of the formula under test.
    for n in range(1,5):
        c=abstract_context(count=n)
        for bounds in product(intervals,repeat=n):
            assignments=list(product(*(range(lo,hi+1) for lo,hi in bounds)))
            labels=[dict(action=a,wdl_bounds=b) for a,b in zip(c.legal_actions,bounds)]
            for root in roots:
                feasible=[v for v in assignments if root is None or root[0]<=max(v)<=root[1]]
                if not feasible:
                    with pytest.raises(ValueError):action_coverage(c,labels,root)
                    continue
                out=action_coverage(c,labels,root)
                for i,row in enumerate(out["rows"]):
                    regrets=[max(v)-v[i] for v in feasible]
                    assert row["regret_bounds"]==[min(regrets),max(regrets)]
                    assert row["feasible_wdl_bounds"]==[min(v[i] for v in feasible),max(v[i] for v in feasible)]
                    kind=("OPTIMAL_SOURCE_CLAIM" if max(regrets)==0 else
                          "SUBOPTIMAL_SOURCE_CLAIM" if min(regrets)>0 else "UNKNOWN")
                    assert row["classification"]==kind
                # Negating every value and switching value-seat must preserve regret.
                neg=[dict(action=a,wdl_bounds=[-b[1],-b[0]]) for a,b in zip(c.legal_actions,bounds)]
                negative=action_coverage(c,neg,None if root is None else [-root[1],-root[0]],value_seat=1)
                assert [r["regret_bounds"] for r in negative["rows"]]==[r["regret_bounds"] for r in out["rows"]]
                cases+=1
    assert cases>5000


def test_same_action_cancels_unknown_value():
    from scripts.leaper_truth_compatibility import paired_action_bounds
    c=abstract_context()
    out=paired_action_bounds(c,[],c.legal_actions[0],c.legal_actions[0])
    assert out["improvement_bounds"]==[0,0]
    assert out["candidate"]["feasible_wdl_bounds"]==[-1,1]


def test_partial_paired_labels_keep_uncertainty():
    from scripts.leaper_truth_compatibility import paired_action_bounds
    c=abstract_context()
    labels=[dict(action=c.legal_actions[0],wdl_bounds=[0,0])]
    assert paired_action_bounds(c,labels,c.legal_actions[0],c.legal_actions[1])["improvement_bounds"]==[-1,1]


def test_paired_bounds_match_all_feasible_assignments():
    from itertools import product
    from scripts.leaper_truth_compatibility import paired_action_bounds
    intervals=[(-1,-1),(-1,0),(-1,1),(0,0),(0,1),(1,1)]
    c=abstract_context(count=3)
    for bounds in product(intervals,repeat=3):
        assignments=list(product(*(range(lo,hi+1) for lo,hi in bounds)))
        labels=[dict(action=a,wdl_bounds=b) for a,b in zip(c.legal_actions,bounds)]
        for root in [None,*intervals]:
            feasible=[v for v in assignments if root is None or root[0]<=max(v)<=root[1]]
            if not feasible:continue
            expected=[min(v[1]-v[0] for v in feasible),max(v[1]-v[0] for v in feasible)]
            assert paired_action_bounds(c,labels,c.legal_actions[0],c.legal_actions[1],root)["improvement_bounds"]==expected


@pytest.fixture(scope="module")
def saved_proof():
    inputs=json.loads(gzip.decompress((DATA/"inputs.json.gz").read_bytes()))
    packet=json.loads(gzip.decompress(Path("docs/research/data/leaper_history_context_20261024/evidence.json.gz").read_bytes()))
    saved=json.loads(packet["documents_utf8"]["context/literal.json"])
    arm=next(a for case in saved["cases"] for row in case["rows"] for a in row["arms"] if any(len(n["children"])>1 for n in a["complete_tree"]))
    family=next(f for f in inputs["families"] if f.get("fingerprint")==arm["fingerprint"])
    context=bind_context(family["rule"],arm["final_record"])
    return context,arm["complete_tree"]


def test_supplied_proof_is_checked_without_filling_states(saved_proof):
    from scripts.leaper_truth_compatibility import verify_saved_tree
    c,nodes=saved_proof
    out=verify_saved_tree(c,nodes)
    assert out["status"]=="VERIFIED_SUPPLIED_COMPLETE_TREE"
    assert out["counts"]["nodes"]==len(nodes)


def test_missing_defense_invalidates_saved_certificate(saved_proof):
    from scripts.leaper_truth_compatibility import verify_saved_tree
    c,nodes=saved_proof;changed=deepcopy(nodes)
    n=next(n for n in changed if len(n["children"])>1);n["children"].pop()
    with pytest.raises(ValueError,match="exact legal frontier"):
        verify_saved_tree(c,changed)


def test_missing_leaf_is_not_resolved_on_demand(saved_proof):
    from scripts.leaper_truth_compatibility import verify_saved_tree
    c,nodes=saved_proof;changed=deepcopy(nodes)
    leaf=next(n for n in changed if not n["children"]);changed.remove(leaf)
    with pytest.raises(ValueError,match="missing certificate continuation"):
        verify_saved_tree(c,changed)


def test_forged_terminal_value_invalidates_certificate(saved_proof):
    from scripts.leaper_truth_compatibility import verify_saved_tree
    c,nodes=saved_proof;changed=deepcopy(nodes)
    leaf=next(n for n in changed if not n["children"]);leaf["value"]=1 if leaf["value"]!=1 else -1
    with pytest.raises(ValueError,match="local WDL equation|terminal label"):
        verify_saved_tree(c,changed)


def test_wrong_history_on_child_is_not_a_position_only_match(saved_proof):
    from scripts.leaper_truth_compatibility import verify_saved_tree
    c,nodes=saved_proof;changed=deepcopy(nodes)
    parent=next(n for n in changed if n["children"])
    parent["children"][0]["state"]["repetition_counts"]=[]
    with pytest.raises(ValueError,match="edge differs"):
        verify_saved_tree(c,changed)


def test_duplicate_or_unreachable_state_is_not_ignored(saved_proof):
    from scripts.leaper_truth_compatibility import verify_saved_tree
    c,nodes=saved_proof
    with pytest.raises(ValueError,match="duplicate certificate"):
        verify_saved_tree(c,nodes+[nodes[0]])
    extra=deepcopy(nodes[0]);extra["state"]["ply_count"]+=100
    with pytest.raises(ValueError,match="unreachable extra"):
        verify_saved_tree(c,nodes+[extra])


@pytest.fixture(scope="module")
def source_index():
    from scripts.qualify_leaper_candidate_truth import PublishedTruth
    return PublishedTruth(DATA)


def test_end_to_end_source_bound_handoff(sample,source_index):
    f,r,c=sample
    result=source_index.check(dict(id="old-control",rule=f["rule"],record=r["full_record"],selected_action=c.legal_actions[0]))
    assert result["compatibility"]=="COMPATIBLE"
    assert result["coverage"]["labelled_actions"]==len(c.legal_actions)
    assert result["selected_action"]["classification"] in ("OPTIMAL_SOURCE_CLAIM","SUBOPTIMAL_SOURCE_CLAIM")
    assert "SOURCE_CLAIM" in result["qualification"]


def test_missing_primary_rule_is_unknown_not_assumed(sample,source_index):
    f,r,c=sample
    result=source_index.check(dict(id="missing-rule",record=r["full_record"]))
    assert result["compatibility"]=="UNKNOWN"
    assert result["reason"]=="MISSING_FULL_CONTEXT" and result["missing"]==["rule"]
    assert result["coverage"] is None


def test_resigned_target_cannot_leak_matching_core_state_truth(sample,source_index):
    f,r,c=sample;record=deepcopy(r["full_record"]);record["resigned_by"]=0
    result=source_index.check(dict(rule=f["rule"],record=record,selected_action=c.legal_actions[0]))
    assert result["compatibility"]=="INCOMPATIBLE" and result["coverage"] is None
    assert result["reason"]=="CONSERVATIVE_RECORD_OR_SESSION_MISMATCH"


def test_new_history_without_matching_source_is_unknown(sample,source_index):
    f,r,c=sample
    from generic_chess.session.serialization import serialize_game_record
    from generic_chess.session.session import GameSession
    session=GameSession.replay(c.session.compiled,c.session.to_record());session.submit(session.legal_actions()[0])
    record=json.loads(serialize_game_record(session.to_record()))
    result=source_index.check(dict(rule=f["rule"],record=record))
    assert result["compatibility"]=="UNKNOWN" and result["reason"]=="NO_MATCHING_COMPLETE_HISTORY_TRUTH"


def test_malformed_record_is_recorded_not_imputed(sample,source_index):
    f,r,c=sample;record=deepcopy(r["full_record"]);record["actions"]=[{}]
    result=source_index.check(dict(rule=f["rule"],record=record))
    assert result["compatibility"]=="UNKNOWN" and result["reason"]=="INVALID_OR_UNSUPPORTED_CONTEXT"


def test_illegal_selected_action_stays_unknown(sample,source_index):
    f,r,c=sample
    result=source_index.check(dict(rule=f["rule"],record=r["full_record"],selected_action={}))
    assert result["compatibility"]=="COMPATIBLE"
    assert result["selected_action"]["classification"]=="UNKNOWN"
