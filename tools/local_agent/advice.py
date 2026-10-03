"""Native advisory transport coordinated by the calling Agent, without another model."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
from .common import ROOT, STATE, LocalFlowError, read_json, write_json

LEDGER = STATE / 'advisory-ledger.json'
CONFIG = STATE / 'advisor.json'
ADVISORY = '''You and the local GenericChess Agent are research partners of nearly equal
authority; user instructions take precedence. Give evidence, primary-source
literal full URLs, objections, useful directions or the smallest falsifiable check.
Distinguish facts from inference and uncertainty. Remain in ordinary Chat: do not
switch to Work, launch workers, issue work orders, or add publication approval
gates. Git is final delivery, not a required communication path. Do not claim
local file access or independent test execution you do not actually possess.
'''

def now():
    return datetime.now(timezone(timedelta(hours=9)))

def sha(data):
    return hashlib.sha256(data).hexdigest()

@contextmanager
def locked():
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE / 'advisory.lock').open('a+b') as f:
        f.seek(0)
        if not f.read(1):
            f.write(b'0'); f.flush()
        f.seek(0)
        if os.name == 'nt':
            import msvcrt
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise LocalFlowError('another advisory operation is active') from exc
        else:
            import fcntl
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise LocalFlowError('another advisory operation is active') from exc
        try:
            yield
        finally:
            f.seek(0)
            if os.name == 'nt':
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)

def configuration():
    config = read_json(CONFIG)
    if config.get('transport') not in {'native', 'courier'} or not config.get('thread_id') or not config.get('project_id'):
        raise LocalFlowError('configure one verified advisor target and transport first')
    return config

def select(ledger, request_id=None):
    requests = ledger.get('requests', {})
    if not requests:
        return None
    request_id = request_id or next(reversed(requests))
    if request_id not in requests:
        raise LocalFlowError('unknown advisory request')
    return requests[request_id]

def consult(question_file: Path, daily=False, code_files=()):
    config = configuration()
    question = question_file.read_text(encoding='utf-8-sig').strip()
    if not question or len(question.encode()) > 12000:
        raise LocalFlowError('provide one bounded nonempty question (up to 12000 bytes)')
    code = []; total = 0
    for file in code_files:
        file = file.resolve()
        if not file.is_relative_to(ROOT.resolve()) or any(p.startswith('.') for p in file.relative_to(ROOT.resolve()).parts):
            raise LocalFlowError('code must be an ordinary file inside this project')
        data = file.read_bytes(); total += len(data)
        if total > 64000:
            raise LocalFlowError('code package exceeds 64000 bytes')
        code.append({'path': file.relative_to(ROOT.resolve()).as_posix(), 'sha256': sha(data), 'text': data.decode('utf-8-sig')})
    key = sha(json.dumps({'question': question, 'code': code}, sort_keys=True).encode())
    with locked():
        ledger = read_json(LEDGER); requests = ledger.setdefault('requests', {}); date = now().date().isoformat()
        if daily and now().hour < 10:
            return {'state': 'NOT_DUE', 'date': date}
        for request in requests.values():
            if request['content_sha256'] == key:
                return {**request, 'duplicate': True}
        for request in requests.values():
            if request['state'] not in {'COMPLETED', 'FROZEN'}:
                raise LocalFlowError('pending request needs reconciliation: ' + request['request_id'])
        if daily and date in ledger.setdefault('daily', {}):
            return {'state': 'DAILY_ALREADY_RESERVED', 'request_id': ledger['daily'][date]}
        request_id = 'GC-ADVICE-' + now().strftime('%Y%m%d-%H%M%S-') + secrets.token_hex(4)
        directory = STATE / 'advisory' / request_id; directory.mkdir(parents=True)
        message = f'REQUEST_ID={request_id}\n' + ADVISORY + '\nQuestion and evidence:\n' + question
        for entry in code:
            message += f'\n\nFILE={entry["path"]}\nSHA256={entry["sha256"]}\n' + entry['text']
        message += '\n\nPlease retain REQUEST_ID in the reply.\n'
        path = directory / 'message.txt'; path.write_text(message, encoding='utf-8')
        record = {'request_id': request_id, 'state': 'PREPARED', 'date': date, 'daily': daily,
                  'transport': config['transport'], 'thread_id': config['thread_id'], 'project_id': config['project_id'],
                  'content_sha256': key, 'payload_sha256': sha(message.encode()), 'message_file': str(path),
                  'code': [{'path': e['path'], 'sha256': e['sha256']} for e in code]}
        requests[request_id] = record
        if daily: ledger['daily'][date] = request_id
        write_json(LEDGER, ledger)
        return record

def consult_status(reconcile=False, request_id=None):
    with locked():
        return select(read_json(LEDGER), request_id) or {'state': 'NEVER_SENT'}

def begin_send(request_id):
    config = configuration()
    with locked():
        ledger = read_json(LEDGER); request = select(ledger, request_id)
        if request is None: raise LocalFlowError('unknown advisory request')
        if request['thread_id'] != config['thread_id'] or request['transport'] != config['transport']:
            raise LocalFlowError('target or transport changed; reconcile original binding')
        message = Path(request['message_file']).read_text(encoding='utf-8')
        if sha(message.encode()) != request['payload_sha256']: raise LocalFlowError('immutable payload changed')
        if request['state'] != 'PREPARED': return {**request, 'action': 'read_thread', 'resend_permitted': False}
        if not config.get('enabled') or config.get('quota_status') != 'verified_no_extra_worker':
            return {**request, 'action': 'CAPABILITY_PENDING', 'quota_status': config.get('quota_status', 'unverified')}
        if request['transport'] != 'native': raise LocalFlowError('Courier is archived; requalify it before selecting')
        request['state'] = 'SEND_UNCERTAIN'; request['send_started_at'] = now().isoformat(); write_json(LEDGER, ledger)
        return {**request, 'action': 'send_message_to_thread', 'prompt': message}

def reconcile_snapshot(request_id, snapshot_file):
    snapshot = json.loads(snapshot_file.read_text(encoding='utf-8-sig'))
    with locked():
        ledger = read_json(LEDGER); request = select(ledger, request_id)
        if not request: raise LocalFlowError('unknown advisory request')
        if snapshot.get('thread', {}).get('id') != request['thread_id']: raise LocalFlowError('snapshot belongs to a different target')
        if snapshot['thread'].get('kind') != 'chatgpt': raise LocalFlowError('advisor must be a ChatGPT chat')
        message = Path(request['message_file']).read_text(encoding='utf-8')
        if sha(message.encode()) != request['payload_sha256']: raise LocalFlowError('immutable payload changed')
        for turn in snapshot.get('turns', []):
            items = turn.get('items', [])
            anchors = [i for i, item in enumerate(items) if item.get('type') == 'userMessage' and not item.get('truncated')
                       and any(c.get('text', '').strip() == message.strip() for c in item.get('content', []))]
            if not anchors: continue
            if any(item.get('type') not in {'userMessage', 'agentMessage'} for item in items):
                raise LocalFlowError('unexpected advisor tool/task activity; inspect quota')
            if turn.get('status') != 'completed' or turn.get('error'):
                request['state'] = 'PENDING'; break
            for item in items[anchors[-1] + 1:]:
                if item.get('type') == 'userMessage': break
                text = item.get('text', '')
                if item.get('type') == 'agentMessage' and text and not item.get('truncated'):
                    if 'REQUEST_ID=' in text and 'REQUEST_ID=' + request_id not in text:
                        raise LocalFlowError('reply request ID conflicts with its anchor')
                    path = Path(request['message_file']).with_name('response.txt'); path.write_text(text, encoding='utf-8')
                    request.update(state='COMPLETED', response_file=str(path), response_sha256=sha(text.encode()),
                                   turn_id=turn.get('id'), response_item_id=item.get('id')); break
            break
        write_json(LEDGER, ledger)
        return {**request, 'resend_permitted': False}

def record_decision(request_id, decision, reason):
    if decision not in {'adopt', 'defer', 'reject'} or not reason.strip(): raise LocalFlowError('record adopt/defer/reject and a reason')
    with locked():
        ledger = read_json(LEDGER); request = select(ledger, request_id)
        if not request or request['state'] != 'COMPLETED': raise LocalFlowError('complete reply required before evaluation')
        request['evaluation'] = {'decision': decision, 'reason': reason.strip(), 'at': now().isoformat()}
        write_json(LEDGER, ledger); return request
