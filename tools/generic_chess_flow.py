from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Sequence


PROJECT_ID = "GENERICCHESS"
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
CONTROL_FIELDS = {
    "GENERICCHESS_STATUS",
    "GENERICCHESS_CANDIDATE_SHA",
    "GENERICCHESS_PROMOTION",
}


class FlowError(RuntimeError):
    pass


def run(
    argv: Sequence[str],
    *,
    cwd: Path,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(argv), cwd=cwd, text=True, encoding="utf-8", errors="replace",
        capture_output=True, env=env,
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
    result = run(command, cwd=root, check=False)
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


def courier(root: Path, *args: str) -> dict[str, Any]:
    comspec = os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe")
    result = run((comspec, "/d", "/c", str(courier_launcher(root)), *args), cwd=root, check=False)
    events: list[dict[str, Any]] = []
    for line in result.stdout.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            events.append(value)
    if result.returncode or not events:
        detail = (result.stderr or result.stdout).strip()
        raise FlowError(f"ChatCourier failed ({result.returncode}): {detail}")
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


def update_response_state(root: Path, state: dict[str, Any], event: dict[str, Any]) -> None:
    if event.get("event") in {"response_received", "response_duplicate"}:
        response_path = event.get("response_path")
        if not isinstance(response_path, str):
            raise FlowError("Courier response event did not include response_path")
        response = Path(response_path)
        text = response.read_text(encoding="utf-8-sig")
        state["last_response_path"] = str(response)
        state["chat_control"] = parse_control_footer(text)
        state["active_request_directory"] = None
        save_state(root, state)
        print(text)


def dispatch_message(root: Path, state: dict[str, Any], source: Path, purpose: str) -> None:
    sandbox = sandbox_root(root)
    require_clean(sandbox)
    require_synced(sandbox, "sandbox")
    body = source.read_text(encoding="utf-8-sig")
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
    event = courier(root, "courier_dispatch", request_directory)
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
    payload["session"] = load_state(root, required=False)
    try:
        caps = courier_capabilities(root)
        payload["courier"] = {"available": True, "projects": caps.get("projects", [])}
    except FlowError as exc:
        payload["courier"] = {"available": False, "detail": str(exc)}
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))


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
    }
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


def command_publish(root: Path, args: argparse.Namespace) -> None:
    if branch(root) != "sandbox":
        raise FlowError("publish must be run from the sandbox worktree")
    state = load_state(root)
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


def command_resume(root: Path, _args: argparse.Namespace) -> None:
    state = load_state(root)
    if state.get("mode") != "courier":
        raise FlowError("resume is only available in courier mode")
    directory = state.get("active_request_directory")
    if not isinstance(directory, str) or not directory:
        raise FlowError("there is no active Courier request to resume")
    event = courier(root, "courier_dispatch", directory)
    update_response_state(root, state, event)


def command_closeout(root: Path, args: argparse.Namespace) -> None:
    state = load_state(root)
    if state.get("mode") != "courier":
        raise FlowError("closeout is only available in courier mode")
    dispatch_message(root, state, Path(args.report_file).resolve(), "closeout")


def command_promote(root: Path, args: argparse.Namespace) -> None:
    state = load_state(root)
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
    state = load_state(root)
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
    start = sub.add_parser("start")
    start.add_argument("--mode", choices=("courier", "local"), required=True)
    start.add_argument("--message-file")
    start.set_defaults(handler=command_start)
    publish = sub.add_parser("publish")
    publish.add_argument("--tests", nargs="*")
    publish.set_defaults(handler=command_publish)
    sub.add_parser("resume").set_defaults(handler=command_resume)
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
        args.handler(root, args)
        return 0
    except FlowError as exc:
        print(f"GENERIC_CHESS_FLOW_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
