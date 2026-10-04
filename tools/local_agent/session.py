"""Bounded receipts and structural checks; no model, scheduler or restart loop."""
from datetime import datetime, timezone
from uuid import uuid4

from .common import STATE, LocalFlowError, read_json, write_json


HARD_REASONS = {'user_stop', 'user_decision', 'tool_limit', 'quota_limit',
                'runtime_limit', 'scientific_complete'}


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
    if data.get('state') == 'active':
        data = dict(data, elapsed_minutes=round(
            (now()-datetime.fromisoformat(data['started_at'])).total_seconds()/60, 3))
    return data


def start():
    if stopped():
        raise LocalFlowError('user stop persists; research start forbidden')
    memo()
    current = read_json(STATE/'session.json')
    thread = read_json(STATE/'rollout.json').get('thread_id')
    if not thread:
        raise LocalFlowError('calling chat identity missing from rollout')
    if current.get('state') == 'active':
        if current['thread_id'] != thread:
            raise LocalFlowError('active segment belongs to another chat')
        current['resumed_at'] = now().isoformat()
        write_json(STATE/'session.json', current)
        return dict(status(), resumed=True)
    value = {'id': str(uuid4()), 'state': 'active', 'thread_id': thread,
             'started_at': now().isoformat(), 'checkpoints': [],
             'research_stage_count': 0}
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


def finish(reason, evidence, alternatives=()):
    current = read_json(STATE/'session.json')
    if current.get('state') != 'active':
        raise LocalFlowError('no active segment to finish')
    if reason not in HARD_REASONS | {'safe_checkpoint', 'no_viable_action'}:
        raise LocalFlowError('soft blockage/publication/inspection is not an ending reason')
    if not evidence.strip():
        raise LocalFlowError('ending evidence required')
    if stopped() and reason != 'user_stop':
        raise LocalFlowError('stop takes precedence')
    ended = now()
    elapsed = (ended-datetime.fromisoformat(current['started_at'])).total_seconds()/60
    if elapsed < 0:
        raise LocalFlowError('clock moved backwards; elapsed duration unverified')
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
        memo()
    value = dict(current, state='ended', ended_at=ended.isoformat(),
                 elapsed_minutes=round(elapsed, 3), reason=reason, ending_evidence=evidence,
                 duration_gate_passed=elapsed >= 60 and bool(current['research_stage_count']),
                 quality_review_required=True)
    # A receipt cannot establish actual effective research or semantic quality.
    receipts = read_json(STATE/'session_receipts.json').get('receipts', [])
    summary = {key: value[key] for key in ('id', 'started_at', 'ended_at',
               'elapsed_minutes', 'reason', 'ending_evidence', 'research_stage_count',
               'duration_gate_passed', 'quality_review_required')}
    write_json(STATE/'session_receipts.json', {'receipts': (receipts+[summary])[-3:]})
    write_json(STATE/'session.json', value)
    return value
