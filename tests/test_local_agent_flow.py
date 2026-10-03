import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import pytest
from tools.local_agent import advice, cli, git_ops
from tools.local_agent.common import LocalFlowError

@pytest.fixture
def env(tmp_path, monkeypatch):
    state = tmp_path / '.local_agent'
    monkeypatch.setattr(advice, 'ROOT', tmp_path)
    monkeypatch.setattr(advice, 'STATE', state)
    monkeypatch.setattr(advice, 'LEDGER', state / 'ledger.json')
    monkeypatch.setattr(advice, 'CONFIG', state / 'advisor.json')
    monkeypatch.setattr(advice, 'now', lambda: datetime(2026, 10, 3, 10, 0, tzinfo=timezone(timedelta(hours=9))))
    advice.write_json(advice.CONFIG, {'transport': 'native', 'thread_id': 'target', 'project_id': 'project',
                                    'enabled': True, 'quota_status': 'verified_no_extra_worker'})
    question = tmp_path / 'question.txt'; question.write_text('What is the smallest independent theoretical question?')
    return tmp_path, question

def snapshot(env, request, *, status='completed', reply='Useful advice', truncated=False, target='target', error=None):
    root, _ = env
    text = Path(request['message_file']).read_text(encoding='utf-8')
    data = {'thread': {'id': target, 'kind': 'chatgpt'}, 'turns': [{'id': 'turn', 'status': status, 'error': error,
            'items': [{'type': 'userMessage', 'content': [{'type': 'text', 'text': text}]},
                      {'type': 'agentMessage', 'id': 'response', 'text': reply, 'truncated': truncated}]}]}
    path = root / 'snapshot.json'; path.write_text(json.dumps(data), encoding='utf-8')
    return path

def complete(env, record):
    return advice.reconcile_snapshot(record['request_id'], snapshot(env, record))

def test_daily_weekend_dedup_and_distinct_on_demand(env):
    root, question = env
    first = advice.consult(question, daily=True)
    assert first['daily'] and first['date'] == '2026-10-03'
    assert advice.consult(question)['request_id'] == first['request_id']
    complete(env, first)
    question.write_text('A different independently bounded question.')
    assert advice.consult(question, daily=True)['state'] == 'DAILY_ALREADY_RESERVED'
    assert advice.consult(question)['request_id'] != first['request_id']

def test_daily_before_ten_is_not_due(env, monkeypatch):
    monkeypatch.setattr(advice, 'now', lambda: datetime(2026, 10, 3, 9, 59, tzinfo=timezone(timedelta(hours=9))))
    assert advice.consult(env[1], daily=True)['state'] == 'NOT_DUE'
    assert advice.consult_status()['state'] == 'NEVER_SENT'

def test_pending_requires_reconcile_without_blocking_local_note(env, monkeypatch):
    first = advice.consult(env[1]); advice.begin_send(first['request_id'])
    env[1].write_text('A new question cannot bypass uncertain delivery.')
    with pytest.raises(LocalFlowError, match='pending'):
        advice.consult(env[1])
    monkeypatch.setattr(cli, 'ACTIVITY', env[0] / 'activity.json')
    monkeypatch.setattr(cli, 'git', lambda *_: 'a' * 40)
    assert cli.note('An independent bounded research observation')['summary']

def test_send_is_durable_and_never_repeats(env):
    request = advice.consult(env[1])
    action = advice.begin_send(request['request_id'])
    assert action['action'] == 'send_message_to_thread'
    assert advice.consult_status()['state'] == 'SEND_UNCERTAIN'
    assert advice.begin_send(request['request_id'])['action'] == 'read_thread'

def test_quota_unknown_prevents_send(env):
    config = advice.read_json(advice.CONFIG); config['quota_status'] = 'unverified'; advice.write_json(advice.CONFIG, config)
    request = advice.consult(env[1])
    assert advice.begin_send(request['request_id'])['action'] == 'CAPABILITY_PENDING'
    assert advice.consult_status()['state'] == 'PREPARED'

def test_changed_payload_and_target_are_rejected(env):
    request = advice.consult(env[1]); message = Path(request['message_file']); original = message.read_text()
    message.write_text(original + 'changed')
    with pytest.raises(LocalFlowError, match='payload'):
        advice.begin_send(request['request_id'])
    message.write_text(original)
    config = advice.read_json(advice.CONFIG); config['thread_id'] = 'different'; advice.write_json(advice.CONFIG, config)
    with pytest.raises(LocalFlowError, match='target'):
        advice.begin_send(request['request_id'])

@pytest.mark.parametrize('status,truncated,error', [('running', False, None), ('completed', True, None),
                                                  ('completed', False, 'login required')])
def test_partial_generating_or_failed_reply_is_not_accepted(env, status, truncated, error):
    request = advice.consult(env[1]); advice.begin_send(request['request_id'])
    result = advice.reconcile_snapshot(request['request_id'], snapshot(env, request, status=status, truncated=truncated, error=error))
    assert result['state'] != 'COMPLETED' and result['resend_permitted'] is False

def test_exact_anchor_accepts_useful_reply_without_footer(env):
    request = advice.consult(env[1]); advice.begin_send(request['request_id'])
    result = complete(env, request)
    assert result['state'] == 'COMPLETED'
    assert Path(result['response_file']).read_text() == 'Useful advice'
    assert advice.record_decision(request['request_id'], 'defer', 'Already tested this frontier witness')['evaluation']['decision'] == 'defer'

def test_wrong_target_and_conflicting_id_do_not_complete(env):
    request = advice.consult(env[1]); advice.begin_send(request['request_id'])
    with pytest.raises(LocalFlowError, match='different target'):
        advice.reconcile_snapshot(request['request_id'], snapshot(env, request, target='other'))
    with pytest.raises(LocalFlowError, match='conflicts'):
        advice.reconcile_snapshot(request['request_id'], snapshot(env, request, reply='REQUEST_ID=another\nAdvice'))

def test_missing_history_never_permits_resend(env):
    request = advice.consult(env[1]); advice.begin_send(request['request_id'])
    path = env[0] / 'snapshot.json'; path.write_text(json.dumps({'thread': {'id': 'target', 'kind': 'chatgpt'}, 'turns': []}))
    result = advice.reconcile_snapshot(request['request_id'], path)
    assert result['state'] == 'SEND_UNCERTAIN' and result['resend_permitted'] is False

def test_non_chat_target_and_worker_activity_rejected(env):
    request = advice.consult(env[1])
    path = snapshot(env, request); data = json.loads(path.read_text()); data['thread']['kind'] = 'codex'; path.write_text(json.dumps(data))
    with pytest.raises(LocalFlowError, match='ChatGPT'):
        advice.reconcile_snapshot(request['request_id'], path)
    data['thread']['kind'] = 'chatgpt'; data['turns'][0]['items'].append({'type': 'workerTask'}); path.write_text(json.dumps(data))
    with pytest.raises(LocalFlowError, match='tool/task'):
        advice.reconcile_snapshot(request['request_id'], path)

def test_code_package_is_hashed_and_cannot_read_outside_root(env):
    root, question = env; code = root / 'engine.py'; code.write_text('value = 1\n')
    request = advice.consult(question, code_files=[code])
    assert request['code'][0]['sha256'] == advice.sha(code.read_bytes())
    assert 'value = 1' in Path(request['message_file']).read_text()
    outside = root.parent / 'outside-code.py'; outside.write_text('secret')
    with pytest.raises(LocalFlowError, match='inside'):
        advice.consult(question, code_files=[outside])

def test_publish_refuses_divergence_before_tests(monkeypatch):
    monkeypatch.setattr(git_ops, '_check_branch', lambda *_: None)
    monkeypatch.setattr(git_ops, '_tests', lambda *_: pytest.fail('must not run tests'))
    monkeypatch.setattr(git_ops, 'git', lambda *args, **_: ('a' * 40 if args == ('rev-parse', 'origin/sandbox') else 'b' * 40))
    monkeypatch.setattr(git_ops, 'run', lambda *_, **__: 'c' * 40)
    with pytest.raises(LocalFlowError, match='diverged'):
        git_ops.publish(['tests/test_session.py'])

def test_single_checkout_promotion_fast_forwards_local_origin(tmp_path, monkeypatch):
    origin = tmp_path / 'origin.git'; repo = tmp_path / 'new-checkout'; repo.mkdir()
    def run(*args, cwd=repo):
        return subprocess.check_output(['git', '-c', 'core.autocrlf=false', *args], cwd=cwd, stderr=subprocess.STDOUT).decode().strip()
    run('init', '--bare', str(origin)); run('init'); run('config', 'user.name', 'Transport test'); run('config', 'user.email', 'test@example.invalid')
    run('checkout', '-b', 'master'); (repo / 'a.txt').write_text('base'); run('add', '.'); run('commit', '-m', 'base'); run('remote', 'add', 'origin', str(origin)); run('push', 'origin', 'master')
    run('checkout', '-b', 'sandbox'); (repo / 'a.txt').write_text('candidate'); run('add', '.'); run('commit', '-m', 'candidate'); run('push', 'origin', 'sandbox'); candidate = run('rev-parse', 'HEAD')
    monkeypatch.setattr(git_ops, 'ROOT', repo)
    monkeypatch.setattr(git_ops, 'git', lambda *args, cwd=repo: run(*args, cwd=cwd))
    monkeypatch.setattr(git_ops, '_tests', lambda *_: None)
    assert git_ops.promote(candidate, ['bounded-test'])['promoted_sha'] == candidate
    assert run('rev-parse', 'master') == candidate and run('branch', '--show-current') == 'sandbox'
