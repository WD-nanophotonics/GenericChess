"""Durable Slack consultation and receive-only Socket Mode transport.

Sending is performed once by the calling Agent's installed Slack tool. This
module has no chat.postMessage, model client, worker launch or scheduler.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import getpass
import hashlib
import json
import logging
import os
import re
import secrets
import sqlite3
import sys
import time

from .common import STATE, ROOT, LocalFlowError, read_json, write_json, git

CONFIG = STATE / 'slack.json'
DB = STATE / 'slack' / 'inbox.sqlite3'


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


@contextmanager
def notification():
    """Local Windows notification, separate from Slack network transport."""
    if os.name != 'nt':
        yield None
        return
    import ctypes
    from ctypes import wintypes
    api = ctypes.WinDLL('kernel32', use_last_error=True)
    api.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
    api.CreateEventW.restype = wintypes.HANDLE
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.WaitForSingleObject.restype = wintypes.DWORD
    api.SetEvent.argtypes = [wintypes.HANDLE]; api.SetEvent.restype = wintypes.BOOL
    api.CloseHandle.argtypes = [wintypes.HANDLE]; api.CloseHandle.restype = wintypes.BOOL
    name = 'Local\\GenericChessInbox-' + digest(str(DB.resolve()).casefold())
    handle = api.CreateEventW(None, False, False, name)
    if not handle:
        raise LocalFlowError('cannot create local inbox notification')
    try:
        yield api, handle
    finally:
        api.CloseHandle(handle)


def notify():
    with notification() as signal:
        if signal and not signal[0].SetEvent(signal[1]):
            raise LocalFlowError('cannot notify local inbox reader')


def config():
    c = read_json(CONFIG)
    if not all(c.get(k) for k in ('team_id', 'channel_id', 'sender_id')):
        raise LocalFlowError('Slack target has not been verified')
    return c


@contextmanager
def database():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB, timeout=10)
    try:
        with db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS requests '
                       '(id TEXT PRIMARY KEY, hash TEXT UNIQUE, data TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS events '
                       '(id TEXT PRIMARY KEY, ts TEXT, thread TEXT, received TEXT, raw TEXT NOT NULL)')
            yield db
    finally:
        db.close()


def put(db, r):
    db.execute('INSERT INTO requests VALUES (?,?,?) ON CONFLICT(id) '
               'DO UPDATE SET data=excluded.data',
               (r['request_id'], r['content_sha256'], json.dumps(r, ensure_ascii=False)))


def get(db, rid=None):
    row = db.execute('SELECT data FROM requests WHERE id=?', (rid,)).fetchone() if rid else db.execute(
        'SELECT data FROM requests ORDER BY rowid DESC LIMIT 1').fetchone()
    return json.loads(row[0]) if row else None


def consult(question_file, daily=False, code_files=()):
    from .advice import ADVISORY, now
    c = config()
    if c.get('stopped'):
        raise LocalFlowError('consultation is stopped')
    if question_file.stat().st_size > 12000:
        raise LocalFlowError('question exceeds 12000 bytes')
    question = question_file.read_text(encoding='utf-8-sig').strip()
    if not question:
        raise LocalFlowError('empty question')
    code = []; total = 0
    for path in code_files:
        path = path.resolve()
        if not path.is_relative_to(ROOT.resolve()) or any(
                p.startswith('.') for p in path.relative_to(ROOT.resolve()).parts):
            raise LocalFlowError('code must be an ordinary file inside this project')
        total += path.stat().st_size
        if total > 64000:
            raise LocalFlowError('code package exceeds 64000 bytes')
        raw = path.read_bytes()
        code.append({'path': path.relative_to(ROOT.resolve()).as_posix(),
                     'sha256': hashlib.sha256(raw).hexdigest(), 'text': raw.decode('utf-8-sig')})
    key = digest(json.dumps([question, code], sort_keys=True))
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        for row in db.execute('SELECT data FROM requests'):
            r = json.loads(row[0])
            if r['content_sha256'] == key:
                return {**r, 'duplicate': True}
            if r['state'] not in {'COMPLETED', 'FROZEN'}:
                raise LocalFlowError('pending Slack request needs reconciliation: ' + r['request_id'])
        if daily:
            if now().hour < 10:
                return {'state': 'NOT_DUE'}
            if any(json.loads(row[0]).get('daily_date') == now().date().isoformat()
                   for row in db.execute('SELECT data FROM requests')):
                return {'state': 'DAILY_ALREADY_RESERVED'}
        rid = 'GC-SLACK-' + now().strftime('%Y%m%d-%H%M%S-') + secrets.token_hex(4)
        mention = f'<@{c["mention_user_id"]}>\n' if c.get('mention_user_id') else ''
        message = mention + f'TYPE=AGENT_REQUEST\nREQUEST_ID={rid}\nPROJECT=GenericChess\nCOMMITTED_BASE_SHA={git("rev-parse", "HEAD")}\n' + ADVISORY + question
        for entry in code:
            message += f'\nLOCAL_CODE_SNAPSHOT={entry["path"]}\nSHA256={entry["sha256"]}\n' + entry['text']
        message += '\nReply in this thread with TYPE=DOT_REPLY and this REQUEST_ID. State conclusion, sources, objections, uncertainty and independently checked evidence. Do not delegate extra workers.'
        # One tool call / one root. Larger content must be prepared as a reviewed attachment.
        if len(message) > 4800:
            raise LocalFlowError('Slack message exceeds 4800 characters; use a bounded excerpt or reviewed attachment')
        r = dict(request_id=rid, content_sha256=key, payload_sha256=digest(message),
                 message=message, state='PREPARED', team_id=c['team_id'], channel_id=c['channel_id'],
                 sender_id=c['sender_id'], advisor_user_id=c['advisor_user_id'],
                 advisor_bot_id=c.get('advisor_bot_id'), advisor_app_id=c.get('advisor_app_id'),
                 daily_date=now().date().isoformat() if daily else None, revisions=[], created_at=stamp())
        put(db, r)
        return r


def status(rid=None):
    with database() as db:
        return get(db, rid) or {'state': 'NEVER_SENT'}


def begin_send(rid):
    c = config()
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        r = get(db, rid)
        if not r:
            raise LocalFlowError('unknown Slack request')
        if any(r.get(k) != c.get(k) for k in ('team_id', 'channel_id', 'sender_id',
                                             'advisor_user_id', 'advisor_bot_id', 'advisor_app_id')):
            raise LocalFlowError('Slack target or identity changed; reconcile original binding')
        if digest(r['message']) != r['payload_sha256']:
            raise LocalFlowError('immutable payload changed')
        if r['state'] != 'PREPARED':
            return {**r, 'action': 'slack-reconcile', 'resend_permitted': False}
        if (c.get('stopped') or not c.get('dispatch_enabled') or not c.get('accepted')
                or c.get('quota_status') != 'verified_no_extra_worker'):
            return {**r, 'action': 'CAPABILITY_PENDING', 'resend_permitted': False}
        r.update(state='SEND_UNCERTAIN', send_started_at=stamp())
        put(db, r)
        return {**r, 'action': 'slack_send_message', 'resend_permitted': False}


def bind_sent(rid, channel, ts):
    """Bind a successful send receipt; uncertain sends require exact anchor recovery."""
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        r = get(db, rid)
        if not r or channel != r['channel_id'] or r['state'] not in {'SEND_UNCERTAIN', 'PENDING'}:
            raise LocalFlowError('invalid send receipt')
        if not re.fullmatch(r'\d+\.\d+', ts) or (r.get('thread_ts') and r['thread_ts'] != ts):
            raise LocalFlowError('conflicting thread binding')
        r.update(thread_ts=ts, state='PENDING')
        put(db, r)
        return r


def ingest(payload):
    """Persist only bound workspace/channel events; duplicates are harmless."""
    c = config()
    if c.get('stopped'):
        return 'STOPPED'
    event = payload.get('event', {})
    if payload.get('team_id') != c['team_id'] or event.get('channel') != c['channel_id']:
        return 'WRONG_TARGET'
    eid = payload.get('event_id')
    if not eid or event.get('type') != 'message':
        return 'UNSUPPORTED'
    msg = event.get('message', event)
    with database() as db:
        cursor = db.execute('INSERT OR IGNORE INTO events VALUES (?,?,?,?,?)',
                            (eid, msg.get('ts', event.get('deleted_ts')),
                             msg.get('thread_ts', msg.get('ts')), stamp(),
                             json.dumps(payload, ensure_ascii=False)))
        result = 'STORED' if cursor.rowcount else 'DUPLICATE'
    notify()  # durable commit first; a waiting local process is notified immediately
    return result


def reconcile(rid):
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        r = get(db, rid)
        if not r:
            raise LocalFlowError('unknown Slack request')
        holds = []
        for row in db.execute('SELECT * FROM events ORDER BY rowid'):
            payload = json.loads(row['raw']); event = payload['event']
            msg = event.get('message', event); text = msg.get('text', '')
            ids = re.findall(r'(?m)^REQUEST_ID=([^\s]+)\s*$', text)
            typ = re.findall(r'(?m)^TYPE=([^\s]+)\s*$', text)
            if not r.get('thread_ts') and r['state'] == 'SEND_UNCERTAIN':
                # Slack adds a transport footer / mention label, so compare a known
                # exact payload prefix after normalizing mention display only.
                clean = re.sub(r'<@([^>|]+)\|[^>]+>', r'<@\1>', text)
                if msg.get('user') == r['sender_id'] and clean.split('\n*Sent using*')[0].rstrip() == r['message'].rstrip():
                    r['thread_ts'] = msg['ts']; r['state'] = 'PENDING'
            if row['thread'] != r.get('thread_ts'):
                continue
            if typ != ['DOT_REPLY']:
                continue
            actor_ok = msg.get('user') == r['advisor_user_id']
            for k in ('bot_id', 'app_id'):
                expected = r.get('advisor_' + k)
                if expected and msg.get(k) != expected:
                    actor_ok = False
            if not actor_ok or ids != [rid] or event.get('subtype') == 'message_deleted':
                holds.append(row['id']); continue
            h = digest(text)
            if h not in [v['sha256'] for v in r['revisions']]:
                read_at = stamp()
                try:
                    posted = float((msg.get('edited') or {}).get('ts') or msg.get('ts'))
                except (TypeError, ValueError):
                    holds.append(row['id']); continue
                r['revisions'].append(dict(sha256=h, text=text, event_id=row['id'],
                                           message_ts=msg.get('ts'), edited=msg.get('edited'),
                                           received_at=row['received'], agent_read_at=read_at,
                                           persist_delay_seconds=round(datetime.fromisoformat(row['received']).timestamp() - posted, 3),
                                           agent_read_delay_seconds=round(datetime.fromisoformat(read_at).timestamp() - posted, 3)))
            # A revision is evidence only: never silently replace an adopted reply.
            if r['state'] != 'COMPLETED':
                r.update(state='COMPLETED', response_sha256=h, response=text)
        r['held_events'] = holds
        r['reconciled_at'] = stamp()
        put(db, r)
        return {**r, 'resend_permitted': False}


def decision(rid, action, reason):
    if action not in {'adopt', 'defer', 'reject'} or not reason.strip():
        raise LocalFlowError('record a decision and evidence-based reason')
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        r = get(db, rid)
        if not r or r['state'] != 'COMPLETED':
            raise LocalFlowError('completed reply required')
        r['evaluation'] = dict(decision=action, reason=reason, response_sha256=r['response_sha256'], at=stamp())
        put(db, r)
        return r


def wait(rid, seconds=300):
    if not 0 <= seconds <= 300:
        raise LocalFlowError('mechanical wait must be between 0 and 300 seconds')
    end = time.monotonic() + seconds
    # Create the event before the first read: a racing commit cannot be missed.
    with notification() as signal:
        while True:
            r = reconcile(rid)
            if r['state'] == 'COMPLETED' or config().get('stopped') or time.monotonic() >= end:
                return r
            remaining = max(0, end - time.monotonic())
            if signal:
                result = signal[0].WaitForSingleObject(signal[1], max(1, int(remaining * 1000)))
                if result not in {0, 258}:  # notification or timeout
                    raise LocalFlowError('local inbox wait failed')
            else:
                time.sleep(min(1, remaining))


def vault():
    if os.name != 'nt':
        raise LocalFlowError('Windows Credential Manager is required')
    from keyring.backends.Windows import WinVaultKeyring
    return WinVaultKeyring()


def credentials(set_values=False):
    c = config(); service = 'GenericChess-Slack-' + c['team_id']
    v = vault()
    if set_values:
        if not sys.stdin.isatty():
            raise LocalFlowError('enter credentials in an interactive local terminal with hidden input')
        for name, prefix in [('app', 'xapp-'), ('bot', 'xoxb-')]:
            secret = getpass.getpass(f'{name} token (hidden input): ')
            if not secret.startswith(prefix):
                raise LocalFlowError('incorrect token type')
            v.set_password(service, name, secret)
        return {'stored': True, 'backend': 'Windows Credential Manager'}
    values = [v.get_password(service, name) for name in ('app', 'bot')]
    if not all(values):
        raise LocalFlowError('receiver credentials missing; use slack-credentials in a local terminal')
    return values


@contextmanager
def receiver_lock():
    # Different lock from short advisory operations; single receiver per project.
    path = STATE / 'slack' / 'receiver.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as f:
        f.seek(0, 2)
        if f.tell() == 0:
            f.write(b'0'); f.flush()
        f.seek(0)
        if os.name == 'nt':
            import msvcrt
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise LocalFlowError('receiver already running') from exc
        else:
            import fcntl
            try:
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise LocalFlowError('receiver already running') from exc
        try:
            yield
        finally:
            f.seek(0)
            if os.name == 'nt':
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(f, fcntl.LOCK_UN)


def receive():
    try:
        return _receive()
    except LocalFlowError:
        raise
    except Exception as exc:
        # No SDK exception bodies, authenticated URLs, tokens or headers in logs.
        raise LocalFlowError('receiver failed: ' + type(exc).__name__) from None


def stop():
    c = config()
    c.update(stopped=True, dispatch_enabled=False, receiver_enabled=False, stopped_at=stamp())
    write_json(CONFIG, c)
    notify()
    return {'stopped': True, 'required_agent_actions': ['pause native heartbeat', 'cancel dot channel monitoring']}


def _receive():
    c = config()
    if c.get('stopped') or not c.get('receiver_enabled'):
        raise LocalFlowError('receiver disabled; restart must not clear stop state')
    app, bot = credentials()
    from slack_sdk import WebClient
    from slack_sdk.socket_mode import SocketModeClient
    from slack_sdk.socket_mode.response import SocketModeResponse
    logger = logging.getLogger('generic-chess-slack-receiver')
    logger.handlers = [logging.NullHandler()]; logger.propagate = False
    logger.setLevel(logging.CRITICAL + 1)
    web = WebClient(token=bot, timeout=15, logger=logger)
    auth = web.auth_test()
    header = next((v for k, v in auth.headers.items() if k.lower() == 'x-oauth-scopes'), '')
    if isinstance(header, list):
        header = ','.join(header)
    scopes = {s.strip() for s in header.split(',') if s.strip()}
    if auth.get('team_id') != c['team_id'] or scopes != {'channels:history'}:
        raise LocalFlowError('receiver workspace or read-only scope qualification failed')
    with receiver_lock():
        client = SocketModeClient(app_token=app, web_client=web, logger=logger)
        def listener(client, request):
            if request.type == 'events_api':
                ingest(request.payload)  # commit before ACK; failures are retriable
            client.send_socket_mode_response(SocketModeResponse(envelope_id=request.envelope_id))
        client.socket_mode_request_listeners.append(listener)
        try:
            client.connect()
            write_json(STATE / 'slack' / 'receiver-health.json',
                       {'started_at': stamp(), 'state': 'connected', 'channel_id': c['channel_id']})
            while not config().get('stopped') and config().get('receiver_enabled'):
                time.sleep(1)
        finally:
            client.close()
            write_json(STATE / 'slack' / 'receiver-health.json', {'state': 'stopped', 'at': stamp()})
    return {'receiver': 'stopped'}
