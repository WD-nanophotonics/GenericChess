"""Slack-only advice facade. No browser, native Chat send or model invocation."""
from datetime import datetime, timedelta, timezone
from .common import STATE, LocalFlowError, read_json

CONFIG = STATE / 'advisor.json'
ADVISORY = """GenericChess collaboration: latest direct user instructions take precedence.
Independently initiated ChatGPT Slack review comments outrank solicited Dot
replies/messages; shared accounts or reply TYPE markers do not prove autonomous
review. Dot is a day-to-day research partner: give evidence, primary-source URLs,
objections, uncertainty and the smallest useful next-step check. Direct bounded
real-time dialogue is allowed. Do not create workers or impose approval gates.
Preserve the user's pure-Leaper-first scope. This message's referenced changes
must be pushed with full remote SHA verified before sending. Local paths alone
do not grant access to local code. Advisor advice does not grant new user scope.
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

def reconcile_snapshot(request_id, snapshot_file, sent_receipt_file=None, supplement=False):
    configuration()
    from .slack_transport import import_snapshot
    return import_snapshot(request_id, snapshot_file, sent_receipt_file, supplement)

def record_decision(request_id, decision, reason):
    configuration()
    from .slack_transport import decision as impl
    return impl(request_id, decision, reason)
