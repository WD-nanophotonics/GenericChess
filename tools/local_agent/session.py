"""Bounded receipts and structural checks; no model, scheduler or restart loop."""
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .common import STATE, LocalFlowError, read_json, write_json


HARD_REASONS = {'user_stop', 'user_decision', 'tool_limit', 'quota_limit',
                'runtime_limit', 'scientific_complete'}
MAINLINE = STATE.parent / 'docs/research/LOCAL_MAINLINE.md'


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
    if reason in {'user_decision', 'runtime_limit'}:
        _validate_block_report(reason, evidence, current)
    if reason == 'scientific_complete':
        _validate_scientific_completion(evidence, current)
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
