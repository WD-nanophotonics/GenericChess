"""Slack-only advice facade. No browser, native Chat send or model invocation."""
from datetime import datetime, timedelta, timezone
from .common import STATE, LocalFlowError, read_json

CONFIG = STATE / 'advisor.json'
ADVISORY = """You and the local GenericChess Agent are research partners of nearly equal
authority; user instructions take precedence. Give evidence, primary-source
full URLs, objections, useful directions or the smallest falsifiable check.
Distinguish facts from inference and uncertainty. Do not launch Work/Codex
workers or impose publication approval gates. Git is final delivery, not a
required communication path. Local paths do not grant access to local code.
"""

def now():
    return datetime.now(timezone(timedelta(hours=9)))

def configuration():
    c = read_json(CONFIG)
    if c.get('transport') != 'slack':
        raise LocalFlowError('only Slack is an active transport')
    return c

def consult(question_file, daily=False, code_files=()):
    configuration()
    from .slack_transport import consult as impl
    return impl(question_file, daily, code_files)

def consult_status(reconcile=False, request_id=None):
    configuration()
    from .slack_transport import status
    return status(request_id)

def begin_send(request_id):
    configuration()
    c = read_json(CONFIG)
    if not c.get('enabled') or c.get('quota_status') != 'verified_no_extra_worker':
        return {'action': 'CAPABILITY_PENDING', 'request_id': request_id}
    from .slack_transport import begin_send as impl
    return impl(request_id)

def reconcile_snapshot(request_id, snapshot_file):
    configuration()
    from .slack_transport import import_snapshot
    return import_snapshot(request_id, snapshot_file)

def record_decision(request_id, decision, reason):
    configuration()
    from .slack_transport import decision as impl
    return impl(request_id, decision, reason)
