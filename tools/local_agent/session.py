"""Bounded receipts and structural checks; no model, scheduler or restart loop."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .common import STATE, LocalFlowError, read_json, write_json


HARD_REASONS = {'user_stop', 'user_decision', 'tool_limit', 'quota_limit',
                'runtime_limit', 'scientific_complete'}
MAINLINE = STATE.parent / 'docs/research/LOCAL_MAINLINE.md'
EFFECTIVE_ACTIVITIES = {'research', 'analysis', 'validation'}
ACTIVITIES = EFFECTIVE_ACTIVITIES | {'documentation', 'transport', 'administration'}


def now():
    return datetime.now(timezone.utc)


def stopped():
    return any(read_json(STATE/name).get(flag, False)
               for name in ('rollout.json', 'advisor.json', 'slack.json')
               for flag in ('user_paused', 'stopped'))


def memo():
    path = STATE/'NEXT_WORK.md'
    if not path.exists():
        raise LocalFlowError('rebuild memo before research start')
    raw = path.read_bytes()
    text = raw.decode('utf-8')
    if len(raw) > 2048 or len(text.splitlines()) > 20:
        raise LocalFlowError('memo exceeds20 lines/2KiB UTF-8')
    fields = {}
    for label in ('State', 'Segment', 'Main', 'Backup1', 'Backup2', 'Evidence'):
        matches = [line[len(label)+1:].strip() for line in text.splitlines()
                   if line.startswith(label+':')]
        if len(matches) != 1 or not matches[0]:
            raise LocalFlowError(f'memo requires one nonempty {label} field')
        fields[label] = matches[0]
    tasks = []
    for label in ('Main', 'Backup1', 'Backup2'):
        parts = [part.strip() for part in fields[label].split('|')]
        if len(parts) != 4 or not all(parts):
            raise LocalFlowError(f'{label}: question | first action | evidence | done condition required')
        tasks.append(parts)
    if len({tuple(task) for task in tasks}) != 3:
        raise LocalFlowError('work reserve requires three distinct tasks')
    return fields


def status():
    data = read_json(STATE/'session.json')
    if data.get('started_at'):
        data = dict(data, **_metrics(data))
    return data


def _metrics(current):
    work = current.get('work_intervals', [])
    if not isinstance(work, list):
        raise LocalFlowError('invalid work ledger')
    spans = []
    seconds = 0.0
    for item in work:
        try:
            first, last = _timestamp(item['started_at']), _timestamp(item['ended_at'])
            recorded = _timestamp(item['recorded_at'])
            duration = (last-first).total_seconds()
            valid = (item['activity'] in ACTIVITIES and duration > 0
                     and item['seconds'] == duration
                     and _timestamp(current['started_at']) <= first < last <= recorded <= now()
                     and isinstance(item['evidence'], str) and item['evidence'].strip())
        except (KeyError, TypeError) as exc:
            raise LocalFlowError('invalid work ledger entry') from exc
        if not valid:
            raise LocalFlowError('invalid work ledger duration/activity/evidence')
        spans.append((first, last))
        if item['activity'] in EFFECTIVE_ACTIVITIES:
            seconds += duration
    spans.sort()
    if any(left[1] > right[0] for left, right in zip(spans, spans[1:])):
        raise LocalFlowError('overlapping work ledger entries')
    end = current.get('ended_at') or current.get('interrupted_at')
    wall_end = datetime.fromisoformat(end) if end else now()
    return dict(wall_minutes=round((wall_end-datetime.fromisoformat(
        current['started_at'])).total_seconds()/60, 3),
        effective_seconds=seconds, effective_minutes=round(seconds/60, 3),
        recorded_work_intervals=len(work))


def _owned():
    current = read_json(STATE/'session.json')
    thread = read_json(STATE/'rollout.json').get('thread_id')
    if not thread or current.get('thread_id') != thread:
        raise LocalFlowError('segment belongs to another chat or identity is missing')
    return current


def _timestamp(value):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError('timezone missing')
        return parsed
    except (TypeError, ValueError) as exc:
        raise LocalFlowError('timezone-aware ISO work timestamps required') from exc


def record_work(started_at, ended_at, activity, evidence):
    """Record evidenced work, never infer effective time from an open clock."""
    if stopped():
        raise LocalFlowError('user stop persists; do not continue research')
    current = _owned()
    if current.get('state') != 'active':
        raise LocalFlowError('start/resume a segment first')
    if activity not in ACTIVITIES or not evidence.strip():
        raise LocalFlowError('known activity and concrete work evidence required')
    first, last = _timestamp(started_at), _timestamp(ended_at)
    window = _timestamp(current.get('resumed_at', current['started_at']))
    if not window <= first < last <= now():
        raise LocalFlowError('work must be within this resumed window, not offline/future time')
    work = current.get('work_intervals', [])
    if any(first < _timestamp(item['ended_at']) and
           last > _timestamp(item['started_at']) for item in work):
        raise LocalFlowError('overlapping or duplicate work interval')
    item = dict(started_at=first.isoformat(), ended_at=last.isoformat(),
                seconds=(last-first).total_seconds(), activity=activity,
                evidence=evidence, recorded_at=now().isoformat())
    current['work_intervals'] = work+[item]
    metrics = _metrics(current)
    write_json(STATE/'session.json', current)
    return dict(item, **metrics)


def start():
    if stopped():
        raise LocalFlowError('user stop persists; research start forbidden')
    memo()
    current = read_json(STATE/'session.json')
    thread = read_json(STATE/'rollout.json').get('thread_id')
    if not thread:
        raise LocalFlowError('calling chat identity missing from rollout')
    if current.get('state') in {'active', 'interrupted'}:
        if current['thread_id'] != thread:
            raise LocalFlowError('active segment belongs to another chat')
        current['resumed_at'] = now().isoformat()
        current['state'] = 'active'
        current.pop('interrupted_at', None)
        # Legacy wall-clock-only receipts provide no verified effective credit.
        if 'work_intervals' not in current:
            current['legacy_effective_time_unverified'] = True
            current['work_intervals'] = []
        write_json(STATE/'session.json', current)
        return dict(status(), resumed=True)
    value = {'id': str(uuid4()), 'state': 'active', 'thread_id': thread,
             'started_at': now().isoformat(), 'checkpoints': [],
             'research_stage_count': 0, 'work_intervals': []}
    write_json(STATE/'session.json', value)
    return dict(value, **_metrics(value))


def checkpoint(question, observation, evidence, next_action, kind='research'):
    if stopped():
        raise LocalFlowError('user stop persists; do not continue research')
    current = _owned()
    if current.get('state') != 'active':
        raise LocalFlowError('start/resume a segment first')
    if kind not in {'research', 'documentation', 'transport'}:
        raise LocalFlowError('unknown checkpoint kind')
    values = (question, observation, evidence, next_action)
    if any(not value.strip() for value in values):
        raise LocalFlowError('concrete question, observation, evidence and next action required')
    item = dict(zip(('question', 'observation', 'evidence', 'next_action'), values),
                kind=kind, at=now().isoformat())
    if any(all(old[key] == item[key] for key in ('question', 'observation', 'evidence'))
           for old in current['checkpoints']):
        raise LocalFlowError('duplicate observation is not a new stage')
    current['checkpoints'] = current['checkpoints']+[item]
    current['research_stage_count'] += kind == 'research'
    write_json(STATE/'session.json', current)
    return item


def finish(reason, evidence, alternatives=()):
    current = _owned()
    if current.get('state') != 'active':
        raise LocalFlowError('no active segment to finish')
    if reason not in HARD_REASONS | {'safe_checkpoint', 'no_viable_action'}:
        raise LocalFlowError('soft blockage/publication/inspection is not an ending reason')
    if not evidence.strip():
        raise LocalFlowError('ending evidence required')
    if stopped() and reason != 'user_stop':
        raise LocalFlowError('stop takes precedence')
    if reason in {'user_decision', 'runtime_limit'}:
        _validate_block_report(reason, evidence, current)
    if reason == 'scientific_complete':
        _validate_scientific_completion(evidence, current)
    ended = now()
    metrics = _metrics(current)
    if metrics['wall_minutes'] < 0:
        raise LocalFlowError('clock moved backwards; elapsed duration unverified')
    if reason not in HARD_REASONS:
        if metrics['effective_seconds'] < 3600:
            raise LocalFlowError('before60 effective minutes; wall/active/idle time cannot pass finish')
        if not current['research_stage_count']:
            raise LocalFlowError('elapsed time alone is not research')
        fresh = [cp for cp in current['checkpoints'] if cp['kind'] == 'research'
                 and cp['at'] >= current.get('resumed_at', current['started_at'])]
        if not fresh:
            raise LocalFlowError('resumed segment needs fresh research; old/idle time is not progress')
        if reason == 'no_viable_action':
            if len(set(alternatives)) < 2 or not set(alternatives) <= {cp['question'] for cp in fresh}:
                raise LocalFlowError('two distinct fresh alternative research questions required')
        memo()
        _validate_quality_review(reason, evidence, current, metrics, fresh)
    value = dict(current, state='ended', ended_at=ended.isoformat(),
                 **metrics, reason=reason, ending_evidence=evidence,
                 duration_gate_passed=metrics['effective_seconds'] >= 3600
                    and bool(current['research_stage_count']),
                 quality_review_required=reason in HARD_REASONS,
                 quality_review_passed=reason not in HARD_REASONS)
    # A receipt cannot establish actual effective research or semantic quality.
    receipts = read_json(STATE/'session_receipts.json').get('receipts', [])
    summary = {key: value[key] for key in ('id', 'started_at', 'ended_at',
               'wall_minutes', 'effective_seconds', 'effective_minutes', 'reason',
               'ending_evidence', 'research_stage_count', 'duration_gate_passed',
               'quality_review_required', 'quality_review_passed')}
    write_json(STATE/'session_receipts.json', {'receipts': (receipts+[summary])[-3:]})
    write_json(STATE/'session.json', value)
    return value


def _report(evidence):
    path = Path(evidence)
    if not path.is_absolute():
        path = STATE.parent/path
    try:
        return read_json(path)
    except (OSError, ValueError) as exc:
        raise LocalFlowError('structured current review report required') from exc


def _validate_quality_review(reason, evidence, current, metrics, fresh):
    report = _report(evidence)
    questions = report.get('research_questions')
    if (report.get('session_id') != current['id']
            or report.get('ending_reason') != reason
            or report.get('reviewed_work_intervals') != current.get('work_intervals', [])
            or report.get('effective_seconds') != metrics['effective_seconds']
            or report.get('old_conclusions_excluded') is not True
            or not isinstance(questions, list) or not questions
            or not all(isinstance(q, str) and q.strip() for q in questions)
            or not set(questions) <= {cp['question'] for cp in fresh}
            or not isinstance(report.get('limitations'), str) or not report['limitations'].strip()
            or not isinstance(report.get('unresolved_issues'), list)):
        raise LocalFlowError('matching work ledger and substantive quality review required')
    reviewed = _timestamp(report.get('reviewed_at'))
    latest = max([_timestamp(current.get('resumed_at', current['started_at']))]
                 + [_timestamp(cp['at']) for cp in fresh]
                 + [_timestamp(item['ended_at']) for item in current.get('work_intervals', [])])
    if not latest <= reviewed <= now():
        raise LocalFlowError('quality review must follow the current work and findings')


def interrupt(evidence):
    """An explicit user redirect suspends a segment; it never passes finish."""
    current = _owned()
    if current.get('state') != 'active':
        raise LocalFlowError('no active segment to interrupt')
    report = _report(evidence)
    if (report.get('session_id') != current['id']
            or report.get('reason') != 'user_redirect'
            or report.get('requested_task') not in {'repair', 'review', 'configuration'}
            or not all(isinstance(report.get(key), str) and report[key].strip()
                       for key in ('user_instruction', 'instruction_reference'))):
        raise LocalFlowError('explicit user bounded-task redirect evidence required')
    observed = _timestamp(report.get('observed_at'))
    if not _timestamp(current['started_at']) <= observed <= now():
        raise LocalFlowError('current user redirect required')
    if 'work_intervals' not in current:
        current['legacy_effective_time_unverified'] = True
        current['work_intervals'] = []
    current.update(state='interrupted', interrupted_at=now().isoformat(),
                   duration_gate_passed=False, quality_review_passed=False)
    current.setdefault('interruptions', []).append(dict(
        at=current['interrupted_at'], reason='user_redirect', evidence=evidence))
    write_json(STATE/'session.json', current)
    return dict(current, **_metrics(current), research_completed=False)


def final_check(mode='research'):
    current = _owned()
    if current.get('state') == 'active':
        raise LocalFlowError('active is not continuing work; finish acceptance required before final')
    if current.get('state') not in {'ended', 'interrupted'}:
        raise LocalFlowError('no accepted finish or explicit bounded-task interruption')
    if mode == 'research' and current.get('state') != 'ended':
        raise LocalFlowError('interrupted is not a completed research segment')
    if mode not in {'research', 'bounded'}:
        raise LocalFlowError('unknown final mode')
    if (mode == 'research' and current.get('reason') not in HARD_REASONS
            and not (current.get('duration_gate_passed')
                     and current.get('quality_review_passed'))):
        raise LocalFlowError('normal research finish acceptance missing')
    return dict(state=current.get('state'), session_id=current['id'],
                research_completed=current.get('state') == 'ended'
                    and current.get('quality_review_passed', False),
                mode=mode, **_metrics(current))


def _validate_block_report(reason, evidence, current):
    """Require a current concrete report; this does not authenticate its truth."""
    path = Path(evidence)
    if not path.is_absolute():
        path = STATE.parent / path
    try:
        report = read_json(path)
        observed = datetime.fromisoformat(report['observed_at'])
        started = datetime.fromisoformat(current['started_at'])
        if reason == 'runtime_limit' and current.get('resumed_at'):
            started = datetime.fromisoformat(current['resumed_at'])
        valid_time = started <= observed <= now()
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise LocalFlowError('current structured block report required') from exc
    if (report.get('session_id') != current['id'] or not valid_time
            or not all(isinstance(report.get(key), str) and report[key].strip()
                       for key in ('failure', 'diagnosis', 'impact',
                                   'attempted_fixes', 'cannot_continue',
                                   'evidence_reference'))):
        raise LocalFlowError('current diagnosed block and attempted fixes required')
    if reason == 'user_decision':
        request = report.get('user_request')
        if (not isinstance(request, dict) or request.get('sent') is not True
                or not all(isinstance(request.get(key), str) and request[key].strip()
                           for key in ('action', 'reference', 'why_agent_cannot_do_it'))):
            raise LocalFlowError('specific already-sent user action request required')
    elif (report.get('limit_kind') not in {'runtime_shutdown', 'runtime_expired',
                                         'resource_exhaustion'}
          or report.get('actual_runtime_exhausted') is not True):
        raise LocalFlowError('actual current runtime exhaustion required; launch failure is not a runtime limit')


def _validate_scientific_completion(evidence, current):
    """Retain genuine early completion, without accepting a local milestone."""
    if not current['research_stage_count']:
        raise LocalFlowError('scientific completion requires actual research evidence')
    path = Path(evidence)
    if not path.is_absolute():
        path = STATE.parent / path
    try:
        report = read_json(path)
        mainline = MAINLINE.read_text(encoding='utf-8')
    except (OSError, ValueError) as exc:
        raise LocalFlowError('whole current objective completion record required') from exc
    if (report.get('session_id') != current['id']
            or report.get('scope') != 'whole_current_objective'
            or report.get('remaining_work') != []
            or not all(isinstance(report.get(key), str) and report[key].strip()
                       for key in ('conclusion', 'evidence_reference'))):
        raise LocalFlowError('whole current objective completion record required; a local milestone is insufficient')
    if 'Science is COMPLETE.' not in mainline or 'Science is OPEN.' in mainline:
        raise LocalFlowError('current mainline remains open; scientific_complete forbidden')
