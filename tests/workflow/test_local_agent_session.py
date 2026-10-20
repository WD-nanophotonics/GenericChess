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


def worked(workspace, minutes=61, activity='research'):
    _, moment = workspace
    first = moment[0]
    moment[0] += timedelta(minutes=minutes)
    return session.record_work(first.isoformat(), moment[0].isoformat(),
                               activity, 'controlled actual-work evidence')


def quality(workspace, reason='safe_checkpoint'):
    path, moment = workspace
    current = session.status()
    target = path/'quality.json'
    target.write_text(json.dumps(dict(
        session_id=current['id'], ending_reason=reason,
        reviewed_work_intervals=current.get('work_intervals', []),
        effective_seconds=current['effective_seconds'], old_conclusions_excluded=True,
        research_questions=[cp['question'] for cp in current['checkpoints']
                            if cp['kind'] == 'research'
                            and cp['at'] >= current.get('resumed_at', current['started_at'])],
        reviewed_at=moment[0].isoformat(), limitations='controlled scope, not all-domain proof',
        unresolved_issues=[])), encoding='utf-8')
    return str(target)


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
    flags = json.loads((path/file).read_text()) if (path/file).exists() else {}
    (path/file).write_text(json.dumps(dict(flags, **{flag: True})))
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
    with pytest.raises(LocalFlowError, match='effective'):
        session.finish('safe_checkpoint', 'elapsed70')


def test_research_stages_normal_finish_reserve_and_last_three_receipts(workspace):
    path, moment = workspace
    for n in range(4):
        session.start()
        session.checkpoint('question', f'new observation{n}', 'report', 'next action')
        with pytest.raises(LocalFlowError, match='duplicate'):
            session.checkpoint('question', f'new observation{n}', 'report', 'other next')
        worked(workspace)
        result = session.finish('safe_checkpoint', quality(workspace))
        assert result['duration_gate_passed'] and result['quality_review_passed']
        assert not result['quality_review_required']
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
    worked(workspace)
    moment[0] += timedelta(hours=2)
    session.start()
    with pytest.raises(LocalFlowError, match='fresh research'):
        session.finish('safe_checkpoint', 'old stage and2hours')
    session.checkpoint('new question', 'new finding', 'new report', 'next')
    assert session.finish('safe_checkpoint', quality(workspace))['quality_review_passed']


def test_no_next_exit_requires_two_fresh_alternative_observations(workspace):
    _, moment = workspace
    session.start()
    session.checkpoint('alt1', 'new finding1', 'report1', 'alt2')
    worked(workspace)
    with pytest.raises(LocalFlowError, match='two distinct'):
        session.finish('no_viable_action', 'old notes', ['alt1', 'unexecuted'])
    session.checkpoint('alt2', 'new finding2', 'report2', 'future exploration')
    assert session.finish('no_viable_action', quality(workspace, 'no_viable_action'),
                          ['alt1', 'alt2'])['state'] == 'ended'


def test_wall_time_and_one_new_checkpoint_never_create_effective_credit(workspace):
    _, moment = workspace
    session.start()
    moment[0] += timedelta(hours=8)
    session.start()
    session.checkpoint('new', 'actual new result', 'report', 'next')
    assert session.status()['effective_seconds'] == 0
    with pytest.raises(LocalFlowError, match='effective'):
        session.finish('safe_checkpoint', quality(workspace))
    assert session.status()['wall_minutes'] == 480


def test_work_ledger_excludes_admin_and_offline_resume_gap(workspace):
    _, moment = workspace
    original = session.start()
    worked(workspace, 20)
    worked(workspace, 10, 'documentation')
    moment[0] += timedelta(hours=5)
    resumed = session.start()
    assert resumed['id'] == original['id']
    assert resumed['started_at'] == original['started_at']
    assert resumed['effective_minutes'] == 20
    worked(workspace, 15, 'validation')
    assert session.status()['effective_minutes'] == 35
    with pytest.raises(LocalFlowError, match='effective'):
        session.finish('safe_checkpoint', 'not enough')


def test_interval_overlap_future_naive_and_pre_resume_are_rejected(workspace):
    _, moment = workspace
    first = session.start()
    worked(workspace, 10)
    with pytest.raises(LocalFlowError, match='overlapping'):
        session.record_work(first['started_at'], moment[0].isoformat(), 'research', 'same')
    with pytest.raises(LocalFlowError, match='future'):
        session.record_work(moment[0].isoformat(),
                            (moment[0]+timedelta(minutes=1)).isoformat(), 'research', 'future')
    with pytest.raises(LocalFlowError, match='timezone-aware'):
        session.record_work('2026-10-04T00:00:00', moment[0].isoformat(), 'research', 'naive')
    moment[0] += timedelta(hours=1)
    session.start()
    with pytest.raises(LocalFlowError, match='resumed window'):
        session.record_work(first['started_at'], moment[0].isoformat(), 'research', 'offline')


def test_effective_work_requires_matching_quality_acceptance(workspace):
    path, moment = workspace
    session.start()
    session.checkpoint('q', 'new controlled observation', 'report', 'next')
    worked(workspace)
    with pytest.raises(LocalFlowError, match='review'):
        session.finish('safe_checkpoint', 'tests passed, published')
    report_path = quality(workspace)
    report = json.loads((path/'quality.json').read_text())
    report['effective_seconds'] += 60
    (path/'quality.json').write_text(json.dumps(report))
    with pytest.raises(LocalFlowError, match='matching'):
        session.finish('safe_checkpoint', report_path)
    report['effective_seconds'] -= 60
    report['reviewed_work_intervals'] = report['reviewed_work_intervals'][:-1]
    (path/'quality.json').write_text(json.dumps(report))
    with pytest.raises(LocalFlowError, match='matching'):
        session.finish('safe_checkpoint', report_path)
    result = session.finish('safe_checkpoint', quality(workspace))
    assert result['effective_minutes'] == 61 and result['quality_review_passed']
    assert session.final_check()['research_completed']


def test_active_final_rejected_and_user_redirect_is_not_research_completion(workspace):
    path, moment = workspace
    first = session.start()
    worked(workspace, 28)
    for mode in ('research', 'bounded'):
        with pytest.raises(LocalFlowError, match='active'):
            session.final_check(mode)
    report = dict(session_id=first['id'], reason='user_redirect', requested_task='repair',
                  user_instruction='Fix the workflow only; no research this turn',
                  instruction_reference='direct user message', observed_at=moment[0].isoformat())
    target = path/'redirect.json'
    target.write_text(json.dumps(report))
    paused = session.interrupt(str(target))
    assert paused['state'] == 'interrupted' and not paused['research_completed']
    assert not paused['duration_gate_passed']
    assert not session.final_check('bounded')['research_completed']
    with pytest.raises(LocalFlowError, match='interrupted'):
        session.final_check()
    moment[0] += timedelta(hours=12)
    resumed = session.start()
    assert resumed['id'] == first['id'] and resumed['effective_minutes'] == 28
    assert resumed['started_at'] == first['started_at']


def test_legacy_active_clock_has_no_automatic_effective_credit(workspace):
    path, moment = workspace
    first = session.start()
    legacy = json.loads((path/'session.json').read_text())
    del legacy['work_intervals']
    (path/'session.json').write_text(json.dumps(legacy))
    moment[0] += timedelta(days=1)
    resumed = session.start()
    assert resumed['id'] == first['id'] and resumed['effective_seconds'] == 0
    with pytest.raises(LocalFlowError, match='effective'):
        session.finish('safe_checkpoint', 'legacy wall time')


def test_old_checkpoint_evidence_is_not_discarded_after_six_entries(workspace):
    session.start()
    for n in range(8):
        session.checkpoint(f'q{n}', 'new result', f'report{n}', 'next')
    assert len(session.status()['checkpoints']) == 8


def test_ledger_seconds_cannot_be_inflated_without_matching_interval(workspace):
    path, _ = workspace
    session.start()
    worked(workspace, 1)
    data = json.loads((path/'session.json').read_text())
    data['work_intervals'][0]['seconds'] = 3600
    (path/'session.json').write_text(json.dumps(data))
    with pytest.raises(LocalFlowError, match='ledger'):
        session.status()
    with pytest.raises(LocalFlowError, match='ledger'):
        session.finish('safe_checkpoint', 'not valid')


def test_quality_cannot_predate_work_or_list_unexecuted_questions(workspace):
    path, moment = workspace
    first = session.start()
    session.checkpoint('real question', 'new result', 'report', 'next')
    worked(workspace)
    target = quality(workspace)
    report = json.loads((path/'quality.json').read_text())
    report['reviewed_at'] = first['started_at']
    (path/'quality.json').write_text(json.dumps(report))
    with pytest.raises(LocalFlowError, match='follow'):
        session.finish('safe_checkpoint', target)
    report['reviewed_at'] = moment[0].isoformat()
    report['research_questions'] = ['unexecuted question']
    (path/'quality.json').write_text(json.dumps(report))
    with pytest.raises(LocalFlowError, match='quality'):
        session.finish('safe_checkpoint', target)


def test_interrupt_requires_real_user_redirect_fields(workspace):
    path, _ = workspace
    session.start()
    target = path/'redirect.json'
    target.write_text(json.dumps(dict(reason='publication', user_instruction='done')))
    with pytest.raises(LocalFlowError, match='explicit user'):
        session.interrupt(str(target))
    assert session.status()['state'] == 'active'


def test_new_cli_work_and_final_commands_do_not_bypass_gate(workspace, capsys):
    _, moment = workspace
    assert cli.main(['session', 'start']) == 0
    first = moment[0]
    moment[0] += timedelta(minutes=28)
    assert cli.main(['session', 'work', '--started-at', first.isoformat(),
                     '--ended-at', moment[0].isoformat(), '--activity', 'validation',
                     '--evidence', 'actual bounded test execution']) == 0
    assert cli.main(['session', 'final-check']) == 2
    assert 'active' in capsys.readouterr().err
    assert cli.main(['session', 'finish', '--reason', 'safe_checkpoint',
                     '--evidence', '28minutes then wait for heartbeat']) == 2
    assert 'before60 effective' in capsys.readouterr().err


def test_cli_status_is_compact_unless_full_history_is_requested(workspace, capsys):
    session.start()
    session.checkpoint('q', 'new result', 'report', 'next')
    worked(workspace, 1)
    assert cli.main(['session', 'status']) == 0
    brief = json.loads(capsys.readouterr().out)
    assert brief['checkpoint_count'] == 1 and brief['effective_minutes'] == 1
    assert 'checkpoints' not in brief and 'work_intervals' not in brief
    assert cli.main(['session', 'status', '--full']) == 0
    full = json.loads(capsys.readouterr().out)
    assert len(full['checkpoints']) == len(full['work_intervals']) == 1


def test_rounded_sixty_minutes_does_not_pass_exact_seconds_gate(workspace):
    _, moment = workspace
    first = session.start()
    session.checkpoint('q', 'new result', 'report', 'next')
    moment[0] += timedelta(seconds=3599.99)
    session.record_work(first['started_at'], moment[0].isoformat(), 'research', 'real work')
    assert session.status()['effective_minutes'] == 60.0
    with pytest.raises(LocalFlowError, match='before60 effective'):
        session.finish('safe_checkpoint', quality(workspace))


def test_cli_bounded_interrupt_reports_incomplete_and_preserves_stops(workspace, capsys):
    path, moment = workspace
    first = session.start()
    target = path/'redirect.json'
    target.write_text(json.dumps(dict(
        session_id=first['id'], reason='user_redirect', requested_task='review',
        user_instruction='Review the prior worker only, no research',
        instruction_reference='direct user message', observed_at=moment[0].isoformat())))
    flags = (path/'rollout.json').read_bytes()
    assert cli.main(['session', 'interrupt', '--evidence', str(target)]) == 0
    capsys.readouterr()
    assert cli.main(['session', 'final-check', '--mode', 'bounded']) == 0
    assert json.loads(capsys.readouterr().out)['research_completed'] is False
    assert (path/'rollout.json').read_bytes() == flags
