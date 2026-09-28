from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from .advice import consult, consult_status
from .common import ROOT, STATE, LocalFlowError, git, read_json, write_json
from .git_ops import publish, promote


ACTIVITY = STATE / "activity.json"
PATROLS = STATE / "patrol.json"


def status() -> dict:
    return {
        "mode": "local-agent",
        "branch": git("branch", "--show-current"),
        "head": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "origin_sandbox": git("rev-parse", "origin/sandbox"),
        "last_activity": read_json(ACTIVITY),
        "last_consultation": consult_status(),
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
    patrol_parser = sub.add_parser("patrol")
    patrol_parser.add_argument("--record", action="store_true")
    n = sub.add_parser("note")
    n.add_argument("--summary", required=True)
    c = sub.add_parser("consult")
    c.add_argument("--question-file", type=Path, required=True)
    cs = sub.add_parser("consult-status")
    cs.add_argument("--reconcile", action="store_true")
    pub = sub.add_parser("publish")
    pub.add_argument("--tests", nargs="+", required=True)
    pro = sub.add_parser("promote")
    pro.add_argument("--candidate", required=True)
    pro.add_argument("--tests", nargs="+", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "status":
            result = status()
        elif args.command == "patrol":
            result = patrol(args.record)
        elif args.command == "note":
            result = note(args.summary)
        elif args.command == "consult":
            result = consult(args.question_file)
        elif args.command == "consult-status":
            result = consult_status(args.reconcile)
        elif args.command == "publish":
            result = publish(args.tests)
        else:
            result = promote(args.candidate, args.tests)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    except (LocalFlowError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"LOCAL_AGENT_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
