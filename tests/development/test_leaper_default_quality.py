"""Reject false success/score/history/TT claims in the published research packet."""
from pathlib import Path
import hashlib,json,shutil
import pytest
from scripts.verify_leaper_default_history_panel import qualify,raw
from scripts.verify_leaper_qorder_mechanism_check import qualify as qualify_q

ROOT=Path(__file__).resolve().parents[2]
PACKET=ROOT/'docs/research/data/leaper_default_quality_20261025'
INPUTS=ROOT/'docs/research/data/leaper_ordering_diagnosis_20261025/next-default-panel-inputs.json.gz'

def copy_run(tmp_path,name):
    d=tmp_path/name;d.mkdir()
    for f in ('plan.json','receipt.json'):(d/f).write_bytes((PACKET/name/f).read_bytes())
    (d/'queries.jsonl').write_bytes(raw(PACKET/name/'queries.jsonl'))
    return d

def rows(d):return [json.loads(x)for x in (d/'queries.jsonl').read_text().splitlines()]
def save(d,rr):(d/'queries.jsonl').write_text(''.join(json.dumps(r)+'\n'for r in rr),encoding='utf-8')

def test_published_complete_history_and_both_actor_qualification(tmp_path):
    d=copy_run(tmp_path,'default45');r=qualify(d,INPUTS)
    assert r['queries']==64 and set(r['by_actor'])=={'0','1'}
    assert r['choice_sensitive']['total']==30
    assert 'next-role-p53'in r['wrong']

def test_actual_losing_win_cannot_be_relabelled_success(tmp_path):
    d=copy_run(tmp_path,'default45');rr=rows(d);r=next(r for r in rr if r['key']=='next-role-p53')
    assert not r['preserves_root_value'];r['preserves_root_value']=True;save(d,rr)
    with pytest.raises(AssertionError):qualify(d,INPUTS)

def test_final_main_iteration_score_must_match_observed_iteration(tmp_path):
    d=copy_run(tmp_path,'default45');rr=rows(d);assert rr[0]['decision']['result_source']=='main_iteration'
    rr[0]['decision']['score']+=1;save(d,rr)
    with pytest.raises(AssertionError):qualify(d,INPUTS)

def test_missing_registered_slot_rejected(tmp_path):
    d=copy_run(tmp_path,'default45');save(d,rows(d)[:-1])
    with pytest.raises(AssertionError):qualify(d,INPUTS)

def test_actor_flip_rejected(tmp_path):
    d=copy_run(tmp_path,'default45');rr=rows(d);r=next(r for r in rr if r['actor']==1);r['actor']=0;save(d,rr)
    with pytest.raises(AssertionError):qualify(d,INPUTS)

def test_root_history_cannot_be_truncated_even_with_rehashed_input(tmp_path):
    d=copy_run(tmp_path,'default45');inp=json.loads(raw(INPUTS));assert inp['cases'][1]['record']['actions']
    inp['cases'][1]['record']['actions'].pop();p=tmp_path/'changed-inputs.json';p.write_text(json.dumps(inp),encoding='utf-8')
    reg=json.loads((d/'plan.json').read_text());reg['inputs_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();(d/'plan.json').write_text(json.dumps(reg),encoding='utf-8')
    with pytest.raises(AssertionError):qualify(d,p)

def test_tt_depth_partition_cannot_hide_missing_hits(tmp_path):
    d=copy_run(tmp_path,'qorder');rr=rows(d);hist=rr[0]['TT_depth_delta'];key=next(iter(hist));hist[key]+=1;save(d,rr)
    with pytest.raises(AssertionError):qualify_q(d,INPUTS)
