import json
from pathlib import Path
import pytest
from tools.local_agent import slack_mailbox as m, slack_transport as old
from tools.local_agent.common import LocalFlowError, write_json

@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "ROOT", tmp_path)
    monkeypatch.setattr(m, "HOME", tmp_path / ".local_agent/slack/mailbox")
    monkeypatch.setattr(m, "STATE", tmp_path / ".local_agent")
    monkeypatch.setattr(m, "CONFIG", tmp_path / ".local_agent/slack.json")
    monkeypatch.setattr(m, "git", lambda *args: "sidemission" if args[0]=="branch" else "a"*40)
    write_json(m.STATE / "role.json", {"role":"DEV_AUX","branch":"sidemission"})
    write_json(m.CONFIG, {"communication_mode":"chat_mailbox","team_id":"T1","channel_id":"C1","sender_id":"U1"})
    return tmp_path

def snapshot(env, channel=(), threads=None, complete=True):
    value={"team_id":"T1","channel_id":"C1","coverage_complete":complete,
           "channel_pages":[{"messages":list(channel),"pagination_info":"No more messages"}],
           "thread_pages":threads or {}}
    path=env/"snapshot.json";path.write_text(json.dumps(value),encoding="utf-8");return path

def msg(ts="10.1",text="CHAT_Comments: inspect this",user="U2"):
    return {"ts":ts,"text":text,"user":user}


def test_empty_live_channel_rendering_is_recognized():
    page = {'messages': 'Channel: #generic-chess (C0C6L21UU20)\n\n',
            'pagination_info': 'There are no more messages available.\n'}
    assert m.messages(page) == []
    with pytest.raises(LocalFlowError):
        m.messages({'messages': 'Unexpected data: not an empty channel'})

def review_and_prepare(env,r):
    for item in r["comments"]:
        m.decide(r["probe_id"],item["ts"],item["sha256"],"defer","Independent check scheduled")
    f=env/"report.txt";f.write_text("Progress and limits; next independent validation.",encoding="utf-8")
    return m.prepare(r["probe_id"],f)

def test_empty_read_one_send_no_wait_or_old_request_gate(env):
    # The old database can contain pending requests; new mailbox never opens it.
    legacy=m.HOME.parent/"inbox.sqlite3"
    legacy.parent.mkdir(parents=True,exist_ok=True);legacy.write_bytes(b"preserved historical pending ledger")
    r=m.start();r=m.ingest(r["probe_id"],snapshot(env))
    assert legacy.read_bytes()==b"preserved historical pending ledger"
    r=review_and_prepare(env,r)
    assert "RECIPIENT=CHAT" in r["message"] and "<@" not in r["message"]
    assert m.begin_send(r["probe_id"])["action"]=="slack_send_message"
    assert m.begin_send(r["probe_id"])["action"]=="reconcile_at_next_probe"
    receipt=env/"receipt.json";receipt.write_text('{"channel_id":"C1","message_ts":"11.1"}')
    m.bind(r["probe_id"],"11.1",receipt)
    assert m.start()["probe_id"]!=r["probe_id"]

def test_unreviewed_then_deferred_comment_and_edit(env):
    r=m.start();r=m.ingest(r["probe_id"],snapshot(env,[msg()]))
    f=env/"report.txt";f.write_text("progress")
    with pytest.raises(LocalFlowError,match="unreviewed"):
        m.prepare(r["probe_id"],f)
    item=r["comments"][0]
    m.decide(r["probe_id"],item["ts"],item["sha256"],"defer","Needs arithmetic check")
    review_and_prepare(env,m.load(r["probe_id"]))
    m.begin_send(r["probe_id"])
    receipt=env/"receipt.json";receipt.write_text('{"channel_id":"C1","message_ts":"11.1"}')
    m.bind(r["probe_id"],"11.1",receipt)
    second=m.start()
    threads={"11.1":[{"messages":[msg("11.1","agent report","U1")],"pagination_info":"There are no more messages in this thread."}]}
    second=m.ingest(second["probe_id"],snapshot(env,[msg(text="CHAT_Comments: edited")],threads))
    assert any("edited" in x["text"] for x in second["comments"])
    assert (m.HOME/"raw").is_dir()

def test_incomplete_read_raw_saved_without_advancing_cursor(env):
    r=m.start()
    with pytest.raises(LocalFlowError,match="previous boundary"):
        m.ingest(r["probe_id"],snapshot(env,[msg()],complete=False))
    assert list((m.HOME/"raw").glob("*.json"))
    assert "coverage" not in json.loads((m.HOME/"state.json").read_text())

def test_duplicate_read_for_same_probe_rejected(env):
    r=m.start();p=snapshot(env,[msg()])
    m.ingest(r["probe_id"],p)
    with pytest.raises(LocalFlowError,match="already completed"):
        m.ingest(r["probe_id"],p)

def test_uncertain_delivery_reconciles_on_next_read_without_resend(env):
    r=m.start();r=m.ingest(r["probe_id"],snapshot(env))
    r=review_and_prepare(env,r);m.begin_send(r["probe_id"])
    assert m.start()["phase"]=="SEND_UNCERTAIN"
    r=m.ingest(r["probe_id"],snapshot(env,[msg("12.1",r["message"],"U1")]))
    assert r["phase"]=="SENT"
    assert m.begin_send(r["probe_id"])["action"]=="reconcile_at_next_probe"

def test_paginated_relevant_threads_must_finish(env):
    r=m.start()
    state=json.loads((m.HOME/"state.json").read_text());state["required_threads"]=["9.1"]
    write_json(m.HOME/"state.json",state)
    r["required_threads"]=["9.1"];m.save(r)
    pages=[{"messages":[msg()],"pagination_info":"There are more messages available."}]
    with pytest.raises(LocalFlowError,match="pagination"):
        m.ingest(r["probe_id"],snapshot(env,threads={"9.1":pages}))
    pages.append({"messages":[msg("10.2","TYPE=CHAT_REPLY\nLate comment")],"pagination_info":"There are no more messages in this thread."})
    r=m.ingest(r["probe_id"],snapshot(env,threads={"9.1":pages}))
    assert len(r["comments"])==2

def test_dot_payload_and_legacy_dispatch_disabled(env,monkeypatch):
    r=m.start();r=m.ingest(r["probe_id"],snapshot(env))
    f=env/"report.txt";f.write_text("<@U2> please ask Dot")
    with pytest.raises(LocalFlowError,match="Dot"):
        m.prepare(r["probe_id"],f)
    monkeypatch.setattr(old,"CONFIG",m.CONFIG)
    with pytest.raises(LocalFlowError,match="paused"):
        old.consult(f)
    with pytest.raises(LocalFlowError,match="paused"):
        old.begin_send("old-pending")

def test_rendered_channel_and_thread_parser(env):
    channel={"messages":"Channel: test\n=== Message from Person (U2) at time === \nMessage TS: 10.1\nCHAT_Comments hello"}
    thread={"messages":"=== THREAD PARENT MESSAGE ===\nFrom: Person (U2)\nTime: time\nMessage TS: 10.1\nroot\n=== THREAD REPLIES (1 total) ===\n\n--- Reply 1 of 1 ---\nFrom: Person (U2)\nTime: time\nMessage TS: 10.2\nTYPE=CHAT_REPLY\nlate"}
    assert m.messages(channel)[0]["ts"]=="10.1"
    assert len(m.messages(thread))==2


def test_chat_thread_plain_supplement_is_reviewed_but_agent_reply_is_not(env):
    r=m.start()
    pages=[{"messages":[msg("9.1","CHAT_Comments original"),msg("10.1","Correction to my earlier review"),
                        msg("10.2","TYPE=AGENT_MAILBOX_REPORT\nAGENT_ID=DEV_AUX")],
            "pagination_info":"There are no more messages in this thread."}]
    r=m.ingest(r["probe_id"],snapshot(env,threads={"9.1":pages}))
    assert {c["ts"] for c in r["comments"]}=={"9.1","10.1"}

def test_stopped_role_and_unverified_receipt_remain_blocked(env):
    r=m.start();r=m.ingest(r["probe_id"],snapshot(env));review_and_prepare(env,r)
    m.begin_send(r["probe_id"])
    receipt=env/"bad-receipt.json";receipt.write_text("{}")
    with pytest.raises(LocalFlowError,match="receipt does not verify"):
        m.bind(r["probe_id"],"11.1",receipt)
    assert m.load(r["probe_id"])["phase"]=="SEND_UNCERTAIN"
    c=json.loads(m.CONFIG.read_text());c["stopped"]=True;write_json(m.CONFIG,c)
    with pytest.raises(LocalFlowError,match="stopped"):
        m.start()

def test_migration_is_own_role_idempotent_and_preserves_stops_and_ledger(env):
    c=json.loads(m.CONFIG.read_text());c.update(stopped=True,mention_user_id="U2")
    write_json(m.CONFIG,c)
    write_json(m.STATE/"advisor.json",{"enabled":True,"stop_reason":"preserve history"})
    m.migrate()
    backup=(m.HOME/"migration-original-config.json").read_bytes()
    m.migrate()
    assert (m.HOME/"migration-original-config.json").read_bytes()==backup
    c=json.loads(m.CONFIG.read_text())
    assert c["stopped"] is True and c["mention_user_id"] is None
    assert json.loads((m.STATE/"advisor.json").read_text())["enabled"] is False

def test_channel_pages_must_reach_actual_boundary(env):
    write_json(m.HOME/"state.json",{"coverage":"5.1"})
    r=m.start()
    p=snapshot(env,[msg("10.1")])
    d=json.loads(p.read_text());d["channel_pages"][0]["pagination_info"]="There are more messages available."
    p.write_text(json.dumps(d))
    with pytest.raises(LocalFlowError,match="previous coverage boundary"):
        m.ingest(r["probe_id"],p)

def test_unmigrated_config_cannot_accidentally_dispatch_dot(env,monkeypatch):
    c=json.loads(m.CONFIG.read_text());c.pop("communication_mode");write_json(m.CONFIG,c)
    monkeypatch.setattr(old,"CONFIG",m.CONFIG)
    f=env/"question.txt";f.write_text("Historical question")
    with pytest.raises(LocalFlowError,match="Dot consultation is paused"):
        old.consult(f)
