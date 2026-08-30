from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
from typing import Any, Sequence


PROJECT_ID = "GENERICCHESS"
WORK_BOOTSTRAP = """Issue the next concrete GenericChess work order.

Inspect the current published sandbox SHA and choose one bounded, useful next
step toward a product-ready GenericChess. Return COMPLETE if no further work is
currently needed, or BLOCKED only when user action is genuinely required.
"""
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
CONTROL_FIELDS = {
    "GENERICCHESS_STATUS",
    "GENERICCHESS_CANDIDATE_SHA",
    "GENERICCHESS_PROMOTION",
}
CONTROL_STATUSES = {"CONTINUE", "COMPLETE", "BLOCKED"}
PROMOTION_VALUES = {"APPROVE", "HOLD"}
WORK_ORDER_ID = re.compile(r"(?m)^WORK_ORDER_ID=([^\s]+)\s*$")
INLINE_CHAT_REFERENCE_THRESHOLD = 24 * 1024


class FlowError(RuntimeError):
    pass


def run(
    argv: Sequence[str],
    *,
    cwd: Path,
    check: bool = True,
    env: dict[str, str] | None = None,
    creationflags: int = 0,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(argv), cwd=cwd, text=True, encoding="utf-8", errors="replace",
        capture_output=True, env=env, creationflags=creationflags,
    )
    if check and result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise FlowError(f"command failed ({result.returncode}): {' '.join(argv)}\n{detail}")
    return result


def git(root: Path, *args: str, check: bool = True, env: dict[str, str] | None = None) -> str:
    return run(
        ("git", "-c", f"safe.directory={root.resolve()}", *args),
        cwd=root,
        check=check,
        env=env,
    ).stdout.strip()


def git_ok(root: Path, *args: str) -> bool:
    return run(
        ("git", "-c", f"safe.directory={root.resolve()}", *args),
        cwd=root,
        check=False,
    ).returncode == 0


def repository_root(start: Path | None = None) -> Path:
    start = (start or Path.cwd()).resolve()
    value = git(start, "rev-parse", "--show-toplevel")
    return Path(value).resolve()


def worktrees(root: Path) -> dict[str, Path]:
    result: dict[str, Path] = {}
    current_path: Path | None = None
    for line in git(root, "worktree", "list", "--porcelain").splitlines():
        if line.startswith("worktree "):
            current_path = Path(line[9:]).resolve()
        elif line.startswith("branch refs/heads/") and current_path is not None:
            result[line.removeprefix("branch refs/heads/")] = current_path
    return result


def branch(root: Path) -> str:
    return git(root, "branch", "--show-current")


def sha(root: Path, ref: str = "HEAD") -> str:
    return git(root, "rev-parse", ref)


def clean(root: Path) -> bool:
    return not git(root, "status", "--porcelain", "--untracked-files=all")


def require_clean(root: Path) -> None:
    if not clean(root):
        raise FlowError(f"working tree is not clean: {root}")


def fetch(root: Path, branch_name: str | None = None) -> None:
    args = ["fetch", "origin"]
    if branch_name:
        args.append(branch_name)
    git(root, *args)


def synced(root: Path, branch_name: str) -> bool:
    return sha(root) == sha(root, f"origin/{branch_name}")


def require_synced(root: Path, branch_name: str) -> None:
    fetch(root, branch_name)
    if not synced(root, branch_name):
        raise FlowError(
            f"{branch_name} is not synchronized: local={sha(root)} "
            f"remote={sha(root, f'origin/{branch_name}') }"
        )


def sandbox_root(root: Path) -> Path:
    trees = worktrees(root)
    if set(trees) != {"master", "sandbox"}:
        raise FlowError(f"expected exactly master and sandbox worktrees, found {sorted(trees)}")
    return trees["sandbox"]


def runtime_dir(root: Path, *, create: bool = True) -> Path:
    path = sandbox_root(root) / ".generic_chess_flow"
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def state_path(root: Path) -> Path:
    return runtime_dir(root, create=False) / "session.json"


def load_state(root: Path, *, required: bool = True) -> dict[str, Any]:
    path = state_path(root)
    if not path.exists():
        if required:
            raise FlowError("no active GenericChess flow session")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FlowError(f"invalid flow state: {path}") from exc
    if not isinstance(value, dict):
        raise FlowError(f"invalid flow state: {path}")
    return value


def active_state(root: Path) -> dict[str, Any]:
    state = load_state(root)
    if state.get("active") is not True:
        raise FlowError("no active GenericChess flow session")
    return state


def require_worker_write_authority(state: dict[str, Any], root: Path | None = None) -> None:
    if state.get("recovery_state") in {"ESCALATED", "HUMAN_REQUIRED"}:
        escalation_id = state.get("escalation_id")
        if root is not None and isinstance(escalation_id, str):
            claim_path = escalation_root(root) / escalation_id / "claim.json"
            if claim_path.is_file():
                claim = json.loads(claim_path.read_text(encoding="utf-8"))
                if os.environ.get("CODEX_THREAD_ID") == claim.get("supervisor_thread_id"):
                    return
        raise FlowError("repository writes are frozen until Supervisor resolution")


def save_state(root: Path, state: dict[str, Any]) -> None:
    path = runtime_dir(root) / "session.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def install_hooks(root: Path) -> None:
    git(root, "config", "core.hooksPath", ".githooks")


def python_for(root: Path) -> str:
    candidate = root / ".venv" / "Scripts" / "python.exe"
    return str(candidate) if candidate.exists() else sys.executable


def run_tests(root: Path, targets: list[str]) -> None:
    command = [python_for(root), "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    command.extend(targets)
    with heavy_lock(root):
        result = run(
            command,
            cwd=root,
            check=False,
            creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0),
        )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if result.returncode:
        raise FlowError(f"tests failed with exit code {result.returncode}")


def courier_launcher(root: Path) -> Path:
    launcher = root.parent / "GmailCourier" / "scripts" / "chat-courier.cmd"
    if not launcher.is_file():
        raise FlowError(f"ChatCourier launcher not found: {launcher}")
    return launcher


def courier(root: Path, *args: str, stream: bool = False,
            allow_failure: bool = False) -> dict[str, Any]:
    comspec = os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe")
    process = subprocess.Popen(
        (comspec, "/d", "/c", str(courier_launcher(root)), *args),
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    events: list[dict[str, Any]] = []
    output: list[str] = []
    assert process.stdout is not None
    for raw in process.stdout:
        line = raw.rstrip("\r\n")
        output.append(line)
        if stream:
            print(line, flush=True)
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    returncode = process.wait()
    if allow_failure and events:
        return events[-1]
    if returncode or not events:
        detail = "\n".join(output).strip()
        next_action = "stop and report the Courier terminal event to the user"
        if events and events[-1].get("event") in {
            "queue_timeout", "queue_recovery_required", "courier_interrupted",
            "response_timeout", "response_protocol_error",
        }:
            next_action = "run generic-chess-flow.cmd resume with the same request"
        raise FlowError(
            f"ChatCourier failed ({returncode}): {detail}\nNEXT_ACTION={next_action}"
        )
    final = events[-1]
    if not final.get("ok", False):
        raise FlowError(f"ChatCourier terminal event: {json.dumps(final, ensure_ascii=False)}")
    return final


def courier_capabilities(root: Path) -> dict[str, Any]:
    return courier(root, "courier_capabilities")


def parse_control_footer(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in CONTROL_FIELDS:
            found[key] = value.strip()
    return found


def validate_control_footer(text: str) -> dict[str, str]:
    control = parse_control_footer(text)
    missing = CONTROL_FIELDS - control.keys()
    if missing:
        raise FlowError("Courier response is missing control fields: " + ", ".join(sorted(missing)))
    if control["GENERICCHESS_STATUS"] not in CONTROL_STATUSES:
        raise FlowError("Courier response has an invalid GENERICCHESS_STATUS")
    candidate = control["GENERICCHESS_CANDIDATE_SHA"]
    if candidate != "NONE" and not FULL_SHA.fullmatch(candidate):
        raise FlowError("Courier response has an invalid GENERICCHESS_CANDIDATE_SHA")
    if control["GENERICCHESS_PROMOTION"] not in PROMOTION_VALUES:
        raise FlowError("Courier response has an invalid GENERICCHESS_PROMOTION")
    return control


def recovery_event(state: dict[str, Any], name: str, **values: Any) -> None:
    timeline = state.setdefault("recovery_timeline", [])
    timeline.append({"event": name, "at": time.time(), **values})
    if len(timeline) > 100:
        del timeline[:-100]


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)


def update_response_state(root: Path, state: dict[str, Any], event: dict[str, Any],
                          *, source: str = "normal") -> None:
    if event.get("event") in {"response_received", "response_duplicate", "courier_latest_response_captured"}:
        response_path = event.get("response_path")
        if not isinstance(response_path, str):
            raise FlowError("Courier response event did not include response_path")
        response = Path(response_path)
        text = response.read_text(encoding="utf-8-sig")
        state["last_response_path"] = str(response)
        control = validate_control_footer(text)
        work_order = WORK_ORDER_ID.search(text)
        state["chat_control"] = control
        state["last_work_order_id"] = work_order.group(1) if work_order else None
        state["work_order_active"] = control["GENERICCHESS_STATUS"] == "CONTINUE"
        state["last_response_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        state["last_response_source"] = source
        state["active_request_directory"] = None
        state["recovery_state"] = "RECOVERED" if source != "normal" else "IDLE"
        recovery_event(state, "response_accepted", source=source,
                       response_sha256=state["last_response_sha256"])
        save_state(root, state)
        print(text)


def chat_message_body(root: Path, source: Path) -> str:
    body = source.read_text(encoding="utf-8-sig")
    if len(body.encode("utf-8")) <= INLINE_CHAT_REFERENCE_THRESHOLD:
        return body
    sandbox = sandbox_root(root).resolve()
    resolved = source.resolve()
    try:
        relative = resolved.relative_to(sandbox)
    except ValueError as exc:
        raise FlowError(
            "large Courier reports must be committed inside the sandbox and published before closeout"
        ) from exc
    relative_git = relative.as_posix()
    if not git_ok(sandbox, "ls-files", "--error-unmatch", "--", relative_git):
        raise FlowError("large Courier report is not tracked by Git")
    if git(sandbox, "diff", "--name-only", "HEAD", "--", relative_git):
        raise FlowError("large Courier report differs from the committed version")
    return (
        "Review the large report from the already published immutable Git checkpoint.\n"
        f"REPOSITORY={git(sandbox, 'remote', 'get-url', 'origin')}\n"
        f"COMMIT={sha(sandbox)}\n"
        f"PATH={relative_git}\n"
        "Do not request the report body through the chat composer; inspect it at this exact commit.\n"
    )


def dispatch_message(root: Path, state: dict[str, Any], source: Path, purpose: str) -> None:
    sandbox = sandbox_root(root)
    require_clean(sandbox)
    require_synced(sandbox, "sandbox")
    body = chat_message_body(root, source)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    key = f"{purpose}-{sha(sandbox)[:12]}-{digest[:12]}"
    generated = runtime_dir(root) / f"{key}.txt"
    generated.write_text(
        body.rstrip()
        + "\n\nRepository authority context:\n"
        + f"PROJECT_ID={PROJECT_ID}\n"
        + f"MASTER_SHA={sha(worktrees(root)['master'])}\n"
        + f"SANDBOX_SHA={sha(sandbox)}\n"
        + "The referenced sandbox SHA is committed and published to origin/sandbox.\n"
        + "End the response with exactly these control fields:\n"
        + "GENERICCHESS_STATUS=CONTINUE|COMPLETE|BLOCKED\n"
        + "GENERICCHESS_CANDIDATE_SHA=<40-hex-sha-or-NONE>\n"
        + "GENERICCHESS_PROMOTION=APPROVE|HOLD\n",
        encoding="utf-8",
    )
    prepared = courier(
        root, "courier_prepare", "--project-id", PROJECT_ID,
        "--idempotency-key", key, "--message-file", str(generated),
    )
    request_directory = prepared.get("request_directory")
    if not isinstance(request_directory, str):
        raise FlowError("Courier prepare did not return a request directory")
    state["active_request_directory"] = request_directory
    state["last_request_key"] = key
    save_state(root, state)
    event = courier(root, "courier_dispatch", request_directory, stream=True)
    update_response_state(root, state, event)


def command_status(root: Path, _args: argparse.Namespace) -> None:
    trees = worktrees(root)
    payload: dict[str, Any] = {"worktrees": {}, "topology_ok": False}
    for name, path in trees.items():
        entry: dict[str, Any] = {"path": str(path), "sha": sha(path), "clean": clean(path)}
        remote = f"origin/{name}"
        exists = git(path, "rev-parse", "--verify", remote, check=False)
        if exists:
            entry["remote_sha"] = sha(path, remote)
            entry["synced"] = entry["sha"] == entry["remote_sha"]
        payload["worktrees"][name] = entry
    if set(trees) == {"master", "sandbox"}:
        payload["topology_ok"] = git_ok(
            root, "merge-base", "--is-ancestor", sha(trees["master"]), sha(trees["sandbox"])
        )
    session = load_state(root, required=False)
    payload["session"] = session
    if session.get("active") is True and session.get("mode") == "local":
        payload["courier"] = {"checked": False, "reason": "skipped_due_to_local_mode"}
    else:
        try:
            caps = courier_capabilities(root)
            payload["courier"] = {"available": True, "projects": caps.get("projects", [])}
        except FlowError as exc:
            payload["courier"] = {"available": False, "detail": str(exc)}
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


@contextmanager
def heavy_lock(root: Path):
    """Allow one low-priority GenericChess compute command at a time."""
    path = runtime_dir(root) / "heavy.lock"
    handle = path.open("a+b")
    if path.stat().st_size == 0:
        handle.write(b"0")
        handle.flush()
    handle.seek(0)
    try:
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:  # pragma: no cover - the workflow is Windows-only
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        handle.close()
        raise FlowError("another GenericChess heavy command is already running") from exc
    try:
        yield
    finally:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:  # pragma: no cover - the workflow is Windows-only
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def command_heavy(root: Path, args: argparse.Namespace) -> int:
    state = active_state(root)
    require_worker_write_authority(state, root)
    if branch(root) != "sandbox":
        raise FlowError("heavy must be run from the sandbox worktree")
    command = list(args.argv)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        raise FlowError("heavy requires a command after --")
    with heavy_lock(root):
        process = subprocess.Popen(
            command,
            cwd=root,
            creationflags=getattr(subprocess, "BELOW_NORMAL_PRIORITY_CLASS", 0),
        )
        return process.wait()


def command_start(root: Path, args: argparse.Namespace) -> None:
    previous = load_state(root, required=False)
    if previous.get("active"):
        if previous.get("mode") != args.mode:
            raise FlowError("an active session cannot change authority mode")
        raise FlowError("a GenericChess flow session is already active")
    install_hooks(root)
    trees = worktrees(root)
    for name in ("master", "sandbox"):
        require_clean(trees[name])
        require_synced(trees[name], name)
    state: dict[str, Any] = {
        "active": True,
        "mode": args.mode,
        "base_master_sha": sha(trees["master"]),
        "base_sandbox_sha": sha(trees["sandbox"]),
        "tested_shas": {},
        "active_request_directory": None,
        "work_order_active": False,
        "last_work_order_id": None,
        "recovery_state": "IDLE",
        "recovery_attempts": 0,
        "recovery_timeline": [],
        "last_probe": None,
        "escalation_id": None,
    }
    work_request_token = getattr(args, "work_request_token", None)
    if work_request_token:
        state["work_request_token"] = work_request_token
    if args.mode == "courier":
        caps = courier_capabilities(root)
        if PROJECT_ID not in caps.get("projects", []):
            raise FlowError(f"ChatCourier project is not configured: {PROJECT_ID}")
    save_state(root, state)
    if args.message_file:
        if args.mode != "courier":
            raise FlowError("--message-file is only valid in courier mode")
        dispatch_message(root, state, Path(args.message_file).resolve(), "start")
    else:
        print(json.dumps(state, indent=2, sort_keys=True))


def command_work(root: Path, _args: argparse.Namespace) -> None:
    """Start or recover the one-line Courier workflow without another state machine."""
    if branch(root) != "sandbox":
        raise FlowError("work must be run from the sandbox worktree")
    state = load_state(root, required=False)
    if state.get("active") is True:
        if state.get("mode") != "courier":
            raise FlowError(
                "a Local mode session is active; continue that task or finish it before Courier work"
            )
        if state.get("active_request_directory"):
            command_recover(root, _args)
            return
        response_path = state.get("last_response_path")
        if isinstance(response_path, str) and Path(response_path).is_file():
            print(Path(response_path).read_text(encoding="utf-8-sig"))
            print("NEXT_ACTION=execute this work order, then publish and closeout")
            return
        token = state.get("work_request_token")
        if not isinstance(token, str) or not token:
            token = uuid.uuid4().hex
            state["work_request_token"] = token
            save_state(root, state)
        source = runtime_dir(root) / "work-bootstrap.txt"
        source.write_text(f"{WORK_BOOTSTRAP}\nWORK_SESSION_ID={token}\n", encoding="utf-8")
        dispatch_message(root, state, source, "start")
        return

    token = uuid.uuid4().hex
    source = runtime_dir(root) / "work-bootstrap.txt"
    source.write_text(f"{WORK_BOOTSTRAP}\nWORK_SESSION_ID={token}\n", encoding="utf-8")
    command_start(
        root,
        argparse.Namespace(
            mode="courier", message_file=str(source), work_request_token=token
        ),
    )


def command_publish(root: Path, args: argparse.Namespace) -> None:
    if branch(root) != "sandbox":
        raise FlowError("publish must be run from the sandbox worktree")
    state = active_state(root)
    require_worker_write_authority(state, root)
    require_clean(root)
    fetch(root, "sandbox")
    remote_sha = sha(root, "origin/sandbox")
    if not git_ok(root, "merge-base", "--is-ancestor", remote_sha, sha(root)):
        raise FlowError("origin/sandbox is not an ancestor of local sandbox; reconcile before publishing")
    targets = args.tests or []
    run_tests(root, targets)
    env = os.environ.copy()
    env["GENERIC_CHESS_FLOW_PUSH"] = "publish"
    git(root, "push", "origin", "sandbox:sandbox", env=env)
    fetch(root, "sandbox")
    if not synced(root, "sandbox"):
        raise FlowError("sandbox push completed but local and remote SHA differ")
    tested = state.setdefault("tested_shas", {})
    tested[sha(root)] = targets or ["<full-pytest>"]
    state["last_published_sha"] = sha(root)
    save_state(root, state)
    print(f"PUBLISHED_SANDBOX_SHA={sha(root)}")


def supervisor_config_path(root: Path) -> Path:
    return runtime_dir(root) / "supervisor.json"


def escalation_root(root: Path) -> Path:
    return runtime_dir(root) / "escalations"


def _file_digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _supervisor_config(root: Path) -> dict[str, Any]:
    path = supervisor_config_path(root)
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FlowError(f"invalid supervisor config: {path}") from exc
    if not isinstance(value, dict):
        raise FlowError(f"invalid supervisor config: {path}")
    return value


def create_escalation(root: Path, state: dict[str, Any], *, reason: str,
                      worker_thread_id: str | None = None) -> dict[str, Any]:
    directory_value = state.get("active_request_directory")
    request_directory = Path(directory_value) if isinstance(directory_value, str) else None
    identity = f"{directory_value}|{state.get('last_published_sha')}"
    escalation_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    directory = escalation_root(root) / escalation_id
    dossier_path = directory / "dossier.json"
    if dossier_path.exists() and not (directory / "resolution.json").exists():
        dossier = json.loads(dossier_path.read_text(encoding="utf-8"))
    else:
        receipt_path = request_directory / "receipt.json" if request_directory else Path()
        events_path = request_directory / "events.jsonl" if request_directory else Path()
        config = _supervisor_config(root)
        dossier = {
            "schema": "generic-chess-supervisor-escalation-v1",
            "escalation_id": escalation_id,
            "status": "PENDING",
            "created_at": time.time(),
            "reason": reason,
            "master_sha": sha(worktrees(root)["master"]),
            "sandbox_sha": sha(sandbox_root(root)),
            "request_directory": directory_value,
            "request_receipt_sha256": _file_digest(receipt_path) if request_directory else None,
            "request_events_sha256": _file_digest(events_path) if request_directory else None,
            "last_probe": state.get("last_probe"),
            "recovery_attempts": state.get("recovery_attempts", 0),
            "worker_thread_id": worker_thread_id or os.environ.get("CODEX_THREAD_ID"),
            "worker_host_id": "local",
            "supervisor_thread_id": config.get("supervisor_thread_id"),
            "supervisor_host_id": config.get("supervisor_host_id", "local"),
            "recommended_action": "inspect the evidence, repair within existing authority, then resume the worker",
        }
        _atomic_json(dossier_path, dossier)
        message = (
            f"GenericChess recovery escalation {escalation_id} requires Supervisor review.\n"
            f"Dossier: {dossier_path}\nSandbox SHA: {dossier['sandbox_sha']}\n"
            "Inspect without creating a replacement Courier request. Resolve the transport/framework issue, "
            "then send an exact continuation message to the recorded worker task."
        )
        (directory / "notification.txt").write_text(message + "\n", encoding="utf-8")
    state["recovery_state"] = "ESCALATED"
    state["escalation_id"] = escalation_id
    recovery_event(state, "supervisor_escalated", escalation_id=escalation_id, reason=reason)
    save_state(root, state)
    print(json.dumps(dossier, indent=2, ensure_ascii=False, sort_keys=True))
    print(f"SUPERVISOR_NOTIFICATION_FILE={directory / 'notification.txt'}")
    return dossier


def command_recover(root: Path, args: argparse.Namespace) -> None:
    state = active_state(root)
    require_worker_write_authority(state, root)
    if state.get("mode") != "courier":
        raise FlowError("recover is only available in courier mode")
    directory = state.get("active_request_directory")
    if not isinstance(directory, str) or not directory:
        raise FlowError("there is no active Courier request to recover")
    worker_thread_id = getattr(args, "worker_thread_id", None) or os.environ.get("CODEX_THREAD_ID")
    state["worker_thread_id"] = worker_thread_id
    state["recovery_state"] = "RECOVERING"
    recovery_event(state, "recovery_started", request_directory=directory)
    save_state(root, state)
    try:
        status = courier(root, "courier_status", directory, allow_failure=True)
        recovery_event(state, "status_read", courier_state=status.get("state"))
        probe = courier(root, "courier_capture_latest", directory,
                        stream=True, allow_failure=True)
        state["last_probe"] = {
            key: probe.get(key) for key in (
                "event", "ok", "fingerprint", "captured_at", "latest_user_turn_found",
                "post_submission_reply_found", "request_match", "response_path",
                "submission_count", "message_sent", "error_code",
            ) if key in probe
        }
        recovery_event(state, "latest_response_probed", **state["last_probe"])
        save_state(root, state)
        if probe.get("ok") and probe.get("request_match") is True and probe.get("response_path"):
            update_response_state(root, state, probe, source="capture_latest")
            return
        if (probe.get("event") == "courier_capture_latest_empty"
                and probe.get("latest_user_turn_found") is False):
            state["recovery_attempts"] = int(state.get("recovery_attempts", 0)) + 1
            recovery_event(state, "evidence_retry_requested",
                           attempt=state["recovery_attempts"])
            save_state(root, state)
            result = courier(root, "courier_retry_once", directory,
                             stream=True, allow_failure=True)
            if result.get("event") in {"response_received", "response_duplicate"} and result.get("response_path"):
                update_response_state(root, state, result, source="evidence_retry")
                return
            reason = f"evidence retry did not recover the request: {result.get('event')}"
        elif (probe.get("event") == "courier_capture_latest_empty"
              and probe.get("latest_user_turn_found") is True):
            result = courier(root, "courier_recover", directory,
                             stream=True, allow_failure=True)
            if result.get("event") in {"response_received", "response_duplicate"} and result.get("response_path"):
                update_response_state(root, state, result, source="read_only_recover")
                return
            reason = f"the Chat request exists but read-only recovery did not complete: {result.get('event')}"
        else:
            reason = f"read-only Chat probe needs Supervisor judgment: {probe.get('event')}"
    except FlowError as exc:
        reason = f"Courier recovery command failed: {exc}"
    create_escalation(root, state, reason=reason, worker_thread_id=worker_thread_id)


def command_resume(root: Path, args: argparse.Namespace) -> None:
    command_recover(root, args)


def command_register_supervisor(root: Path, args: argparse.Namespace) -> None:
    thread_id = args.thread_id or os.environ.get("CODEX_THREAD_ID")
    if not isinstance(thread_id, str) or not thread_id:
        raise FlowError("a supervisor thread id is required")
    value = {
        "schema": "generic-chess-supervisor-v1",
        "supervisor_thread_id": thread_id,
        "supervisor_host_id": args.host_id,
        "registered_at": time.time(),
    }
    _atomic_json(supervisor_config_path(root), value)
    print(json.dumps(value, indent=2, sort_keys=True))


def command_escalate(root: Path, args: argparse.Namespace) -> None:
    state = active_state(root)
    create_escalation(root, state, reason=args.reason,
                      worker_thread_id=args.worker_thread_id)


def _escalation_directory(root: Path, escalation_id: str) -> Path:
    if not re.fullmatch(r"[0-9a-f]{20}", escalation_id):
        raise FlowError("invalid escalation id")
    directory = escalation_root(root) / escalation_id
    if not (directory / "dossier.json").is_file():
        raise FlowError("unknown escalation id")
    return directory


def command_supervisor_pending(root: Path, _args: argparse.Namespace) -> None:
    pending = []
    base = escalation_root(root)
    if base.exists():
        for dossier_path in sorted(base.glob("*/dossier.json")):
            if not (dossier_path.parent / "resolution.json").exists():
                pending.append(json.loads(dossier_path.read_text(encoding="utf-8")))
    print(json.dumps({"pending": pending}, indent=2, ensure_ascii=False, sort_keys=True))


def command_supervisor_claim(root: Path, args: argparse.Namespace) -> None:
    config = _supervisor_config(root)
    current = os.environ.get("CODEX_THREAD_ID")
    if current != config.get("supervisor_thread_id"):
        raise FlowError("only the registered Supervisor task may claim an escalation")
    directory = _escalation_directory(root, args.escalation_id)
    claim_path = directory / "claim.json"
    value = {"escalation_id": args.escalation_id, "supervisor_thread_id": current,
             "claimed_at": time.time()}
    if claim_path.exists():
        existing = json.loads(claim_path.read_text(encoding="utf-8"))
        if existing.get("supervisor_thread_id") != current:
            raise FlowError("the escalation is claimed by another task")
        value = existing
    else:
        claim_path.parent.mkdir(parents=True, exist_ok=True)
        with claim_path.open("x", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
    print(json.dumps(value, indent=2, sort_keys=True))


def command_supervisor_resolve(root: Path, args: argparse.Namespace) -> None:
    directory = _escalation_directory(root, args.escalation_id)
    claim = json.loads((directory / "claim.json").read_text(encoding="utf-8"))
    current = os.environ.get("CODEX_THREAD_ID")
    if current != claim.get("supervisor_thread_id"):
        raise FlowError("only the claiming Supervisor task may resolve an escalation")
    detail = Path(args.detail_file).read_text(encoding="utf-8-sig") if args.detail_file else args.action
    payload = {
        "schema": "generic-chess-supervisor-resolution-v1",
        "escalation_id": args.escalation_id,
        "action": args.action,
        "detail": detail,
        "supervisor_thread_id": current,
        "resolved_at": time.time(),
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    payload["resolution_sha256"] = hashlib.sha256(canonical).hexdigest()
    _atomic_json(directory / "resolution.json", payload)
    dossier = json.loads((directory / "dossier.json").read_text(encoding="utf-8"))
    state = active_state(root)
    if args.action == "USER_SUPERSEDED_REQUEST":
        state["retired_request_directory"] = state.get("active_request_directory")
        state["active_request_directory"] = None
        state["last_response_path"] = None
        state["work_order_active"] = False
    state["recovery_state"] = "HUMAN_REQUIRED" if args.action == "HUMAN_REQUIRED" else "RECOVERED"
    recovery_event(state, "supervisor_resolved", escalation_id=args.escalation_id,
                   action=args.action, resolution_sha256=payload["resolution_sha256"])
    save_state(root, state)
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    print(f"WORKER_THREAD_ID={dossier.get('worker_thread_id')}")
    print(f"WORKER_HOST_ID={dossier.get('worker_host_id', 'local')}")


def command_supervisor_resend(root: Path, args: argparse.Namespace) -> None:
    directory = _escalation_directory(root, args.escalation_id)
    claim_path = directory / "claim.json"
    if not claim_path.is_file():
        raise FlowError("the Supervisor must claim the escalation before resend review")
    claim = json.loads(claim_path.read_text(encoding="utf-8"))
    current = os.environ.get("CODEX_THREAD_ID")
    if current != claim.get("supervisor_thread_id"):
        raise FlowError("only the claiming Supervisor task may authorize resend_once")
    state = active_state(root)
    request_directory = state.get("active_request_directory")
    if not isinstance(request_directory, str) or not request_directory:
        raise FlowError("there is no active immutable Courier request to resend")
    probe = courier(root, "courier_capture_latest", request_directory,
                    stream=True, allow_failure=True)
    if probe.get("request_match") is True and probe.get("response_path"):
        update_response_state(root, state, probe, source="supervisor_capture_latest")
        return
    if (probe.get("event") != "courier_capture_latest_empty"
            or probe.get("latest_user_turn_found") is not False):
        raise FlowError("Supervisor resend requires fresh proof that the request is absent")
    result = courier(root, "courier_resend_once", request_directory,
                     stream=True, allow_failure=True)
    recovery_event(state, "supervisor_resend_reviewed", escalation_id=args.escalation_id,
                   result_event=result.get("event"))
    save_state(root, state)
    if result.get("event") in {"response_received", "response_duplicate"} and result.get("response_path"):
        update_response_state(root, state, result, source="supervisor_resend")
        return
    raise FlowError(f"Supervisor resend_once did not recover the request: {result.get('event')}")


def command_closeout(root: Path, args: argparse.Namespace) -> None:
    state = active_state(root)
    require_worker_write_authority(state, root)
    if state.get("mode") != "courier":
        raise FlowError("closeout is only available in courier mode")
    dispatch_message(root, state, Path(args.report_file).resolve(), "closeout")


def command_promote(root: Path, args: argparse.Namespace) -> None:
    state = active_state(root)
    require_worker_write_authority(state, root)
    candidate = args.candidate.lower()
    if not FULL_SHA.fullmatch(candidate):
        raise FlowError("candidate must be a full 40-character lowercase SHA")
    trees = worktrees(root)
    master, sandbox = trees["master"], trees["sandbox"]
    require_clean(master)
    require_clean(sandbox)
    require_synced(master, "master")
    require_synced(sandbox, "sandbox")
    if candidate != sha(sandbox):
        raise FlowError("v1 promotion requires candidate to equal the synchronized sandbox HEAD")
    if candidate not in state.get("tested_shas", {}):
        raise FlowError("candidate has not passed publish tests in the active session")
    if not git_ok(master, "merge-base", "--is-ancestor", sha(master), candidate):
        raise FlowError("master is not an ancestor of the candidate; non-fast-forward promotion is forbidden")
    if state.get("mode") == "courier":
        if state.get("last_response_source") not in {None, "normal"}:
            raise FlowError("a recovery response cannot implicitly authorize promotion")
        control = state.get("chat_control", {})
        if control.get("GENERICCHESS_PROMOTION") != "APPROVE":
            raise FlowError("the latest Chat response does not approve promotion")
        if control.get("GENERICCHESS_CANDIDATE_SHA") != candidate:
            raise FlowError("Chat promotion approval is not bound to the requested candidate SHA")
    git(master, "merge", "--ff-only", candidate)
    env = os.environ.copy()
    env["GENERIC_CHESS_FLOW_PUSH"] = "promote"
    git(master, "push", "origin", "master:master", env=env)
    fetch(master, "master")
    if not synced(master, "master"):
        raise FlowError("master promotion push completed but local and remote SHA differ")
    state["last_promoted_sha"] = candidate
    save_state(root, state)
    print(f"PROMOTED_MASTER_SHA={candidate}")


def command_finish(root: Path, _args: argparse.Namespace) -> None:
    state = active_state(root)
    trees = worktrees(root)
    for name in ("master", "sandbox"):
        require_clean(trees[name])
        require_synced(trees[name], name)
    if state.get("active_request_directory"):
        raise FlowError("cannot finish while a Courier request still needs reconciliation")
    if state.get("mode") == "courier":
        status = state.get("chat_control", {}).get("GENERICCHESS_STATUS")
        if status not in {"COMPLETE", "BLOCKED"}:
            raise FlowError("Chat has not marked the Courier workflow COMPLETE or BLOCKED")
    state["active"] = False
    save_state(root, state)
    print("GENERIC_CHESS_FLOW_FINISHED")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="generic-chess-flow")
    sub = value.add_subparsers(dest="command", required=True)
    sub.add_parser("status").set_defaults(handler=command_status)
    sub.add_parser("work").set_defaults(handler=command_work)
    start = sub.add_parser("start")
    start.add_argument("--mode", choices=("courier", "local"), required=True)
    start.add_argument("--message-file")
    start.set_defaults(handler=command_start)
    publish = sub.add_parser("publish")
    publish.add_argument("--tests", nargs="*")
    publish.set_defaults(handler=command_publish)
    heavy = sub.add_parser("heavy")
    heavy.add_argument("argv", nargs=argparse.REMAINDER)
    heavy.set_defaults(handler=command_heavy)
    recover = sub.add_parser("recover")
    recover.add_argument("--worker-thread-id")
    recover.set_defaults(handler=command_recover)
    resume = sub.add_parser("resume")
    resume.add_argument("--worker-thread-id")
    resume.set_defaults(handler=command_resume)
    register = sub.add_parser("register-supervisor")
    register.add_argument("--thread-id")
    register.add_argument("--host-id", default="local")
    register.set_defaults(handler=command_register_supervisor)
    escalate = sub.add_parser("escalate")
    escalate.add_argument("--reason", required=True)
    escalate.add_argument("--worker-thread-id")
    escalate.set_defaults(handler=command_escalate)
    sub.add_parser("supervisor-pending").set_defaults(handler=command_supervisor_pending)
    claim = sub.add_parser("supervisor-claim")
    claim.add_argument("--escalation-id", required=True)
    claim.set_defaults(handler=command_supervisor_claim)
    resolve = sub.add_parser("supervisor-resolve")
    resolve.add_argument("--escalation-id", required=True)
    resolve.add_argument("--action", choices=("RESUME_WORKER", "RECOVERED", "USER_SUPERSEDED_REQUEST", "HUMAN_REQUIRED"), required=True)
    resolve.add_argument("--detail-file")
    resolve.set_defaults(handler=command_supervisor_resolve)
    resend = sub.add_parser("supervisor-resend")
    resend.add_argument("--escalation-id", required=True)
    resend.set_defaults(handler=command_supervisor_resend)
    closeout = sub.add_parser("closeout")
    closeout.add_argument("--report-file", required=True)
    closeout.set_defaults(handler=command_closeout)
    promote = sub.add_parser("promote")
    promote.add_argument("--candidate", required=True)
    promote.set_defaults(handler=command_promote)
    sub.add_parser("finish").set_defaults(handler=command_finish)
    return value


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        root = repository_root()
        result = args.handler(root, args)
        return int(result or 0)
    except FlowError as exc:
        print(f"GENERIC_CHESS_FLOW_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
