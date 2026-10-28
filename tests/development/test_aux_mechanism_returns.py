"""Contract-layer negative controls; public source archive verification is separate."""
from pathlib import Path
import copy,gzip,json,hashlib
import pytest
from generic_chess.core.errors import IllegalActionError
from scripts import verify_aux_mechanism_returns as M

@pytest.fixture
def packet():
    p=Path(__file__).parents[1]/"fixtures"/"aux_mechanism_returns_20261029.json.gz"
    return json.loads(gzip.decompress(p.read_bytes()))

def install(monkeypatch,packet):
    members={k:v.encode("utf8") for k,v in packet["members"].items()}
    monkeypatch.setattr(M,"archive",lambda:(members,packet["binding"]))

def coherent_change(packet,name,change):
    # Test the post-byte-binding consumer, not merely a trivial outer hash mismatch.
    key="mechanism-witness/"+name
    row=json.loads(packet["members"][key]);change(row)
    packet["members"][key]=json.dumps(row)
    old=json.loads(packet["members"]["mechanism-original-reader.json"])
    for x in old["records"]:
        if x["file"]==name:x["sha256"]=hashlib.sha256(packet["members"][key].encode()).hexdigest()
    packet["members"]["mechanism-original-reader.json"]=json.dumps(old)

def test_exact_eight_returns_and_three_root_branches(tmp_path,monkeypatch,packet):
    install(monkeypatch,packet);v=M.run(tmp_path/"result.json")
    assert len(v["decisions"])==8
    assert v["actual_consumer_submissions"]["total"]==63
    assert [x["immediate_opponent_wins"]for x in v["all_root_children"]]==[1,0,0]
    assert [x["raw_default_root_view"]for x in v["all_root_children"]]==[-492,-492,-488]
    assert [x["result_q"]for x in v["decisions"]]==[0,0,0,0,0,0,4,4]

def test_numeric_boolean_cannot_impersonate_frozen_arm(tmp_path,monkeypatch,packet):
    coherent_change(packet,"search-1.json",lambda r:r.update(on=1));install(monkeypatch,packet)
    with pytest.raises(AssertionError):M.run(tmp_path/"result.json")

def test_requested_Q4_cannot_relabel_retained_first_Q0(tmp_path,monkeypatch,packet):
    coherent_change(packet,"default-search-0.json",lambda r:r["decision"].update(result_ordinary_qdepth=4))
    install(monkeypatch,packet)
    with pytest.raises(AssertionError):M.run(tmp_path/"result.json")

def test_full_semantic_PV_identity_not_just_coordinates(tmp_path,monkeypatch,packet):
    coherent_change(packet,"default-search-2.json",lambda r:r["decision"]["principal_variation"][1].update(actor_type_id="N"))
    install(monkeypatch,packet)
    with pytest.raises(IllegalActionError):M.run(tmp_path/"result.json")
