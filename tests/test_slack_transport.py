import pytest
from tools.local_agent import slack_transport as s, advice
from tools.local_agent.common import LocalFlowError, write_json


@pytest.fixture
def env(tmp_path, monkeypatch):
    for name, value in dict(ROOT=tmp_path, STATE=tmp_path / '.local_agent',
                            CONFIG=tmp_path / 'slack.json', DB=tmp_path / 'inbox.sqlite3').items():
        monkeypatch.setattr(s, name, value)
    monkeypatch.setattr(s, 'git', lambda *_: 'a' * 40)
    c = dict(team_id='T1', channel_id='C1', sender_id='U1', advisor_user_id='U2',
             advisor_bot_id='B2', advisor_app_id='A2', stopped=False,
             dispatch_enabled=True, accepted=True, quota_status='verified_no_extra_worker')
    write_json(s.CONFIG, c)
    q = tmp_path / 'question.txt'; q.write_text('Which small observation tests this claim?')
    return q


def sent(q):
    r = s.consult(q); s.begin_send(r['request_id']); s.bind_sent(r['request_id'], 'C1', '100.1')
    return s.status(r['request_id'])


def event(r, eid='E1', **changes):
    msg = dict(type='message', channel='C1', ts='101.1', thread_ts='100.1', user='U2', bot_id='B2', app_id='A2',
               text=f'TYPE=DOT_REPLY\nREQUEST_ID={r["request_id"]}\nUseful conclusion, with uncertainty.')
    msg.update(changes)
    return dict(team_id='T1', event_id=eid, event=msg)


def test_send_after_crash_never_repeats_and_binding_cannot_change(env):
    r = s.consult(env)
    assert s.begin_send(r['request_id'])['action'] == 'slack_send_message'
    assert s.begin_send(r['request_id'])['action'] == 'slack-reconcile'
    with pytest.raises(LocalFlowError):
        s.bind_sent(r['request_id'], 'Cwrong', '100.1')
    s.bind_sent(r['request_id'], 'C1', '100.1')
    with pytest.raises(LocalFlowError):
        s.bind_sent(r['request_id'], 'C1', '100.2')


def test_duplicate_request_event_reconnect_and_revision_preserve_decision(env):
    r = sent(env); rid = r['request_id']; payload = event(r)
    assert s.consult(env)['request_id'] == rid
    assert s.ingest(payload) == 'STORED'
    assert s.ingest(payload) == 'DUPLICATE'
    assert s.reconcile(rid)['state'] == 'COMPLETED'
    s.decision(rid, 'defer', 'Needs an independent source')
    changed = event(r, 'E2', text=f'TYPE=DOT_REPLY\nREQUEST_ID={rid}\nEdited advice', edited={'ts': '102.1'})
    changed['event'] = dict(type='message', subtype='message_changed', channel='C1', message=changed['event'])
    s.ingest(changed)
    result = s.reconcile(rid)
    assert len(result['revisions']) == 2
    assert result['response'] == payload['event']['text']
    assert result['evaluation']['response_sha256'] == result['response_sha256']
    assert result['revisions'][-1]['agent_read_at']


@pytest.mark.parametrize('changes', [dict(channel='Cwrong'), dict(thread_ts='100.2'),
    dict(user='Uwrong'), dict(bot_id='Bwrong'), dict(app_id='Awrong'),
    dict(text='TYPE=DOT_REPLY\nREQUEST_ID=wrong\nConflict'),
    dict(text='TYPE=DOT_REPLY\nREQUEST_ID=wrong\nREQUEST_ID=duplicate\nConflict'),
    dict(text='TYPE=AGENT_RESULT\nREQUEST_ID=other\nNo new consultation'),
    dict(user='U1')])
def test_wrong_channel_identity_thread_conflict_and_self_reply(env, changes):
    r = sent(env); s.ingest(event(r, **changes))
    assert s.reconcile(r['request_id'])['state'] == 'PENDING'
    assert s.begin_send(r['request_id'])['resend_permitted'] is False


def test_wrong_workspace_and_missing_event_id(env):
    r = sent(env); e = event(r); e['team_id'] = 'Twrong'
    assert s.ingest(e) == 'WRONG_TARGET'
    e['team_id'] = 'T1'; e.pop('event_id')
    assert s.ingest(e) == 'UNSUPPORTED'


def test_uncertain_send_recovers_exact_original_not_another_request(env):
    r = s.consult(env); s.begin_send(r['request_id'])
    e = event(r, user='U1', ts='100.1', thread_ts=None, text=r['message'] + '\n*Sent using* app')
    e['event'].pop('thread_ts')
    s.ingest(e); s.ingest(event(r, 'E2'))
    assert s.reconcile(r['request_id'])['state'] == 'COMPLETED'


def test_stop_persists_blocks_send_and_receive_but_reconcile_still_works(env):
    r = s.consult(env); s.stop()
    assert s.begin_send(r['request_id'])['action'] == 'CAPABILITY_PENDING'
    assert s.ingest(event(r)) == 'STOPPED'
    with pytest.raises(LocalFlowError, match='disabled'):
        s.receive()
    assert s.reconcile(r['request_id'])['state'] == 'PREPARED'
    with pytest.raises(LocalFlowError, match='stopped'):
        s.consult(env)


def test_payload_identity_and_quota_gate(env):
    r = s.consult(env)
    c = s.config(); c['quota_status'] = 'unverified'; write_json(s.CONFIG, c)
    assert s.begin_send(r['request_id'])['action'] == 'CAPABILITY_PENDING'
    c['quota_status'] = 'verified_no_extra_worker'; c['team_id'] = 'Twrong'; write_json(s.CONFIG, c)
    with pytest.raises(LocalFlowError, match='identity'):
        s.begin_send(r['request_id'])


def test_wait_bound_and_pending_does_not_resend(env):
    r = sent(env)
    assert s.wait(r['request_id'], 0)['state'] == 'PENDING'
    with pytest.raises(LocalFlowError, match='300'):
        s.wait(r['request_id'], 301)
    env.write_text('Different question')
    with pytest.raises(LocalFlowError, match='pending'):
        s.consult(env)


def test_single_instance_lock(env):
    with s.receiver_lock():
        with pytest.raises(LocalFlowError, match='already running'):
            with s.receiver_lock():
                pass


def test_selected_transport_routes_existing_interfaces(env, monkeypatch):
    monkeypatch.setattr(advice, 'CONFIG', env.parent / 'advisor.json')
    write_json(advice.CONFIG, {'transport': 'slack'})
    r = advice.consult(env)
    assert advice.consult_status()['request_id'] == r['request_id']
    assert advice.begin_send(r['request_id'])['action'] == 'slack_send_message'
    with pytest.raises(LocalFlowError, match='persisted inbox'):
        advice.reconcile_snapshot(r['request_id'], env)


def test_shared_account_reply_and_role_filter(env):
    c = s.config(); c.update(advisor_user_id='U1', advisor_bot_id=None, advisor_app_id=None)
    write_json(s.CONFIG, c)
    r = sent(env)
    s.ingest(event(r, user='U1', text=f'TYPE=AGENT_RESULT\nREQUEST_ID={r["request_id"]}\nDone'))
    assert s.reconcile(r['request_id'])['state'] == 'PENDING'
    s.ingest(event(r, 'E2', user='U1'))
    assert s.reconcile(r['request_id'])['state'] == 'COMPLETED'


@pytest.mark.parametrize('name', ['SlackApiError', 'SlackClientError', 'TimeoutError'])
def test_receiver_failure_is_sanitized_and_never_clears_stop_or_resends(env, monkeypatch, name):
    cls = type(name, (Exception,), {})
    def fail():
        raise cls('token and authenticated URL must never be logged')
    monkeypatch.setattr(s, '_receive', fail)
    with pytest.raises(LocalFlowError) as exc:
        s.receive()
    assert str(exc.value) == 'receiver failed: ' + name


def test_explicit_receiver_disabled_and_dispatch_acceptance(env):
    r = s.consult(env)
    c = s.config(); c['accepted'] = False; write_json(s.CONFIG, c)
    assert s.begin_send(r['request_id'])['action'] == 'CAPABILITY_PENDING'
    assert s.status(r['request_id'])['state'] == 'PREPARED'
    with pytest.raises(LocalFlowError, match='disabled'):
        s.receive()
