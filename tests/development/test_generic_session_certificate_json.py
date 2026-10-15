"""Actual typed proof artifacts replay without invoking a proof search."""
from copy import deepcopy
import json
import pytest
from scripts.generic_session_win_proof_pn import prove_session_win_pn
from scripts.generic_session_win_proof import verify_session_certificate,SessionStrategyCursor,execute
from scripts.generic_session_certificate_json import export_session_certificate,decode_session_certificate
from generic_chess.session.result import SessionStatus
from test_generic_session_win_proof import session,claim


@pytest.mark.parametrize('defender',[False,True])
def test_json_roundtrip_preserves_real_session_and_complete_strategy(defender):
    current=session(claim(1,'LOSS'),k=0,b=2,r=10,turn=1) if defender else session(claim(0,'WIN'))
    result=prove_session_win_pn(current,target=0,max_nodes=65536,seconds=3.,max_depth=8)
    assert result.status=='PROVEN_WIN'
    raw=json.loads(json.dumps(export_session_certificate(current,result.certificate),sort_keys=True))
    replayed,certificate=decode_session_certificate(current.compiled,raw)
    assert replayed.to_record()==current.to_record() and replayed.state==current.state and certificate==result.certificate
    assert verify_session_certificate(replayed,certificate,seconds=3.)['verified']
    cursor=SessionStrategyCursor(replayed,certificate,seconds=3.)
    while replayed.result.status is SessionStatus.ONGOING:
        choice=cursor.choose(replayed) if replayed.state.position.side_to_move==0 else cursor.node.edges[0][0]
        cursor.commit(replayed,choice)
    assert replayed.result.winner==0 and current.result.status is SessionStatus.ONGOING


@pytest.mark.parametrize('corruption',['version_bool','target_bool','rank_bool','winner_bool','mixed_choice','unknown_choice','root_hash','record_schema_bool','missing_defense'])
def test_corrupt_json_never_becomes_an_accepted_proof(corruption):
    current=session(claim(1,'LOSS'),k=0,b=2,r=10,turn=1)
    certificate=prove_session_win_pn(current,target=0,max_nodes=65536,seconds=3.,max_depth=8).certificate
    raw=deepcopy(export_session_certificate(current,certificate))
    if corruption=='version_bool':raw['schema_version']=True
    elif corruption=='target_bool':raw['target']=False
    elif corruption=='rank_bool':raw['tree']['rank']=True
    elif corruption=='winner_bool':raw['tree']['edges'][0]['child']['terminal']['winner']=False
    elif corruption=='mixed_choice':raw['tree']['edges'][0]['choice']['action']={'kind':'pass'}
    elif corruption=='unknown_choice':raw['tree']['edges'][0]['choice']['kind']='MAGIC_WIN'
    elif corruption=='root_hash':raw['root_state_repr_sha256']='0'*64
    elif corruption=='record_schema_bool':raw['root_record']['schema_version']=True
    elif corruption=='missing_defense':raw['tree']['edges']=raw['tree']['edges'][1:]
    try:replayed,decoded=decode_session_certificate(current.compiled,raw)
    except ValueError:return
    assert not verify_session_certificate(replayed,decoded,seconds=3.)['verified']


def test_transport_limits_fail_without_running_a_prover():
    current=session(claim(0,'WIN'));cert=prove_session_win_pn(current,max_depth=1,seconds=3.).certificate
    raw=export_session_certificate(current,cert)
    with pytest.raises(ValueError,match='limit'):decode_session_certificate(current.compiled,raw,max_nodes=1)
    with pytest.raises(ValueError,match='limit'):export_session_certificate(current,cert,max_nodes=1)
