"""Reject invented quality labels and lost histories in the retained probe."""
import gzip
import json
from pathlib import Path
import pytest
from scripts.verify_leaper_ordering_diagnosis import qualify, load, rows


PACKET=Path(__file__).resolve().parents[2]/'docs/research/data/leaper_ordering_diagnosis_20261025'


def copy_inputs(tmp_path):
    for name in ('ordering-plan.json','prepared.json','ordering-queries.jsonl'):
        src=PACKET/name
        if not src.exists():src=src.with_suffix(src.suffix+'.gz')
        (tmp_path/src.name).write_bytes(src.read_bytes())
    return tmp_path


def test_retained_histories_actions_and_pvs_qualify():
    result=qualify(PACKET)
    assert result['status']=='PASS' and result['retained_queries']==6
    assert result['new_Player_queries']==result['new_graph_or_solver_calls']==0


def test_reader_rejects_lost_complete_history(tmp_path):
    d=copy_inputs(tmp_path);data=load(d/'prepared.json')
    data['cases'][1]['record']['actions'].pop()
    (d/'prepared.json').write_text(json.dumps(data),encoding='utf-8')
    with pytest.raises(AssertionError):qualify(d)


def test_reader_rejects_fabricated_wdl(tmp_path):
    d=copy_inputs(tmp_path);data=rows(d/'ordering-queries.jsonl')
    data[0]['published_child_WDL']=0
    (d/'ordering-queries.jsonl').write_text('\n'.join(json.dumps(r)for r in data)+'\n',encoding='utf-8')
    with pytest.raises(AssertionError):qualify(d)


def test_reader_rejects_missing_planned_query(tmp_path):
    d=copy_inputs(tmp_path);data=rows(d/'ordering-queries.jsonl')
    (d/'ordering-queries.jsonl').write_text('\n'.join(json.dumps(r)for r in data[:-1])+'\n',encoding='utf-8')
    with pytest.raises(AssertionError,match='missing/reordered'):qualify(d)


def test_anywin_reader_rejects_truncated_terminal_proof(tmp_path):
    from scripts.verify_leaper_search_goal_check import qualify as goal_qualify
    source=PACKET/'goal'
    for name in ('plan.json','case.json','receipt.json'):
        (tmp_path/name).write_text(json.dumps(load(source/name)),encoding='utf-8')
    data=rows(source/'queries.jsonl')
    data[0]['decision']['principal_variation'].pop()
    (tmp_path/'queries.jsonl').write_text('\n'.join(json.dumps(r)for r in data)+'\n',encoding='utf-8')
    with pytest.raises(AssertionError):goal_qualify(tmp_path,PACKET)
