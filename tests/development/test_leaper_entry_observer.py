"""Actual observer contracts, no quality or timing experiment."""
import ast,inspect,textwrap
from types import SimpleNamespace
import pytest
from test_leaper_threat_ordering import fixture
from scripts.leaper_entry_observer import EntryObserver,_Instrument
from scripts.leaper_threat_policy import threat_policy
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
import generic_chess.ai.alphabeta.search as search

def invariant(d):
    # Preserve all returned semantic/work/provider contracts, exclude clocks only.
    from scripts.research_record import record_value
    return {k:v for k,v in record_value(d).items() if 'seconds' not in k and not k.startswith('time_to_') and k!='evaluation_profile_cache_hit'}

@pytest.mark.parametrize('policy',[False,True])
def test_observer_preserves_fixed_work_action_value_PV_TT_and_undo(policy,tmp_path):
    c,s=fixture();before=s.to_record();decisions=[];original=search.negamax;oldcheck=search._Budget.check
    for enabled in (False,True):
        p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=False,use_aspiration=False));o=EntryObserver('fixed-'+str(policy))
        with threat_policy(policy):
            if enabled:
                with o.installed():d=p.choose_action(s,SearchLimits(max_depth=2,max_nodes=50000,quiescence_max_depth=0,quiescence_hard_max_depth=8))
            else:d=p.choose_action(s,SearchLimits(max_depth=2,max_nodes=50000,quiescence_max_depth=0,quiescence_hard_max_depth=8))
        from scripts.research_record import write_record
        write_record(tmp_path/("observer-"+str(enabled)+".json"),{'decision':d,'observer':o.result(d) if enabled else None})
        decisions.append(d);assert d.completed_depth==2 and d.runtime_depth_balanced and s.to_record()==before;assert search.negamax is original and search._Budget.check is oldcheck
        if enabled:
            result=o.result(d);assert not result['errors'];assert result['retained_root_attempt'] is not None;assert sum(v.get('child_entry',0) for v in result['counts'].values())>0
            if policy:assert result['retained_changed_entries']>0;assert any(w['root_attempt']==result['retained_root_attempt'] and w['entry']=='AFTER_ORIGINAL_BUDGET_CHECK' for w in result['witnesses'])
    assert invariant(decisions[0])==invariant(decisions[1])

def test_budget_rejection_at_negamax_entry_does_not_count_child_entry():
    c,s=fixture();before=s.to_record();o=EntryObserver('budget-entry')
    token=SimpleNamespace(is_cancelled=lambda:bool(o.stack and o.stack[-1]['parent'] is not None))
    with threat_policy(True),o.installed():d=AlphaBetaPlayer(c,use_disk_cache=False).choose_action(s,SearchLimits(max_depth=2,max_nodes=50000),cancel_token=token)
    r=o.result(d);assert d.termination_reason=='cancelled' and d.runtime_depth_balanced and s.to_record()==before
    assert sum(v.get('abort_before_entry',0) for v in r['counts'].values())==1
    assert sum(v.get('child_entry',0) for v in r['counts'].values())==0
    assert r['retained_root_attempt'] is None and r['retained_changed_entries'] is None

def test_warm_TT_return_is_separate_from_ordered_child_activity():
    c,s=fixture();p=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=False,use_aspiration=False));decisions=[]
    for i in range(2):
        o=EntryObserver('warm-'+str(i))
        with threat_policy(True),o.installed():d=p.choose_action(s,SearchLimits(max_depth=2,max_nodes=50000,quiescence_max_depth=0,quiescence_hard_max_depth=8))
        decisions.append(d)
        if i:
            r=o.result(d);assert not r['errors'];assert any(x['return_source']=='TT_return' and x['children']==0 for x in r['roots']);assert r['retained_changed_entries']==0
    assert decisions[0].score==decisions[1].score

def test_AST_hooks_skip_nested_helper_returns_and_keep_one_existing_entry_check():
    original=search.negamax;tree=ast.parse(textwrap.dedent(inspect.getsource(original)));x=_Instrument();x.visit(tree)
    assert x.entry_hooks==1
    helpers=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='child_search'];assert len(helpers)==1
    assert not any(isinstance(n,ast.Name) and n.id=='_endpoint_observer' for n in ast.walk(helpers[0]))
    assert sum(r['source']=='TT_return' for r in x.returns)==3
