"""Actual-history boundaries for the frozen trajectory observers."""
import json,gzip
from pathlib import Path
from dataclasses import replace
import pytest
from scripts import leaper_design as L
from scripts.leaper_explorer_truth import load
from scripts.leaper_twoa_trajectory_truth import FrozenHistoryTruth
from scripts.leaper_twoa_trajectory_capacity import CooperativeCapacity
from scripts.verify_leaper_twoa_graph import verify
from scripts.verify_leaper_twoa_safety import admission,SOURCE

BASE=Path('docs/research/data/leaper_scope_and_headroom_20261024')
POLICY=Path('docs/research/data/leaper_component_policy_20261024/packet.json.gz')

@pytest.fixture(scope='module')
def observers():
    packet=load(BASE/'twoa-graph.json.gz');source=load(SOURCE);c,_=admission(packet,source)
    receipt,g=verify(packet,source,return_graph=True)
    assert receipt['counts']['Core_vertices']==125940
    return c,FrozenHistoryTruth(packet,g,c),CooperativeCapacity(g,c)

def replay(c,record):return L.GameSession.replay(c,L.deserialize_game_record(json.dumps(record)))

def test_physical_draw_safety_does_not_mean_no_cooperative_mate(observers):
    c,truth,capacity=observers;s=replay(c,load(SOURCE)['worlds'][1]['roots'][0]['record'])
    assert truth.label(s.state)==(0,None,'physical_draw_safety')
    result=capacity.at(s)
    assert result['possible'] and result['distance']==11

def test_same_board_and_clock_cannot_borrow_a_decisive_physical_label(observers):
    c,truth,capacity=observers
    win=replay(c,load(BASE/'twoa-equalclock.json')['record'])
    draw=replay(c,load(BASE/'twoa-barrier-safety.json.gz')['roots'][0]['record'])
    assert win.state.position==draw.state.position and win.state.ply_count==draw.state.ply_count==26
    assert truth.label(win.state)[0]is None and truth.label(draw.state)[0]is None
    assert capacity.at(win)['distance']==3
    assert capacity.at(draw)['distance']==5

def test_last_actual_game_ply_obeys_clock_and_does_not_get_physical_mate_label(observers):
    c,truth,capacity=observers
    docs=json.loads(gzip.decompress(POLICY.read_bytes()))['documents_utf8']
    game=json.loads(docs['forward/game-000.json']);record=game['final_record']
    s=replay(c,record|{'actions':record['actions'][:63]})
    assert s.state.ply_count==63 and not s.state.terminal_status.is_terminal
    assert truth.label(s.state)[0]==0
    result=capacity.at(s)
    assert not result['possible'] and result['basis']=='clock_too_short' and result['distance']>1
    final=replay(c,record)
    assert capacity.at(final)['basis']=='actual_terminal' and truth.label(final.state)[0]==0

def test_missing_complete_history_is_not_a_draw(observers):
    c,truth,_=observers
    s=replay(c,load(BASE/'twoa-equalclock.json')['record'])
    with pytest.raises(ValueError,match='complete history'):
        truth.label(replace(s.state,history=s.state.history[:-1]))

def test_foreign_fingerprint_is_rejected(observers):
    c,truth,_=observers;s=replay(c,load(SOURCE)['worlds'][1]['roots'][0]['record'])
    bad=replace(s.state,position=replace(s.state.position,ruleset_fingerprint='0'*64))
    with pytest.raises(ValueError):truth.label(bad)
