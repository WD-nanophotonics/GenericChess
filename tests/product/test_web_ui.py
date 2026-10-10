"""Real Core API contracts and deterministic browser-worker lifecycle tests."""
import asyncio
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
import uuid

import pytest
pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient
from generic_chess.ui.web.app import create_app
from generic_chess.ui.web.models import GameConfig, Operation
from generic_chess.ui.web.service import GameService, GameError

@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as c:
        yield c


def new(client, kind="western_chess", mode="pvp", human=0):
    r = client.post("/api/games", json={"config": {"kind":kind,"mode":mode,"human":human,"think_seconds":.5}})
    assert r.status_code == 200, r.text
    return r.json()


def op(client, state, kind, **extra):
    return client.post(f"/api/games/{state['id']}/operations", json={"kind":kind,
        "expected_revision":state["revision"],"request_id":uuid.uuid4().hex,**extra})


def poll(client, game_id, predicate, timeout=8):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        state=client.get(f"/api/games/{game_id}").json()
        if predicate(state): return state
        time.sleep(.01)
    raise AssertionError(f"state did not settle: {state}")


@pytest.mark.parametrize("kind", ["western_chess","standard_shogi","generated","hybrid"])
@pytest.mark.parametrize("human", [0,1])
def test_real_pve_roundtrip_restore_restart(client, tmp_path, kind, human):
    state=new(client, kind, "pve", human)
    if human==1:
        state=poll(client,state["id"],lambda s:s["ply"]==1 and not s["ai"]["thinking"])
    assert state["actions"]
    state=op(client,state,"action",action_id=state["actions"][0]["id"]).json()
    state=poll(client,state["id"],lambda s:s["ply"]>=2 and not s["ai"]["thinking"] and not s["ai"]["queued"])
    assert state["result"]["status"]=="ongoing"
    bundle=client.get(f"/api/games/{state['id']}/export/bundle").json()
    record=client.get(f"/api/games/{state['id']}/export/record").json()
    original_squares=state["squares"]
    state=op(client,state,"import",format="bundle",content=bundle).json()
    assert state["ply"]==len(record["actions"])
    assert state["squares"]==original_squares
    state=op(client,state,"suspend").json()
    service=GameService(tmp_path)
    try:
        recovered=service.get(state["id"])
        assert not recovered.active and recovered.task is None
        assert json.loads(recovered.controller.record_text())==record
        assert recovered.config.human==human
        assert recovered.snapshot()["squares"]==state["squares"]
    finally:
        service.executor.shutdown()
    state=op(client,state,"resume").json()
    state=op(client,state,"restart").json()
    assert state["ply"]==0


def test_action_versions_idempotency_and_foreign_action(client):
    state=new(client)
    body={"kind":"action","expected_revision":state["revision"],"request_id":"unique",
          "action_id":state["actions"][0]["id"]}
    url=f"/api/games/{state['id']}/operations"
    moved=client.post(url,json=body)
    assert moved.status_code==200 and moved.json()["ply"]==1
    again=client.post(url,json=body)
    assert again.status_code==200 and again.json()["ply"]==1
    body["action_id"]="invalid"
    assert client.post(url,json=body).status_code==409
    stale=op(client,state,"restart")
    assert stale.status_code==409 and stale.json()["state"]["ply"]==1
    state=moved.json()
    assert op(client,state,"action",action_id="made-up-action").status_code==400
    assert client.get(f"/api/games/{state['id']}").json()["revision"]==state["revision"]


def test_invalid_import_preserves_live_game_and_rules_record_pair(client):
    state=new(client,"generated")
    moved=op(client,state,"action",action_id=state["actions"][0]["id"]).json()
    for fmt,content in [("record","{broken"),("rules",{"invalid":1}),("bundle",{})]:
        r=op(client,moved,"import",format=fmt,content=content)
        assert r.status_code==400
        assert r.json()["state"]==moved
    other=client.post('/api/games',json={'config':{'kind':'generated','seed':43,'mode':'pvp'}}).json()
    record=client.get(f"/api/games/{other['id']}/export/record").json()
    assert op(client,moved,"import",format="record",content=record).status_code==400
    rules=client.get(f"/api/games/{state['id']}/export/rules").json()
    imported=op(client,moved,"import",format="rules",content=rules).json()
    assert imported["fingerprint"]==state["fingerprint"] and imported["ply"]==0


def test_history_readonly_and_terminal_resignation(client):
    state=new(client)
    state=op(client,state,"action",action_id=state["actions"][0]["id"]).json()
    state=op(client,state,"history",ply=0).json()
    assert state["displayed_ply"]==0 and not state["actions"]
    assert op(client,state,"resign").status_code==400
    assert op(client,state,"action",action_id="invalid").status_code==400
    state=op(client,state,"live").json()
    assert state["actions"] and state["displayed_ply"] is None
    state=op(client,state,"resign").json()
    assert state["result"]=={"status":"resignation","winner":0}
    assert not state["actions"] and not state["can_undo"]
    state=op(client,state,"restart").json()
    assert state["result"]["status"]=="ongoing" and state["ply"]==0


def test_rules_promotion_drop_and_textures(client):
    from conftest import T, king_type, make_ruleset
    from generic_chess.core.movement import LeapAtom, RayAtom
    from generic_chess.rules.serialization import serialize_ruleset
    state=new(client)
    pawn=T("P",LeapAtom((0,1)),is_promotable=True,targets=("G",))
    gold=T("G",LeapAtom((1,0)),LeapAtom((-1,0)),LeapAtom((0,-1)))
    rules=make_ruleset(8,[king_type(),pawn,gold],auto_promotion=True,
                      lines=[".......k","....P...","........","........","........","........","........","K......."])
    state=op(client,state,"import",format="rules",content=serialize_ruleset(rules)).json()
    promotion=next(a for a in state["actions"] if a["action"].get("promotion_target_id"))
    state=op(client,state,"action",action_id=promotion["id"]).json()
    assert any(s["piece"] and s["piece"]["promoted"] for s in state["squares"])
    assert client.get(f"/api/games/{state['id']}/textures/G/0.svg").headers["content-type"].startswith("image/svg+xml")
    rook=T("R",RayAtom((0,1)),RayAtom((0,-1)),RayAtom((1,0)),RayAtom((-1,0)))
    rules=make_ruleset(4,[king_type(),rook],lines=["...k","....","r...","R..K"])
    state=op(client,state,"import",format="rules",content=serialize_ruleset(rules)).json()
    capture=next(a for a in state["actions"] if a["action"].get("from")==[0,0] and a["action"].get("to")==[0,1])
    state=op(client,state,"action",action_id=capture["id"]).json()
    assert state["hands"][0]==[{"type_id":"R","count":1}]
    state=op(client,state,"action",action_id=state["actions"][0]["id"]).json()
    drop=next(a for a in state["actions"] if a["action"]["kind"] in ("drop","semantic_drop"))
    state=op(client,state,"action",action_id=drop["id"]).json()
    assert not state["hands"][0]


def test_websocket_initial_updates_and_reconnect(client):
    state=new(client)
    url=f"/api/games/{state['id']}/events"
    with client.websocket_connect(url) as ws:
        assert ws.receive_json()["revision"]==state["revision"]
        changed=op(client,state,"action",action_id=state["actions"][0]["id"]).json()
        assert ws.receive_json()["ply"]==1
    with client.websocket_connect(url) as ws:
        assert ws.receive_json()["revision"]==changed["revision"]


def test_loopback_origin_and_validation(client):
    assert client.post('/api/games',json={},headers={'Origin':'https://attacker.example'}).status_code==403
    assert client.post('/api/games',json={'config':{'board_size':100}}).status_code==422
    assert client.get('/api/games/../../unknown').status_code==404


@pytest.mark.parametrize("kind", ["undo","restart","history","import","suspend"])
def test_cancelled_worker_cannot_commit_old_action(tmp_path,monkeypatch,kind):
    started=threading.Event(); release=threading.Event()
    def choose(session, limits, cancel_token):
        action=session.legal_actions()[0]
        started.set()
        assert release.wait(3)
        return SimpleNamespace(action=action)
    monkeypatch.setattr('generic_chess.ui.web.service.create_ui_player',lambda *a,**k:SimpleNamespace(choose_action=choose))
    with TestClient(create_app(tmp_path)) as c:
        state=new(c,mode="pve")
        state=op(c,state,"action",action_id=state["actions"][0]["id"]).json()
        assert started.wait(2)
        state=c.get(f"/api/games/{state['id']}").json()
        data={"history":{"ply":0},"import":{"format":"rules","content":c.get(f"/api/games/{state['id']}/export/rules").json()}}.get(kind,{})
        changed=op(c,state,kind,**data)
        assert changed.status_code==200, changed.text
        if kind=="import":
            # The imported game starts on the human turn, so there is no replacement search.
            assert changed.json()["side_to_move"]==0
        release.set()
        settled=poll(c,state["id"],lambda s:not s["ai"]["thinking"] and not s["ai"]["queued"])
        assert settled["ply"]==(0 if kind in ("undo","restart","import") else 1)


def test_ai_failure_pauses_and_resume_retries(tmp_path,monkeypatch):
    def fail(*a,**k): raise RuntimeError('test failure')
    monkeypatch.setattr('generic_chess.ui.web.service.create_ui_player',lambda *a,**k:SimpleNamespace(choose_action=fail))
    with TestClient(create_app(tmp_path)) as c:
        state=new(c,mode="pve",human=1)
        state=poll(c,state["id"],lambda s:s["ai"]["paused"] and not s["ai"]["queued"])
        assert state["ply"]==0 and state["ai"]["error"]
        monkeypatch.setattr('generic_chess.ui.web.service.create_ui_player',lambda *a,**k:SimpleNamespace(choose_action=lambda session,limits,cancel_token:SimpleNamespace(action=session.legal_actions()[0])))
        c.app.state.service.games[state["id"]].player=None
        state=op(c,state,"resume_ai").json()
        state=poll(c,state["id"],lambda s:s["ply"]==1)
        assert not state["ai"]["error"]


def test_pve_undo_after_reply_returns_to_human_decision(client):
    state=new(client,mode="pve")
    state=op(client,state,"action",action_id=state["actions"][0]["id"]).json()
    state=poll(client,state["id"],lambda s:s["ply"]==2 and not s["ai"]["queued"])
    state=op(client,state,"undo").json()
    assert state["ply"]==0 and state["side_to_move"]==0
    state=new(client,mode="pve",human=1)
    state=poll(client,state["id"],lambda s:s["ply"]==1 and not s["ai"]["queued"])
    assert not state["can_undo"]
    state=op(client,state,"action",action_id=state["actions"][0]["id"]).json()
    state=poll(client,state["id"],lambda s:s["ply"]==3 and not s["ai"]["queued"])
    state=op(client,state,"undo").json()
    assert state["ply"]==1 and state["side_to_move"]==1


def test_corrupt_save_is_reported_and_no_qt_import(client,tmp_path):
    (tmp_path/'bad.json').write_text('{broken')
    assert client.get('/api/games').json()['warning']
    code="import sys; sys.modules['PySide6']=None; from generic_chess.ui.web.app import create_app; from generic_chess.ui.controller import UIController; print('qt-free')"
    run=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
    assert run.returncode==0 and 'qt-free' in run.stdout


def test_service_shutdown_cancels_and_joins_owned_worker(tmp_path,monkeypatch):
    started=threading.Event(); cancelled=threading.Event()
    def choose(session,limits,cancel_token):
        started.set()
        end=time.monotonic()+3
        while not cancel_token.is_cancelled() and time.monotonic()<end:
            time.sleep(.005)
        assert cancel_token.is_cancelled()
        cancelled.set()
        return SimpleNamespace(action=session.legal_actions()[0])
    monkeypatch.setattr('generic_chess.ui.web.service.create_ui_player',lambda *a,**k:SimpleNamespace(choose_action=choose))
    app=create_app(tmp_path)
    with TestClient(app) as c:
        new(c,mode='pve',human=1)
        assert started.wait(2)
    assert cancelled.is_set()
    assert all(not thread.is_alive() for thread in app.state.service.executor._threads)


def test_save_failure_remains_visible_and_bundle_export_works(tmp_path,monkeypatch):
    app=create_app(tmp_path)
    with TestClient(app) as c:
        state=new(c)
        def fail_replace(*a,**k): raise OSError('test disk failure')
        monkeypatch.setattr(Path,'replace',fail_replace)
        changed=op(c,state,'action',action_id=state['actions'][0]['id'])
        assert changed.status_code==200 and changed.json()['storage_error']
        saved=c.get(f"/api/games/{state['id']}/export/bundle").json()
        assert len(saved['record']['actions'])==1
