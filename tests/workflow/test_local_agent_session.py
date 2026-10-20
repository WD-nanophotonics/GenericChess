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
        session.work_start('bounded research')
        moment[0] += timedelta(minutes=61)
        session.work_stop('report and command receipts')
        result = session.finish('safe_checkpoint', 'new evidence reviewed; reserve ready')
        assert result['duration_gate_passed'] and result['quality_review_required']
    assert len(json.loads((path/'session_receipts.json').read_text())['receipts']) == 3


@pytest.mark.parametrize('content', [MEMO+'x'*2048, MEMO+'ä¸­'*700, MEMO+'\n'*21,
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
    with pytest.raises(LocalFlowError, match='effective research'):
        session.finish('safe_checkpoint', 'fresh stage alone is not60minutes')
    session.work_start('new question')
    moment[0] += timedelta(minutes=60)
    session.work_stop('new report and experiment receipt')
    assert session.finish('safe_checkpoint', 'new stage reviewed')['quality_review_required']


def test_no_next_exit_requires_two_fresh_alternative_observations(workspace):
    _, moment = workspace
    session.start()
    session.checkpoint('alt1', 'new finding1', 'report1', 'alt2')
    session.work_start('alt1')
    moment[0] += timedelta(minutes=61)
    session.work_stop('report1')
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



def test_wall70_but_work5_is_rejected(workspace):
    _, moment = workspace
    session.start()
    session.work_start('concrete research')
    moment[0] += timedelta(minutes=5)
    session.work_stop('actual five-minute experiment receipt')
    moment[0] += timedelta(minutes=65)
    session.checkpoint('q', 'new finding', 'report', 'continue')
    with pytest.raises(LocalFlowError, match='effective research'):
        session.finish('safe_checkpoint', 'wall70 is not effective70')
    assert session.status()['effective_work_seconds'] == 300
    assert session.status()['state'] == 'active'


def test_closed_intervals_survive_compact_and_idle_and_finish_syncs_memo(workspace):
    path, moment = workspace
    first = session.start()
    session.work_start('research before compact')
    moment[0] += timedelta(minutes=25)
    session.work_stop('first report')
    moment[0] += timedelta(hours=8)
    resumed = session.start()
    assert resumed['id'] == first['id']
    assert resumed['started_at'] == first['started_at']
    assert resumed['effective_work_seconds'] == 1500
    session.start()  # repeated recovery must not mint another ID or work credit
    session.work_start('research after compact')
    moment[0] += timedelta(minutes=35)
    session.work_stop('second report')
    session.checkpoint('q', 'fresh result', 'second report', 'next task')
    result = session.finish('safe_checkpoint', 'two supported research intervals')
    assert result['effective_work_seconds'] == 3600
    assert result['duration_gate_passed'] and result['memo_synced']
    text = (path/'NEXT_WORK.md').read_text()
    assert f"Segment: ENDED {first['id']}" in text
    assert 'work=3600.000s' in text and 'safe_checkpoint' in text
    assert len(text.encode()) <= 2048


def test_open_interval_not_credited_on_status_finish_or_resume(workspace):
    _, moment = workspace
    session.start()
    session.work_start('work interrupted before evidence')
    moment[0] += timedelta(hours=3)
    session.checkpoint('q', 'finding', 'evidence', 'next')
    assert session.status()['effective_work_seconds'] == 0
    with pytest.raises(LocalFlowError, match='close work interval'):
        session.finish('safe_checkpoint', 'open interval is not proof')
    resumed = session.start()
    assert resumed['effective_work_seconds'] == 0
    assert resumed['active_work'] is None
    assert len(resumed['uncredited_work']) == 1
    session.start()
    assert len(session.status()['uncredited_work']) == 1
    with pytest.raises(LocalFlowError, match='no active work'):
        session.work_stop('cannot close pre-interruption interval')


def test_work_interval_lifecycle_evidence_and_admin_separation(workspace):
    _, moment = workspace
    with pytest.raises(LocalFlowError, match='start/resume'):
        session.work_start('q')
    session.start()
    with pytest.raises(LocalFlowError, match='question'):
        session.work_start(' ')
    session.work_start('bounded experiment and analysis')
    with pytest.raises(LocalFlowError, match='already active'):
        session.work_start('second computation')
    for kind in ('documentation', 'transport'):
        with pytest.raises(LocalFlowError, match='stop research work'):
            session.checkpoint('q', 'administrative task', 'receipt', 'next', kind)
    with pytest.raises(LocalFlowError, match='evidence'):
        session.work_stop(' ')
    moment[0] += timedelta(minutes=2)
    assert session.work_stop('specific experiment command/output')['effective_work_seconds'] == 120
    with pytest.raises(LocalFlowError, match='no active work'):
        session.work_stop('duplicate closure')
    session.checkpoint('q', 'sent message', 'receipt', 'next', 'transport')


def test_overlapping_computation_and_analysis_are_union_not_sum(workspace):
    _, moment = workspace
    current = session.start()
    base = moment[0]
    def span(a,b):
        return dict(started_at=(base+timedelta(minutes=a)).isoformat(),
                    ended_at=(base+timedelta(minutes=b)).isoformat(),
                    question='one scientific question', evidence='exact run receipt')
    current['work_intervals'] = [span(0,40), span(20,60), span(10,15)]
    assert session.work_seconds(current, base+timedelta(minutes=60)) == 3600


def test_clock_reversal_and_future_intervals_fail_closed(workspace):
    path, moment = workspace
    current = session.start()
    moment[0] += timedelta(minutes=10)
    session.work_start('q')
    moment[0] -= timedelta(minutes=1)
    with pytest.raises(LocalFlowError, match='clock'):
        session.work_stop('not a valid interval')
    assert session.status()['state'] == 'active'
    current['work_intervals'] = [dict(started_at=current['started_at'],
        ended_at=(moment[0]+timedelta(hours=1)).isoformat(), question='q', evidence='e')]
    with pytest.raises(LocalFlowError, match='clock'):
        session.work_seconds(current, moment[0])


def test_legacy_active_wall_time_gets_no_automatic_credit(workspace):
    path, moment = workspace
    current = session.start()
    for key in ('work_intervals', 'work_accounting_version', 'effective_work_seconds', 'active_work'):
        current.pop(key)
    (path/'session.json').write_text(json.dumps(current))
    legacy = {'id':'historical', 'elapsed_minutes':70, 'duration_gate_passed':True}
    original = json.dumps({'receipts':[legacy]})
    (path/'session_receipts.json').write_text(original)
    moment[0] += timedelta(hours=9)
    resumed = session.start()
    assert resumed['id'] == current['id']
    assert resumed['started_at'] == current['started_at']
    assert resumed['effective_work_seconds'] == 0
    assert (path/'session_receipts.json').read_text() == original
    session.checkpoint('q', 'new result', 'report', 'next')
    with pytest.raises(LocalFlowError, match='effective research'):
        session.finish('safe_checkpoint', 'legacy elapsed is insufficient')


def test_user_stop_discards_unconfirmed_interval_and_missing_memo_does_not_delay_stop(workspace):
    path, moment = workspace
    session.start()
    session.work_start('q')
    moment[0] += timedelta(hours=2)
    (path/'rollout.json').write_text(json.dumps({'thread_id':'same-chat','user_paused':True}))
    (path/'NEXT_WORK.md').unlink()
    with pytest.raises(LocalFlowError, match='user stop'):
        session.work_stop('do not continue after stop')
    result = session.finish('user_stop', 'explicit user stop')
    assert result['state'] == 'ended'
    assert result['effective_work_seconds'] == 0
    assert not result['duration_gate_passed'] and not result['memo_synced']
    assert result['active_work'] is None


def test_work_cli_commands_roundtrip(workspace, capsys):
    _, moment = workspace
    assert cli.main(['session','start']) == 0
    assert cli.main(['session','work-start','--question','q']) == 0
    moment[0] += timedelta(seconds=10)
    assert cli.main(['session','work-stop','--evidence','specific research receipt']) == 0
    assert session.status()['effective_work_seconds'] == 10



def test_below_exact_boundary_never_rounds_up(workspace):
    _, moment = workspace
    session.start()
    session.work_start('q')
    moment[0] += timedelta(seconds=3600, microseconds=-1)
    session.work_stop('report')
    session.checkpoint('q', 'actual result', 'report', 'next')
    moment[0] += timedelta(minutes=1)
    with pytest.raises(LocalFlowError, match='effective research'):
        session.finish('safe_checkpoint', 'do not round3599.999999up')


@pytest.mark.parametrize('bad', ['not-a-time', '2026-10-04T00:00:00'])
def test_invalid_or_naive_interval_timestamps_are_rejected(workspace, bad):
    _, moment = workspace
    current = session.start()
    current['work_intervals'] = [dict(started_at=bad,
        ended_at=moment[0].isoformat(), question='q', evidence='e')]
    with pytest.raises(LocalFlowError, match='clock'):
        session.work_seconds(current, moment[0])


def test_memo_write_failure_does_not_record_normal_success(workspace, monkeypatch):
    path, moment = workspace
    session.start()
    session.work_start('q')
    moment[0] += timedelta(minutes=60)
    session.work_stop('report')
    session.checkpoint('q', 'fresh result', 'report', 'next')
    def fail_replace(*args):
        raise OSError('fixture write failure')
    monkeypatch.setattr(session.os, 'replace', fail_replace)
    with pytest.raises(LocalFlowError, match='synchronize ended memo'):
        session.finish('safe_checkpoint', 'report')
    assert session.status()['state'] == 'active'
    assert not (path/'session_receipts.json').exists()


def test_explicit_stop_retains_invalid_accounting_without_inventing_credit(workspace):
    path, moment = workspace
    current = session.start()
    current['work_intervals'] = [dict(started_at='broken', ended_at='broken',
        question='q', evidence='e')]
    (path/'session.json').write_text(json.dumps(current))
    result = session.finish('user_stop', 'explicit stop')
    assert result['state'] == 'ended'
    assert result['effective_work_seconds'] == 0
    assert 'work_accounting_error' in result
    assert result['work_intervals'] == current['work_intervals']
