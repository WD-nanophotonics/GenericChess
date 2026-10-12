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


@pytest.mark.parametrize('reason', ['user_decision', 'runtime_limit'])
def test_old_4551_or_generic_prose_cannot_finish_as_hard_blocker(workspace, reason):
    path, _ = workspace
    session.start()
    with pytest.raises(LocalFlowError, match='current JSON'):
        session.finish(reason, 'old WinError4551; wait for a path')
    assert session.status()['state'] == 'active'
    assert not (path/'session_receipts.json').exists()


def blocker_record(workspace, reason):
    path, moment = workspace
    current = session.start()
    data = dict(session_id=current['id'], observed_at=moment[0].isoformat())
    if reason == 'user_decision':
        data.update(diagnosis_status='confirmed', serious_user_required=True,
            diagnosis='Application control requires a human-owned policy choice',
            checks_attempted=['Read actual target CodeIntegrity event and signature'],
            why_agent_cannot_resolve='Agent lacks authority to change system security',
            required_user_action='Choose the stated system security setting and report completion',
            user_report_text='Concrete cause, impact and required step have been sent',
            user_report_reference='current-chat-delivered-message-fixture',
            user_reported_at=moment[0].isoformat())
    else:
        data.update(runtime_exhausted=True, runtime_category='forced_runtime_shutdown',
            actual_runtime_event='Current environment forcibly shut down execution')
    (path/'blocking.json').write_text(json.dumps(data))
    return path, moment, data


@pytest.mark.parametrize('reason', ['user_decision', 'runtime_limit'])
def test_current_diagnosed_report_or_actual_runtime_event_can_end(workspace, reason):
    path, _, _ = blocker_record(workspace, reason)
    result = session.finish(reason, 'blocking.json')
    assert result['state'] == 'ended' and not result['duration_gate_passed']


@pytest.mark.parametrize('change', [
    {'diagnosis_status': 'unknown'}, {'serious_user_required': False},
    {'checks_attempted': []}, {'checks_attempted': 'only an old error'},
    {'why_agent_cannot_resolve': ''}, {'required_user_action': ''},
    {'user_report_text': ''}, {'user_report_reference': ''},
    {'session_id': 'old-session'}, {'observed_at': '2026-10-03T00:00:00+00:00'},
    {'user_reported_at': '2026-10-03T00:00:00+00:00'},
])
def test_user_decision_requires_current_diagnosis_and_already_reported_action(workspace, change):
    path, _, data = blocker_record(workspace, 'user_decision')
    data.update(change)
    (path/'blocking.json').write_text(json.dumps(data))
    with pytest.raises(LocalFlowError, match='blocking evidence'):
        session.finish('user_decision', 'blocking.json')
    assert session.status()['state'] == 'active'


@pytest.mark.parametrize('change', [
    {'runtime_exhausted': False}, {'runtime_category': 'program_launch_failure'},
    {'runtime_category': 'planned_batch_budget'}, {'actual_runtime_event': ''},
    {'session_id': 'old-session'}, {'observed_at': '2026-10-03T00:00:00+00:00'},
])
def test_program_error_or_old_record_is_not_environment_exhaustion(workspace, change):
    path, _, data = blocker_record(workspace, 'runtime_limit')
    data.update(change)
    (path/'blocking.json').write_text(json.dumps(data))
    with pytest.raises(LocalFlowError, match='blocking evidence'):
        session.finish('runtime_limit', 'blocking.json')
    assert session.status()['state'] == 'active'


def test_scientific_complete_is_not_an_early_exit_loophole(workspace):
    session.start()
    with pytest.raises(LocalFlowError, match='before60'):
        session.finish('scientific_complete', 'a small assigned check completed')
    assert session.status()['state'] == 'active'
