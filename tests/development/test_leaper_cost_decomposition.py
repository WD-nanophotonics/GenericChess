"""Scope/record-boundary controls for the data-only cost analysis."""
from copy import deepcopy
from pathlib import Path
import pytest
from scripts.leaper_cost_decomposition import analyze_documents,derive_row,load_screen,rank_correlation

BUNDLE=Path('docs/research/data/leaper_forward_width_20261024/screen-evidence.json.gz')

@pytest.fixture(scope='module')
def docs():return load_screen(BUNDLE)


def test_all_sealed_counts_keep_shortcuts_censors_and_outer_residual(docs):
    a=analyze_documents(docs)
    assert len(a['rows'])==1152 and a['new_Player_calls']==0
    from collections import Counter
    assert Counter(r['reason'] for r in a['rows'])=={'time_limit':1016,'root_immediate_win':130,'node_limit':6}
    assert all(r['qnodes']==0 for r in a['rows'])
    assert all(r['position_keys_computed']==r['successors_searched']+r['tt_probes'] for r in a['rows'])
    b=a['batches'][0]
    assert b['wall_seconds']==pytest.approx(b['query_seconds']+b['player_setup_seconds']+b['rule_setup_seconds']+b['unassigned_outer_residual_seconds'])
    assert b['unassigned_outer_residual_seconds']==pytest.approx(269.92777510080487)
    # Diagnostic filtering preserves original ALL associations and both levels.
    c=next(x for x in a['associations'] if x['n']==4 and x['budget']==32768 and x['stratum']=='ALL' and x['target']=='total_work')
    assert c['roots']==192 and c['rules']==24
    assert c['root']['forward2_width']!=c['rule_mean']['forward2_width']


def test_duplicate_physical_return_is_not_independent_replication(docs):
    d=deepcopy(docs);d['N32768.json']['rows'][1]=deepcopy(d['N32768.json']['rows'][0])
    with pytest.raises(ValueError,match='duplicate'):analyze_documents(d)


def test_counter_interpretation_rejects_qsearch_and_inconsistent_key_bookkeeping(docs):
    row=deepcopy(docs['N32768.json']['rows'][0]);meta=next(m for m in docs['metadata.json']['rows'] if m['seed']==row['seed'])
    row['decision']['qnodes']=1
    with pytest.raises(ValueError,match='Q0/runtime'):derive_row(row,meta,32768)
    row['decision']['qnodes']=0;row['decision']['position_keys_computed']+=1
    with pytest.raises(ValueError,match='Q0/runtime'):derive_row(row,meta,32768)


def test_wrapper_cost_is_not_permitted_to_exceed_enclosing_query(docs):
    row=deepcopy(docs['N32768.json']['rows'][0]);meta=next(m for m in docs['metadata.json']['rows'] if m['seed']==row['seed'])
    row['decision']['legal_generation_seconds']=row['query_seconds']*2
    with pytest.raises(ValueError,match='wrapper time'):derive_row(row,meta,32768)


def test_rank_ties_and_constant_feature_are_explicit():
    assert rank_correlation([1,1,2,2],[1,2,3,4])==pytest.approx(2/(5**.5))
    assert rank_correlation([1,1],[1,2]) is None
    with pytest.raises(ValueError):rank_correlation([],[])


@pytest.fixture
def mini(docs):
    from scripts.leaper_cost_decomposition import analyze_policy_returns
    seed=docs['N32768.json']['rows'][0]['seed']
    w=next(w for w in docs['inputs.json']['worlds'] if w['seed']==seed)
    m=next(w for w in docs['metadata.json']['rows'] if w['seed']==seed)
    old=deepcopy(docs['N32768.json']);old['rows']=old['rows'][:1];old['worlds']=[next(w for w in old['worlds'] if w['seed']==seed)]
    old['missing_slots']=[];old['protocol']['planned_queries']=1
    new=deepcopy(old);new['protocol']['check_only_qsearch']=True
    plan={'planned_new_calls':2,'new_arms':[{'label':'checkQ0','qdepth':0,'check_only_qsearch':True},{'label':'ordinaryQ4','qdepth':4,'check_only_qsearch':False}],
          'input_sha256':old['protocol']['input_sha256'],'source_sha256':{'scripts/semantic_probe_cost.py':old['protocol']['source_sha256']}}
    return analyze_policy_returns,plan,{'worlds':[w]},{'rows':[m]},old,new


def test_policy_reader_keeps_old_reference_and_missing_planned_slots(mini):
    fn,plan,inputs,meta,old,new=mini;seed=old['rows'][0]['seed'];new['rows']=[];new['missing_slots']=[[seed,0,0,'all']]
    r=fn(plan,inputs,meta,old,{'checkQ0':new})
    assert r['coverage'][0]['new_execution'] is False
    assert r['coverage'][1]['observed']==0 and r['coverage'][1]['missing']==1
    assert r['paired_comparisons'][0]['matched_full_inputs']==0
    assert r['new_PV_Core_plies']==0


def test_policy_reader_rejects_wrong_leaf_flag_source_and_history(mini):
    fn,plan,inputs,meta,old,new=mini
    bad=deepcopy(new);bad['protocol']['check_only_qsearch']=False
    with pytest.raises(ValueError,match='policy/limit'):fn(plan,inputs,meta,old,{'checkQ0':bad})
    bad=deepcopy(new);bad['protocol']['source_sha256']='wrong'
    with pytest.raises(ValueError,match='source'):fn(plan,inputs,meta,old,{'checkQ0':bad})
    bad=deepcopy(new);bad['worlds'][0]['roots'][0]['record']['actions']=[{}]
    with pytest.raises(ValueError,match='history'):fn(plan,inputs,meta,old,{'checkQ0':bad})


def test_policy_reader_replays_actual_retained_pv_without_query(mini):
    fn,plan,inputs,meta,old,new=mini;r=fn(plan,inputs,meta,old,{'checkQ0':new},qualify_pvs=True)
    assert r['new_PV_Core_plies']==len(new['rows'][0]['decision']['principal_variation'])
    assert r['paired_comparisons'][0]['root_shortcut_membership_mismatches']==[]
    assert r['paired_comparisons'][0]['changed_literal_actions']==0
