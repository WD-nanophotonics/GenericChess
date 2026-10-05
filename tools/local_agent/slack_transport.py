"""Durable Slack consultation using the calling Agent plugin.

Sending is performed once by the calling Agent's installed Slack tool. This
module has no chat.postMessage, model client, worker launch or scheduler.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import re
import secrets
import sqlite3

from .common import STATE, ROOT, LocalFlowError, read_json, write_json, git

CONFIG = STATE / 'slack.json'
DB = STATE / 'slack' / 'inbox.sqlite3'


def stamp():
    return datetime.now(timezone.utc).isoformat()


def digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


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
            if '```' in entry['text']:
                raise LocalFlowError('code snapshot contains a Slack fence; use a reviewed attachment instead')
            message += f'\nLOCAL_CODE_SNAPSHOT={entry["path"]}\nSHA256={entry["sha256"]}\n```\n' + entry['text'] + ('' if entry['text'].endswith('\n') else '\n') + '```\n'
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


def _canonical(text):
    text = re.sub(r'<@([^>|]+)\|[^>]+>', r'<@\1>', text)
    text = re.sub(r'<(https?://[^>|]+)(?:\|[^>]+)?>', r'\1', text)
    text = re.sub(r'\n\*Sent using\* <@[^>]+>\s*$', '', text).rstrip()
    # The installed plugin removes paragraph blank lines during Markdown
    # rendering. Preserve code whitespace, normalize only prose separators.
    lines = []; local_code = False; fenced = False
    for line in text.splitlines():
        if line.startswith('LOCAL_CODE_SNAPSHOT='):
            local_code = True
        if line.startswith('```'):
            fenced = not fenced
        if line.startswith('Reply in this thread with TYPE=DOT_REPLY'):
            local_code = False
        # Observed plugin rendering drops one prose-leading space. Preserve
        # code indentation and Markdown list/quote structure; no text is dropped.
        if (not local_code and not fenced and line.startswith(' ')
                and not line.startswith('  ')
                and not re.match(r' [*+>#-]| \d+[.)]\s', line)):
            line = line[1:]
        if line.strip() or local_code or fenced:
            lines.append(line)
    return '\n'.join(lines)


def parse_plugin_thread(result):
    """Parse the plugin's complete rendered thread; ambiguous delimiters fail closed.

    Server-provided pagination is outside message bodies. Preserve the raw
    tool result as evidence; this is not a claim of Slack Events API metadata.
    """
    if result.get('isError'):
        raise LocalFlowError('Slack read failed; preserve request without resending')
    blocks = [json.loads(b['text']) for b in result.get('content', [])
              if b.get('type') == 'text' and b.get('text', '').startswith('{')]
    data = next((b for b in blocks if 'messages' in b), None)
    if not data or 'There are no more messages in this thread.' not in data.get('pagination_info', ''):
        raise LocalFlowError('complete paginated Slack thread evidence is required')
    text = data['messages']
    header = r'From: [^\n]*\((U[A-Z0-9]+)\)\nTime: [^\n]*\nMessage TS: (\d+\.\d+)\n'
    parent = re.match(r'=== THREAD PARENT MESSAGE ===\n' + header, text)
    if not parent:
        raise LocalFlowError('unrecognized Slack parent metadata')
    sections = list(re.finditer(r'\n=== THREAD REPLIES \((\d+) total\) ===\n', text))
    if not sections:
        suffix = '\n\nNo thread messsages\n'
        if not text.endswith(suffix):
            raise LocalFlowError('unrecognized empty thread evidence')
        return [dict(user=parent[1], ts=parent[2], text=text[parent.end():-len(suffix)])]
    if len(sections) != 1:
        raise LocalFlowError('ambiguous Slack thread delimiters')
    section = sections[0]; count = int(section[1])
    replies = list(re.finditer(r'\n--- Reply (\d+) of (\d+) ---\n' + header, text[section.end():]))
    if len(replies) != count or any(int(m[1]) != i + 1 or int(m[2]) != count for i, m in enumerate(replies)):
        raise LocalFlowError('ambiguous or incomplete Slack reply metadata')
    messages = [dict(user=parent[1], ts=parent[2], text=text[parent.end():section.start()].rstrip())]
    body = text[section.end():]
    for i, m in enumerate(replies):
        end = replies[i + 1].start() if i + 1 < len(replies) else len(body)
        messages.append(dict(user=m[3], ts=m[4], thread_ts=parent[2], text=body[m.end():end].rstrip()))
    return messages


def _rendered_emphasis(text):
    """Observed plugin *italic* -> _italic_ projection of EXPECTED prose only.

    Preserve all body characters, inline/fenced code and LOCAL_CODE_SNAPSHOT.
    This is formatting evidence, not permission to change mathematical tokens.
    Future requests should put multiplication expressions inside inline code.
    """
    result = []; fenced = False; local_code = False
    single_star = re.compile(r'(?<![\\*])\*([^\s*](?:[^*\n]*[^\s*])?)\*(?!\*)')
    for line in text.splitlines():
        if line.startswith('LOCAL_CODE_SNAPSHOT='):
            local_code = True
        if line.startswith('Reply in this thread with TYPE=DOT_REPLY'):
            local_code = False
        if line.startswith('```'):
            fenced = not fenced
            result.append(line); continue
        if local_code or fenced:
            result.append(line); continue
        parts = re.split(r'(`+[^`]*`+)', line)
        result.append(''.join(part if part.startswith('`') else single_star.sub(r'_\1_', part)
                              for part in parts))
    return '\n'.join(result)


def _payload_matches(observed, expected):
    actual = _canonical(observed); original = _canonical(expected)
    return actual in {original, _rendered_emphasis(original),
                      _rendered_bullets(original),
                      _rendered_bullets(_rendered_emphasis(original))}


def _rendered_bullets(text):
    """Observed plugin '- ' -> '• ' projection of expected prose only.

    Preserve indentation, body, code snapshots and fenced code exactly.
    Root identity, request ID, target and immutable ledger hashes still match.
    """
    lines = []; fenced = False; local_code = False
    for line in text.splitlines():
        if line.startswith('LOCAL_CODE_SNAPSHOT='):
            local_code = True
        if line.startswith('Reply in this thread with TYPE=DOT_REPLY'):
            local_code = False
        if line.startswith('```'):
            fenced = not fenced
            lines.append(line); continue
        if not local_code and not fenced and line.startswith('- '):
            line = '• ' + line[2:]
        lines.append(line)
    return '\n'.join(lines)


def import_snapshot(rid, path):
    snapshot = json.loads(path.read_text(encoding='utf-8-sig'))
    r = status(rid)
    if r.get('state') not in {'SEND_UNCERTAIN', 'PENDING', 'COMPLETED'}:
        raise LocalFlowError('no dispatched Slack request to reconcile')
    if snapshot.get('source') != 'Slack plugin read_thread':
        raise LocalFlowError('snapshot must preserve the actual Slack plugin tool result')
    if any(snapshot.get(k) != r[k] for k in ('team_id', 'channel_id')):
        raise LocalFlowError('snapshot belongs to another Slack target')
    messages = parse_plugin_thread(snapshot['tool_result'])
    root = messages[0]
    if (root['user'] != r['sender_id'] or snapshot.get('thread_ts') != root['ts']
            or (r.get('thread_ts') and r['thread_ts'] != root['ts'])
            or not _payload_matches(root['text'], r['message'])):
        raise LocalFlowError('Slack root account, thread or exact payload does not match')
    if not r.get('thread_ts'):
        bind_sent(rid, r['channel_id'], root['ts'])
    for msg in messages:
        ingest({'team_id': r['team_id'], 'event_id': 'plugin-observation-' + digest(
                json.dumps([r['channel_id'], msg['ts'], msg['text']], ensure_ascii=False)),
                'source': 'Slack plugin snapshot', 'event': dict(type='message', channel=r['channel_id'], **msg)})
    return reconcile(rid)


def bind_sent(rid, channel, ts):
    """Bind a successful send receipt; uncertain sends require exact anchor recovery."""
    with database() as db:
        db.execute('BEGIN IMMEDIATE')
        r = get(db, rid)
        if not r or channel != r['channel_id'] or r['state'] not in {'SEND_UNCERTAIN', 'PENDING'}:
            raise LocalFlowError('invalid send receipt')
        if not re.fullmatch(r'\d+\.\d{6}', ts) or (r.get('thread_ts') and r['thread_ts'] != ts):
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
                # Recover only the original target/payload, including observed
                # prose rendering; never repeat an uncertain send.
                clean = re.sub(r'<@([^>|]+)\|[^>]+>', r'<@\1>', text)
                if msg.get('user') == r['sender_id'] and _payload_matches(clean.split('\n*Sent using*')[0], r['message']):
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
            # Revisions remain evidence; adoption is tied to the reviewed hash.
            if r['state'] != 'COMPLETED':
                r.update(state='COMPLETED', response_sha256=h, response=text)
        r['held_events'] = holds
        if r['revisions']:
            # Several full posts may make one answer. Preserve all matched posts,
            # choosing the latest observed revision of each post before review.
            latest = {v['message_ts']: v for v in r['revisions']}
            response = '\n\n'.join(v['text'] for v in sorted(latest.values(), key=lambda v: float(v['message_ts'])))
            if not r.get('evaluation'):
                r.update(response=response, response_sha256=digest(response))
            r['unreviewed_response_sha256'] = (digest(response)
                if r.get('evaluation') and digest(response) != r['evaluation']['response_sha256'] else None)
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
        # Only an explicit renewed review adopts later posts or edited evidence.
        latest = {v['message_ts']: v for v in r['revisions']}
        response = '\n\n'.join(v['text'] for v in sorted(latest.values(), key=lambda v: float(v['message_ts'])))
        r.update(response=response, response_sha256=digest(response), unreviewed_response_sha256=None)
        r['evaluation'] = dict(decision=action, reason=reason, response_sha256=r['response_sha256'], at=stamp())
        put(db, r)
        return r


def stop():
    c = config()
    c.update(stopped=True, dispatch_enabled=False, stopped_at=stamp())
    write_json(CONFIG, c)
    advisor = read_json(STATE / 'advisor.json'); advisor['enabled'] = False
    write_json(STATE / 'advisor.json', advisor)
    rollout = read_json(STATE / 'rollout.json'); rollout['user_paused'] = True
    write_json(STATE / 'rollout.json', rollout)
    return {'stopped': True, 'required_agent_actions': ['pause native heartbeat', 'cancel dot channel monitoring']}
