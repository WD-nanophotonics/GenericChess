import hashlib,json
from fractions import Fraction as F
from pathlib import Path
from scripts.chess_exact_contact_family import exact_chess_contact_intervals
from scripts.shogi_exact_twenty_family import exact_twenty_intervals
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'docs/research/data'
def test_frozen_vectors_keep_two_laws_common_scales_and_all_modes():
    r=json.loads((DATA/'exact_contact_vectors_20261005.json').read_text())
    assert r['complete'] and not r['admitted_official_prior']
    for law,values in r['vectors'].items():
        for game,fn,count in (('chess',exact_chess_contact_intervals,5),('shogi',exact_twenty_intervals,20)):
            assert len(values[game]['weights'])==count
            assert values[game]['weights']=={kind+':'+mode:str(lo) for (kind,mode),(lo,hi) in fn(law).items()}
            assert all(0<F(value)<=1 for value in values[game]['weights'].values())
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin

def test_complete_new_root_rejects_checked_child_without_subsetting():
    r=json.loads((DATA/'shogi_exact_family_execution_20261005.json').read_text())
    assert r['complete'] and len(r['children'])==69 and r['public_transitions']==69 and r['enumerated']==4830
    assert r['checked_children']==['sem_00_standard_drop_contract:g72:P@i8']
    for key in ('old_strict','new_strict'):
        assert not r[key]['complete'] and r[key]['selected'] is None
        assert all(v['reason']=='checked leaf outside deployment scope' for v in r[key]['by_law'].values())
    for law,row in r['approximate_checked_ablation'].items():
        assert len(row['scores'])==69 and len(row['tie_set'])==63
        assert row['selected']=='sem_00_standard_drop_contract:g72:P@a1'
        assert r['checked_children'][0] in row['tie_set']
        assert set(row['tie_set'])=={k for k,v in row['scores'].items() if v==row['score']}
        weights=exact_twenty_intervals(law)
        quiet={F(v) for k,v in row['scores'].items() if k not in row['tie_set']}
        assert len(quiet)==1
        assert F(row['score'])-next(iter(quiet))==(weights['board','P'][0]-weights['hand','P'][0])/39
    assert len(r['unit_ablation']['scores'])==69
    assert len(set(r['unit_ablation']['scores'].values()))==1
    assert r['source_queries']==0 and r['seconds']+0.110<15
    for path,pin in r['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
