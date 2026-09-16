from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid
from typing import Any, Sequence


PROJECT_ID = "GENERICCHESS"
WORK_BOOTSTRAP = """Issue the next concrete GenericChess work order.

Inspect the current published sandbox SHA and choose one bounded, useful next
step that directly tests or improves playing strength, self-improvement, or the
main algorithm. Process, audit, and formatting work is justified only when it
removes a demonstrated blocker that a smaller fix cannot remove. Return COMPLETE
if no further work is currently needed, or BLOCKED only when user action is
genuinely required.
"""
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
CONTROL_FIELDS = {
    "GENERICCHESS_STATUS",
    "GENERICCHESS_CANDIDATE_SHA",
    "GENERICCHESS_PROMOTION",
}
BUSINESS_CONTROL_FIELDS = {"LOCAL_SUPERVISOR_REQUIRED"}
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
COMPUTE_PLAN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
COMPUTE_POLICY_PATH = Path(__file__).with_name("compute_policy.json")
LARGE_COMPUTE_QUOTA_WALL_MINUTES = 120
LARGE_COMPUTE_QUOTA_WINDOW_SECONDS = 24 * 60 * 60


class FlowError(RuntimeError):
    pass


def repo_relative_path(root: Path, path: str | Path) -> str:
    """Return a repository-relative POSIX path, rejecting paths outside root."""
    repository = Path(root).resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = repository / candidate
    try:
        return candidate.resolve().relative_to(repository).as_posix()
    except ValueError as exc:
        raise FlowError(f"path is outside the repository: {path}") from exc


def _read_json_file(path: Path, label: str) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FlowError(f"invalid {label}: {path}") from exc
    if not isinstance(value, dict):
        raise FlowError(f"invalid {label}: {path}")
    return value


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


def _load_resource_envelope(path_value: str | Path) -> dict[str, Any]:
    path = Path(path_value).resolve()
    return _validate_resource_envelope(_read_json_file(path, "resource envelope"))


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


def _load_compute_plan(root: Path, path_value: str | Path) -> dict[str, Any]:
    path = Path(path_value).resolve()
    plan = _read_json_file(path, "compute plan")
    required = {
        "schema", "plan_id", "version", "scientific_decision",
        "why_smaller_evidence_insufficient", "reusable_evidence", "stages",
        "resource_envelope", "checkpoint_behavior", "stage_pause_points",
        "early_stop_rules", "failure_exit_path", "alternatives", "command_argv",
    }
    if plan.get("schema") != COMPUTE_PLAN_SCHEMA or not required.issubset(plan):
        raise FlowError("compute plan is missing required fields")
    if not COMPUTE_PLAN_ID.fullmatch(str(plan["plan_id"])) or not isinstance(plan["version"], int) or plan["version"] <= 0:
        raise FlowError("compute plan identity is invalid")
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
    return plan


def _canonical_argv(root: Path, argv: Sequence[str]) -> list[str]:
    canonical: list[str] = []
    for part in argv:
        normalized = part.replace("\\", "/")
        if "://" in normalized:
            canonical.append(part)
            continue
        candidate = Path(part)
        explicit_path = (
            candidate.is_absolute()
            or part.startswith(("./", "../", ".\\", "..\\"))
            or (Path(root) / candidate).exists()
        )
        if not explicit_path:
            canonical.append(part)
            continue
        try:
            canonical.append(repo_relative_path(root, part))
        except FlowError:
            canonical.append(normalized)
    return canonical


def _work_order_recorded_at(state: dict[str, Any]) -> float | None:
    """Return the local receipt time for the currently imported work order."""
    response_sha = state.get("last_response_sha256")
    timeline = state.get("recovery_timeline", [])
    if not isinstance(timeline, list):
        return None
    for event in reversed(timeline):
        if not isinstance(event, dict) or event.get("event") != "response_accepted":
            continue
        if response_sha is not None and event.get("response_sha256") != response_sha:
            continue
        recorded_at = event.get("at")
        if isinstance(recorded_at, (int, float)) and recorded_at >= 0:
            return float(recorded_at)
    return None


def _large_compute_quota_records(root: Path) -> list[float]:
    """Read only successful-child quota markers from durable runtime state."""
    records: list[float] = []
    base = runtime_dir(root)
    state_paths = list((base / "heavy-runs").glob("*/state.json")) if (base / "heavy-runs").exists() else []
    for path in state_paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict) or payload.get("quota_counted") is not True:
            continue
        expected = payload.get("expected_wall_minutes")
        recorded_at = payload.get("work_order_recorded_at")
        if (
            isinstance(expected, (int, float))
            and expected > LARGE_COMPUTE_QUOTA_WALL_MINUTES
            and isinstance(recorded_at, (int, float))
            and recorded_at >= 0
        ):
            records.append(float(recorded_at))
    return records


def _large_compute_schedule(root: Path, envelope: dict[str, Any],
                            state: dict[str, Any]) -> tuple[float | None, bool]:
    """Return receipt time and whether another >2h run exists in its 24h window.

    This is scheduling information, not an authorization gate.  The Supervisor
    prefers smaller work or a split plan when possible, but may run necessary
    mainline compute rather than leave the workflow idle.
    """
    expected = envelope.get("expected_wall_minutes")
    if not isinstance(expected, (int, float)) or expected <= LARGE_COMPUTE_QUOTA_WALL_MINUTES:
        return None, False
    recorded_at = _work_order_recorded_at(state)
    if recorded_at is None:
        return None, False
    prior = [
        value for value in _large_compute_quota_records(root)
        if abs(recorded_at - value) <= LARGE_COMPUTE_QUOTA_WINDOW_SECONDS
    ]
    return recorded_at, bool(prior)


def _enforce_compute_gate(root: Path, args: argparse.Namespace,
                          command: list[str] | None = None) -> dict[str, Any]:
    envelope_path = getattr(args, "resource_envelope", None)
    plan_path = getattr(args, "compute_plan", None)
    plan = None
    if plan_path:
        plan = _load_compute_plan(root, plan_path)
    if plan is not None:
        envelope = _validate_resource_envelope(plan["resource_envelope"])
    elif envelope_path:
        envelope = _load_resource_envelope(envelope_path)
    else:
        raise FlowError("heavy requires an explicit --resource-envelope or --compute-plan declaration")
    large = _compute_is_large(envelope)
    if plan is not None and command is not None and _canonical_argv(root, plan["command_argv"]) != _canonical_argv(root, command):
        raise FlowError("compute plan command/stage/budget identity differs from the run")
    recorded_at = None
    scheduling_conflict = False
    quota_required = (
        isinstance(envelope.get("expected_wall_minutes"), (int, float))
        and envelope["expected_wall_minutes"] > LARGE_COMPUTE_QUOTA_WALL_MINUTES
    )
    if quota_required:
        recorded_at, scheduling_conflict = _large_compute_schedule(
            root, envelope, active_state(root)
        )
    return {
        "resource_envelope": envelope,
        "compute_plan_id": plan["plan_id"] if plan else None,
        "compute_size": "large" if large else "small_or_medium",
        "hard_wall_minutes": envelope["hard_wall_minutes"],
        "expected_wall_minutes": envelope["expected_wall_minutes"],
        "work_order_recorded_at": recorded_at,
        "quota_required": quota_required,
        "quota_counted": False,
        "large_compute_within_24h": scheduling_conflict,
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


def _apply_current_supervisor_resolution(root: Path, state: dict[str, Any]) -> bool:
    """Apply one newer signed resolution and retire its obsolete pause fields."""
    escalation_id = state.get("escalation_id")
    if not isinstance(escalation_id, str):
        return False
    path = escalation_root(root) / escalation_id / "resolution.json"
    if not path.is_file():
        return False
    try:
        resolution = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(resolution, dict) or resolution.get("action") not in {
        "RESUME_WORKER", "RECOVERED", "USER_SUPERSEDED_REQUEST",
    }:
        return False
    resolved_at = resolution.get("resolved_at")
    if not isinstance(resolved_at, (int, float)):
        return False
    chat_control = state.get("chat_control") if isinstance(state.get("chat_control"), dict) else {}
    legacy_compute_hold = (
        chat_control.get("GENERICCHESS_COMPUTE_PLAN_APPROVAL") == "HOLD"
        and isinstance(state.get("pending_compute_plan"), dict)
    )
    prior_decision = state.get("supervisor_decision_at")
    if isinstance(prior_decision, (int, float)) and resolved_at <= prior_decision:
        return False
    # A newer accepted response is a newer decision boundary; an old
    # escalation must not clear that response's business notice.
    for event in state.get("recovery_timeline", []):
        if (isinstance(event, dict) and event.get("event") == "response_accepted"
                and isinstance(event.get("at"), (int, float))
                and event["at"] > resolved_at and not legacy_compute_hold):
            return False
    state["supervisor_decision_at"] = float(resolved_at)
    state["local_supervisor_required"] = False
    state.pop("escalation_id", None)
    state.pop("business_supervisor_notice_path", None)
    state.pop("pending_compute_plan", None)
    for key in (
        "GENERICCHESS_COMPUTE_PLAN_APPROVAL",
        "GENERICCHESS_COMPUTE_PLAN_SHA",
        "GENERICCHESS_COMPUTE_ENVELOPE_SHA",
    ):
        chat_control.pop(key, None)
    if state.get("recovery_state") in {"ESCALATED", "HUMAN_REQUIRED"}:
        state["recovery_state"] = "IDLE"
    recovery_event(state, "supervisor_pause_cleared", resolution_sha256=resolution.get("resolution_sha256"))
    return True


def _clear_retired_compute_fields(state: dict[str, Any]) -> bool:
    """Drop state left by the removed Chat compute-approval protocol."""
    changed = state.pop("pending_compute_plan", None) is not None
    control = state.get("chat_control")
    if isinstance(control, dict):
        for key in (
            "GENERICCHESS_COMPUTE_PLAN_APPROVAL",
            "GENERICCHESS_COMPUTE_PLAN_SHA",
            "GENERICCHESS_COMPUTE_ENVELOPE_SHA",
        ):
            changed = control.pop(key, None) is not None or changed
    return changed


def active_state(root: Path) -> dict[str, Any]:
    state = load_state(root)
    if state.get("active") is not True:
        raise FlowError("no active GenericChess flow session")
    changed = _apply_current_supervisor_resolution(root, state)
    changed = _clear_retired_compute_fields(state) or changed
    if changed:
        save_state(root, state)
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
        key = key.strip()
        if key in CONTROL_FIELDS | BUSINESS_CONTROL_FIELDS:
            found[key] = value.strip()
    return found


def normalize_control_footer(text: str) -> tuple[dict[str, str], list[str]]:
    control = parse_control_footer(text)
    warnings: list[str] = []
    defaults = {
        "GENERICCHESS_STATUS": "CONTINUE",
        "GENERICCHESS_CANDIDATE_SHA": "NONE",
        "GENERICCHESS_PROMOTION": "HOLD",
    }
    for key, default in defaults.items():
        if key not in control:
            warnings.append(f"missing {key}; defaulted to {default}")
            control[key] = default
    if control["GENERICCHESS_STATUS"] not in CONTROL_STATUSES:
        warnings.append(
            f"invalid GENERICCHESS_STATUS={control['GENERICCHESS_STATUS']!r}; defaulted to CONTINUE"
        )
        control["GENERICCHESS_STATUS"] = "CONTINUE"
    candidate = control["GENERICCHESS_CANDIDATE_SHA"]
    if candidate != "NONE" and not FULL_SHA.fullmatch(candidate):
        warnings.append(
            f"invalid GENERICCHESS_CANDIDATE_SHA={candidate!r}; defaulted to NONE"
        )
        control["GENERICCHESS_CANDIDATE_SHA"] = "NONE"
        candidate = "NONE"
    if control["GENERICCHESS_PROMOTION"] not in PROMOTION_VALUES:
        warnings.append(
            f"invalid GENERICCHESS_PROMOTION={control['GENERICCHESS_PROMOTION']!r}; defaulted to HOLD"
        )
        control["GENERICCHESS_PROMOTION"] = "HOLD"
    if control["GENERICCHESS_PROMOTION"] == "APPROVE" and candidate == "NONE":
        warnings.append("GENERICCHESS_PROMOTION=APPROVE without a valid candidate; downgraded to HOLD")
        control["GENERICCHESS_PROMOTION"] = "HOLD"
    return control, warnings


def validate_control_footer(text: str) -> dict[str, str]:
    """Return normalized controls while retaining the legacy public helper."""
    control, _warnings = normalize_control_footer(text)
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


def _record_business_escalation(root: Path, state: dict[str, Any], control: dict[str, str],
                                response_sha256: str) -> str | None:
    """Record one mechanical Supervisor notice without freezing Courier recovery."""
    if control.get("LOCAL_SUPERVISOR_REQUIRED", "").casefold() != "true":
        return None
    notice_key = hashlib.sha256(
        f"{state.get('active_request_id', '')}\n{response_sha256}".encode("utf-8")
    ).hexdigest()[:20]
    notices = state.setdefault("business_supervisor_notifications", {})
    if notice_key in notices:
        state["local_supervisor_required"] = True
        state["business_supervisor_notice_path"] = notices[notice_key].get("notice_path")
        return state["business_supervisor_notice_path"]
    directory = runtime_dir(root) / "business-escalations" / notice_key
    _atomic_json(directory / "notice.json", {
        "schema": "generic-chess-business-escalation-v1",
        "notice_key": notice_key,
        "kind": "LOCAL_SUPERVISOR_REQUIRED",
        "request_id": state.get("active_request_id"),
        "worker_thread_id": state.get("worker_thread_id"),
        "response_sha256": response_sha256,
        "created_at": time.time(),
        "detail": "Chat marked this response LOCAL_SUPERVISOR_REQUIRED=true. Import the response normally; do not retry Courier transport.",
    })
    notices[notice_key] = {
        "kind": "LOCAL_SUPERVISOR_REQUIRED",
        "response_sha256": response_sha256,
        "notice_path": str(directory / "notice.json"),
    }
    state["local_supervisor_required"] = True
    state["business_supervisor_notice_path"] = str(directory / "notice.json")
    recovery_event(state, "business_supervisor_notification_recorded", notice_key=notice_key)
    return state["business_supervisor_notice_path"]


def update_response_state(root: Path, state: dict[str, Any], event: dict[str, Any],
                          *, source: str = "normal") -> None:
    if event.get("event") in {"response_received", "response_duplicate", "courier_latest_response_captured"}:
        response_path = event.get("response_path")
        if not isinstance(response_path, str):
            raise FlowError("Courier response event did not include response_path")
        response = Path(response_path)
        text = response.read_text(encoding="utf-8-sig")
        control, warnings = normalize_control_footer(text)
        state["last_response_path"] = str(response)
        work_order = WORK_ORDER_ID.search(text)
        state["chat_control"] = control
        state["control_warnings"] = warnings
        state["last_work_order_id"] = work_order.group(1) if work_order else None
        state["work_order_active"] = control["GENERICCHESS_STATUS"] == "CONTINUE"
        state["last_response_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        state["last_response_source"] = source
        state["active_request_directory"] = None
        state["recovery_state"] = "RECOVERED" if source != "normal" else "IDLE"
        notice_path = _record_business_escalation(
            root, state, control, state["last_response_sha256"]
        )
        if notice_path:
            state["business_supervisor_notice_path"] = notice_path
        recovery_event(state, "response_accepted", source=source,
                       response_sha256=state["last_response_sha256"])
        save_state(root, state)
        print(_console_safe(text))
        if notice_path:
            print("NEXT_ACTION=notify registered Supervisor")
            print(f"SUPERVISOR_NOTICE_PATH={notice_path}")


def chat_message_body(root: Path, source: Path, *, reference_only: bool = False) -> str:
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


def _migration_dispatch_key(state: dict[str, Any], purpose: str,
                            base_key: str) -> str:
    """Give the next equivalent dispatch after supersession a fresh identity."""
    retired_directory = state.get("retired_request_directory")
    migration = state.get("superseded_request_migration")
    if not isinstance(retired_directory, str) or not retired_directory:
        return base_key
    if not isinstance(migration, dict):
        migration = {
            "status": "PENDING",
            "retired_request_directory": retired_directory,
            "retired_request_id": state.get("retired_request_id")
                or Path(retired_directory).name,
            "retired_request_key": state.get("retired_request_key"),
        }
    if migration.get("status") not in {"PENDING", "CONSUMED"}:
        return base_key
    bound_purpose = migration.get("purpose")
    bound_base_key = migration.get("base_key")
    if bound_purpose is not None and bound_purpose != purpose:
        return base_key
    if bound_base_key is not None and bound_base_key != base_key:
        return base_key
    migration["purpose"] = purpose
    migration["base_key"] = base_key
    migration.setdefault(
        "migration_key",
        f"{base_key}-migration-{uuid.uuid4().hex[:12]}",
    )
    migration["status"] = "CONSUMED"
    state["superseded_request_migration"] = migration
    if state.get("active_request_directory") == retired_directory:
        state["active_request_directory"] = None
        if state.get("active_request_id") == migration.get("retired_request_id"):
            state["active_request_id"] = None
    return migration["migration_key"]


def dispatch_message(root: Path, state: dict[str, Any], source: Path, purpose: str,
                     attachments: list[Path] | None = None) -> None:
    sandbox = sandbox_root(root)
    require_clean(sandbox)
    require_synced(sandbox, "sandbox")
    report_size = source.stat().st_size
    if purpose in {"closeout", "blocker"} and report_size > INLINE_CHAT_REFERENCE_THRESHOLD and not attachments:
        raise FlowError("closeout/blocker exceeds 24 KiB; provide a concise summary or an explicit attachment")
    body = chat_message_body(
        root, source,
        reference_only=purpose in {"closeout", "blocker"} and report_size > INLINE_CHAT_REFERENCE_THRESHOLD,
    )
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    base_key = f"{purpose}-{sha(sandbox)[:12]}-{digest[:12]}"
    key = _migration_dispatch_key(state, purpose, base_key)
    generated = runtime_dir(root) / f"{key}.txt"
    generated.write_text(
        body.rstrip()
        + "\n\nRepository authority context:\n"
        + f"PROJECT_ID={PROJECT_ID}\n"
        + f"MASTER_SHA={sha(worktrees(root)['master'])}\n"
        + f"SANDBOX_SHA={sha(sandbox)}\n"
        + "The referenced sandbox SHA is committed and published to origin/sandbox.\n"
        + "Prioritize actual playing-strength, self-improvement, and main-algorithm work. Process or audit work must remove a demonstrated mainline blocker and use the smallest sufficient fix; five consecutive non-mainline work orders is a direction warning.\n"
        + "Ordinary explanatory responses are valid even when control fields are omitted; the flow imports the body and defaults missing/invalid controls to CONTINUE/NONE/HOLD.\n"
        + "Only explicit valid control fields may authorize COMPLETE, BLOCKED, or promotion.\n"
        + "End the response with these control fields when applicable:\n"
        + "GENERICCHESS_STATUS=CONTINUE|COMPLETE|BLOCKED\n"
        + "GENERICCHESS_CANDIDATE_SHA=<40-hex-sha-or-NONE>\n"
        + "GENERICCHESS_PROMOTION=APPROVE|HOLD\n",
        encoding="utf-8",
    )
    if key != base_key:
        save_state(root, state)
    prepare_args = [
        "courier_prepare", "--project-id", PROJECT_ID,
        "--idempotency-key", key, "--message-file", str(generated),
    ]
    for attachment in attachments or ():
        resolved_attachment = Path(attachment).resolve()
        if not resolved_attachment.is_file():
            raise FlowError(f"Courier attachment does not exist: {resolved_attachment}")
        prepare_args.extend(("--attachment", str(resolved_attachment)))
    prepared = courier(root, *prepare_args)
    request_directory = prepared.get("request_directory")
    if not isinstance(request_directory, str):
        raise FlowError("Courier prepare did not return a request directory")
    if key != base_key and request_directory == state.get("retired_request_directory"):
        raise FlowError("superseded Courier request was returned for a migration dispatch")
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
    changed = session.get("active") is True and _apply_current_supervisor_resolution(root, session)
    changed = _clear_retired_compute_fields(session) or changed
    if changed:
        save_state(root, session)
    payload["session"] = {
        key: session.get(key) for key in (
            "active", "mode", "worker_thread_id", "active_request_id",
            "recovery_state", "work_order_active",
        )
    }
    heavy = None
    heavy_root = runtime_dir(root) / "heavy-runs"
    heavy_states = sorted(
        heavy_root.glob("*/state.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if heavy_root.exists() else []
    if heavy_states:
        try:
            candidate = json.loads(heavy_states[0].read_text(encoding="utf-8"))
            heavy = candidate if isinstance(candidate, dict) else None
        except (OSError, json.JSONDecodeError):
            heavy = {"status": "invalid"}
    payload["heavy"] = None if not heavy else {
        key: heavy.get(key) for key in ("run_id", "label", "status", "pid")
    }
    hold = active_supervisor_hold(root)
    payload["hold"] = None if not hold else {
        key: hold.get(key) for key in ("hold_id", "status", "severity", "created_at")
    }
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
    if compute_metadata.get("quota_required"):
        raise FlowError("large compute quota requires heavy-start for durable child accounting")
    with heavy_lock(root):
        process = subprocess.Popen(command, cwd=root)
        return process.wait()


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
    if payload["status"] not in {"starting", "running", "completed", "failed", "timed_out", "stale"}:
        raise FlowError("invalid heavy run status")
    result = dict(payload)
    if payload["status"] in {"completed", "failed", "timed_out", "stale"}:
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


def _terminate_heavy_process_tree(process: subprocess.Popen[str]) -> None:
    """Terminate only the verified Heavy child and its descendants."""
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
        )
    else:  # pragma: no cover - the workflow is Windows-only
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except (OSError, ProcessLookupError):
            process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


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
                hard_wall_minutes = state.get("hard_wall_minutes")
                hard_wall_seconds = (
                    float(hard_wall_minutes) * 60
                    if isinstance(hard_wall_minutes, (int, float)) and hard_wall_minutes > 0
                    else None
                )
                while True:
                    try:
                        code = process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        code = None
                    now = time.time()
                    state["heartbeat_at"] = now
                    _atomic_json(state_path, state)
                    if (
                        code is None
                        and hard_wall_seconds is not None
                        and now - float(state["started_at"]) >= hard_wall_seconds
                    ):
                        _terminate_heavy_process_tree(process)
                        state.update({
                            "status": "timed_out",
                            "exit_code": None,
                            "timeout_reason": "hard_wall_minutes_exceeded",
                            "finished_at": time.time(),
                            "heartbeat_at": time.time(),
                        })
                        _atomic_json(state_path, state)
                        return 1
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
    command = list(args.argv)
    if command and command[0] == "--":
        command.pop(0)
    plan_path = getattr(args, "compute_plan", None)
    plan = None
    if plan_path:
        plan = _load_compute_plan(root, plan_path)
        if not command:
            command = list(plan["command_argv"])
    if not command:
        raise FlowError("heavy-start requires --compute-plan or a command after --")
    label = args.label or (plan["plan_id"] if plan is not None else None)
    if not isinstance(label, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", label):
        raise FlowError("invalid heavy label")
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
            if current.get("quota_required"):
                current["quota_counted"] = True
                _atomic_json(run_dir / "state.json", current)
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
    changed = state.get("active") is True and _apply_current_supervisor_resolution(root, state)
    changed = _clear_retired_compute_fields(state) or changed
    if changed:
        save_state(root, state)
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
    if _optional_file_digest(response_path) != expected_response_sha:
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


def escalation_root(root: Path) -> Path:
    return runtime_dir(root) / "escalations"


def _optional_file_digest(path: Path) -> str | None:
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
    state = load_state(root, required=False)
    if state:
        state.update({
            "worker_thread_id": thread_id,
            "worker_host_id": args.host_id,
            "worker_registered_at": value["worker_registered_at"],
        })
        save_state(root, state)
    print(json.dumps(value, indent=2, sort_keys=True))


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
            "request_receipt_sha256": _optional_file_digest(receipt_path) if request_directory else None,
            "request_events_sha256": _optional_file_digest(events_path) if request_directory else None,
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


def _request_directory_from_pending_escalation(root: Path, state: dict[str, Any]) -> str | None:
    """Recover a request binding cleared by an earlier false-positive import."""
    escalation_id = state.get("escalation_id")
    request_id = state.get("active_request_id")
    if not isinstance(escalation_id, str) or not isinstance(request_id, str):
        return None
    directory = escalation_root(root) / escalation_id
    resolution_path = directory / "resolution.json"
    if resolution_path.exists():
        try:
            resolution = json.loads(resolution_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if resolution.get("action") not in {"RESUME_WORKER", "RECOVERED"}:
            return None
    try:
        dossier = json.loads((directory / "dossier.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    candidate = dossier.get("request_directory")
    if not isinstance(candidate, str) or Path(candidate).name != request_id:
        return None
    if not Path(candidate).is_dir():
        return None
    return candidate


def command_recover(root: Path, args: argparse.Namespace) -> None:
    state = active_state(root)
    require_worker_write_authority(state, root)
    if state.get("mode") != "courier":
        raise FlowError("recover is only available in courier mode")
    directory = state.get("active_request_directory")
    if not isinstance(directory, str) or not directory:
        directory = _request_directory_from_pending_escalation(root, state)
        if directory is None:
            raise FlowError("there is no active Courier request to recover")
        state["active_request_directory"] = directory
        recovery_event(state, "request_binding_restored", request_directory=directory)
    worker_thread_id = getattr(args, "worker_thread_id", None) or os.environ.get("CODEX_THREAD_ID")
    state["worker_thread_id"] = worker_thread_id
    state["recovery_state"] = "RECOVERING"
    recovery_event(state, "recovery_started", request_directory=directory)
    save_state(root, state)
    try:
        status = courier(root, "courier_status", directory, allow_failure=True)
        recovery_event(state, "status_read", courier_state=status.get("state"))
        if (status.get("state") == "response_received"
                and isinstance(status.get("response_path"), str)):
            update_response_state(
                root, state,
                {"event": "response_received", "response_path": status["response_path"]},
                source="read_only_recover",
            )
            return
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
    state = active_state(root)
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
    if args.action == "USER_SUPERSEDED_REQUEST":
        retired_directory = state.get("active_request_directory")
        state["retired_request_directory"] = retired_directory
        if isinstance(retired_directory, str) and retired_directory:
            state["retired_request_id"] = state.get("active_request_id") or Path(retired_directory).name
        state["retired_request_key"] = state.get("last_request_key")
        state["superseded_request_migration"] = {
            "status": "PENDING",
            "retired_request_directory": retired_directory,
            "retired_request_id": state.get("retired_request_id"),
            "retired_request_key": state.get("retired_request_key"),
        }
        state["active_request_directory"] = None
        state["last_response_path"] = None
        state["work_order_active"] = False
    probe = dossier.get("last_probe") if isinstance(dossier.get("last_probe"), dict) else {}
    active_request = state.get("active_request_directory")
    dossier_request = dossier.get("request_directory")
    dossier_request_id = Path(dossier_request).name if isinstance(dossier_request, str) else None
    same_active_request = (
        isinstance(active_request, str)
        and active_request == dossier_request
    )
    cleared_same_request = (
        active_request is None
        and state.get("escalation_id") == args.escalation_id
        and (
            state.get("active_request_id") == probe.get("request_id")
            or (dossier_request_id is not None
                and state.get("active_request_id") == dossier_request_id)
        )
    )
    proven_reply = (
        args.action in {"RESUME_WORKER", "RECOVERED"}
        and (same_active_request or cleared_same_request)
        and probe.get("request_match") is True
        and probe.get("post_submission_reply_found") is True
        and isinstance(probe.get("response_path"), str)
    )
    if proven_reply:
        response_path = Path(probe["response_path"])
        try:
            response_text = response_path.read_text(encoding="utf-8-sig")
        except OSError:
            proven_reply = False
        else:
            response_sha256 = hashlib.sha256(response_text.encode("utf-8")).hexdigest()
    if proven_reply:
        state["active_request_directory"] = None
        state["last_response_path"] = str(response_path)
        state["last_response_sha256"] = response_sha256
        state["recovery_state"] = "IDLE"
        recovery_event(state, "resolved_reply_request_cleared",
                       request_directory=dossier["request_directory"],
                       response_path=str(response_path),
                       response_sha256=response_sha256)
    else:
        # A resolved scientific/business escalation may have no Courier
        # request directory at all.  Once the Supervisor has signed RESUME,
        # there is no request left to recover, so return the worker to IDLE;
        # keep RECOVERED for unresolved/unproven request-bound recovery.
        if (
            args.action in {"RESUME_WORKER", "RECOVERED"}
            and active_request is None
            and dossier_request is None
        ):
            state["recovery_state"] = "IDLE"
        else:
            state["recovery_state"] = "HUMAN_REQUIRED" if args.action == "HUMAN_REQUIRED" else "RECOVERED"
    _apply_current_supervisor_resolution(root, state)
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
    recovery_command = (
        "courier_retry_once"
        if probe.get("safe_next_action") == "courier_retry_once"
        and probe.get("submission_count") == 0
        else "courier_resend_once"
    )
    result = courier(root, recovery_command, request_directory,
                     stream=True, allow_failure=True)
    # The ordinary evidence retry may already have been consumed by a
    # pre-submit browser failure.  A registered Supervisor reviewing fresh
    # zero-submission evidence is exactly the bounded recovery handled by
    # courier_resend_once; do not strand the request merely because the probe
    # still recommends the ordinary retry command.
    if (recovery_command == "courier_retry_once"
            and result.get("event") == "courier_retry_refused"
            and probe.get("submission_count") == 0):
        recovery_command = "courier_resend_once"
        result = courier(root, recovery_command, request_directory,
                         stream=True, allow_failure=True)
    recovery_event(state, "supervisor_resend_reviewed", escalation_id=args.escalation_id,
                   recovery_command=recovery_command, result_event=result.get("event"))
    save_state(root, state)
    if result.get("event") in {"response_received", "response_duplicate"} and result.get("response_path"):
        update_response_state(root, state, result, source="supervisor_resend")
        return
    raise FlowError(
        f"Supervisor {recovery_command} did not recover the request: {result.get('event')}"
    )


def command_closeout(root: Path, args: argparse.Namespace) -> None:
    state = active_state(root)
    require_worker_write_authority(state, root)
    require_no_supervisor_hold(root)
    if state.get("mode") != "courier":
        raise FlowError("closeout is only available in courier mode")
    dispatch_message(root, state, Path(args.report_file).resolve(), "closeout",
                     [Path(value).resolve() for value in getattr(args, "attachment", [])])


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
    heavy_start.add_argument("--label")
    heavy_start.add_argument("--resource-envelope")
    heavy_start.add_argument("--compute-plan")
    heavy_start.add_argument("argv", nargs=argparse.REMAINDER)
    heavy_start.set_defaults(handler=command_heavy_start)
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
    closeout.add_argument("--attachment", action="append", default=[],
                          help="explicit evidence file to upload with the closeout")
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
