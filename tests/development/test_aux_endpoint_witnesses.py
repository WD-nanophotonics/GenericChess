"""Reader boundary tests on a labelled projection of actual published evidence."""
import copy,gzip,json
from pathlib import Path
import pytest
from scripts.verify_aux_endpoint_witnesses import retained_witnesses

FIXTURE=Path(__file__).resolve().parents[1]/"fixtures/aux_endpoint_observer_20261029.json.gz"
def row():return json.loads(gzip.decompress(FIXTURE.read_bytes()))["row"]

def test_actual_retained_root_witness_projection_admitted():
    r=row();w=retained_witnesses(r)
    assert len(w)==1 and w[0]["ply"]==1 and w[0]["return"]=="NORMAL"

@pytest.mark.parametrize("damage",["prebudget","wrong_parent","unaccepted","rank_unchanged","stale_depth"])
def test_witness_reader_refuses_false_positive_activity(damage):
    r=copy.deepcopy(row());o=r["observer"];w=o["witnesses"][0]
    if damage=="prebudget":w["entry"]="BEFORE_ORIGINAL_BUDGET_CHECK"
    elif damage=="wrong_parent":w["parent_id"]+=1
    elif damage=="unaccepted":o["retained_root_attempt"]+=1
    elif damage=="stale_depth":o["completed_depth"]+=1
    else:w["candidate_rank"]=w["baseline_rank"]
    with pytest.raises(AssertionError):retained_witnesses(r)
