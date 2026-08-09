from __future__ import annotations

import base64
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
import re
import sqlite3
import subprocess
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

ADDRESS = "icywoods.1@gmail.com"
PREFIX = "[GC-BRIDGE]"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


def now() -> str:
    return datetime.now(UTC).isoformat()


def safe_name(name: str, fallback: str = "attachment") -> str:
    name = Path(name.replace("\\", "/")).name.strip().rstrip(". ")
    name = re.sub(r"[<>:\\|?*\x00-\x1f]", "_", name)
    if not name or name.upper().split(".")[0] in RESERVED or name in {".", ".."}:
        return fallback
    return name[:180]


def task_slug(subject: str, message_id: str) -> str:
    text = re.sub(r"^\[GC-BRIDGE\](?:\[[A-Z]+\])?\s*", "", subject, flags=re.I)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", text).strip("-.")
    return (slug[:80] or f"message-{message_id}")


def extract_headers(message: dict[str, Any]) -> dict[str, str]:
    return {h["name"].lower(): h["value"] for h in message.get("payload", {}).get("headers", [])}


def is_protocol_message(message: dict[str, Any]) -> bool:
    headers = extract_headers(message)
    subject = headers.get("subject", "")
    sender = headers.get("from", "").lower()
    recipient = headers.get("to", "").lower()
    return subject.upper().startswith(PREFIX) and ADDRESS in sender and ADDRESS in recipient


def protocol_type(subject: str) -> str:
    match = re.match(r"^\[GC-BRIDGE\]\[([A-Z]+)\]", subject, re.I)
    return match.group(1).upper() if match else "UNKNOWN"


@dataclass(frozen=True)
class Paths:
    root: Path

    @property
    def runtime(self) -> Path: return self.root / ".bridge"
    @property
    def inbox(self) -> Path: return self.root / "coordination" / "inbox"
    @property
    def db(self) -> Path: return self.runtime / "state.sqlite"
    @property
    def status(self) -> Path: return self.runtime / "status.json"
    @property
    def lock(self) -> Path: return self.runtime / "courier.lock"
    @property
    def daemon_lock(self) -> Path: return self.runtime / "daemon.lock"
    @property
    def log(self) -> Path: return self.runtime / "logs" / "courier.log"
    @property
    def autostart(self) -> Path: return self.runtime / "autostart.json"


class State:
    def __init__(self, paths: Paths):
        paths.runtime.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(paths.db)
        self.conn.execute("CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, unit TEXT NOT NULL, committed INTEGER NOT NULL DEFAULT 0, pushed INTEGER NOT NULL DEFAULT 0, error TEXT, received_at TEXT NOT NULL)")
        self.conn.commit()

    def get(self, message_id: str):
        return self.conn.execute("SELECT id, unit, committed, pushed FROM messages WHERE id=?", (message_id,)).fetchone()

    def record(self, message_id: str, unit: str) -> None:
        self.conn.execute("INSERT OR IGNORE INTO messages(id,unit,received_at) VALUES(?,?,?)", (message_id, unit, now())); self.conn.commit()

    def mark(self, message_id: str, *, committed: bool | None = None, pushed: bool | None = None, error: str | None = None) -> None:
        sets, values = [], []
        for key, value in (("committed", committed), ("pushed", pushed), ("error", error)):
            if value is not None: sets.append(f"{key}=?"); values.append(int(value) if isinstance(value, bool) else value)
        if sets: self.conn.execute(f"UPDATE messages SET {', '.join(sets)} WHERE id=?", (*values, message_id)); self.conn.commit()

    def pending_push(self): return self.conn.execute("SELECT id FROM messages WHERE committed=1 AND pushed=0").fetchall()
    def close(self): self.conn.close()


@contextmanager
def sync_lock(paths: Paths, timeout: float = 30.0) -> Iterator[None]:
    paths.runtime.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(paths.lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); break
        except FileExistsError:
            try:
                owner = int(paths.lock.read_text(encoding="ascii").strip())
                if not pid_alive(owner): paths.lock.unlink(); continue
            except (OSError, ValueError): pass
            if time.monotonic() >= deadline: raise RuntimeError("another gc-bridge sync is active")
            time.sleep(0.1)
    try:
        os.write(fd, str(os.getpid()).encode()); yield
    finally:
        os.close(fd)
        try: paths.lock.unlink()
        except FileNotFoundError: pass


@contextmanager
def daemon_lock(paths: Paths) -> Iterator[None]:
    paths.runtime.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(paths.daemon_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        try:
            owner = int(paths.daemon_lock.read_text(encoding="ascii").strip())
            if not pid_alive(owner): paths.daemon_lock.unlink(); fd = os.open(paths.daemon_lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            else: raise RuntimeError("another gc-bridge daemon is active")
        except (OSError, ValueError) as exc:
            raise RuntimeError("another gc-bridge daemon is active") from exc
    try:
        os.write(fd, str(os.getpid()).encode()); yield
    finally:
        os.close(fd)
        try: paths.daemon_lock.unlink()
        except FileNotFoundError: pass


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent) as f:
        json.dump(data, f, indent=2, sort_keys=True); f.flush(); os.fsync(f.fileno()); temp = Path(f.name)
    os.replace(temp, path)


def write_status(paths: Paths, **values: Any) -> None:
    prior = {}
    try: prior = json.loads(paths.status.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): pass
    prior.update(values); atomic_json(paths.status, prior)


def write_autostart(paths: Paths, **values: Any) -> None:
    prior = {}
    try: prior = json.loads(paths.autostart.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): pass
    prior.update(values); atomic_json(paths.autostart, prior)


def pid_alive(pid: int) -> bool:
    try: os.kill(pid, 0)
    except OSError: return False
    return True


def status(paths: Paths, stale_seconds: int = 90) -> dict[str, Any]:
    try: data = json.loads(paths.status.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): return {"state": "STOPPED"}
    try: autostart = json.loads(paths.autostart.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError): autostart = None
    # Versions before the Run-key fallback reported a Scheduler ACL failure as
    # a daemon error. Treat that precise legacy record as stopped, not unhealthy.
    if (data.get("state") == "error" and data.get("last_error", "").strip() == "ERROR: Access is denied."
            and autostart and autostart.get("method") == "registry-run-key"):
        data["state"] = "stopped"; data["last_error"] = None
    pid = data.get("pid")
    try: age = time.time() - datetime.fromisoformat(data["last_poll_at"]).timestamp()
    except (KeyError, ValueError): age = float("inf")
    data["state"] = "HEALTHY" if data.get("state") == "running" and isinstance(pid, int) and pid_alive(pid) and age <= stale_seconds else ("ERROR" if data.get("last_error") else "STALE")
    data["heartbeat_age_seconds"] = round(age, 1) if age != float("inf") else None
    data["autostart"] = autostart
    return data


def git_environment() -> dict[str, str]:
    """Do not inherit a dead localhost proxy into durable courier retries."""
    env = os.environ.copy()
    for key in ("GIT_HTTP_PROXY", "GIT_HTTPS_PROXY", "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env.pop(key, None)
    return env


def git(paths: Paths, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", str(paths.root), *args], text=True, capture_output=True, check=False, env=git_environment())


def assert_chat_repo(paths: Paths) -> None:
    branch = git(paths, "branch", "--show-current").stdout.strip()
    remote = git(paths, "remote", "get-url", "origin").stdout.strip()
    if branch != "chat" or "WD-nanophotonics/GenericChess" not in remote:
        raise RuntimeError("refusing Git operation: expected GenericChess origin and chat branch")


def commit_and_push(paths: Paths, state: State, message_id: str, unit: Path) -> None:
    assert_chat_repo(paths)
    row = state.get(message_id)
    if not row[2]:
        relative = unit.relative_to(paths.root)
        if git(paths, "add", "--", str(relative)).returncode: raise RuntimeError("git add failed")
        result = git(paths, "commit", "-m", f"Receive GC bridge task {unit.name}", "--", str(relative))
        if result.returncode: raise RuntimeError(f"git commit failed: {result.stderr.strip()}")
        state.mark(message_id, committed=True)
    result = git(paths, "push", "origin", "chat")
    if result.returncode:
        state.mark(message_id, error=f"pending push: {result.stderr.strip()[-300:]}")
        return
    state.mark(message_id, pushed=True, error="")


def parts(payload: dict[str, Any]):
    for part in payload.get("parts", []):
        yield from parts(part)
    if payload.get("filename") and payload.get("body", {}).get("attachmentId"):
        yield payload


def existing_unit(paths: Paths, message_id: str) -> Path | None:
    """Find a published unit after a crash between rename and SQLite update."""
    if not paths.inbox.exists(): return None
    for manifest in paths.inbox.glob("*/manifest.json"):
        try:
            if json.loads(manifest.read_text(encoding="utf-8")).get("message_id") == message_id:
                return manifest.parent
        except (OSError, json.JSONDecodeError):
            continue
    return None


def receive_message(service: Any, paths: Paths, state: State, summary: dict[str, str]) -> bool:
    message_id = summary["id"]
    row = state.get(message_id)
    if row:
        if not row[2]: commit_and_push(paths, state, message_id, paths.inbox / row[1])
        return False
    recovered = existing_unit(paths, message_id)
    if recovered:
        state.record(message_id, recovered.name)
        commit_and_push(paths, state, message_id, recovered)
        return False
    message = service.users().messages().get(userId="me", id=message_id, format="full").execute()
    if not is_protocol_message(message): return False
    headers = extract_headers(message); subject = headers.get("subject", "")
    unit_name = task_slug(subject, message_id); final = paths.inbox / unit_name
    if final.exists(): unit_name = f"{unit_name}-{message_id[:12]}"; final = paths.inbox / unit_name
    paths.inbox.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="receive-", dir=paths.runtime) as tmp:
        stage = Path(tmp) / unit_name; stage.mkdir()
        attachments = []
        used: set[str] = set()
        for index, part in enumerate(parts(message.get("payload", {})), 1):
            filename = safe_name(part["filename"], f"attachment-{index}")
            while filename.lower() in used: filename = f"{Path(filename).stem}-{index}{Path(filename).suffix}"
            used.add(filename.lower())
            blob = service.users().messages().attachments().get(userId="me", messageId=message_id, id=part["body"]["attachmentId"]).execute()["data"]
            data = base64.urlsafe_b64decode(blob + "=" * (-len(blob) % 4)); target = stage / filename
            target.write_bytes(data)
            attachments.append({"filename": filename, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
        manifest = {"message_id": message_id, "thread_id": message.get("threadId"), "subject": subject, "timestamp": message.get("internalDate"), "downloaded_at": now(), "protocol": PREFIX, "type": protocol_type(subject), "attachments": attachments}
        atomic_json(stage / "manifest.json", manifest)
        os.replace(stage, final)
    state.record(message_id, unit_name)
    commit_and_push(paths, state, message_id, final)
    return True


def gmail_service(config_dir: Path):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    token = config_dir / "token.json"
    if not token.exists(): raise RuntimeError("not authorized; run gc-bridge auth")
    creds = Credentials.from_authorized_user_file(token, SCOPES)
    if creds.expired and creds.refresh_token: creds.refresh(Request()); token.write_text(creds.to_json(), encoding="utf-8")
    if not creds.valid: raise RuntimeError("OAuth token is invalid; run gc-bridge auth")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def configure_logging(paths: Paths) -> None:
    paths.log.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("gc_bridge")
    if not logger.handlers:
        handler = RotatingFileHandler(paths.log, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler); logger.setLevel(logging.INFO)


def sync(paths: Paths, config_dir: Path) -> int:
    with sync_lock(paths):
        state = State(paths)
        try:
            service = gmail_service(config_dir)
            query = f'from:{ADDRESS} to:{ADDRESS} subject:"{PREFIX}" has:attachment'
            response = service.users().messages().list(userId="me", q=query, maxResults=100).execute()
            received = sum(receive_message(service, paths, state, item) for item in response.get("messages", []))
            for (message_id,) in state.pending_push():
                row = state.get(message_id); commit_and_push(paths, state, message_id, paths.inbox / row[1])
            return received
        finally: state.close()
