"""Reject incomplete or relabelled prospectively registered experiments, zero queries."""
from pathlib import Path
import json,pytest
from scripts.verify_leaper_qorder_prospective import validate_registration
# Registration-only tests use small immutable fixture data built from the actual source definition.
from scripts.leaper_qorder_prospective import PAIRS
from scripts import leaper_design as L
from dataclasses import replace
import hashlib

def registration():
    rules={};cases=[]
    for i,(a,b)in enumerate(PAIRS):
        r=L.ruleset_to_dict(replace(L.definition(a,b),max_ply=64));rh=hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest();rules[rh]=r
        for ply in(0,5):cases.append(dict(key=f'r{i}-p{ply}'))
    slots=[]
    for i,c in enumerate(cases):
        for o in((False,True)if i%2==0 else(True,False)):slots.append(dict(key=c['key'],ordered=o))
    return dict(slots=slots),dict(cases=cases,rules=rules)

def test_complete_prospective_registration():
    p,i=registration();validate_registration(p,i)

def test_missing_case_arms_not_a_complete_panel():
    p,i=registration();p['slots']=p['slots'][:-2]
    with pytest.raises(AssertionError):validate_registration(p,i)

def test_duplicate_arm_rejected():
    p,i=registration();p['slots'][1]=p['slots'][0]
    with pytest.raises(AssertionError):validate_registration(p,i)

def test_rule_relabelled_without_matching_exact_hash_rejected():
    p,i=registration();next(iter(i['rules'].values()))['max_ply']=63
    with pytest.raises(AssertionError):validate_registration(p,i)
