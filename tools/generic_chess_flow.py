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
OPTIONAL_COMPUTE_CONTROL_FIELDS = {
    "GENERICCHESS_COMPUTE_PLAN_APPROVAL",
    "GENERICCHESS_COMPUTE_PLAN_SHA",
    "GENERICCHESS_COMPUTE_ENVELOPE_SHA",
}
CONTROL_STATUSES = {"CONTINUE", "COMPLETE", "BLOCKED"}
PROMOTION_VALUES = {"APPROVE", "HOLD"}
WORK_ORDER_ID = re.compile(r"(?m)^WORK_ORDER_ID=([^\s]+)\s*$")
INLINE_CHAT_REFERENCE_THRESHOLD = 24 * 1024
HANDOFF_BRANCH = "workflow-state"
HANDOFF_SCHEMA = "generic-chess-handoff-v1"
HANDOFF_HOST = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
HANDOFF_STAGES = {"SUBMIT_CLOSEOUT", "REQUEST_NEXT_ORDER", "COMPLETE"}
COMPUTE_PLAN_SCHEMA = "generic-chess-compute-plan-v1"
COMPUTE_ENVELOPE_SCHEMA = "generic-chess-resource-envelope-v1"
COMPUTE_APPROVAL_SCHEMA = "generic-chess-compute-approval-v1"
COMPUTE_PLAN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
COMPUTE_POLICY_PATH = Path(__file__).with_name("compute_policy.json")


class FlowError(RuntimeError):
    pass


def _read_json_file(path: Path, label: str) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FlowError(f"invalid {label}: {path}") from exc
    if not isinstance(value, dict):
        raise FlowError(f"invalid {label}: {path}")
    return value


def _json_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _file_digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise FlowError(f"cannot read file: {path}") from exc


def _compute_policy() -> dict[str, Any]:
    policy = _read_json_file(COMPUTE_POLICY_PATH, "compute policy")
    if policy.get("schema") != "generic-chess-compute-policy-v1":
        raise FlowError("invalid compute policy schema")
    thresholds = policy.get("thresholds")
    if not isinstance(thresholds, dict) or not all(
        isinstance(thresholds.get(key), (int, float)) and thresholds[key] >= 0
        for key in (
            "expected_wall_minutes_gt", "maximum_games_gt",
            "expected_cpu_hours_gt", "arena_pairs_gte", "stage_count_gt",
        )
    ):
        raise FlowError("compute policy thresholds are invalid")
    if not isinstance(policy.get("max_declared_logical_cpu"), int) or policy["max_declared_logical_cpu"] <= 0:
        raise FlowError("compute policy CPU limit is invalid")
    return policy


def _validate_resource_envelope(value: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema", "envelope_id", "logical_cpu_count", "intended_cpu_lanes",
        "expected_wall_minutes", "hard_wall_minutes", "expected_cpu_hours",
        "hard_cpu_hours", "arena_pairs", "maximum_games", "maximum_nodes",
        "maximum_plies", "maximum_concurrent_games", "stage_count",
    }
    if value.get("schema") != COMPUTE_ENVELOPE_SCHEMA or not required.issubset(value):
        raise FlowError("resource envelope is missing required fields")
    if not COMPUTE_PLAN_ID.fullmatch(str(value["envelope_id"])):
        raise FlowError("resource envelope id is invalid")
    for key in (
        "logical_cpu_count", "intended_cpu_lanes", "hard_wall_minutes",
        "hard_cpu_hours", "arena_pairs", "maximum_games", "maximum_nodes",
        "maximum_plies", "maximum_concurrent_games", "stage_count",
    ):
        if not isinstance(value[key], int) or value[key] <= 0:
            raise FlowError(f"resource envelope field is invalid: {key}")
    for key in ("expected_wall_minutes", "expected_cpu_hours"):
        if value[key] is not None and (
            not isinstance(value[key], (int, float)) or value[key] < 0
        ):
            raise FlowError(f"resource envelope field is invalid: {key}")
    if value["intended_cpu_lanes"] > value["maximum_concurrent_games"]:
        raise FlowError("resource envelope lanes exceed concurrent-game cap")
    if value["maximum_concurrent_games"] > value["logical_cpu_count"]:
        raise FlowError("resource envelope concurrency exceeds declared CPU")
    if value["expected_wall_minutes"] is not None and value["expected_wall_minutes"] > value["hard_wall_minutes"]:
        raise FlowError("resource envelope wall estimate exceeds hard ceiling")
    if value["expected_cpu_hours"] is not None and value["expected_cpu_hours"] > value["hard_cpu_hours"]:
        raise FlowError("resource envelope CPU estimate exceeds hard ceiling")
    return value


def _load_resource_envelope(path_value: str | Path) -> tuple[dict[str, Any], str]:
    path = Path(path_value).resolve()
    value = _validate_resource_envelope(_read_json_file(path, "resource envelope"))
    return value, _json_digest(value)


def _compute_is_large(envelope: dict[str, Any]) -> bool:
    thresholds = _compute_policy()["thresholds"]
    return (
        envelope["expected_wall_minutes"] is None
        or envelope["expected_cpu_hours"] is None
        or envelope["expected_wall_minutes"] > thresholds["expected_wall_minutes_gt"]
        or envelope["maximum_games"] > thresholds["maximum_games_gt"]
        or envelope["expected_cpu_hours"] > thresholds["expected_cpu_hours_gt"]
        or envelope["arena_pairs"] >= thresholds["arena_pairs_gte"]
        or envelope["stage_count"] > thresholds["stage_count_gt"]
    )


def _load_compute_plan(root: Path, path_value: str | Path) -> tuple[dict[str, Any], str]:
    path = Path(path_value).resolve()
    plan = _read_json_file(path, "compute plan")
    required = {
        "schema", "plan_id", "version", "sandbox_sha", "scientific_decision",
        "why_smaller_evidence_insufficient", "reusable_evidence", "stages",
        "resource_envelope", "checkpoint_behavior", "stage_pause_points",
        "early_stop_rules", "failure_exit_path", "alternatives", "command_argv",
    }
    if plan.get("schema") != COMPUTE_PLAN_SCHEMA or not required.issubset(plan):
        raise FlowError("compute plan is missing required fields")
    if not COMPUTE_PLAN_ID.fullmatch(str(plan["plan_id"])) or not isinstance(plan["version"], int) or plan["version"] <= 0:
        raise FlowError("compute plan identity is invalid")
    if plan["sandbox_sha"] != sha(root) or not FULL_SHA.fullmatch(plan["sandbox_sha"]):
        raise FlowError("compute plan is not bound to the current sandbox SHA")
    for key in (
        "scientific_decision", "why_smaller_evidence_insufficient",
        "checkpoint_behavior", "failure_exit_path",
    ):
        if not isinstance(plan[key], str) or not plan[key].strip():
            raise FlowError(f"compute plan field is empty: {key}")
    for key in ("reusable_evidence", "stages", "stage_pause_points", "early_stop_rules", "alternatives"):
        if not isinstance(plan[key], list) or not plan[key]:
            raise FlowError(f"compute plan field is empty: {key}")
    if not all(isinstance(part, str) and part for part in plan["command_argv"]):
        raise FlowError("compute plan command_argv is invalid")
    _validate_resource_envelope(plan["resource_envelope"])
    return plan, _file_digest(path)


def _compute_approval_path(root: Path, plan_id: str) -> Path:
    return runtime_dir(root) / "compute-approvals" / f"{plan_id}.json"


def _require_registered_supervisor(root: Path) -> str:
    config = _supervisor_config(root)
    current = os.environ.get("CODEX_THREAD_ID")
    if not isinstance(current, str) or current != config.get("supervisor_thread_id"):
        raise FlowError("only the registered Supervisor task may perform this action")
    return current


def _validate_compute_approval(root: Path, plan: dict[str, Any], plan_sha: str,
                               envelope_sha: str) -> dict[str, Any]:
    path = _compute_approval_path(root, plan["plan_id"])
    if not path.is_file():
        raise FlowError("large compute requires a valid Supervisor approval")
    approval = _read_json_file(path, "compute approval")
    required = {
        "schema", "plan_id", "plan_sha256", "sandbox_sha", "envelope_sha256",
        "chat_response_sha256", "supervisor_thread_id", "approved_at", "revoked",
    }
    if approval.get("schema") != COMPUTE_APPROVAL_SCHEMA or not required.issubset(approval):
        raise FlowError("compute approval is malformed")
    if approval["revoked"] is not False:
        raise FlowError("compute approval has been revoked")
    state = active_state(root)
    if (
        approval["plan_id"] != plan["plan_id"]
        or approval["plan_sha256"] != plan_sha
        or approval["sandbox_sha"] != sha(root)
        or approval["envelope_sha256"] != envelope_sha
        or approval["supervisor_thread_id"] != _supervisor_config(root).get("supervisor_thread_id")
        or approval["chat_response_sha256"] != state.get("last_response_sha256")
        or state.get("last_response_source") != "normal"
    ):
        raise FlowError("compute approval is stale or not bound to the current Chat response")
    control = state.get("chat_control", {})
    if (
        control.get("GENERICCHESS_COMPUTE_PLAN_APPROVAL") != "APPROVE"
        or control.get("GENERICCHESS_COMPUTE_PLAN_SHA") != plan_sha
        or control.get("GENERICCHESS_COMPUTE_ENVELOPE_SHA") != envelope_sha
    ):
        raise FlowError("Chat has not approved this exact compute plan and envelope")
    return approval


def _enforce_compute_gate(root: Path, args: argparse.Namespace,
                          command: list[str] | None = None) -> dict[str, Any]:
    envelope_path = getattr(args, "resource_envelope", None)
    if not envelope_path:
        raise FlowError("heavy requires an explicit --resource-envelope declaration")
    envelope, envelope_sha = _load_resource_envelope(envelope_path)
    plan_path = getattr(args, "compute_plan", None)
    plan = None
    plan_sha = None
    if plan_path:
        plan, plan_sha = _load_compute_plan(root, plan_path)
        if plan["resource_envelope"] != envelope:
            raise FlowError("compute plan envelope differs from the run declaration")
    large = _compute_is_large(envelope)
    if large:
        if plan is None or plan_sha is None:
            raise FlowError("large compute requires an explicit versioned --compute-plan")
        if command is not None and plan["command_argv"] != command:
            raise FlowError("compute plan command/stage/budget identity differs from the run")
        _validate_compute_approval(root, plan, plan_sha, envelope_sha)
    elif plan is not None:
        if plan["sandbox_sha"] != sha(root):
            raise FlowError("compute plan SHA is stale")
    return {
        "resource_envelope_sha256": envelope_sha,
        "compute_plan_sha256": plan_sha,
        "compute_plan_id": plan["plan_id"] if plan else None,
        "compute_size": "large" if large else "small_or_medium",
    }


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


def machine_config_path() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    return base / "GenericChess" / "machine.json"


def load_machine(*, required: bool = True) -> dict[str, Any]:
    path = machine_config_path()
    if not path.is_file():
        if required:
            raise FlowError("machine identity is not configured; run machine-setup --host-id <id>")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FlowError(f"invalid machine identity: {path}") from exc
    if (not isinstance(value, dict) or value.get("schema") != "generic-chess-machine-v1"
            or not HANDOFF_HOST.fullmatch(str(value.get("host_id", "")))):
        raise FlowError(f"invalid machine identity: {path}")
    return value


def save_machine(host_id: str) -> dict[str, Any]:
    if not HANDOFF_HOST.fullmatch(host_id):
        raise FlowError("host ID must contain only letters, numbers, dot, underscore, or hyphen")
    path = machine_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = load_machine(required=False)
    if existing and existing.get("host_id") != host_id:
        raise FlowError(f"this machine is already registered as {existing.get('host_id')}")
    value = existing or {
        "schema": "generic-chess-machine-v1",
        "host_id": host_id,
        "machine_id": uuid.uuid4().hex,
        "registered_at": int(time.time()),
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    return value


def handoff_repo_path(root: Path) -> Path:
    return runtime_dir(root) / "workflow-state-repo"


def _remote_handoff_sha(root: Path) -> str | None:
    result = run(
        ("git", "-c", f"safe.directory={root.resolve()}", "ls-remote", "--heads", "origin", HANDOFF_BRANCH),
        cwd=root, check=False,
    )
    if result.returncode:
        raise FlowError(f"cannot read remote workflow ownership: {(result.stderr or result.stdout).strip()}")
    line = result.stdout.strip()
    return line.split()[0] if line else None


def _configure_handoff_repo(repo: Path, product_root: Path) -> None:
    git(repo, "config", "user.name", "GenericChess Flow")
    git(repo, "config", "user.email", "generic-chess-flow@local.invalid")
    git(repo, "config", "core.hooksPath", str((product_root / ".githooks").resolve()))


def ensure_handoff_repo(root: Path, *, initialize: dict[str, Any] | None = None) -> Path:
    product_root = root
    hooks_root = sandbox_root(root)
    repo = handoff_repo_path(root)
    remote_url = git(product_root, "remote", "get-url", "origin")
    remote_sha = _remote_handoff_sha(product_root)
    if not (repo / ".git").exists():
        if remote_sha:
            repo.parent.mkdir(parents=True, exist_ok=True)
            run(("git", "clone", "--single-branch", "--branch", HANDOFF_BRANCH,
                 remote_url, str(repo)), cwd=repo.parent)
        else:
            if initialize is None:
                raise FlowError("remote workflow-state branch is not initialized")
            repo.mkdir(parents=True, exist_ok=True)
            git(repo, "init", "-b", HANDOFF_BRANCH)
            git(repo, "remote", "add", "origin", remote_url)
            _configure_handoff_repo(repo, hooks_root)
            _write_handoff_files(repo, initialize, None)
            git(repo, "add", "handoff.json")
            git(repo, "commit", "-m", "Initialize GenericChess workflow ownership")
            env = os.environ.copy(); env["GENERIC_CHESS_FLOW_PUSH"] = "handoff"
            git(repo, "push", "-u", "origin", f"{HANDOFF_BRANCH}:{HANDOFF_BRANCH}", env=env)
            return repo
    _configure_handoff_repo(repo, hooks_root)
    git(repo, "fetch", "origin", HANDOFF_BRANCH)
    local_sha = sha(repo)
    remote_sha = sha(repo, f"origin/{HANDOFF_BRANCH}")
    if local_sha != remote_sha:
        if git_ok(repo, "merge-base", "--is-ancestor", local_sha, remote_sha):
            git(repo, "merge", "--ff-only", f"origin/{HANDOFF_BRANCH}")
        elif not git_ok(repo, "merge-base", "--is-ancestor", remote_sha, local_sha):
            raise FlowError("local workflow-state history diverged; preserve it for audit and re-clone")
    return repo


def load_handoff(repo: Path) -> dict[str, Any]:
    path = repo / "handoff.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FlowError(f"invalid handoff capsule: {path}") from exc
    if (not isinstance(value, dict) or value.get("schema") != HANDOFF_SCHEMA
            or value.get("state") not in {"CLAIMED", "RELEASED"}
            or not isinstance(value.get("generation"), int)):
        raise FlowError(f"invalid handoff capsule: {path}")
    return value


def _write_handoff_files(repo: Path, capsule: dict[str, Any], closeout: str | None) -> None:
    (repo / "handoff.json").write_text(
        json.dumps(capsule, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8", newline="\n",
    )
    payload = repo / "closeout.md"
    if closeout is None:
        payload.unlink(missing_ok=True)
    else:
        payload.write_text(closeout.rstrip() + "\n", encoding="utf-8", newline="")


def commit_handoff(root: Path, repo: Path, capsule: dict[str, Any], *,
                   closeout: str | None, message: str) -> None:
    _write_handoff_files(repo, capsule, closeout)
    git(repo, "add", "-A")
    git(repo, "commit", "-m", message)
    env = os.environ.copy(); env["GENERIC_CHESS_FLOW_PUSH"] = "handoff"
    git(repo, "push", "origin", f"{HANDOFF_BRANCH}:{HANDOFF_BRANCH}", env=env)
    git(repo, "fetch", "origin", HANDOFF_BRANCH)
    if sha(repo) != sha(repo, f"origin/{HANDOFF_BRANCH}"):
        raise FlowError("workflow-state push did not synchronize exactly")


def require_handoff_owner(root: Path) -> None:
    marker = root / ".workflow-state-enabled"
    if not marker.is_file():
        if not (root / ".git").exists():
            return
        try:
            marker = sandbox_root(root) / ".workflow-state-enabled"
        except FlowError:
            return
        if not marker.is_file():
            return
    machine = load_machine()
    repo = ensure_handoff_repo(root)
    capsule = load_handoff(repo)
    owner = capsule.get("owner")
    if (capsule.get("state") != "CLAIMED" or not isinstance(owner, dict)
            or owner.get("machine_id") != machine.get("machine_id")
            or owner.get("host_id") != machine.get("host_id")):
        raise FlowError("this machine does not own the remote GenericChess workflow")


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
    if root is not None:
        require_handoff_owner(root)
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
    basetemp = runtime_dir(root) / "pytest-runs" / uuid.uuid4().hex
    basetemp.mkdir(parents=True, exist_ok=False)
    command = [
        python_for(root), "-m", "pytest", "-q", "-p", "no:cacheprovider",
        "--basetemp", str(basetemp),
    ]
    command.extend(targets)
    with heavy_lock(root):
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
        if key in CONTROL_FIELDS | OPTIONAL_COMPUTE_CONTROL_FIELDS:
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


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)


def _console_safe(text: str, encoding: str | None = None) -> str:
    selected = encoding or getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(selected, errors="backslashreplace").decode(selected)


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
        print(_console_safe(text))


def chat_message_body(root: Path, source: Path, *, reference_only: bool = False) -> str:
    body = source.read_text(encoding="utf-8-sig")
    if not reference_only and len(body.encode("utf-8")) <= INLINE_CHAT_REFERENCE_THRESHOLD:
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
        raise FlowError("Courier closeout report is not tracked by Git")
    if git(sandbox, "diff", "--name-only", "HEAD", "--", relative_git):
        raise FlowError("Courier closeout report differs from the committed version")
    if not git_ok(sandbox, "rev-parse", "--verify", "origin/sandbox"):
        raise FlowError("Courier closeout report requires a published sandbox checkpoint")
    local_sha = sha(sandbox)
    published_sha = sha(sandbox, "origin/sandbox")
    if local_sha != published_sha:
        raise FlowError(
            f"Courier closeout report requires the published sandbox SHA: local={local_sha} remote={published_sha}"
        )
    return (
        "Review the Courier closeout/blocker report from this published immutable Git checkpoint.\n"
        f"REPOSITORY={git(sandbox, 'remote', 'get-url', 'origin')}\n"
        f"COMMIT={local_sha}\n"
        f"PATH={relative_git}\n"
        f"REPORT_SHA256={hashlib.sha256(resolved.read_bytes()).hexdigest()}\n"
        "Do not include or request the report body through the chat composer; inspect it at this exact commit.\n"
    )


def dispatch_message(root: Path, state: dict[str, Any], source: Path, purpose: str) -> None:
    sandbox = sandbox_root(root)
    require_clean(sandbox)
    require_synced(sandbox, "sandbox")
    body = chat_message_body(root, source, reference_only=purpose in {"closeout", "blocker"})
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
    state["active_request_id"] = prepared.get("request_id") or Path(request_directory).name
    state["active_request_fingerprint"] = prepared.get("fingerprint")
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
    """Allow one GenericChess compute command at a time."""
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
    require_no_supervisor_hold(root)
    if branch(root) != "sandbox":
        raise FlowError("heavy must be run from the sandbox worktree")
    command = list(args.argv)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        raise FlowError("heavy requires a command after --")
    compute_metadata = _enforce_compute_gate(root, args, command)
    with heavy_lock(root):
        process = subprocess.Popen(command, cwd=root)
        return process.wait()


def _chat_compute_approval(root: Path, path_value: str | Path, plan: dict[str, Any],
                           plan_sha: str, envelope_sha: str) -> dict[str, Any]:
    approval = _read_json_file(Path(path_value).resolve(), "Chat compute approval")
    required = {
        "schema", "decision", "plan_id", "plan_sha256", "sandbox_sha",
        "envelope_sha256", "chat_response_sha256",
    }
    if approval.get("schema") != "generic-chess-chat-compute-approval-v1" or not required.issubset(approval):
        raise FlowError("Chat compute approval is malformed")
    state = active_state(root)
    if (
        approval["decision"] != "APPROVE"
        or approval["plan_id"] != plan["plan_id"]
        or approval["plan_sha256"] != plan_sha
        or approval["sandbox_sha"] != sha(root)
        or approval["envelope_sha256"] != envelope_sha
        or approval["chat_response_sha256"] != state.get("last_response_sha256")
        or state.get("last_response_source") != "normal"
    ):
        raise FlowError("Chat compute approval is stale or does not bind this plan")
    control = state.get("chat_control", {})
    if (
        control.get("GENERICCHESS_COMPUTE_PLAN_APPROVAL") != "APPROVE"
        or control.get("GENERICCHESS_COMPUTE_PLAN_SHA") != plan_sha
        or control.get("GENERICCHESS_COMPUTE_ENVELOPE_SHA") != envelope_sha
    ):
        raise FlowError("current Chat response does not approve this exact compute plan")
    return approval


def command_compute_plan_approve(root: Path, args: argparse.Namespace) -> int:
    _require_registered_supervisor(root)
    plan, plan_sha = _load_compute_plan(root, args.plan_file)
    envelope = _validate_resource_envelope(plan["resource_envelope"])
    if not _compute_is_large(envelope):
        raise FlowError("Supervisor approval is only required for a large compute plan")
    envelope_sha = _json_digest(envelope)
    chat = _chat_compute_approval(root, args.chat_approval_file, plan, plan_sha, envelope_sha)
    path = _compute_approval_path(root, plan["plan_id"])
    record = {
        "schema": COMPUTE_APPROVAL_SCHEMA,
        "plan_id": plan["plan_id"],
        "plan_sha256": plan_sha,
        "sandbox_sha": sha(root),
        "envelope_sha256": envelope_sha,
        "chat_response_sha256": chat["chat_response_sha256"],
        "supervisor_thread_id": _supervisor_config(root).get("supervisor_thread_id"),
        "approved_at": time.time(),
        "revoked": False,
    }
    if path.exists():
        previous = _read_json_file(path, "compute approval")
        if previous.get("revoked") is False:
            comparable = {key: previous.get(key) for key in record if key != "approved_at"}
            expected = {key: record.get(key) for key in record if key != "approved_at"}
            if comparable == expected:
                print(json.dumps(previous, indent=2, sort_keys=True))
                return 0
            raise FlowError("an active approval already exists for this plan")
    _atomic_json(path, record)
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


def command_compute_plan_status(root: Path, args: argparse.Namespace) -> int:
    plan, plan_sha = _load_compute_plan(root, args.plan_file)
    envelope = _validate_resource_envelope(plan["resource_envelope"])
    path = _compute_approval_path(root, plan["plan_id"])
    approval = _read_json_file(path, "compute approval") if path.exists() else None
    payload = {
        "plan_id": plan["plan_id"],
        "plan_sha256": plan_sha,
        "sandbox_sha": sha(root),
        "envelope_sha256": _json_digest(envelope),
        "compute_size": "large" if _compute_is_large(envelope) else "small_or_medium",
        "approval": approval,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def command_compute_plan_revoke(root: Path, args: argparse.Namespace) -> int:
    supervisor = _require_registered_supervisor(root)
    plan, plan_sha = _load_compute_plan(root, args.plan_file)
    path = _compute_approval_path(root, plan["plan_id"])
    if not path.exists():
        raise FlowError("no approval exists for this compute plan")
    approval = _read_json_file(path, "compute approval")
    if approval.get("plan_sha256") != plan_sha or approval.get("sandbox_sha") != sha(root):
        raise FlowError("cannot revoke a stale or mismatched compute approval")
    if approval.get("revoked") is True:
        print(json.dumps(approval, indent=2, sort_keys=True))
        return 0
    approval.update({"revoked": True, "revoked_at": time.time(), "revoked_by": supervisor})
    _atomic_json(path, approval)
    print(json.dumps(approval, indent=2, sort_keys=True))
    return 0


def _heavy_run_dir(root: Path, run_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", run_id):
        raise FlowError("invalid heavy run id")
    return runtime_dir(root) / "heavy-runs" / run_id


def _process_creation_time(pid: int) -> float | None:
    """Return OS process creation time, or None when the PID is not alive."""
    if not isinstance(pid, int) or pid <= 0:
        return None
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        process_query_limited_information = 0x1000
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.GetProcessTimes.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
        ]
        kernel32.GetProcessTimes.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(process_query_limited_information, False, pid)
        if not handle:
            return None
        try:
            created = wintypes.FILETIME()
            exited = wintypes.FILETIME()
            kernel = wintypes.FILETIME()
            user = wintypes.FILETIME()
            if not kernel32.GetProcessTimes(
                handle,
                ctypes.byref(created),
                ctypes.byref(exited),
                ctypes.byref(kernel),
                ctypes.byref(user),
            ):
                return None
            ticks = (created.dwHighDateTime << 32) | created.dwLowDateTime
            return (ticks - 116444736000000000) / 10_000_000
        finally:
            kernel32.CloseHandle(handle)
    try:  # pragma: no cover - the workflow is Windows-only
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii").split()
        boot_time = next(
            float(line.split()[1])
            for line in Path("/proc/stat").read_text(encoding="ascii").splitlines()
            if line.startswith("btime ")
        )
        return boot_time + int(stat[21]) / os.sysconf("SC_CLK_TCK")
    except (OSError, StopIteration, ValueError, IndexError):
        return None


def _same_process(pid: Any, created_at: Any) -> bool:
    if not isinstance(pid, int) or not isinstance(created_at, (int, float)):
        return False
    actual = _process_creation_time(pid)
    return actual is not None and abs(actual - float(created_at)) < 0.01


def _classified_heavy_state(payload: Any, *, now: float | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict) or payload.get("schema") != "generic-chess-heavy-v1":
        raise FlowError("invalid heavy run state schema")
    required = {
        "run_id", "label", "argv_digest", "status", "started_at",
        "stdout_path", "stderr_path", "state_path",
    }
    if not required.issubset(payload):
        raise FlowError("invalid heavy run state fields")
    if (
        not isinstance(payload["run_id"], str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", payload["run_id"])
        or not isinstance(payload["label"], str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", payload["label"])
        or not isinstance(payload["argv_digest"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", payload["argv_digest"])
        or not isinstance(payload["started_at"], (int, float))
        or not all(isinstance(payload[field], str) for field in (
            "stdout_path", "stderr_path", "state_path"
        ))
    ):
        raise FlowError("invalid heavy run state values")
    if payload["status"] not in {"starting", "running", "completed", "failed", "stale"}:
        raise FlowError("invalid heavy run status")
    result = dict(payload)
    if payload["status"] in {"completed", "failed", "stale"}:
        return result
    current_time = time.time() if now is None else now
    heartbeat = payload.get("heartbeat_at", payload["started_at"])
    if not isinstance(heartbeat, (int, float)) or current_time - heartbeat > 60:
        result["status"] = "stale"
        result["stale_reason"] = "heartbeat_expired"
        return result
    if payload["status"] == "running":
        if not _same_process(payload.get("monitor_pid"), payload.get("monitor_created_at")):
            result["status"] = "stale"
            result["stale_reason"] = "monitor_process_identity_mismatch"
        elif not _same_process(payload.get("child_pid"), payload.get("child_created_at")):
            result["status"] = "stale"
            result["stale_reason"] = "child_process_identity_mismatch"
    return result


def command_heavy_monitor(root: Path, args: argparse.Namespace) -> int:
    run_dir = _heavy_run_dir(root, args.run_id)
    state_path = run_dir / "state.json"
    state: dict[str, Any] = {}
    try:
        command = json.loads((run_dir / "command.json").read_text(encoding="utf-8"))
        if not isinstance(command, list) or not command or not all(
            isinstance(part, str) and part for part in command
        ):
            raise FlowError("invalid heavy command payload")
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(state, dict) or state.get("status") != "starting":
            raise FlowError("heavy monitor requires a starting run state")
        with heavy_lock(root):
            now = time.time()
            monitor_created_at = _process_creation_time(os.getpid())
            if monitor_created_at is None:
                raise FlowError("cannot read heavy monitor process identity")
            state.update({
                "monitor_pid": os.getpid(),
                "monitor_created_at": monitor_created_at,
                "lock_acquired_at": now,
                "heartbeat_at": now,
            })
            _atomic_json(state_path, state)
            with (run_dir / "stdout.log").open("ab") as out, (
                run_dir / "stderr.log"
            ).open("ab") as err:
                child_flags = (
                    subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
                    if os.name == "nt" else 0
                )
                process = subprocess.Popen(
                    command, cwd=root, stdout=out, stderr=err,
                    creationflags=child_flags,
                )
                child_created_at = _process_creation_time(process.pid)
                if child_created_at is None:
                    process.terminate()
                    raise FlowError("cannot read heavy child process identity")
                now = time.time()
                state.update({
                    "status": "running",
                    "child_pid": process.pid,
                    "child_created_at": child_created_at,
                    "child_started_at": now,
                    "handshake_at": now,
                    "heartbeat_at": now,
                })
                _atomic_json(state_path, state)
                while True:
                    try:
                        code = process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        code = None
                    now = time.time()
                    state["heartbeat_at"] = now
                    _atomic_json(state_path, state)
                    if code is not None:
                        break
            state.update({
                "status": "completed" if code == 0 else "failed",
                "exit_code": code,
                "finished_at": time.time(),
                "heartbeat_at": time.time(),
            })
            _atomic_json(state_path, state)
            return int(code)
    except BaseException as exc:
        if not state and state_path.is_file():
            try:
                loaded = json.loads(state_path.read_text(encoding="utf-8"))
                state = loaded if isinstance(loaded, dict) else {}
            except (OSError, json.JSONDecodeError):
                state = {}
        state.update({
            "schema": "generic-chess-heavy-v1",
            "run_id": args.run_id,
            "status": "failed",
            "exit_code": None,
            "error": f"{type(exc).__name__}: {exc}",
            "finished_at": time.time(),
            "heartbeat_at": time.time(),
        })
        _atomic_json(state_path, state)
        return 1


def command_heavy_start(root: Path, args: argparse.Namespace) -> int:
    state = active_state(root)
    require_worker_write_authority(state, root)
    require_no_supervisor_hold(root)
    if branch(root) != "sandbox":
        raise FlowError("heavy-start must be run from the sandbox worktree")
    label = args.label
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", label):
        raise FlowError("invalid heavy label")
    command = list(args.argv)
    if command and command[0] == "--":
        command.pop(0)
    if not command:
        raise FlowError("heavy-start requires a command after --")
    compute_metadata = _enforce_compute_gate(root, args, command)
    run_id = f"{label}-{uuid.uuid4().hex[:12]}"
    run_dir = _heavy_run_dir(root, run_id)
    run_dir.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha256(
        json.dumps(command, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    _atomic_json(run_dir / "command.json", command)
    _atomic_json(run_dir / "state.json", {
        "schema": "generic-chess-heavy-v1",
        "run_id": run_id,
        "label": label,
        "argv_digest": digest,
        "status": "starting",
        "started_at": time.time(),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "state_path": str(run_dir / "state.json"),
        **compute_metadata,
    })
    flags = (
        subprocess.DETACHED_PROCESS
        | subprocess.CREATE_NEW_PROCESS_GROUP
        | subprocess.CREATE_NO_WINDOW
        if os.name == "nt" else 0
    )
    try:
        monitor = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "__heavy-monitor", "--run-id", run_id],
            cwd=root,
            creationflags=flags,
            close_fds=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        failed = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        failed.update({
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
            "exit_code": None,
            "finished_at": time.time(),
            "heartbeat_at": time.time(),
        })
        _atomic_json(run_dir / "state.json", failed)
        raise FlowError(f"heavy-start could not launch monitor: {exc}") from exc
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            current = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            time.sleep(.1)
            continue
        if current.get("handshake_at") and current.get("child_pid"):
            print(json.dumps(current, sort_keys=True))
            return 0
        if current.get("status") == "failed":
            raise FlowError(f"heavy-start failed: {current.get('error', 'unknown monitor error')}")
        if monitor.poll() is not None:
            raise FlowError(f"heavy-start monitor exited before handshake ({monitor.returncode})")
        time.sleep(.1)
    try:
        monitor.terminate()
    except OSError:
        pass
    current = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    if current.get("status") == "starting":
        current.update({
            "status": "failed",
            "error": "heavy-start monitor handshake timed out",
            "exit_code": None,
            "finished_at": time.time(),
            "heartbeat_at": time.time(),
        })
        _atomic_json(run_dir / "state.json", current)
    raise FlowError("heavy-start monitor handshake timed out")


def command_heavy_status(root: Path, args: argparse.Namespace) -> int:
    base = runtime_dir(root) / "heavy-runs"
    paths = ([_heavy_run_dir(root, args.run_id)] if args.run_id else
             sorted(base.glob("*/state.json")) if base.exists() else [])
    rows = []
    for path in paths:
        if path.is_dir():
            path = path / "state.json"
        if not path.is_file():
            raise FlowError(f"heavy run state does not exist: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FlowError(f"invalid heavy run state: {path}") from exc
        try:
            rows.append(_classified_heavy_state(payload))
        except FlowError as exc:
            raise FlowError(f"invalid heavy run state: {path}: {exc}") from exc
    print(json.dumps(rows, indent=2, sort_keys=True))
    return 0


def command_start(root: Path, args: argparse.Namespace) -> None:
    previous = load_state(root, required=False)
    if previous.get("active"):
        if previous.get("mode") != args.mode:
            raise FlowError("an active session cannot change authority mode")
        raise FlowError("a GenericChess flow session is already active")
    require_no_supervisor_hold(root)
    require_handoff_owner(root)
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
        "active_request_id": None,
        "active_request_fingerprint": None,
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
    require_handoff_owner(root)
    state = load_state(root, required=False)
    if state.get("active") is True:
        if state.get("mode") != "courier":
            raise FlowError(
                "a Local mode session is active; continue that task or finish it before Courier work"
            )
        require_no_supervisor_hold(root)
        if state.get("active_request_directory"):
            command_recover(root, _args)
            return
        if state.get("resume_stage") == "SUBMIT_CLOSEOUT":
            report = state.get("handoff_closeout_path")
            if isinstance(report, str) and Path(report).is_file():
                print(f"NEXT_ACTION=submit the preserved closeout with --report-file {report}")
                print(f"WORK_ORDER_ID={state.get('last_work_order_id')}")
                print(f"BUSINESS_CANDIDATE_SHA={state.get('business_candidate_sha')}")
                return
        response_path = state.get("last_response_path")
        if isinstance(response_path, str) and Path(response_path).is_file():
            print(_console_safe(Path(response_path).read_text(encoding="utf-8-sig")))
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

    require_no_supervisor_hold(root)
    token = uuid.uuid4().hex
    source = runtime_dir(root) / "work-bootstrap.txt"
    source.write_text(f"{WORK_BOOTSTRAP}\nWORK_SESSION_ID={token}\n", encoding="utf-8")
    command_start(
        root,
        argparse.Namespace(
            mode="courier", message_file=str(source), work_request_token=token
        ),
    )


def _unresolved_escalation_ids(root: Path) -> list[str]:
    pending = []
    base = escalation_root(root)
    if not base.exists():
        return pending
    for dossier_path in sorted(base.glob("*/dossier.json")):
        if not (dossier_path.parent / "resolution.json").is_file():
            pending.append(dossier_path.parent.name)
    return pending


def command_followup(root: Path, args: argparse.Namespace) -> None:
    """Dispatch a short inline follow-up within an already active Courier session."""
    state = active_state(root)
    if state.get("mode") != "courier":
        raise FlowError("followup is only available in courier mode")
    require_worker_write_authority(state, root)
    require_no_supervisor_hold(root)
    if state.get("active_request_directory"):
        raise FlowError("cannot follow up while a Courier request is unresolved")
    if state.get("recovery_state") not in (None, "IDLE"):
        raise FlowError("cannot follow up while Courier recovery is unresolved")
    pending = _unresolved_escalation_ids(root)
    if pending:
        raise FlowError(f"cannot follow up while escalation is unresolved: {pending[0]}")
    response_value = state.get("last_response_path")
    response_path = Path(response_value) if isinstance(response_value, str) else None
    expected_response_sha = state.get("last_response_sha256")
    if response_path is None or not response_path.is_file() or not isinstance(expected_response_sha, str):
        raise FlowError("followup requires a captured and accepted prior Courier response")
    if _file_digest(response_path) != expected_response_sha:
        raise FlowError("followup prior Courier response hash mismatch")
    source = Path(args.message_file).resolve()
    try:
        body = source.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise FlowError(f"cannot read followup message: {source}") from exc
    if not body.strip():
        raise FlowError("followup message must not be empty")
    if len(body.encode("utf-8")) > INLINE_CHAT_REFERENCE_THRESHOLD:
        raise FlowError("followup message must be a short inline protocol/binding delta")
    require_clean(root)
    require_synced(root, "sandbox")
    dispatch_message(root, state, source, "followup")


def command_publish(root: Path, args: argparse.Namespace) -> None:
    if branch(root) != "sandbox":
        raise FlowError("publish must be run from the sandbox worktree")
    state = active_state(root)
    require_worker_write_authority(state, root)
    require_no_supervisor_hold(root)
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
    if getattr(args, "infrastructure", False):
        state["framework_published_sha"] = sha(root)
    else:
        state["last_published_sha"] = sha(root)
    save_state(root, state)
    print(f"PUBLISHED_SANDBOX_SHA={sha(root)}")


def supervisor_config_path(root: Path) -> Path:
    return runtime_dir(root) / "supervisor.json"


def supervisor_hold_path(root: Path) -> Path:
    return runtime_dir(root) / "active-supervisor-hold.json"


def supervisor_hold_history_root(root: Path) -> Path:
    return runtime_dir(root) / "supervisor-holds"


def supervisor_audit_path(root: Path) -> Path:
    return runtime_dir(root) / "supervisor-audit.json"


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


def _current_supervisor(root: Path) -> tuple[dict[str, Any], str]:
    config = _supervisor_config(root)
    current = os.environ.get("CODEX_THREAD_ID")
    if not current or current != config.get("supervisor_thread_id"):
        raise FlowError("only the registered Supervisor task may perform this action")
    return config, current


def active_supervisor_hold(root: Path) -> dict[str, Any] | None:
    path = supervisor_hold_path(root)
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FlowError(f"invalid Supervisor HOLD: {path}") from exc
    if not isinstance(value, dict) or value.get("schema") != "generic-chess-supervisor-hold-v1":
        raise FlowError(f"invalid Supervisor HOLD: {path}")
    return value if value.get("status") == "ACTIVE" else None


def require_no_supervisor_hold(root: Path) -> None:
    hold = active_supervisor_hold(root)
    if hold is not None:
        raise FlowError(
            f"Supervisor HOLD {hold.get('hold_id')} blocks worker writes and workflow progress"
        )


def command_register_worker(root: Path, args: argparse.Namespace) -> None:
    config, _current = _current_supervisor(root)
    thread_id = args.thread_id
    if not isinstance(thread_id, str) or not thread_id:
        raise FlowError("a worker thread id is required")
    value = dict(config)
    value.update({
        "worker_thread_id": thread_id,
        "worker_host_id": args.host_id,
        "worker_registered_at": time.time(),
    })
    _atomic_json(supervisor_config_path(root), value)
    print(json.dumps(value, indent=2, sort_keys=True))


def command_supervisor_audit_status(root: Path, _args: argparse.Namespace) -> None:
    path = supervisor_audit_path(root)
    if not path.is_file():
        print(json.dumps({"recorded": False, "audit": None}, indent=2, sort_keys=True))
        return
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FlowError(f"invalid Supervisor audit state: {path}") from exc
    if not isinstance(value, dict) or value.get("schema") != "generic-chess-supervisor-audit-v1":
        raise FlowError(f"invalid Supervisor audit state: {path}")
    print(json.dumps({"recorded": True, "audit": value}, indent=2,
                     ensure_ascii=False, sort_keys=True))


def command_supervisor_audit_record(root: Path, args: argparse.Namespace) -> int:
    config, current = _current_supervisor(root)
    worker_thread_id = config.get("worker_thread_id")
    if not isinstance(worker_thread_id, str) or not worker_thread_id:
        raise FlowError("a worker task must be registered before recording an audit")
    path = supervisor_audit_path(root)
    previous: dict[str, Any] | None = None
    if path.is_file():
        try:
            candidate = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FlowError(f"invalid Supervisor audit state: {path}") from exc
        if not isinstance(candidate, dict):
            raise FlowError(f"invalid Supervisor audit state: {path}")
        previous = candidate
    message_key = args.message_key or None
    duplicate = bool(
        message_key
        and previous
        and previous.get("message_key") == message_key
        and previous.get("worker_cursor") == (args.worker_cursor or None)
    )
    if duplicate:
        print(json.dumps({"recorded": False, "duplicate": True, "audit": previous},
                         indent=2, ensure_ascii=False, sort_keys=True))
        return 4
    value = {
        "schema": "generic-chess-supervisor-audit-v1",
        "classification": args.classification,
        "worker_status": args.worker_status,
        "worker_cursor": args.worker_cursor or None,
        "message_key": message_key,
        "hold_id": args.hold_id or None,
        "recorded_at": time.time(),
        "supervisor_thread_id": current,
        "worker_thread_id": worker_thread_id,
    }
    _atomic_json(path, value)
    print(json.dumps({"recorded": True, "duplicate": False, "audit": value},
                     indent=2, ensure_ascii=False, sort_keys=True))
    return 0


def command_supervisor_hold(root: Path, args: argparse.Namespace) -> None:
    config, current = _current_supervisor(root)
    existing = active_supervisor_hold(root)
    if existing is not None:
        print(json.dumps(existing, indent=2, ensure_ascii=False, sort_keys=True))
        return
    reason_path = Path(args.reason_file).resolve()
    try:
        reason = reason_path.read_text(encoding="utf-8-sig").strip()
    except OSError as exc:
        raise FlowError(f"cannot read HOLD reason file: {reason_path}") from exc
    if not reason:
        raise FlowError("HOLD reason must not be empty")
    worker_thread_id = args.worker_thread_id or config.get("worker_thread_id")
    if not isinstance(worker_thread_id, str) or not worker_thread_id:
        raise FlowError("a registered or explicit worker thread id is required")
    created_at = time.time()
    identity = f"{current}|{worker_thread_id}|{created_at}|{reason}"
    hold_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    value = {
        "schema": "generic-chess-supervisor-hold-v1",
        "hold_id": hold_id,
        "status": "ACTIVE",
        "severity": "URGENT",
        "reason": reason,
        "reason_file": str(reason_path),
        "supervisor_thread_id": current,
        "supervisor_host_id": config.get("supervisor_host_id", "local"),
        "worker_thread_id": worker_thread_id,
        "worker_host_id": config.get("worker_host_id", "local"),
        "created_at": created_at,
    }
    history = supervisor_hold_history_root(root) / hold_id
    history.mkdir(parents=True, exist_ok=False)
    _atomic_json(history / "hold.json", value)
    _atomic_json(supervisor_hold_path(root), value)
    print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))


def command_supervisor_hold_status(root: Path, args: argparse.Namespace) -> int:
    hold = active_supervisor_hold(root)
    payload = {"active": hold is not None, "hold": hold}
    print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    return 3 if hold is not None and getattr(args, "check_write", False) else 0


def command_supervisor_release(root: Path, args: argparse.Namespace) -> None:
    _config, current = _current_supervisor(root)
    path = supervisor_hold_path(root)
    if not path.is_file():
        raise FlowError("there is no Supervisor HOLD to release")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("hold_id") != args.hold_id:
        raise FlowError("the requested HOLD is not the current HOLD")
    if value.get("status") == "RELEASED":
        print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))
        return
    detail_path = Path(args.detail_file).resolve()
    try:
        detail = detail_path.read_text(encoding="utf-8-sig").strip()
    except OSError as exc:
        raise FlowError(f"cannot read HOLD release detail: {detail_path}") from exc
    if not detail:
        raise FlowError("HOLD release detail must not be empty")
    resolution = {
        "schema": "generic-chess-supervisor-hold-resolution-v1",
        "hold_id": args.hold_id,
        "detail": detail,
        "detail_file": str(detail_path),
        "supervisor_thread_id": current,
        "released_at": time.time(),
    }
    canonical = json.dumps(resolution, ensure_ascii=False, sort_keys=True).encode("utf-8")
    resolution["resolution_sha256"] = hashlib.sha256(canonical).hexdigest()
    history = supervisor_hold_history_root(root) / args.hold_id
    _atomic_json(history / "resolution.json", resolution)
    released = dict(value)
    released.update({
        "status": "RELEASED",
        "released_at": resolution["released_at"],
        "resolution_sha256": resolution["resolution_sha256"],
    })
    _atomic_json(path, released)
    print(json.dumps(released, indent=2, ensure_ascii=False, sort_keys=True))


def create_escalation(root: Path, state: dict[str, Any], *, reason: str,
                      worker_thread_id: str | None = None) -> dict[str, Any]:
    directory_value = state.get("active_request_directory")
    request_directory = Path(directory_value) if isinstance(directory_value, str) else None
    identity = f"{directory_value}|{state.get('last_published_sha')}"
    escalation_id = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
    directory = escalation_root(root) / escalation_id
    dossier_path = directory / "dossier.json"
    resolution_path = directory / "resolution.json"
    if dossier_path.exists() and resolution_path.exists():
        # A resolved escalation is immutable. Do not reopen the same ID.
        return json.loads(dossier_path.read_text(encoding="utf-8"))
    if dossier_path.exists():
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


def _healthy_live_owner_wait(state: dict[str, Any], probe: dict[str, Any]) -> bool:
    """Treat a matching live Courier owner as healthy waiting, not recovery failure."""
    if probe.get("event") != "courier_capture_latest_busy":
        return False
    if probe.get("live_owner_found") is not True:
        return False
    request_directory = state.get("active_request_directory")
    if not isinstance(request_directory, str) or not request_directory:
        return False
    expected_request_id = state.get("active_request_id") or Path(request_directory).name
    if probe.get("project_id") != PROJECT_ID or probe.get("request_id") != expected_request_id:
        return False
    expected_fingerprint = state.get("active_request_fingerprint")
    if not isinstance(expected_fingerprint, str) or not expected_fingerprint:
        return False
    if probe.get("fingerprint") != expected_fingerprint:
        return False
    owner_pid = probe.get("owner_pid")
    if owner_pid is not None:
        return _same_process(owner_pid, probe.get("owner_created_at"))
    return True


def _healthy_chat_contention_wait(state: dict[str, Any], status: dict[str, Any]) -> bool:
    """Accept only Courier's live, request-bound shared-Chat wait proof."""
    if status.get("event") != "courier_status":
        return False
    if status.get("state") not in {"chat_busy_waiting", "chat_busy_reconnecting"}:
        return False
    if status.get("contention_wait_active") is not True:
        return False
    if status.get("agent_action_required") is not False:
        return False
    if status.get("safe_next_action") != "wait_for_same_request":
        return False
    request_directory = state.get("active_request_directory")
    if not isinstance(request_directory, str) or not request_directory:
        return False
    expected_request_id = state.get("active_request_id") or Path(request_directory).name
    if status.get("project_id") != PROJECT_ID or status.get("request_id") != expected_request_id:
        return False
    expected_fingerprint = state.get("active_request_fingerprint")
    return (
        isinstance(expected_fingerprint, str)
        and bool(expected_fingerprint)
        and status.get("fingerprint") == expected_fingerprint
    )


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
        if _healthy_chat_contention_wait(state, status):
            state["recovery_state"] = "IDLE"
            state["last_probe"] = {
                key: status.get(key) for key in (
                    "event", "ok", "state", "project_id", "request_id", "fingerprint",
                    "contention_wait_active", "agent_action_required", "safe_next_action",
                )
            }
            recovery_event(
                state, "healthy_chat_contention_waiting",
                request_id=status["request_id"], courier_state=status["state"],
            )
            save_state(root, state)
            print(json.dumps({
                "event": "healthy_chat_contention_waiting",
                "ok": True,
                "project_id": status["project_id"],
                "request_id": status["request_id"],
                "courier_state": status["state"],
                "agent_action_required": False,
            }, sort_keys=True))
            return
        probe = courier(root, "courier_capture_latest", directory,
                        stream=True, allow_failure=True)
        state["last_probe"] = {
            key: probe.get(key) for key in (
                "event", "ok", "fingerprint", "captured_at", "latest_user_turn_found",
                "post_submission_reply_found", "request_match", "response_path",
                "submission_count", "message_sent", "error_code", "project_id",
                "request_id", "live_owner_found", "owner_pid", "owner_created_at",
            ) if key in probe
        }
        recovery_event(state, "latest_response_probed", **state["last_probe"])
        save_state(root, state)
        if _healthy_live_owner_wait(state, probe):
            state["recovery_state"] = "IDLE"
            recovery_event(state, "healthy_live_owner_waiting", request_id=probe["request_id"])
            save_state(root, state)
            print(json.dumps({
                "event": "healthy_live_owner_waiting",
                "ok": True,
                "project_id": probe["project_id"],
                "request_id": probe["request_id"],
            }, sort_keys=True))
            return
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
    proven_reply = (
        args.action in {"RESUME_WORKER", "RECOVERED"}
        and isinstance(state.get("active_request_directory"), str)
        and state.get("active_request_directory") == dossier.get("request_directory")
        and isinstance(dossier.get("last_probe"), dict)
        and dossier["last_probe"].get("request_match") is True
        and dossier["last_probe"].get("post_submission_reply_found") is True
        and isinstance(dossier["last_probe"].get("response_path"), str)
    )
    if proven_reply:
        state["active_request_directory"] = None
        state["recovery_state"] = "IDLE"
        recovery_event(state, "resolved_reply_request_cleared",
                       request_directory=dossier["request_directory"])
    else:
        state["recovery_state"] = "HUMAN_REQUIRED" if args.action == "HUMAN_REQUIRED" else "RECOVERED"
    recovery_event(state, "supervisor_resolved", escalation_id=args.escalation_id,
                   action=args.action, resolution_sha256=payload["resolution_sha256"])
    save_state(root, state)
    print(_console_safe(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)))
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
    require_no_supervisor_hold(root)
    if state.get("mode") != "courier":
        raise FlowError("closeout is only available in courier mode")
    dispatch_message(root, state, Path(args.report_file).resolve(), "closeout")


def command_promote(root: Path, args: argparse.Namespace) -> None:
    state = active_state(root)
    require_worker_write_authority(state, root)
    require_no_supervisor_hold(root)
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
    require_handoff_owner(root)
    state = active_state(root)
    require_no_supervisor_hold(root)
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


def courier_repository(root: Path) -> Path:
    return courier_launcher(root).parent.parent.resolve()


def courier_quiescence(root: Path) -> dict[str, Any]:
    value = courier(root, "courier_quiescence", allow_failure=True)
    if value.get("event") != "courier_quiescence" or value.get("quiescent") is not True:
        raise FlowError(f"ChatCourier is not quiescent: {json.dumps(value, ensure_ascii=False)}")
    return value


def _capsule_repository_state(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    trees = worktrees(root)
    courier_root = courier_repository(root)
    fetch(courier_root, "sandbox")
    courier_sha = sha(courier_root)
    remote_courier_sha = sha(courier_root, "origin/sandbox")
    if courier_sha != remote_courier_sha:
        raise FlowError(
            f"Courier must equal origin/sandbox before handoff: local={courier_sha} remote={remote_courier_sha}"
        )
    caps = courier_capabilities(root)
    generic = {
        "repository": git(root, "remote", "get-url", "origin"),
        "master_sha": sha(trees["master"]),
        "sandbox_sha": sha(trees["sandbox"]),
    }
    courier_info = {
        "repository": git(courier_root, "remote", "get-url", "origin"),
        "branch": "sandbox",
        "sha": courier_sha,
        "build_id": caps.get("courier_build_id"),
    }
    return generic, courier_info


def _portable_closeout(path_value: str | None) -> tuple[str | None, str | None]:
    if path_value is None:
        return None, None
    path = Path(path_value).resolve()
    if not path.is_file():
        raise FlowError(f"closeout file does not exist: {path}")
    data = path.read_bytes()
    if len(data) > 32 * 1024:
        raise FlowError("handoff closeout exceeds 32 KiB; publish it and hand off a repository path")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FlowError("handoff closeout must be UTF-8") from exc
    forbidden = (
        r"https://(?:www\.)?chatgpt\.com/",
        r"(?i)C:\\Users\\",
        r"(?i)CODEX_THREAD_ID",
        r"(?i)(?:password|private[_ -]?key|access[_ -]?token)\s*[:=]",
    )
    for pattern in forbidden:
        if re.search(pattern, text):
            raise FlowError(f"closeout contains non-portable or sensitive text matching {pattern}")
    text = text.replace("\r\n", "\n").replace("\r", "\n").rstrip() + "\n"
    return text, hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validated_handoff_closeout(path: Path, expected_sha256: str | None) -> str | None:
    if not path.is_file():
        return None
    try:
        text = path.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise FlowError("handoff closeout must be UTF-8") from exc
    legacy_windows = text.replace("\r\n", "\n")
    collapsed_windows = re.sub(r"\r+(?=\n)", "\r", text)
    canonical_lf = text.replace("\r\n", "\n").replace("\r", "\n")
    candidates = []
    for candidate in (text, legacy_windows, collapsed_windows, canonical_lf):
        for representation in (
            candidate,
            candidate.rstrip() + ("\r\n" if "\r\n" in candidate else "\n"),
        ):
            if representation not in candidates:
                candidates.append(representation)
    if expected_sha256:
        for candidate in candidates:
            if hashlib.sha256(candidate.encode("utf-8")).hexdigest() == expected_sha256:
                return candidate
        raise FlowError("handoff closeout payload hash does not match")
    return candidates[0]


def command_machine_setup(root: Path, args: argparse.Namespace) -> None:
    machine = save_machine(args.host_id)
    remote_sha = _remote_handoff_sha(root)
    if remote_sha is None:
        generic, courier_info = _capsule_repository_state(root)
        capsule = {
            "schema": HANDOFF_SCHEMA,
            "generation": 0,
            "state": "CLAIMED",
            "owner": {
                "host_id": machine["host_id"],
                "machine_id": machine["machine_id"],
            },
            "target_host_id": None,
            "generic": generic,
            "courier": courier_info,
            "workflow": {"resume_stage": "REQUEST_NEXT_ORDER"},
            "created_at": int(time.time()),
        }
        ensure_handoff_repo(root, initialize=capsule)
    else:
        ensure_handoff_repo(root)
    print(json.dumps({"machine": machine, "workflow_state_initialized": True},
                     indent=2, sort_keys=True))


def command_handoff_status(root: Path, _args: argparse.Namespace) -> None:
    repo = ensure_handoff_repo(root)
    value = load_handoff(repo)
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def command_handoff_release(root: Path, args: argparse.Namespace) -> None:
    if not HANDOFF_HOST.fullmatch(args.to):
        raise FlowError("target host ID is invalid")
    require_handoff_owner(root)
    state = active_state(root)
    trees = worktrees(root)
    for name in ("master", "sandbox"):
        require_clean(trees[name])
        require_synced(trees[name], name)
    if state.get("active_request_directory"):
        raise FlowError("cannot release while a Courier request needs reconciliation")
    if state.get("recovery_state") in {"ESCALATED", "HUMAN_REQUIRED"}:
        raise FlowError("cannot release with an unresolved escalation")
    courier_quiescence(root)
    status = state.get("chat_control", {}).get("GENERICCHESS_STATUS")
    if status == "COMPLETE":
        stage = "COMPLETE"
    elif state.get("work_order_active") is True:
        stage = "SUBMIT_CLOSEOUT"
    else:
        stage = "REQUEST_NEXT_ORDER"
    closeout, closeout_sha = _portable_closeout(args.closeout_file)
    if stage == "SUBMIT_CLOSEOUT" and closeout is None:
        raise FlowError("an active work order requires --closeout-file at handoff")
    generic, courier_info = _capsule_repository_state(root)
    candidate = (state.get("business_candidate_sha") or state.get("last_published_sha")
                 or generic["sandbox_sha"])
    tested = state.get("tested_shas", {}).get(candidate, [])
    generic["business_candidate_sha"] = candidate
    repo = ensure_handoff_repo(root)
    previous = load_handoff(repo)
    capsule = {
        "schema": HANDOFF_SCHEMA,
        "generation": int(previous["generation"]) + 1,
        "state": "RELEASED",
        "owner": None,
        "target_host_id": args.to,
        "generic": generic,
        "courier": courier_info,
        "workflow": {
            "mode": state.get("mode"),
            "resume_stage": stage,
            "work_order_active": bool(state.get("work_order_active")),
            "last_work_order_id": state.get("last_work_order_id"),
            "chat_control": state.get("chat_control", {}),
            "work_request_token": state.get("work_request_token"),
            "tested_candidate_targets": tested,
            "closeout_sha256": closeout_sha,
        },
        "created_at": int(time.time()),
    }
    commit_handoff(root, repo, capsule, closeout=closeout,
                   message=f"Release GenericChess workflow to {args.to}")
    state["handoff_released"] = True
    state["handoff_generation"] = capsule["generation"]
    state["resume_stage"] = stage
    save_state(root, state)
    print(json.dumps(capsule, ensure_ascii=False, indent=2, sort_keys=True))


def command_handoff_claim(root: Path, args: argparse.Namespace) -> None:
    machine = save_machine(args.host_id)
    repo = ensure_handoff_repo(root)
    capsule = load_handoff(repo)
    if capsule.get("state") != "RELEASED":
        raise FlowError("workflow is not released")
    if capsule.get("target_host_id") not in {args.host_id, "*"}:
        raise FlowError(f"workflow is released to {capsule.get('target_host_id')}, not {args.host_id}")
    trees = worktrees(root)
    for name in ("master", "sandbox"):
        require_clean(trees[name])
        require_synced(trees[name], name)
        expected = capsule["generic"][f"{name}_sha"]
        if sha(trees[name]) != expected:
            raise FlowError(f"{name} SHA does not match handoff capsule")
    courier_root = courier_repository(root)
    fetch(courier_root, "sandbox")
    if sha(courier_root) != capsule["courier"]["sha"] or not synced(courier_root, "sandbox"):
        raise FlowError("Courier checkout does not match the handoff capsule")
    caps = courier_capabilities(root)
    if PROJECT_ID not in caps.get("projects", []):
        raise FlowError("ChatCourier project GENERICCHESS is not registered on this machine")
    courier_quiescence(root)

    claimed = dict(capsule)
    claimed["generation"] = int(capsule["generation"]) + 1
    claimed["state"] = "CLAIMED"
    claimed["owner"] = {"host_id": args.host_id, "machine_id": machine["machine_id"]}
    claimed["target_host_id"] = None
    claimed["created_at"] = int(time.time())
    closeout_path = repo / "closeout.md"
    expected_closeout = capsule.get("workflow", {}).get("closeout_sha256")
    closeout = _validated_handoff_closeout(closeout_path, expected_closeout)
    commit_handoff(root, repo, claimed, closeout=closeout,
                   message=f"Claim GenericChess workflow on {args.host_id}")

    workflow = claimed.get("workflow", {})
    candidate = claimed["generic"].get("business_candidate_sha")
    local_closeout = None
    if closeout is not None:
        local_path = runtime_dir(root) / "handoff-closeout.md"
        local_path.write_text(closeout, encoding="utf-8", newline="")
        local_closeout = str(local_path)
    restored = {
        "active": workflow.get("resume_stage") != "COMPLETE",
        "mode": workflow.get("mode", "courier"),
        "base_master_sha": claimed["generic"]["master_sha"],
        "base_sandbox_sha": claimed["generic"]["sandbox_sha"],
        "active_request_directory": None,
        "work_order_active": bool(workflow.get("work_order_active")),
        "last_work_order_id": workflow.get("last_work_order_id"),
        "last_published_sha": candidate,
        "business_candidate_sha": candidate,
        "chat_control": workflow.get("chat_control", {}),
        "work_request_token": workflow.get("work_request_token"),
        "tested_shas": {candidate: workflow.get("tested_candidate_targets", [])} if candidate else {},
        "recovery_state": "IDLE",
        "recovery_attempts": 0,
        "recovery_timeline": [],
        "last_probe": None,
        "escalation_id": None,
        "resume_stage": workflow.get("resume_stage"),
        "handoff_closeout_path": local_closeout,
        "handoff_generation": claimed["generation"],
    }
    save_state(root, restored)
    print(json.dumps({"claimed": claimed, "restored_session": restored},
                     ensure_ascii=False, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(prog="generic-chess-flow")
    sub = value.add_subparsers(dest="command", required=True)
    sub.add_parser("status").set_defaults(handler=command_status)
    machine = sub.add_parser("machine-setup")
    machine.add_argument("--host-id", required=True)
    machine.set_defaults(handler=command_machine_setup)
    sub.add_parser("handoff-status").set_defaults(handler=command_handoff_status)
    release = sub.add_parser("handoff-release")
    release.add_argument("--to", required=True)
    release.add_argument("--closeout-file")
    release.set_defaults(handler=command_handoff_release)
    claim_handoff = sub.add_parser("handoff-claim")
    claim_handoff.add_argument("--host-id", required=True)
    claim_handoff.set_defaults(handler=command_handoff_claim)
    sub.add_parser("work").set_defaults(handler=command_work)
    followup = sub.add_parser("followup")
    followup.add_argument("--message-file", required=True)
    followup.set_defaults(handler=command_followup)
    start = sub.add_parser("start")
    start.add_argument("--mode", choices=("courier", "local"), required=True)
    start.add_argument("--message-file")
    start.set_defaults(handler=command_start)
    publish = sub.add_parser("publish")
    publish.add_argument("--tests", nargs="*")
    publish.add_argument("--infrastructure", action="store_true",
                         help="publish workflow infrastructure without replacing the business candidate")
    publish.set_defaults(handler=command_publish)
    heavy = sub.add_parser("heavy")
    heavy.add_argument("--resource-envelope", required=True)
    heavy.add_argument("--compute-plan")
    heavy.add_argument("argv", nargs=argparse.REMAINDER)
    heavy.set_defaults(handler=command_heavy)
    heavy_start = sub.add_parser("heavy-start")
    heavy_start.add_argument("--label", required=True)
    heavy_start.add_argument("--resource-envelope", required=True)
    heavy_start.add_argument("--compute-plan")
    heavy_start.add_argument("argv", nargs=argparse.REMAINDER)
    heavy_start.set_defaults(handler=command_heavy_start)
    compute_approve = sub.add_parser("compute-plan-approve")
    compute_approve.add_argument("--plan-file", required=True)
    compute_approve.add_argument("--chat-approval-file", required=True)
    compute_approve.set_defaults(handler=command_compute_plan_approve)
    compute_status = sub.add_parser("compute-plan-status")
    compute_status.add_argument("--plan-file", required=True)
    compute_status.set_defaults(handler=command_compute_plan_status)
    compute_revoke = sub.add_parser("compute-plan-revoke")
    compute_revoke.add_argument("--plan-file", required=True)
    compute_revoke.set_defaults(handler=command_compute_plan_revoke)
    heavy_status = sub.add_parser("heavy-status")
    heavy_status.add_argument("--run-id")
    heavy_status.set_defaults(handler=command_heavy_status)
    heavy_monitor = sub.add_parser("__heavy-monitor")
    heavy_monitor.add_argument("--run-id", required=True)
    heavy_monitor.set_defaults(handler=command_heavy_monitor)
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
    worker = sub.add_parser("register-worker")
    worker.add_argument("--thread-id", required=True)
    worker.add_argument("--host-id", default="local")
    worker.set_defaults(handler=command_register_worker)
    audit_status = sub.add_parser("supervisor-audit-status")
    audit_status.set_defaults(handler=command_supervisor_audit_status)
    audit = sub.add_parser("supervisor-audit-record")
    audit.add_argument("--classification", required=True, choices=(
        "HEALTHY_RUNNING", "UNJUSTIFIED_IDLE", "NONURGENT_CORRECTION",
        "URGENT_HOLD", "LEGITIMATE_STOP", "HUMAN_REQUIRED"))
    audit.add_argument("--worker-status", required=True)
    audit.add_argument("--worker-cursor")
    audit.add_argument("--message-key")
    audit.add_argument("--hold-id")
    audit.set_defaults(handler=command_supervisor_audit_record)
    hold = sub.add_parser("supervisor-hold")
    hold.add_argument("--reason-file", required=True)
    hold.add_argument("--worker-thread-id")
    hold.set_defaults(handler=command_supervisor_hold)
    hold_status = sub.add_parser("supervisor-hold-status")
    hold_status.add_argument("--check-write", action="store_true")
    hold_status.set_defaults(handler=command_supervisor_hold_status)
    release_hold = sub.add_parser("supervisor-release")
    release_hold.add_argument("--hold-id", required=True)
    release_hold.add_argument("--detail-file", required=True)
    release_hold.set_defaults(handler=command_supervisor_release)
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
