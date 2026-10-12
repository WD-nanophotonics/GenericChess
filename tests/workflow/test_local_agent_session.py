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
    monkeypatch.setattr(session, 'MAINLINE', tmp_path/'mainline.md')
    session.MAINLINE.write_text('Science is OPEN.', encoding='utf-8')
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


@pytest.mark.parametrize('file,flag', [(file, flag)
    for file in ('rollout.json', 'advisor.json', 'slack.json')
    for flag in ('user_paused', 'stopped')])
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


@pytest.mark.parametrize('reason', ['tool_limit', 'quota_limit'])
def test_hard_obstruction_requires_evidence_and_can_end_early(workspace, reason):
    session.start()
    with pytest.raises(LocalFlowError, match='evidence'):
        session.finish(reason, '')
    result = session.finish(reason, 'actual unavailable tool/quota with failure record')
    assert result['state'] == 'ended' and not result['duration_gate_passed']


@pytest.mark.parametrize('reason', ['user_decision', 'runtime_limit'])
def test_old_4551_or_vague_text_is_not_a_completed_handoff(workspace, reason):
    path, _ = workspace
    session.start()
    with pytest.raises(LocalFlowError, match='structured block'):
        session.finish(reason, 'Windows4551; waiting for a usable path')
    assert session.status()['state'] == 'active'
    assert not (path/'session_receipts.json').exists()


def block_report(path, moment):
    current = session.status()
    report = dict(session_id=current['id'], observed_at=moment[0].isoformat(),
                  failure='binary launch rejected with4551',
                  diagnosis='CodeIntegrity3077 identifies SAC enforcement',
                  impact='required engine cannot start',
                  attempted_fixes='checked exact event, signature and normal alternatives',
                  cannot_continue='this required operation needs user intervention',
                  evidence_reference='saved exact project event/launch result')
    target = path/'block.json'
    target.write_text(json.dumps(report), encoding='utf-8')
    return target, report


def test_diagnosis_without_specific_sent_request_stays_active(workspace):
    path, moment = workspace
    session.start()
    target, report = block_report(path, moment)
    with pytest.raises(LocalFlowError, match='already-sent'):
        session.finish('user_decision', str(target))
    report['user_request'] = dict(sent=True, action='user decides system policy change',
                                 reference='saved actual user-visible request',
                                 why_agent_cannot_do_it='system change not authorized')
    target.write_text(json.dumps(report), encoding='utf-8')
    assert session.finish('user_decision', str(target))['state'] == 'ended'


def test_launch_failure_is_not_runtime_exhaustion_but_real_limit_can_exit(workspace):
    path, moment = workspace
    session.start()
    target, report = block_report(path, moment)
    report.update(limit_kind='binary_launch_policy', actual_runtime_exhausted=True)
    target.write_text(json.dumps(report), encoding='utf-8')
    with pytest.raises(LocalFlowError, match='runtime exhaustion'):
        session.finish('runtime_limit', str(target))
    report.update(failure='current execution host shutdown',
                  diagnosis='current host reports execution runtime expired',
                  limit_kind='runtime_expired')
    target.write_text(json.dumps(report), encoding='utf-8')
    assert session.finish('runtime_limit', str(target))['state'] == 'ended'


def test_old_segment_report_cannot_end_new_segment(workspace):
    path, moment = workspace
    session.start()
    target, report = block_report(path, moment)
    report['session_id'] = 'old-segment'
    target.write_text(json.dumps(report), encoding='utf-8')
    with pytest.raises(LocalFlowError, match='current diagnosed'):
        session.finish('runtime_limit', str(target))


def test_resumed_environment_cannot_reuse_old_runtime_exhaustion(workspace):
    path, moment = workspace
    first = session.start()
    target, report = block_report(path, moment)
    report.update(limit_kind='runtime_expired', actual_runtime_exhausted=True)
    target.write_text(json.dumps(report), encoding='utf-8')
    moment[0] += timedelta(minutes=5)
    resumed = session.start()
    assert resumed['id'] == first['id'] and resumed['started_at'] == first['started_at']
    with pytest.raises(LocalFlowError, match='current diagnosed'):
        session.finish('runtime_limit', str(target))


def test_scientific_label_cannot_end_zero_research_segment(workspace):
    session.start()
    with pytest.raises(LocalFlowError, match='actual research'):
        session.finish('scientific_complete', 'one local experiment done')
    assert session.status()['state'] == 'active'


def test_open_mainline_cannot_be_closed_by_completion_label(workspace):
    path, _ = workspace
    current = session.start()
    session.checkpoint('bounded question', 'local result', 'report', 'more research')
    target = path/'completion.json'
    target.write_text(json.dumps(dict(session_id=current['id'],
        scope='whole_current_objective', remaining_work=[],
        conclusion='claimed completion', evidence_reference='result')), encoding='utf-8')
    with pytest.raises(LocalFlowError, match='remains open'):
        session.finish('scientific_complete', str(target))
    assert session.status()['state'] == 'active'


def test_local_milestone_rejected_but_real_whole_completion_can_end_early(workspace):
    path, _ = workspace
    current = session.start()
    session.checkpoint('whole objective', 'objective evidence examined', 'report', 'deliver')
    session.MAINLINE.write_text('Science is COMPLETE.', encoding='utf-8')
    target = path/'completion.json'
    report = dict(session_id=current['id'], scope='local_milestone', remaining_work=[],
                  conclusion='one check passed', evidence_reference='report')
    target.write_text(json.dumps(report), encoding='utf-8')
    with pytest.raises(LocalFlowError, match='local milestone'):
        session.finish('scientific_complete', str(target))
    report.update(scope='whole_current_objective', remaining_work=['unfinished research'])
    target.write_text(json.dumps(report), encoding='utf-8')
    with pytest.raises(LocalFlowError, match='whole current objective'):
        session.finish('scientific_complete', str(target))
    report['remaining_work'] = []
    target.write_text(json.dumps(report), encoding='utf-8')
    result = session.finish('scientific_complete', str(target))
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
