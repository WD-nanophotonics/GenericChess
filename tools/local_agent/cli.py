from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from .advice import consult, consult_status, begin_send, reconcile_snapshot, record_decision
from .common import ROOT, STATE, LocalFlowError, git, read_json, write_json
from .git_ops import publish, promote


ACTIVITY = STATE / "activity.json"
PATROLS = STATE / "patrol.json"


def consultation_summary(result: dict) -> dict:
    return {key: result[key] for key in ('request_id', 'state', 'channel_id',
            'thread_ts', 'response_sha256', 'unreviewed_response_sha256',
            'evaluation', 'held_events', 'resend_permitted') if key in result} | {
            'matched_reply_posts': len({v['message_ts'] for v in result.get('revisions', [])}),
            'reply_revision_count': len(result.get('revisions', []))}


def status() -> dict:
    return {
        "mode": "local-agent",
        "branch": git("branch", "--show-current"),
        "head": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "origin_sandbox": git("rev-parse", "origin/sandbox"),
        "last_activity": read_json(ACTIVITY),
        "last_consultation": consultation_summary(consult_status()),
    }


def note(summary: str) -> dict:
    summary = summary.strip()
    if len(summary) < 12 or summary.casefold() in {"waiting", "still working", "no change"}:
        raise LocalFlowError("record a concrete observation or artifact, not a waiting status")
    value = {"at": datetime.now(timezone.utc).isoformat(),
             "summary": summary, "head": git("rev-parse", "HEAD")}
    write_json(ACTIVITY, value)
    return value


def patrol(record: bool = False) -> dict:
    value = read_json(ACTIVITY)
    head = git("rev-parse", "HEAD")
    last_commit_at = datetime.fromisoformat(git("show", "-s", "--format=%cI", "HEAD"))
    at = value.get("at")
    if isinstance(at, str):
        try:
            progress_at = max(datetime.fromisoformat(at), last_commit_at)
        except ValueError:
            progress_at = last_commit_at
    else:
        progress_at = last_commit_at
    age_hours = round((datetime.now(timezone.utc) - progress_at).total_seconds() / 3600, 2)
    previous = read_json(PATROLS)
    snapshot = {"head": head, "activity_at": at}
    same = bool(previous) and previous.get("snapshot") == snapshot
    repeated = previous.get("consecutive_same_snapshot", 0) + 1 if same else 0
    result = {
        "mode": "local-agent", "head": head,
        "last_observable_progress_at": progress_at.isoformat(),
        "hours_since_observable_progress": age_hours,
        "health": "observable_progress" if age_hours < 2 else "progress_unverified",
        "last_activity": value.get("summary"),
        "previous_patrol_at": previous.get("at"),
        "same_snapshot_as_previous_patrol": same,
        "consecutive_same_snapshot": repeated,
        "interpretation": "No recent artifact is visible; this does not prove the agent is idle."
        if age_hours >= 2 else "Recent artifact or progress note is visible.",
    }
    if record:
        write_json(PATROLS, {"at": datetime.now(timezone.utc).isoformat(),
                             "snapshot": snapshot,
                             "consecutive_same_snapshot": repeated})
    return result


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="generic-chess-local")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("status")
    sub.add_parser("stop")
    session_parser = sub.add_parser('session', help='work-segment receipts, not a runner')
    actions = session_parser.add_subparsers(dest='session_action', required=True)
    actions.add_parser('start')
    actions.add_parser('status')
    cp = actions.add_parser('checkpoint')
    for field in ('question', 'observation', 'evidence', 'next-action'):
        cp.add_argument('--'+field, required=True)
    cp.add_argument('--kind', choices=('research', 'documentation', 'transport'), default='research')
    end = actions.add_parser('finish')
    end.add_argument('--reason', required=True)
    end.add_argument('--evidence', required=True)
    end.add_argument('--alternative', action='append', default=[], help='fresh checkpoint question; repeat for no_viable_action')
    receipt = sub.add_parser("slack-bind-sent")
    receipt.add_argument("--request-id", required=True)
    receipt.add_argument("--channel-id", required=True)
    receipt.add_argument("--message-ts", required=True)
    patrol_parser = sub.add_parser("patrol")
    patrol_parser.add_argument("--record", action="store_true")
    n = sub.add_parser("note")
    n.add_argument("--summary", required=True)
    c = sub.add_parser("consult")
    c.add_argument("--question-file", type=Path)
    c.add_argument("--daily", action="store_true")
    c.add_argument("--code-file", type=Path, action="append", default=[])
    c.add_argument("--begin-send", metavar="REQUEST_ID")
    cs = sub.add_parser("consult-status")
    cs.add_argument("--request-id")
    cs.add_argument("--full", action="store_true", help="include full request/reply evidence")
    rec = sub.add_parser("reconcile")
    rec.add_argument("--request-id", required=True)
    rec.add_argument("--snapshot-file", type=Path)
    rec.add_argument("--decision", choices=["adopt", "defer", "reject"])
    rec.add_argument("--reason")
    rec.add_argument("--full", action="store_true", help="include full request/reply evidence")
    pub = sub.add_parser("publish")
    pub.add_argument("--tests", nargs="+", required=True)
    pro = sub.add_parser("promote")
    pro.add_argument("--candidate", required=True)
    pro.add_argument("--tests", nargs="+", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        if args.command == "status":
            result = status()
        elif args.command == 'session':
            from . import session
            if args.session_action == 'start':
                result = session.start()
            elif args.session_action == 'status':
                result = session.status()
            elif args.session_action == 'checkpoint':
                result = session.checkpoint(args.question, args.observation,
                    args.evidence, args.next_action, args.kind)
            else:
                result = session.finish(args.reason, args.evidence, args.alternative)
        elif args.command == 'stop':
            from .slack_transport import stop
            result = stop()
        elif args.command == 'slack-bind-sent':
            from .slack_transport import bind_sent
            result = bind_sent(args.request_id, args.channel_id, args.message_ts)
        elif args.command == "patrol":
            result = patrol(args.record)
        elif args.command == "note":
            result = note(args.summary)
        elif args.command == "consult":
            if args.begin_send:
                if args.question_file or args.code_file or args.daily:
                    raise LocalFlowError("begin-send cannot change an existing request")
                result = begin_send(args.begin_send)
            elif args.question_file:
                result = consult(args.question_file, args.daily, args.code_file)
            else:
                raise LocalFlowError("provide --question-file or --begin-send")
        elif args.command == "consult-status":
            result = consult_status(request_id=args.request_id)
        elif args.command == "reconcile":
            if args.snapshot_file:
                result = reconcile_snapshot(args.request_id, args.snapshot_file)
            elif args.decision and args.reason:
                result = record_decision(args.request_id, args.decision, args.reason)
            else:
                if read_json(STATE / 'advisor.json').get('transport') == 'slack':
                    from .slack_transport import reconcile
                    result = reconcile(args.request_id)
                else:
                    result = consult_status(request_id=args.request_id)
        elif args.command == "publish":
            result = publish(args.tests)
        else:
            result = promote(args.candidate, args.tests)
        if args.command in {'consult-status', 'reconcile'} and not args.full:
            result = consultation_summary(result)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (LocalFlowError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"LOCAL_AGENT_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
