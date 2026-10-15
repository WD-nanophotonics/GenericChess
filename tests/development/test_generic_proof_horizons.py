import pytest
from scripts.generic_proof_horizons import dev_cases,horizon_settings


def plan():
    return dict(H=16,horizons=[16,24],proof_modes=[True],study_kind='FIXED_HYBRID_PRICES_PAIRED_HORIZONS',baseline_index=0,candidate_roles=['TO_MOVE','OTHER'],opponents=[dict(id='U64'),dict(id='U4096')],families=[dict(family=i,phase='DEV') for i in range(2)])


def test_both_horizons_have_every_physical_role_price_and_opponent():
    p=plan();cases=list(dev_cases(p,1));keys=[(f['family'],q,i,c,o['id'],r,h) for f,q,i,c,o,r,h in cases]
    assert len(keys)==len(set(keys))==64
    for family in (0,1):
        subset=[x for x in keys if x[0]==family]
        assert len(subset)==32 and {x[-1] for x in subset}=={16,24}
    # Adjacent price pairs share one horizon but reverse order by role/color.
    assert [x[2] for x in cases[:2]]==[0,1]
    assert [x[2] for x in cases[4:6]]==[1,0]


@pytest.mark.parametrize('change',[{'horizons':[16,16]},{'horizons':[True,24]},{'proof_modes':[1]},{'study_kind':'LEARN'},{'families':[dict(family=0,phase='TRAIN')]}])
def test_reject_ambiguous_or_unfrozen_training_identity(change):
    p=plan();p.update(change)
    with pytest.raises(ValueError):horizon_settings(p)
