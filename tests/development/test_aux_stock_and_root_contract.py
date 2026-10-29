"""Scoped stock semantics and OFFLINE exhausted-root receipt controls."""
import copy,gzip,json
from pathlib import Path
from dataclasses import replace
import pytest
from scripts import aux_captured_stock_contract as S
from scripts.verify_aux_metamorphic_root import validate

DATA=Path(__file__).resolve().parents[2]/"docs/research/data/aux_representation_contract_20261029"
def raw(name):return gzip.decompress((DATA/name).read_bytes())

def test_no_drop_stock_full_history_and_real_free_gradient(tmp_path):
    f=tmp_path/"frozen.json";f.write_bytes(raw("stock-inputs.json.gz"))
    v=S.run(f,tmp_path/"observed.json")
    for r in v["routes"].values():
        row=r["trace"][4]
        assert row["learner"][0]["raw_model_gradient"]==[0.,0.]
        assert row["learner"][1]["raw_model_gradient"]==[0.,-.1]
        assert r["trace"][-1]["terminal"]["status"]=="repetition"
        assert r["model_updates"]==0

def test_inert_stock_contract_rejects_even_one_enabled_drop_square():
    a,b,_=S.definitions_pair()
    owners=b.drop_allowed["P"]
    mask=(True,)+owners[0][1:]
    bad=replace(b,drop_allowed={**b.drop_allowed,"P":(mask,owners[1])})
    with pytest.raises(AssertionError):S.admit_inert_pair(a,bad)

def test_promoted_capture_returns_base_stock_not_current_type():
    v=S.promotion_boundary()
    for r in v["routes"].values():
        promoted,captured=r["trace"][1],r["trace"][4]
        assert promoted["hand_P"]==promoted["base_P"]-1==0
        assert promoted["hand_P"]!=promoted["current_P"]-1
        assert captured["hand_P"]==-1

def inputs():
    return (raw("metamorphic-root-inputs.json.gz"),
        json.loads(raw("metamorphic-root-observed.json.gz")),
        json.loads(raw("metamorphic-root-dispatch.json.gz")))

def test_exhausted_root_receipt_tie_is_not_quality_failure():
    f,r,d=inputs();v=validate(f,r,d)
    assert v["both_in_mapped_D1_argmax"] and not v["literal_selected_action_maps"]
    assert v["actual_Player_calls"]==2 and not v["quality_or_speed_gain_established"]

@pytest.mark.parametrize("damage",["binding","duplicate","unmatched_action","false_equality"])
def test_offline_root_reader_rejects_corrupt_receipts(damage):
    f,r,d=inputs();r=copy.deepcopy(r)
    if damage=="binding":r["frozen_sha256"]="0"*64
    elif damage=="duplicate":r["calls"][1]=copy.deepcopy(r["calls"][0])
    elif damage=="unmatched_action":r["calls"][1]["decision"]["action"]["actor_type_id"]="UNOBSERVED"
    else:r["literal_selected_action_maps"]=True
    with pytest.raises(AssertionError):validate(f,r,d)
