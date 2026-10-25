import pytest
from scripts import leaper_design as L
from scripts.leaper_point_coverage import PointCoverage
from tests.development.test_leaper_forced_quiet_q import context,call
from generic_chess.ai.alphabeta import search as S

def setup(**kw):
    ss,ctx=context(**kw);ctx.qdepth_limit=4;leaf=dict(child_record=L.record_value(ss.to_record()),actions=[],remaining=1,state_sha256=L.state_sha(ss.state));return ctx,PointCoverage(ctx.compiled,leaf)

def test_actual_coverage_computes_clock_value_and_charges_work():
    ctx,p=setup();old=S.negamax
    with p:assert call(ctx)==0 and ctx.stats.nodes>0 and p.records[0]['completed_depth']==1
    assert S.negamax is old;ctx.runtime.assert_balanced()

def test_missing_action_path_is_transparent():
    ctx,p=setup();p.path_actions=[object()]
    with p:assert call(ctx)==4242 and not p.records
    ctx.runtime.assert_balanced()

def test_qbudget_still_rejects_coverage_before_nested_call():
    ctx,p=setup(qcap=1)
    with pytest.raises(S.SearchAborted,match='qsearch_budget'):
        with p:call(ctx)
    assert not p.records;ctx.runtime.assert_balanced()
