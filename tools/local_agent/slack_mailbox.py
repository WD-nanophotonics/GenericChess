"""Periodic Slack mailbox. No Dot calls, scheduler, polling or network client.

The calling Agent performs one logical paginated read and at most one send.
Exact raw tool output is saved privately before parsing or accepting comments.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import uuid
from .common import ROOT, STATE, LocalFlowError, git, read_json, write_json

HOME = STATE / "slack" / "mailbox"
CONFIG = STATE / "slack.json"

def digest(value):
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()

def canonical(text):
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())

def check():
    c = read_json(CONFIG)
    if c.get("communication_mode") != "chat_mailbox":
        raise LocalFlowError("migrate this role to chat_mailbox first")
    if c.get("stopped"):
        raise LocalFlowError("Slack communication is stopped for this role")
    role = read_json(STATE / "role.json")
    if role.get("role") not in {"PRIMARY_SANDBOX", "DEV_AUX", "DEEPSEEK_AUX"}:
        raise LocalFlowError("unknown project role")
    if git("branch", "--show-current") != role.get("branch"):
        raise LocalFlowError("role/branch mismatch")
    if not all(c.get(k) for k in ("team_id", "channel_id", "sender_id")):
        raise LocalFlowError("verified Slack route missing")
    return c, role

def migrate():
    role = read_json(STATE / "role.json")
    if role.get("role") not in {"PRIMARY_SANDBOX", "DEV_AUX", "DEEPSEEK_AUX"} or git("branch", "--show-current") != role.get("branch"):
        raise LocalFlowError("migrate only the calling role's own checkout")
    backup = HOME / "migration-original-config.json"
    git("check-ignore", str(backup.relative_to(ROOT)))
    if not backup.exists():
        write_json(backup, {"slack": read_json(CONFIG), "advisor": read_json(STATE / "advisor.json")})
    slack = read_json(CONFIG)
    slack.update(communication_mode="chat_mailbox", dot_enabled=False, mention_user_id=None)
    write_json(CONFIG, slack)
    advisor = read_json(STATE / "advisor.json")
    advisor.update(enabled=False, communication_mode="chat_mailbox", dot_enabled=False,
                   mode_reason="User2026-10-20: periodic read/save/report to Chat; no realtime Dot dispatch")
    write_json(STATE / "advisor.json", advisor)
    return {"role": role["role"], "communication_mode": "chat_mailbox",
            "dot_enabled": False, "historical_ledger_preserved": True,
            "schedule_changed": False, "stops_preserved": True}

def location(probe_id):
    if not re.fullmatch(r"GC-MAIL-[A-Za-z0-9-]+", probe_id):
        raise LocalFlowError("invalid probe ID")
    return HOME / "probes" / (probe_id + ".json")

def load(probe_id):
    r = read_json(location(probe_id))
    if not r:
        raise LocalFlowError("unknown probe")
    return r

def save(r):
    write_json(location(r["probe_id"]), r)
    return r

def start():
    c, role = check()
    state = read_json(HOME / "state.json")
    if state.get("active"):
        old = load(state["active"])
        if old["phase"] != "SENT":
            return {**old, "resume": True, "automatic_retry_available": False}
    rid = "GC-MAIL-" + uuid.uuid4().hex
    r = dict(probe_id=rid, phase="READ_REQUIRED", role=role["role"],
             team_id=c["team_id"], channel_id=c["channel_id"], sender_id=c["sender_id"],
             previous_coverage=state.get("coverage"), decisions={}, comments=[],
             required_threads=state.get("required_threads", []))
    save(r)
    write_json(HOME / "state.json", {**state, "active": rid})
    return r

def page_data(raw):
    if raw.get("isError"):
        raise LocalFlowError("Slack read failed")
    if "messages" in raw:
        return raw
    for block in raw.get("content", []):
        if block.get("type") == "text":
            try:
                data = json.loads(block["text"])
            except (ValueError, KeyError):
                continue
            if "messages" in data:
                return data
    raise LocalFlowError("Slack page has no message data")

def messages(raw):
    data = page_data(raw)
    if isinstance(data["messages"], list):
        return data["messages"]
    text = data["messages"]
    channel = list(re.finditer(
        r"=== Message from [^\n]*\((U[A-Z0-9]+)\) at [^\n]+ ===\s*\nMessage TS: (\d+\.\d+)\n", text))
    if channel:
        return [dict(user=m[1], ts=m[2],
                     text=re.sub(r"\nThread: [^\n]+\s*$", "", text[m.end():channel[i+1].start() if i+1<len(channel) else len(text)]).strip())
                for i, m in enumerate(channel)]
    headers = list(re.finditer(r"From: [^\n]*\((U[A-Z0-9]+)\)\nTime: [^\n]*\nMessage TS: (\d+\.\d+)\n", text))
    if not headers:
        if "no messages" in text.lower():
            return []
        raise LocalFlowError("unrecognized Slack message rendering")
    result = []
    for i, m in enumerate(headers):
        body = text[m.end():headers[i+1].start() if i+1<len(headers) else len(text)]
        body = re.split(r"\n(?:--- Reply \d+ of \d+ ---|=== THREAD REPLIES)", body)[0]
        result.append(dict(user=m[1], ts=m[2], text=body.strip()))
    return result

def is_chat(text):
    return bool(re.search(r"(?m)^(?:CHAT_Comments\b|TYPE=CHAT(?:_COMMENT|_REPLY|_NOTE|_ASSESSMENT)?\s*$)", text))

def ingest(probe_id, snapshot_file):
    check()
    r = load(probe_id)
    if r["phase"] not in {"READ_REQUIRED", "SEND_UNCERTAIN"}:
        raise LocalFlowError("this probe already completed its logical read")
    raw = Path(snapshot_file).read_bytes()
    target = HOME / "raw" / (digest(raw) + ".json")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(raw)
    snapshot = json.loads(raw.decode("utf-8-sig"))
    if snapshot.get("channel_id") != r["channel_id"] or snapshot.get("team_id") != r["team_id"]:
        raise LocalFlowError("snapshot belongs to another Slack route; original retained")
    if not snapshot.get("coverage_complete"):
        raise LocalFlowError("logical read must cover the previous boundary and complete relevant threads")
    thread_pages = snapshot.get("thread_pages", {})
    if not set(r["required_threads"]).issubset(thread_pages):
        raise LocalFlowError("tracked relevant thread missing from logical read")
    for pages in thread_pages.values():
        if not pages or "There are more messages" in page_data(pages[-1]).get("pagination_info", ""):
            raise LocalFlowError("relevant thread pagination is incomplete")
    pages = snapshot.get("channel_pages", [])
    if not pages:
        raise LocalFlowError("channel read required")
    channel_messages = [m for p in pages for m in messages(p)]
    previous = r.get("previous_coverage")
    if "There are more messages" in page_data(pages[-1]).get("pagination_info", ""):
        if not previous or not any(float(m["ts"]) <= float(previous) for m in channel_messages):
            raise LocalFlowError("channel pagination has not reached the previous coverage boundary")
    all_messages = []
    for page in pages:
        all_messages.extend(messages(page))
    chat_threads = set(read_json(HOME / "state.json").get("chat_threads", []))
    for thread, items in thread_pages.items():
        thread_messages = [m for page in items for m in messages(page)]
        if any(m["ts"] == thread and is_chat(m.get("text", "")) for m in thread_messages):
            chat_threads.add(thread)
        all_messages.extend({**m, "thread_ts": thread, "chat_thread": thread in chat_threads}
                            for m in thread_messages)
    # Raw bytes are durable before any cursor or acceptance decision changes.
    state = read_json(HOME / "state.json")
    seen = state.get("seen", {})
    candidates = {(m["ts"], m["sha256"]): m for m in state.get("backlog", {}).values()}
    sent_matches = []
    for m in all_messages:
        body = m.get("text", "")
        if r["phase"] == "SEND_UNCERTAIN" and m.get("user") == r["sender_id"] and r["probe_id"] in body:
            if canonical(r["message"]) in canonical(body):
                sent_matches.append(m)
        agent_post = bool(re.search(r"(?m)^(?:TYPE=AGENT|AGENT_ID=|PRIMARY_SANDBOX|DEV_AUX|DEEPSEEK_AUX)", body))
        if is_chat(body) or (m.get("chat_thread") and not agent_post):
            h = digest(body)
            for key in list(candidates):
                if key[0] == m["ts"] and key[1] != h:
                    candidates.pop(key)
            if seen.get(m["ts"]) != h:
                candidates[(m["ts"], h)] = {**m, "sha256": h}
            seen[m["ts"]] = h
    times = [m["ts"] for m in channel_messages] + ([previous] if previous else [])
    coverage = max(times, key=float, default=None)
    r.update(raw_snapshot=str(target), raw_sha256=digest(raw), coverage=coverage,
             comments=list(candidates.values()))
    state.update(seen=seen, coverage=coverage, chat_threads=sorted(chat_threads), backlog={m["ts"]: m for m in candidates.values()},
                 required_threads=sorted(set(state.get("required_threads", [])) | set(thread_pages)))
    if r["phase"] == "SEND_UNCERTAIN":
        if len({m["ts"] for m in sent_matches}) == 1:
            r.update(phase="SENT", message_ts=sent_matches[0]["ts"], delivery_basis="next_probe_readback")
        else:
            r["uncertain_send_reconciled"] = False
    else:
        r["phase"] = "READ_SAVED"
    write_json(HOME / "state.json", state)
    return save(r)

def decide(probe_id, ts, sha256, decision, reason):
    check()
    r = load(probe_id)
    if decision not in {"adopt", "defer", "reject"} or not reason.strip():
        raise LocalFlowError("record an evidence-based adopt/defer/reject decision")
    if not any(m["ts"] == ts and m["sha256"] == sha256 for m in r["comments"]):
        raise LocalFlowError("decision must reference an exact saved message revision")
    key = ts + ":" + sha256
    r["decisions"][key] = dict(decision=decision, reason=reason, executed=False)
    state = read_json(HOME / "state.json")
    state.setdefault("reviews", {})[key] = r["decisions"][key]
    if decision != "defer":
        state.setdefault("backlog", {}).pop(ts, None)
    write_json(HOME / "state.json", state)
    return save(r)

def prepare(probe_id, report_file):
    check()
    r = load(probe_id)
    if r["phase"] != "READ_SAVED":
        raise LocalFlowError("one completed read required; uncertain sends reconcile next probe")
    if any(m["ts"] + ":" + m["sha256"] not in r["decisions"] for m in r["comments"]):
        raise LocalFlowError("unreviewed Chat comments must be accepted, deferred or rejected")
    report = Path(report_file).read_text(encoding="utf-8-sig").strip()
    if not report or re.search(r"<@|@dot|RECIPIENT=DOT|TYPE=DOT_REPLY", report, re.I):
        raise LocalFlowError("mailbox report must be nonempty and contain no Dot mentions or requests")
    reviewed = "; ".join(k.split(":")[0] + "=" + d["decision"] for k,d in r["decisions"].items()) or "none"
    message = (f'TYPE=AGENT_MAILBOX_REPORT\nPROJECT=GenericChess\nAGENT_ID={r["role"]}\n'
               f'RECIPIENT=CHAT\nPROBE_ID={probe_id}\nCOMMITTED_BASE_SHA={git("rev-parse", "HEAD")}\n'
               f'REVIEWED_COMMENTS={reviewed}\n\n{report}')
    if len(message) > 4800:
        raise LocalFlowError("report exceeds one Slack message; use checked fixed-SHA evidence links")
    r.update(phase="PREPARED", message=message, payload_sha256=digest(message))
    return save(r)

def begin_send(probe_id):
    check()
    r = load(probe_id)
    if r["phase"] != "PREPARED":
        return {**r, "action": "reconcile_at_next_probe", "automatic_retry_available": False}
    if digest(r["message"]) != r["payload_sha256"]:
        raise LocalFlowError("immutable report changed")
    r["phase"] = "SEND_UNCERTAIN"
    save(r)
    return {**r, "action": "slack_send_message", "automatic_retry_available": False}

def bind(probe_id, message_ts, receipt_file):
    check()
    r = load(probe_id)
    if r["phase"] != "SEND_UNCERTAIN" or not re.fullmatch(r"\d+\.\d+", message_ts):
        raise LocalFlowError("binding requires one dispatched report and valid Slack timestamp")
    raw = Path(receipt_file).read_bytes()
    target = HOME / "raw" / (digest(raw) + ".json")
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(raw)
    receipt = json.loads(raw.decode("utf-8-sig"))
    if receipt.get("isError"):
        raise LocalFlowError("send receipt reports failure; keep uncertain until next probe")
    serialized = re.sub(r"\\+/", "/", json.dumps(receipt, ensure_ascii=False))
    link = f'/archives/{r["channel_id"]}/p{message_ts.replace(".", "")}'
    structured = receipt.get("structuredContent") or receipt
    if not (structured.get("channel_id") == r["channel_id"] and structured.get("message_ts") == message_ts) and link not in serialized:
        raise LocalFlowError("receipt does not verify the expected channel and message timestamp")
    r.update(phase="SENT", message_ts=message_ts, receipt_sha256=digest(raw),
             delivery_basis="successful_send_receipt", chat_read=False, chat_executed=False)
    state = read_json(HOME / "state.json")
    state["required_threads"] = sorted(set(state.get("required_threads", [])) | {message_ts})
    write_json(HOME / "state.json", state)
    return save(r)

