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


@pytest.fixture(scope="module")
def lower_proof(saved_proof):
    from scripts.verify_leaper_truth_controls import trim_supplied_tree
    c,nodes=saved_proof
    root=next(n for n in nodes if digest(n["state"])==c.identity["state_sha256"])
    return c,trim_supplied_tree(nodes,c.identity["state_sha256"],root["value"]),root["value"]


def test_one_sided_saved_strategy_is_not_exact_value_claim(lower_proof):
    from scripts.leaper_truth_compatibility import verify_bound_tree
    c,nodes,bound=lower_proof
    out=verify_bound_tree(c,nodes,bound)
    assert out["status"]=="VERIFIED_FINITE_STRATEGY_BOUND"
    assert out["wdl_bounds"]==[bound,1]
    assert out["counts"]["nodes"]==len(nodes)


def test_one_sided_missing_universal_defense_is_rejected(lower_proof):
    from scripts.leaper_truth_compatibility import verify_bound_tree
    c,nodes,bound=lower_proof;changed=deepcopy(nodes)
    universal=next(n for n in changed if n["state"]["position"]["side_to_move"]==1 and n["children"])
    universal["children"].pop()
    with pytest.raises(ValueError,match="missing a legal defense"):
        verify_bound_tree(c,changed,bound)


def test_one_sided_ongoing_cutoff_is_not_an_oracle_leaf(lower_proof):
    from scripts.leaper_truth_compatibility import verify_bound_tree
    c,nodes,bound=lower_proof;changed=deepcopy(nodes)
    root=next(n for n in changed if digest(n["state"])==c.identity["state_sha256"])
    root["children"]=[]
    with pytest.raises(ValueError,match="requires one move|missing a legal defense"):
        verify_bound_tree(c,changed,bound)


def test_declarations_are_explicitly_outside_move_proof_scope():
    from generic_chess import build_standard_shogi_ruleset,compile_ruleset_for_execution
    from generic_chess.session.session import GameSession
    from scripts.leaper_truth_compatibility import verify_bound_tree,verify_saved_tree
    session=GameSession(compile_ruleset_for_execution(build_standard_shogi_ruleset()))
    assert session.compiled.declarations
    c=Context(session,dict(side_to_move=0,terminal=dict(status="ongoing",winner=None)),())
    for check in (lambda:action_coverage(c,[]),lambda:verify_saved_tree(c,[]),lambda:verify_bound_tree(c,[],0)):
        with pytest.raises(ValueError,match="declaration choices"):
            check()


def test_tightened_false_bound_fails_on_actual_terminal(lower_proof):
    from scripts.leaper_truth_compatibility import verify_bound_tree
    c,nodes,bound=lower_proof
    assert bound<1
    with pytest.raises(ValueError,match="terminal does not satisfy"):
        verify_bound_tree(c,nodes,bound+1)


def test_supplied_strategy_does_not_read_heuristic_value_tags(lower_proof):
    from scripts.leaper_truth_compatibility import verify_bound_tree
    c,nodes,bound=lower_proof;changed=deepcopy(nodes)
    for n in changed:n["value"]="arbitrary heuristic - not consumed"
    assert verify_bound_tree(c,changed,bound)["status"]=="VERIFIED_FINITE_STRATEGY_BOUND"


def test_wrong_seat_rejects_asymmetric_bound(lower_proof):
    from scripts.leaper_truth_compatibility import verify_bound_tree
    c,nodes,bound=lower_proof
    # A strategy's quantifiers are bound to a named seat, not alternate negamax tags.
    with pytest.raises(ValueError):
        verify_bound_tree(c,nodes,bound,value_seat=1)


def test_linear_interval_bounds_against_literal_weighted_completions():
    from itertools import product
    from fractions import Fraction
    from scripts.leaper_truth_compatibility import linear_interval_bounds
    intervals=[(-1,-1),(-1,0),(-1,1),(0,0),(0,1),(1,1)]
    for bounds in product(intervals,repeat=3):
        values=list(product(*(range(lo,hi+1) for lo,hi in bounds)))
        for root in [None,*intervals]:
            feasible=[v for v in values if root is None or root[0]<=max(v)<=root[1]]
            for coefficients in product((-2,-1,0,1,2),repeat=3):
                if not feasible:
                    with pytest.raises(ValueError):linear_interval_bounds(bounds,coefficients,root)
                    continue
                expected=[sum(c*v for c,v in zip(coefficients,row)) for row in feasible]
                actual=linear_interval_bounds(bounds,coefficients,root)
                assert actual["bounds"]==[min(expected),max(expected)]
                for label in ("lower_interval_completion","upper_interval_completion"):
                    assert tuple(actual[label]) in feasible
    result=linear_interval_bounds([[-1,1],[0,1]],["1/3","-2/7"],[0,0])
    assert result["bounds"]==[Fraction(-1,3),Fraction(0)]


def test_reversed_pairs_cancel_shared_unknown_values():
    from scripts.leaper_truth_compatibility import bound_same_context_pairs
    c=abstract_context(count=3);a,b=c.legal_actions[:2]
    result=bound_same_context_pairs(c,[],[dict(baseline_action=a,candidate_action=b),dict(baseline_action=b,candidate_action=a)])
    assert result["mean_improvement_bounds"]==["0","0"]
    assert result["planned_slots"]==2 and result["unknown_slots"]==0
    assert all(r["coefficient"]=="0" for r in result["coalesced_action_coefficients"])


def test_unknown_slots_keep_fixed_denominator_without_draw_imputation():
    from scripts.leaper_truth_compatibility import bound_same_context_pairs
    c=abstract_context(count=3);a,b=c.legal_actions[:2]
    labels=[dict(action=a,wdl_bounds=[-1,-1]),dict(action=b,wdl_bounds=[1,1])]
    result=bound_same_context_pairs(c,labels,[dict(baseline_action=a,candidate_action=b),dict(weight=1)])
    assert result["weighted_sum_bounds"]==["0","4"]
    assert result["mean_improvement_bounds"]==["0","2"]
    assert result["planned_weight"]=="2" and result["unknown_slots"]==1


def test_rational_weights_and_partial_cancellation_are_exact():
    from scripts.leaper_truth_compatibility import bound_same_context_pairs
    c=abstract_context(count=2);a,b=c.legal_actions
    result=bound_same_context_pairs(c,[],[dict(baseline_action=a,candidate_action=b,weight="1/3"),dict(baseline_action=b,candidate_action=a,weight="1/6")])
    assert result["planned_weight"]=="1/2"
    assert result["mean_improvement_bounds"]==["-2/3","2/3"]
    with pytest.raises(ValueError,match="weights must be exact"):
        bound_same_context_pairs(c,[],[dict(baseline_action=a,candidate_action=b,weight=0.5)])


def test_root_constraint_tightens_joint_weighted_bounds():
    from scripts.leaper_truth_compatibility import bound_same_context_pairs
    c=abstract_context(count=3);a,b,d=c.legal_actions
    result=bound_same_context_pairs(c,[],[dict(baseline_action=a,candidate_action=b)],[-1,-1])
    assert result["mean_improvement_bounds"]==["0","0"]


@pytest.fixture(scope="module")
def paired_history_proofs():
    inputs=json.loads(gzip.decompress((DATA/"inputs.json.gz").read_bytes()))
    packet=json.loads(gzip.decompress(Path("docs/research/data/leaper_history_context_20261024/evidence.json.gz").read_bytes()))
    old=json.loads(packet["documents_utf8"]["context/literal.json"])
    aa=old["cases"][0]["rows"]
    arms=[r["arms"][0] for r in aa]
    family=next(f for f in inputs["families"] if f.get("fingerprint")==arms[0]["fingerprint"])
    source=bind_context(family["rule"],arms[0]["final_record"])
    target=bind_context(family["rule"],arms[1]["final_record"],compiled=source.session.compiled)
    return source,target,arms


def test_checked_revalidation_does_not_relax_default_context_matching(paired_history_proofs):
    from scripts.leaper_truth_compatibility import revalidate_bound_strategy
    from scripts.verify_leaper_truth_controls import trim_supplied_tree
    source,target,arms=paired_history_proofs
    cert=trim_supplied_tree(arms[0]["complete_tree"],source.identity["state_sha256"],-1)
    result=revalidate_bound_strategy(source,target,cert,-1)
    assert result["status"]=="REVALIDATED_FINITE_STRATEGY_BOUND"
    assert compare_contexts(source,target)["status"]=="INCOMPATIBLE"
    assert result["verification"]["context"]==target.identity


def test_revalidation_failure_is_not_a_disproof(paired_history_proofs):
    from scripts.leaper_truth_compatibility import revalidate_bound_strategy
    from scripts.verify_leaper_truth_controls import trim_supplied_tree
    source,target,arms=paired_history_proofs
    assert arms[0]["value"]==-1 and arms[1]["value"]==0
    cert=trim_supplied_tree(arms[0]["complete_tree"],source.identity["state_sha256"],-1,direction="upper")
    result=revalidate_bound_strategy(source,target,cert,-1,direction="upper")
    assert result["status"]=="NOT_PROVED_BY_THIS_CERTIFICATE"
    assert "Failure is not disproof" in result["limitation"]


def test_different_history_cannot_consume_source_full_state_nodes(paired_history_proofs):
    from scripts.leaper_truth_compatibility import verify_bound_tree
    from scripts.verify_leaper_truth_controls import trim_supplied_tree
    source,target,arms=paired_history_proofs
    cert=trim_supplied_tree(arms[0]["complete_tree"],source.identity["state_sha256"],-1)
    with pytest.raises(ValueError,match="missing bound-certificate continuation"):
        verify_bound_tree(target,cert,-1)


def test_no_observed_source_repetition_does_not_transfer_exact_loss(paired_history_proofs):
    from scripts.leaper_truth_compatibility import revalidate_bound_strategy
    from scripts.verify_leaper_truth_controls import trim_supplied_tree
    source,target,arms=paired_history_proofs
    cert=trim_supplied_tree(arms[0]["complete_tree"],source.identity["state_sha256"],-1,direction="upper")
    assert all(n["state"]["terminal_status"]["status"]!="repetition" for n in cert)
    exact=revalidate_bound_strategy(source,target,cert,-1,direction="upper")
    weakened=revalidate_bound_strategy(source,target,cert,0,direction="upper")
    assert exact["status"]=="NOT_PROVED_BY_THIS_CERTIFICATE"
    assert weakened["status"]=="REVALIDATED_FINITE_STRATEGY_BOUND"
    assert weakened["verification"]["wdl_bounds"]==[-1,0]


@pytest.fixture
def historical_packet_fixture(sample,source_index):
    import hashlib
    f,r,c=sample
    rule_key=hashlib.sha256(json.dumps(f["rule"],sort_keys=True).encode()).hexdigest()
    old=source_index.rows[r["state_sha256"]]
    values={digest(b["action"]):b["wdl_bounds"][0] for b in old["action_bounds"]}
    from generic_chess.core.actions import action_to_dict
    from scripts.research_record import record_value
    case=dict(key="fixture-only",rule_sha256=rule_key,record=r["full_record"],state_sha256=r["state_sha256"],
              absolute_ply=0,actor=0,remaining=6,incoming_counts=c.identity["repetition_counts"],
              root_global_WDL=old["wdl_bounds"][0],root_own_WDL=old["wdl_bounds"][0],source_episode="old-fixture",
              labelled_actions=[dict(action=record_value(a),truth=dict(value=values[digest(action_to_dict(a))])) for a in c.session.legal_actions()])
    packet=dict(rules={rule_key:f["rule"]},cases=[case],status="TEST_FIXTURE_ONLY")
    envelope=dict(source_key=case["key"],root_record=case["record"],rule_sha256=rule_key)
    return packet,envelope


def run_historical_fixture(tmp_path,packet,envelope):
    import hashlib
    from scripts.qualify_published_leaper_panel import qualify_panel
    raw=json.dumps(packet).encode();envelope=dict(envelope,source_input_hash=hashlib.sha256(raw).hexdigest())
    src=tmp_path/"inputs.json.gz";env=tmp_path/"envelope.json.gz"
    src.write_bytes(gzip.compress(raw));env.write_bytes(gzip.compress(json.dumps(envelope).encode()))
    return qualify_panel(src,env)


def test_historical_source_hash_is_not_semantic_fingerprint(tmp_path,historical_packet_fixture):
    packet,envelope=historical_packet_fixture
    result=run_historical_fixture(tmp_path,packet,envelope)
    assert result["status"]=="PASS" and result["distinct_rules"]==1
    assert result["prepared_branch_root"]["context"]["ruleset_fingerprint"]!=envelope["rule_sha256"]


def test_historical_missing_action_label_is_not_invented(tmp_path,historical_packet_fixture):
    packet,envelope=historical_packet_fixture
    packet["cases"][0]["labelled_actions"].pop()
    with pytest.raises(ValueError,match="frontier not complete"):
        run_historical_fixture(tmp_path,packet,envelope)


def test_unknown_historical_label_stays_unknown(tmp_path,historical_packet_fixture):
    packet,envelope=historical_packet_fixture
    packet["cases"][0]["labelled_actions"][0]["truth"]["value"]=None
    result=run_historical_fixture(tmp_path,packet,envelope)
    assert result["counts"]["unknown_source_labels"]==1
    row=result["prepared_branch_root"]["coverage"]["rows"][0]
    assert not row["labelled"] and row["wdl_bounds"]==[-1,1]
    assert row["classification"]=="UNKNOWN"


def test_corrupt_historical_full_state_is_rejected(tmp_path,historical_packet_fixture):
    packet,envelope=historical_packet_fixture
    packet["cases"][0]["state_sha256"]="bad"
    with pytest.raises(ValueError,match="full-state replay differs"):
        run_historical_fixture(tmp_path,packet,envelope)


def test_corrupt_historical_counts_are_rejected(tmp_path,historical_packet_fixture):
    packet,envelope=historical_packet_fixture
    packet["cases"][0]["incoming_counts"]=[]
    with pytest.raises(ValueError,match="incoming count map differs"):
        run_historical_fixture(tmp_path,packet,envelope)


def test_certified_label_cannot_silently_switch_named_seat():
    c=abstract_context(count=2)
    label=dict(action=c.legal_actions[0],wdl_bounds=[1,1],value_seat=1)
    with pytest.raises(ValueError,match="perspective differs"):
        action_coverage(c,[label],value_seat=0)
    assert action_coverage(c,[label],value_seat=1)["value_seat"]==1


def test_new_primary_behavior_denominator_uses_nonempty_groups():
    path=Path("docs/research/data/aux_truth_compatibility_20261026/new-primary-compatibility.json.gz")
    packet=json.loads(gzip.decompress(path.read_bytes()))
    covered={g["case_id"] for g in packet["behavior"]}
    all_roots={r["id"] for r in packet["rows"]}
    assert len(covered)==12 and len(all_roots)==24
    assert packet["counts"]["behavior_covered_source_contexts"]==len(covered)
    assert packet["counts"]["source_contexts_without_games"]==len(all_roots-covered)
    assert {r["id"] for r in packet["rows"] if r["saved_behavior_game_ids"]}==covered
    assert sum(r["action_label_coverage"]["UNLABELLED"] for r in packet["rows"])==254
    assert all(r["H6_truth_compatibility"]["status"]=="INCOMPATIBLE" and r["root_WDL"]=="UNKNOWN" for r in packet["rows"])
    assert all(g["qualification"]=="ACTUAL_GAME_RECORD_REPLAYED_NOT_MINIMAX_PROOF" for g in packet["behavior"])
