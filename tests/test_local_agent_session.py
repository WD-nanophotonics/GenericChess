from datetime import datetime, timezone, timedelta
import json

import pytest

from tools.local_agent import session, cli
from tools.local_agent.common import LocalFlowError


MEMO = '''State: scientific objective open
Segment: next start uses session state
Main: q1 | inspect rule1 | report1 | record assumption
Backup1: q2 | inspect code2 | report2 | state scope
Backup2: q3 | fetch paper3 | report3 | give test
Evidence: docs/research/LOCAL_MAINLINE.md
'''


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.setattr(session, 'STATE', tmp_path)
    (tmp_path/'NEXT_WORK.md').write_text(MEMO, encoding='utf-8')
    (tmp_path/'rollout.json').write_text(json.dumps({'thread_id': 'same-chat'}))
    moment = [datetime(2026, 10, 4, tzinfo=timezone.utc)]
    monkeypatch.setattr(session, 'now', lambda: moment[0])
    return tmp_path, moment


def test_compact_resume_preserves_id_start_and_does_not_create_other_writer(workspace):
    path, moment = workspace
    first = session.start()
    moment[0] += timedelta(minutes=20)
    recovered = session.start()
    assert recovered['resumed'] and recovered['id'] == first['id']
    assert recovered['started_at'] == first['started_at']
    (path/'rollout.json').write_text(json.dumps({'thread_id': 'different-chat'}))
    with pytest.raises(LocalFlowError, match='another chat'):
        session.start()


@pytest.mark.parametrize('file,flag', [('rollout.json', 'user_paused'), ('slack.json', 'stopped')])
def test_stop_cannot_be_cleared_by_start_or_checkpoint(workspace, file, flag):
    path, _ = workspace
    session.start()
    (path/file).write_text(json.dumps({flag: True}))
    with pytest.raises(LocalFlowError, match='stop'):
        session.start()
    with pytest.raises(LocalFlowError, match='stop'):
        session.checkpoint('q', 'new finding', 'evidence', 'next')
    result = session.finish('user_stop', 'explicit user stop')
    assert not result['duration_gate_passed']
    assert json.loads((path/file).read_text())[flag]


def test_soft_exit_cannot_be_relabelled_and_early_normal_exit_keeps_active(workspace):
    path, _ = workspace
    session.start()
    for reason in ('inspection', 'publication', 'no_new_reply', 'no_new_formula'):
        with pytest.raises(LocalFlowError, match='ending reason'):
            session.finish(reason, 'old evidence')
    for reason in ('safe_checkpoint', 'no_viable_action'):
        with pytest.raises(LocalFlowError, match='before60'):
            session.finish(reason, 'old alternatives reviewed')
    assert session.status()['state'] == 'active'
    assert not (path/'session_receipts.json').exists()


def test_idle_transport_and_documentation_do_not_pass_duration(workspace):
    _, moment = workspace
    session.start()
    session.checkpoint('q', 'reply transported', 'slack read', 'research next', 'transport')
    session.checkpoint('q', 'manual saved', 'manual', 'research next', 'documentation')
    moment[0] += timedelta(minutes=70)
    with pytest.raises(LocalFlowError, match='alone'):
        session.finish('safe_checkpoint', 'elapsed70')


def test_research_stages_normal_finish_reserve_and_last_three_receipts(workspace):
    path, moment = workspace
    for n in range(4):
        session.start()
        session.checkpoint('question', f'new observation{n}', 'report', 'next action')
        with pytest.raises(LocalFlowError, match='duplicate'):
            session.checkpoint('question', f'new observation{n}', 'report', 'other next')
        moment[0] += timedelta(minutes=61)
        result = session.finish('safe_checkpoint', 'new evidence reviewed; reserve ready')
        assert result['duration_gate_passed'] and result['quality_review_required']
    assert len(json.loads((path/'session_receipts.json').read_text())['receipts']) == 3


@pytest.mark.parametrize('content', [MEMO+'x'*2048, MEMO+'中'*700, MEMO+'\n'*21,
    MEMO.replace('Main:', 'Other:'), MEMO.replace('q1 | inspect rule1 | report1 | record assumption', 'find new principle'),
    MEMO.replace('q2 | inspect code2 | report2 | state scope', 'q1 | inspect rule1 | report1 | record assumption')])
def test_memo_missing_oversized_abstract_or_duplicate_fields_fail(workspace, content):
    path, _ = workspace
    (path/'NEXT_WORK.md').write_text(content, encoding='utf-8')
    with pytest.raises(LocalFlowError):
        session.start()


def test_hard_obstruction_requires_evidence_and_can_end_early(workspace):
    session.start()
    with pytest.raises(LocalFlowError, match='evidence'):
        session.finish('tool_limit', '')
    result = session.finish('tool_limit', 'actual unavailable tool with failure record')
    assert result['state'] == 'ended' and not result['duration_gate_passed']


def test_missing_memo_must_be_rebuilt_before_start(workspace):
    path, _ = workspace
    (path/'NEXT_WORK.md').unlink()
    with pytest.raises(LocalFlowError, match='rebuild memo'):
        session.start()
    assert not (path/'session.json').exists()


def test_cli_dispatch_and_error_exit(workspace, capsys):
    assert cli.main(['session', 'start']) == 0
    assert cli.main(['session', 'finish', '--reason', 'safe_checkpoint', '--evidence', 'too soon']) == 2
    assert 'before60' in capsys.readouterr().err


def test_resume_after_idle_requires_new_research_not_old_checkpoint(workspace):
    _, moment = workspace
    session.start()
    session.checkpoint('old question', 'old finding', 'report', 'next')
    moment[0] += timedelta(hours=2)
    session.start()
    with pytest.raises(LocalFlowError, match='fresh research'):
        session.finish('safe_checkpoint', 'old stage and2hours')
    session.checkpoint('new question', 'new finding', 'new report', 'next')
    assert session.finish('safe_checkpoint', 'new stage reviewed')['quality_review_required']


def test_no_next_exit_requires_two_fresh_alternative_observations(workspace):
    _, moment = workspace
    session.start()
    session.checkpoint('alt1', 'new finding1', 'report1', 'alt2')
    moment[0] += timedelta(minutes=61)
    with pytest.raises(LocalFlowError, match='two distinct'):
        session.finish('no_viable_action', 'old notes', ['alt1', 'unexecuted'])
    session.checkpoint('alt2', 'new finding2', 'report2', 'future exploration')
    assert session.finish('no_viable_action', 'specific new failures', ['alt1', 'alt2'])['state'] == 'ended'
