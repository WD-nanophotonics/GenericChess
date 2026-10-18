from __future__ import annotations

import os
import re
from pathlib import Path
import uuid

from .common import ROOT, STATE, LocalFlowError, git, run, read_json


FULL_SHA = re.compile(r"[0-9a-f]{40}\Z")


def _check_branch(path: Path, name: str) -> None:
    if git("branch", "--show-current", cwd=path) != name:
        raise LocalFlowError(f"expected {name} branch in {path}")
    if git("status", "--porcelain", cwd=path):
        raise LocalFlowError(f"worktree is not clean: {path}")


def _tests(targets: list[str]) -> None:
    if not targets:
        raise LocalFlowError("at least one relevant pytest target is required")
    executable = ROOT / ".venv" / "Scripts" / "python.exe"
    role = read_json(ROOT / ".local_agent/role.json")
    configured = Path(role.get("python_executable", ""))
    interpreter = str(executable) if executable.is_file() else str(configured) if configured.is_file() else "python"
    base = STATE / "pytest-runs" / uuid.uuid4().hex
    base.parent.mkdir(parents=True, exist_ok=True)
    result = run(interpreter, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                 "--basetemp", str(base), *targets)
    if result:
        print(result)


def _push(path: Path, branch: str, mode: str) -> None:
    previous = os.environ.get("GENERIC_CHESS_LOCAL_PUSH")
    os.environ["GENERIC_CHESS_LOCAL_PUSH"] = mode
    try:
        git("push", "origin", branch, cwd=path)
    finally:
        if previous is None:
            os.environ.pop("GENERIC_CHESS_LOCAL_PUSH", None)
        else:
            os.environ["GENERIC_CHESS_LOCAL_PUSH"] = previous


def publish(targets: list[str], branch: str = "sandbox") -> dict:
    roles = {"PRIMARY_SANDBOX": "sandbox", "DEEPSEEK_AUX": "codex/deepseek-aux"}
    role = read_json(ROOT / ".local_agent/role.json")
    agent = role.get("agent_id", "PRIMARY_SANDBOX")
    if branch not in roles.values() or roles.get(agent) != branch:
        raise LocalFlowError("publication branch does not match this checkout role")
    if role.get("branch", branch) != branch:
        raise LocalFlowError("configured publication branch differs")
    _check_branch(ROOT, branch)
    # The sandbox route is unchanged; only the explicitly bound auxiliary may
    # create its fixed new remote branch on its first publication.
    exists = branch == "sandbox" or bool(git("ls-remote", "--heads", "origin", "refs/heads/" + branch))
    if exists:
        git("fetch", "origin", branch)
        if git("rev-parse", "origin/" + branch) != git("rev-parse", "HEAD"):
            ancestor = run("git", "merge-base", "origin/" + branch, "HEAD")
            if ancestor != git("rev-parse", "origin/" + branch):
                raise LocalFlowError(branch + " diverged from origin/" + branch)
    _tests(targets)
    _check_branch(ROOT, branch)
    candidate = git("rev-parse", "HEAD")
    _push(ROOT, branch, "publish")
    git("fetch", "origin", branch)
    published = git("rev-parse", "origin/" + branch)
    if published != candidate:
        raise LocalFlowError("remote " + branch + " SHA differs after push")
    return {"published_sha": published, "branch": branch}


def promote(candidate: str, targets: list[str]) -> dict:
    if not FULL_SHA.fullmatch(candidate):
        raise LocalFlowError("candidate must be a full SHA")
    _check_branch(ROOT, "sandbox")
    git("fetch", "origin", "sandbox", "master")
    if candidate != git("rev-parse", "HEAD") or candidate != git("rev-parse", "origin/sandbox"):
        raise LocalFlowError("candidate must equal local and published sandbox HEAD")
    if git("merge-base", "origin/master", candidate) != git("rev-parse", "origin/master"):
        raise LocalFlowError("candidate is not a fast-forward of master")
    _tests(targets)
    _check_branch(ROOT, "sandbox")
    _push(ROOT, f"{candidate}:refs/heads/master", "promote")
    git("fetch", "origin", "master")
    if git("rev-parse", "origin/master") != candidate:
        raise LocalFlowError("remote master SHA differs after push")
    git("branch", "-f", "master", candidate)
    return {"promoted_sha": candidate, "branch": "master"}
