"""Check exact input-domain counting rather than infer a matched effect."""
from pathlib import Path
from copy import deepcopy
import pytest
from scripts.verify_leaper_delayed_capture import load
from scripts.leaper_safe_support import qualify

DATA=Path(__file__).resolve().parents[2]/'docs/research/data/leaper_support_and_delayed_win_20261024'


def packet():return load(DATA/'support-registration.json'),load(DATA/'support.json.gz')


def test_missing_translation_term_cannot_hide_behind_retained_count():
    reg,m=packet();m['cases'][0]['terms'].pop()
    with pytest.raises(AssertionError):qualify(reg,m)


def test_changed_lower_polynomial_coefficient_must_be_recomputed():
    reg,m=packet();m['cases'][0]['polynomial']['0']+=1
    with pytest.raises(AssertionError):qualify(reg,m)


def test_maximal_pair_theorem_requires_actual_rule_to_match_missing_bits():
    reg,m=packet();a,b=m['maximal_proper_pairs'][:2]
    for field in ('A','B','count','placement','rule','root'):b[field]=deepcopy(a[field])
    with pytest.raises(AssertionError):qualify(reg,m)


def test_exact_support_counts_do_not_extrapolate_stable_polynomial_to_n3():
    reg,m=packet();q=qualify(reg,m)
    union=next(c for c in q['cases']if c['A']==31)
    assert union['counts'][0]['direct']==0 and union['counts'][0]['polynomial']==528
    assert union['counts'][1]['direct']==5124


def test_extra_actor_breaks_single_actor_support_union_law():
    from scripts.leaper_support_interactions import qualify as interaction_qualify
    m=load(DATA/'interaction.json.gz');q=interaction_qualify(m)
    assert q['algebraic_mask_identity_checks']==3072
    assert [(r['A'],r['admitted'])for r in m['extra_A_control']]==[(22,True),(23,False),(30,False)]
