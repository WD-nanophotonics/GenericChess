from copy import deepcopy
import pytest
from scripts.leaper_truth_views import initial_history_view
from scripts.leaper_explorer_truth import score


def fixture():
    return dict(rules={'A':{}},roots=[dict(id=str(i),fingerprint='A',mu_id='old',ply=i,
        split='exposed',wdl_fork=False,cooperative_decisive=True,universal_draw=False)
        for i in range(2)])


def test_view_changes_mu_not_history_and_cannot_be_fuzzily_scored():
    truth=fixture();original=deepcopy(truth);view=initial_history_view(truth)
    assert truth==original and len(view['roots'])==1
    assert view['roots'][0]['id']=='0'and view['roots'][0]['parent_mu_id']=='old'
    assert view['roots'][0]['mu_id']!='old'
    q=dict(id='0',fingerprint='A',mu_id='old',property='cooperative_decisive',
           probability=.5,source_sha='a'*40,cost=dict(nodes=1))
    with pytest.raises(ValueError,match='mu binding'):score(view,dict(format='leaper-explorer-predictions-v1',predictions=[q]))
    q['mu_id']=view['roots'][0]['mu_id']
    out=score(view,dict(format='leaper-explorer-predictions-v1',predictions=[q]))
    row=next(r for r in out['rows']if r['property']=='cooperative_decisive')
    assert row['denominator']==1 and row['brier_known']==.25


def test_missing_or_multiple_original_initials_are_not_an_implicit_view():
    truth=fixture();truth['roots'][0]['ply']=2
    with pytest.raises(ValueError):initial_history_view(truth)
    truth=fixture();truth['roots'][1]['ply']=0
    with pytest.raises(ValueError):initial_history_view(truth)
