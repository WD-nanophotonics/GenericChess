import gzip,json
import pytest
from scripts.leaper_ab_odd_truth import clock_proof


def graph(path,root_rank=1,winner=0):
    g=dict(positions=[[0,''],[1,''],[0,'']],edges=[[1,2],[],[2]],terminals={'1':winner},relative_values={'0':1,'1':-1,'2':0},ranks={'0':root_rank,'1':0})
    path.write_bytes(gzip.compress(json.dumps(g).encode()));return path


def test_clock_dp_counts_terminal_zero_then_one_step_win_and_fixed_point(tmp_path):
    r=clock_proof(graph(tmp_path/'g.gz'),tmp_path/'proof.json')
    assert [row['WIN']for row in r['rows']]==[1,2]
    assert r['fixed_point_verified']and r['verified']


def test_clock_dp_rejects_false_distance_and_other_winning_seat(tmp_path):
    with pytest.raises(AssertionError):clock_proof(graph(tmp_path/'bad-rank.gz',root_rank=2),tmp_path/'bad-rank.json')
    with pytest.raises(AssertionError):clock_proof(graph(tmp_path/'wrong-seat.gz',winner=1),tmp_path/'wrong-seat.json')
