import pytest
from scripts.verify_leaper_any_win_return import paired

def item(b,a,correct=True):return dict(budget=b,key='same',arm=a,correct=correct,sensitive=True,seconds=1.,caller_seconds=1.,events=3,goal_stop=False,win_band=False,time_censored=False)

def test_budget_identity_prevents_cross_budget_pair():
 x=paired([item('balanced50k','default'),item('deep200k','anywin')]);assert x['balanced50k']['pairs']==x['deep200k']['pairs']==0

def test_regression_remains_in_its_budget_even_if_other_repairs():
 x=paired([item('balanced50k','default'),item('balanced50k','anywin',False),item('deep200k','default',False),item('deep200k','anywin')]);assert x['balanced50k']['regressions']==['same']and x['deep200k']['repairs']==['same']

def test_duplicate_arm_cannot_inflate_guard():
 with pytest.raises(AssertionError,match='duplicatearm'):paired([item('balanced50k','default')]*2)


def test_active_prefix_does_not_parse_uncommitted_trailing_line(tmp_path):
 from scripts.verify_leaper_any_win_return import completed_prefix
 p=tmp_path/'queries.jsonl';p.write_bytes(b'{"a":1}\n{"a":2}\n{"a":')
 assert completed_prefix(p,128)==[{'a':1},{'a':2}]
