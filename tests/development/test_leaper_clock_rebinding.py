"""Closure and full-history guards for reuse across changed draw clocks."""
from copy import deepcopy
from pathlib import Path
import json,time
from collections import Counter
import pytest

from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.generic_session_certificate_json import decode_session_certificate
from scripts.generic_session_win_proof import verify_session_certificate
from scripts.leaper_single_parity_truth import admit,bare_opponent_bound
from scripts.leaper_clock_rebinding import check_domain,expand
from scripts.leaper_explorer_truth import load
from scripts.verify_leaper_single_parity import literal_value

P=Path('docs/research/data/leaper_single_parity_20261023')


@pytest.fixture(scope='module')
def data():return load(P/'inputs.json.gz')


def test_missing_closure_vertex_cannot_be_unknown_or_draw(data):
    cert=load(P/'clock-domain.json.gz');cert['positions'].pop(0)
    with pytest.raises(ValueError,match='closure missing'):
        check_domain(cert,data['worlds'])


def test_same_mask_different_rule_clock_is_not_automatic_binding(data):
    cert=load(P/'clock-domain.json.gz');cert['target_rule']['max_ply']=128
    with pytest.raises(ValueError,match='dynamic declaration mismatch'):
        check_domain(cert,data['worlds'])


def test_history_replay_does_not_accept_an_edited_counter_snapshot(data):
    ws=deepcopy(data['worlds']);ws[20]['initial_state']['repetition_counts'][0][1]=3
    with pytest.raises(ValueError,match='complete target state mismatch'):
        check_domain(load(P/'clock-domain.json.gz'),ws)


def test_duplicate_vertex_rejected(data):
    cert=load(P/'clock-domain.json.gz');cert['positions'].append(cert['positions'][0])
    with pytest.raises(ValueError,match='duplicate domain'):
        check_domain(cert,data['worlds'])


def test_literal_all_defense_certificate_cannot_drop_reply(data):
    row=load(P/'clock-rebinding.json.gz')['rows'][0];raw=deepcopy(row['literal_win_certificate'])
    # Root is the winner's OR move; its child is the defender's AND node.
    defender=raw['tree']['edges'][0]['child']
    assert len(defender['edges'])>1
    defender['edges'].pop()
    _,c,_=admit(data['worlds'][20]['rule'],require_parity=False)
    session,certificate=decode_session_certificate(c,raw)
    assert not verify_session_certificate(session,certificate,max_nodes=8192,seconds=30)['verified']


@pytest.mark.parametrize('index',[0,1,2,3])
def test_literal_clock_boundary_with_or_without_actual_count_three(index):
    row=load(P/'clock-controls.json.gz')['rows'][index]
    _,c,_=admit(row['rule'],require_parity=False)
    session=GameSession.replay(c,deserialize_game_record(json.dumps(row['record'])))
    assert max(n for key,n in session.state.repetition_counts)==(3 if row['loops']else 1)
    counts=Counter()
    assert literal_value(session,counts,start=time.perf_counter())==row['value']==(0 if row['remaining']==4 else 1)


def test_bare_opponent_can_never_win_but_mixed_A_is_not_automatically_winning(data):
    w=data['worlds'][24];_,c,_=admit(w['rule'],require_parity=False)
    assert bare_opponent_bound(GameSession(c).state.position)==[0,1]
    row=load(P/'truth.json.gz')['rows'][24]
    assert row['wdl_bounds']==[0,1]and row['cooperative_decisive']is None
