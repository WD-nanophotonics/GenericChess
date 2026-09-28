from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess

from .common import ROOT, STATE, LocalFlowError, read_json, write_json


PROJECT = "GENERICCHESS"
LEDGER = STATE / "consultations.json"
LAUNCHER = ROOT.parent / "GmailCourier" / "scripts" / "chat-courier.cmd"
ADVISORY = """GenericChess scientific consultation. You are an adviser, not a work-order issuer.
Search current authoritative sources, original papers, official game rules, and relevant
open-source implementations where useful. Write source links as literal full URLs so they
survive plain-text capture. Distinguish evidence from
inference, challenge the hypothesis, and suggest the smallest falsifiable next check.
Do not assign tasks, set publication or promotion gates, demand Supervisor review,
or emit GenericChess work-order/status control fields. The local Agent decides.

Local question and evidence:
"""


def _courier(*args: str) -> dict:
    if not LAUNCHER.is_file():
        raise LocalFlowError(f"ChatCourier launcher is missing: {LAUNCHER}")
    command = ["cmd.exe", "/d", "/c", str(LAUNCHER), *args]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    events = []
    for line in result.stdout.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    if result.returncode or not events:
        raise LocalFlowError(f"ChatCourier {args[0]} failed: "
                             f"{result.stdout[-1500:]} {result.stderr[-500:]}")
    final = events[-1]
    if final.get("ok") is False:
        raise LocalFlowError(f"ChatCourier {args[0]} rejected: {final}")
    return final


def consult(question_file: Path) -> dict:
    question = question_file.read_text(encoding="utf-8-sig").strip()
    if not question:
        raise LocalFlowError("consultation question is empty")
    if len(question.encode("utf-8")) > 12_000:
        raise LocalFlowError("consultation is too long; send one bounded question")
    # Japan does not observe daylight saving time; a fixed offset also works
    # on Windows Python installations without an IANA tzdata package.
    local_day = datetime.now(timezone(timedelta(hours=9))).date()
    if local_day.weekday() >= 5:
        raise LocalFlowError("daily consultation runs on active Tokyo weekdays only")
    today = local_day.isoformat()
    ledger = read_json(LEDGER)
    records = ledger.setdefault("days", {})
    if today in records:
        raise LocalFlowError(f"one consultation already reserved for {today}; use consult-status")
    pending = [day for day, value in records.items()
               if value.get("state") not in {"COMPLETED", "FROZEN"}]
    if pending:
        raise LocalFlowError(f"prior consultation needs reconciliation: {pending[-1]}")
    payload = STATE / f"consult-{today}.txt"
    payload.parent.mkdir(parents=True, exist_ok=True)
    payload.write_text(ADVISORY + question + "\n", encoding="utf-8")
    record = {"state": "RESERVED", "question_file": str(question_file.resolve()),
              "message_file": str(payload), "idempotency_key": f"LOCAL-ADVICE-{today.replace('-', '')}"}
    records[today] = record
    write_json(LEDGER, ledger)
    prepared = _courier("courier_prepare", "--project-id", PROJECT,
                        "--idempotency-key", record["idempotency_key"],
                        "--message-file", str(payload))
    request_directory = prepared.get("request_directory")
    if not isinstance(request_directory, str):
        raise LocalFlowError(f"prepare lacked request_directory: {prepared}")
    record.update({"state": "PREPARED", "request_directory": request_directory})
    write_json(LEDGER, ledger)
    result = _courier("run", request_directory)
    record["last_event"] = result
    record["state"] = "COMPLETED" if result.get("event") == "response_received" else "PENDING"
    write_json(LEDGER, ledger)
    return record


def consult_status(reconcile: bool = False) -> dict:
    ledger = read_json(LEDGER)
    records = ledger.get("days", {})
    if not records:
        return {"state": "NEVER_SENT"}
    day = max(records)
    record = records[day]
    directory = record.get("request_directory")
    if not directory and reconcile and record.get("state") == "RESERVED":
        # Preparation is idempotent under this day's immutable key and payload.
        prepared = _courier("courier_prepare", "--project-id", PROJECT,
                            "--idempotency-key", record["idempotency_key"],
                            "--message-file", record["message_file"])
        directory = prepared.get("request_directory")
        if not isinstance(directory, str):
            raise LocalFlowError(f"prepare lacked request_directory: {prepared}")
        record.update({"state": "PREPARED", "request_directory": directory})
        write_json(LEDGER, ledger)
    if not directory:
        return {"day": day, **record}
    event = _courier("reconcile" if reconcile else "status", directory)
    if event.get("state_class") == "COMPLETED" or event.get("event") == "response_received":
        record["state"] = "COMPLETED"
        write_json(LEDGER, ledger)
    return {"day": day, "local_state": record["state"], "courier": event}
