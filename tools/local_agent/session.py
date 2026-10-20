"""Bounded receipts and structural checks; no model, scheduler or restart loop."""
from datetime import datetime, timezone
from uuid import uuid4
from pathlib import Path
import os

from .common import STATE, LocalFlowError, read_json, write_json
from .environment import require_identity


HARD_REASONS = {'user_stop', 'user_decision', 'tool_limit', 'quota_limit',
                'runtime_limit'}


def now():
    return datetime.now(timezone.utc)


def stopped():
    return (read_json(STATE/'rollout.json').get('user_paused', False)
            or read_json(STATE/'slack.json').get('stopped', False))


def memo():
    path = STATE/'NEXT_WORK.md'
    if not path.exists():
        raise LocalFlowError('rebuild memo before research start')
    raw = path.read_bytes()
    text = raw.decode('utf-8-sig')
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


def work_seconds(current, at):
    """Confirmed work only; merge overlaps so concurrency earns no double credit."""
    spans = []
    try:
        origin = datetime.fromisoformat(current['started_at'])
        if not origin.tzinfo or not at.tzinfo:
            raise ValueError('timezone-aware timestamps required')
        for item in current.get('work_intervals', []):
            begin = datetime.fromisoformat(item['started_at'])
            end = datetime.fromisoformat(item['ended_at'])
            if (not begin.tzinfo or not end.tzinfo or
                    begin < origin or end < begin or end > at or
                    not item['question'].strip() or not item['evidence'].strip()):
                raise ValueError('invalid confirmed interval')
            spans.append((begin, end))
        merged = []
        for begin, end in sorted(spans):
            if merged and begin <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
            else:
                merged.append((begin, end))
        return sum((end-begin).total_seconds() for begin, end in merged)
    except (KeyError, TypeError, ValueError, AttributeError) as error:
        raise LocalFlowError('invalid work accounting or clock: ' + str(error)) from error


def work_start(question):
    if stopped():
        raise LocalFlowError('user stop persists; research work forbidden')
    current = read_json(STATE/'session.json')
    if current.get('state') != 'active':
        raise LocalFlowError('start/resume a segment first')
    if not question.strip():
        raise LocalFlowError('concrete research question required')
    if current.get('active_work'):
        raise LocalFlowError('one work interval already active; no overlapping writer')
    at = now()
    work_seconds(current, at)
    last = current.get('resumed_at', current['started_at'])
    if at < datetime.fromisoformat(last):
        raise LocalFlowError('clock moved backwards; work start unverified')
    current['active_work'] = dict(question=question, started_at=at.isoformat())
    current.setdefault('work_intervals', [])
    current['work_accounting_version'] = 1
    write_json(STATE/'session.json', current)
    return current['active_work']


def work_stop(evidence):
    if stopped():
        raise LocalFlowError('user stop persists; finish with user_stop')
    current = read_json(STATE/'session.json')
    if current.get('state') != 'active' or not current.get('active_work'):
        raise LocalFlowError('no active work interval to stop')
    if not evidence.strip():
        raise LocalFlowError('concrete research evidence required')
    at = now()
    item = dict(current['active_work'], ended_at=at.isoformat(), evidence=evidence)
    current.setdefault('work_intervals', []).append(item)
    seconds = work_seconds(current, at)
    current['active_work'] = None
    current['effective_work_seconds'] = seconds
    write_json(STATE/'session.json', current)
    return dict(item, effective_work_seconds=seconds)


def discard_open_work(current, at, reason):
    if current.get('active_work'):
        current.setdefault('uncredited_work', []).append(dict(
            current['active_work'], interrupted_at=at.isoformat(), reason=reason))
        current['active_work'] = None


def ended_memo(value, required):
    """Prepare a compact ended Segment line; never prevent an explicit stop."""
    path = STATE/'NEXT_WORK.md'
    try:
        memo()
        lines = path.read_text(encoding='utf-8-sig').splitlines()
        segment = (f"Segment: ENDED {value['id']}; start={value['started_at']}; "
                   f"work={value['effective_work_seconds']:.3f}s; {value['reason']}.")
        text = '\n'.join(segment if line.startswith('Segment:') else line
                         for line in lines) + '\n'
        if len(text.encode('utf-8')) > 2048:
            raise LocalFlowError('ended memo exceeds2KiB; shorten other fields first')
        return text
    except (OSError, UnicodeError, LocalFlowError):
        if required:
            raise
        return None


def status():
    data = read_json(STATE/'session.json')
    if data.get('state') == 'active':
        at = now()
        elapsed = (at-datetime.fromisoformat(data['started_at'])).total_seconds()/60
        if elapsed < 0:
            raise LocalFlowError('clock moved backwards; elapsed duration unverified')
        data = dict(data, elapsed_minutes=round(elapsed, 3),
                    effective_work_seconds=work_seconds(data, at),
                    work_accounting_version=data.get('work_accounting_version', 1))
    return data


def start():
    if stopped():
        raise LocalFlowError('user stop persists; research start forbidden')
    require_identity()
    memo()
    current = read_json(STATE/'session.json')
    thread = read_json(STATE/'rollout.json').get('thread_id')
    if not thread:
        raise LocalFlowError('calling chat identity missing from rollout')
    if current.get('state') == 'active':
        if current['thread_id'] != thread:
            raise LocalFlowError('active segment belongs to another chat')
        at = now()
        if at < datetime.fromisoformat(current.get('resumed_at', current['started_at'])):
            raise LocalFlowError('clock moved backwards; resume unverified')
        current['effective_work_seconds'] = work_seconds(current, at)
        discard_open_work(current, at, 'resume: unfinished interval unconfirmed')
        current.setdefault('work_intervals', [])
        current['work_accounting_version'] = 1
        current['resumed_at'] = at.isoformat()
        write_json(STATE/'session.json', current)
        return dict(status(), resumed=True)
    value = {'id': str(uuid4()), 'state': 'active', 'thread_id': thread,
             'started_at': now().isoformat(), 'checkpoints': [],
             'research_stage_count': 0, 'work_accounting_version': 1,
             'work_intervals': [], 'effective_work_seconds': 0, 'active_work': None}
    write_json(STATE/'session.json', value)
    return value


def checkpoint(question, observation, evidence, next_action, kind='research'):
    if stopped():
        raise LocalFlowError('user stop persists; do not continue research')
    current = read_json(STATE/'session.json')
    if current.get('state') != 'active':
        raise LocalFlowError('start/resume a segment first')
    if kind not in {'research', 'documentation', 'transport'}:
        raise LocalFlowError('unknown checkpoint kind')
    if kind != 'research' and current.get('active_work'):
        raise LocalFlowError('stop research work before documentation/transport')
    values = (question, observation, evidence, next_action)
    if any(not value.strip() for value in values):
        raise LocalFlowError('concrete question, observation, evidence and next action required')
    item = dict(zip(('question', 'observation', 'evidence', 'next_action'), values),
                kind=kind, at=now().isoformat())
    if any(all(old[key] == item[key] for key in ('question', 'observation', 'evidence'))
           for old in current['checkpoints']):
        raise LocalFlowError('duplicate observation is not a new stage')
    current['checkpoints'] = (current['checkpoints']+[item])[-6:]
    current['research_stage_count'] += kind == 'research'
    write_json(STATE/'session.json', current)
    return item


def blocking_evidence(reason, evidence, current, ended):
    """Require current evidence for the two historically misused exit reasons.

    This checks records, not the truth of a diagnosis or report delivery.
    The calling Agent still reports and pauses its native schedule itself.
    """
    path = Path(evidence)
    if not path.is_absolute():
        path = STATE / path
    if not path.resolve().is_relative_to(STATE.resolve()) or not path.is_file():
        raise LocalFlowError('blocking exit requires current JSON evidence in own state')
    try:
        record = read_json(path)
        observed = datetime.fromisoformat(record['observed_at'])
        start = datetime.fromisoformat(current.get('resumed_at', current['started_at']))
        if record.get('session_id') != current['id'] or not start <= observed <= ended:
            raise ValueError('stale session or observation')
        if reason == 'user_decision':
            fields = ('diagnosis', 'why_agent_cannot_resolve', 'required_user_action',
                      'user_report_text', 'user_report_reference')
            if (record.get('diagnosis_status') != 'confirmed'
                    or record.get('serious_user_required') is not True
                    or not isinstance(record.get('checks_attempted'), list)
                    or not record['checks_attempted']
                    or any(not isinstance(x, str) or not x.strip()
                           for x in record['checks_attempted'])
                    or any(not isinstance(record.get(k), str) or not record[k].strip()
                           for k in fields)):
                raise ValueError('diagnosis and delivered concrete user action required')
            reported = datetime.fromisoformat(record['user_reported_at'])
            if not observed <= reported <= ended:
                raise ValueError('user report is not current')
        elif (record.get('runtime_exhausted') is not True
              or record.get('runtime_category') not in {
                  'execution_environment_exhausted', 'platform_context_limit',
                  'forced_runtime_shutdown'}
              or not isinstance(record.get('actual_runtime_event'), str)
              or not record['actual_runtime_event'].strip()):
            raise ValueError('actual current environment exhaustion required')
    except (OSError, ValueError, TypeError, KeyError) as error:
        raise LocalFlowError('invalid current blocking evidence: ' + str(error)) from error


def finish(reason, evidence, alternatives=()):
    current = read_json(STATE/'session.json')
    if current.get('state') != 'active':
        raise LocalFlowError('no active segment to finish')
    if reason not in HARD_REASONS | {'safe_checkpoint', 'no_viable_action', 'scientific_complete'}:
        raise LocalFlowError('soft blockage/publication/inspection is not an ending reason')
    if not evidence.strip():
        raise LocalFlowError('ending evidence required')
    if stopped() and reason != 'user_stop':
        raise LocalFlowError('stop takes precedence')
    ended = now()
    elapsed = (ended-datetime.fromisoformat(current['started_at'])).total_seconds()/60
    if elapsed < 0:
        raise LocalFlowError('clock moved backwards; elapsed duration unverified')
    if reason in {'user_decision', 'runtime_limit'}:
        blocking_evidence(reason, evidence, current, ended)
    accounting_error = None
    try:
        seconds = work_seconds(current, ended)
    except LocalFlowError as error:
        if reason not in HARD_REASONS:
            raise
        seconds = 0
        accounting_error = str(error)
    if reason not in HARD_REASONS:
        if elapsed < 60:
            raise LocalFlowError('before60 minutes switch tasks/explore; normal finish forbidden')
        if not current['research_stage_count']:
            raise LocalFlowError('elapsed time alone is not research')
        fresh = [cp for cp in current['checkpoints'] if cp['kind'] == 'research'
                 and cp['at'] >= current.get('resumed_at', current['started_at'])]
        if not fresh:
            raise LocalFlowError('resumed segment needs fresh research; old/idle time is not progress')
        if reason == 'no_viable_action':
            if len(set(alternatives)) < 2 or not set(alternatives) <= {cp['question'] for cp in fresh}:
                raise LocalFlowError('two distinct fresh alternative research questions required')
        if current.get('active_work'):
            raise LocalFlowError('close work interval with evidence before finish')
        if seconds < 3600:
            raise LocalFlowError('effective research work below60 minutes; continue useful work')
        memo()
    discard_open_work(current, ended, 'hard finish: unfinished interval unconfirmed')
    value = dict(current, state='ended', ended_at=ended.isoformat(),
                 elapsed_minutes=round(elapsed, 3), reason=reason, ending_evidence=evidence,
                 effective_work_seconds=seconds, work_accounting_version=1,
                 duration_gate_passed=seconds >= 3600 and bool(current['research_stage_count']),
                 quality_review_required=True)
    # Evidence-backed declared intervals are not independent activity telemetry.
    if accounting_error:
        value['work_accounting_error'] = accounting_error
    memo_text = ended_memo(value, reason not in HARD_REASONS)
    value['memo_synced'] = False
    if memo_text is not None:
        target = STATE/'NEXT_WORK.md'
        temporary = target.with_name(f'.NEXT_WORK.{os.getpid()}.tmp')
        try:
            temporary.write_text(memo_text, encoding='utf-8')
            os.replace(temporary, target)
            value['memo_synced'] = True
        except OSError as error:
            if reason not in HARD_REASONS:
                raise LocalFlowError('cannot synchronize ended memo: ' + str(error)) from error
    receipts = read_json(STATE/'session_receipts.json').get('receipts', [])
    summary = {key: value[key] for key in ('id', 'started_at', 'ended_at',
               'elapsed_minutes', 'reason', 'ending_evidence', 'research_stage_count',
               'duration_gate_passed', 'quality_review_required', 'effective_work_seconds',
               'work_accounting_version', 'memo_synced')}
    write_json(STATE/'session_receipts.json', {'receipts': (receipts+[summary])[-3:]})
    write_json(STATE/'session.json', value)
    return value
