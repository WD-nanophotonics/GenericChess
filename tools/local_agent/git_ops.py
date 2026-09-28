from __future__ import annotations

import os
import re
from pathlib import Path
import uuid

from .common import ROOT, STATE, LocalFlowError, git, run


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
    interpreter = str(executable) if executable.is_file() else "python"
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


def publish(targets: list[str]) -> dict:
    _check_branch(ROOT, "sandbox")
    git("fetch", "origin", "sandbox")
    if git("rev-parse", "origin/sandbox") != git("rev-parse", "HEAD"):
        ancestor = run("git", "merge-base", "origin/sandbox", "HEAD")
        if ancestor != git("rev-parse", "origin/sandbox"):
            raise LocalFlowError("sandbox diverged from origin/sandbox")
    _tests(targets)
    _check_branch(ROOT, "sandbox")
    candidate = git("rev-parse", "HEAD")
    _push(ROOT, "sandbox", "publish")
    git("fetch", "origin", "sandbox")
    published = git("rev-parse", "origin/sandbox")
    if published != candidate:
        raise LocalFlowError("remote sandbox SHA differs after push")
    return {"published_sha": published, "branch": "sandbox"}


def promote(candidate: str, targets: list[str]) -> dict:
    if not FULL_SHA.fullmatch(candidate):
        raise LocalFlowError("candidate must be a full SHA")
    master = ROOT.parent / "GenericChess"
    if not master.is_dir():
        raise LocalFlowError("master checkout is missing")
    _check_branch(ROOT, "sandbox")
    _check_branch(master, "master")
    git("fetch", "origin", "sandbox", "master")
    if candidate != git("rev-parse", "HEAD") or candidate != git("rev-parse", "origin/sandbox"):
        raise LocalFlowError("candidate must equal local and published sandbox HEAD")
    git("fetch", "origin", "master", cwd=master)
    if git("rev-parse", "HEAD", cwd=master) != git("rev-parse", "origin/master", cwd=master):
        raise LocalFlowError("master checkout is not synchronized")
    if git("merge-base", "master", candidate) != git("rev-parse", "master", cwd=master):
        raise LocalFlowError("candidate is not a fast-forward of master")
    _tests(targets)
    _check_branch(ROOT, "sandbox")
    _check_branch(master, "master")
    git("merge", "--ff-only", candidate, cwd=master)
    _push(master, "master", "promote")
    git("fetch", "origin", "master", cwd=master)
    if git("rev-parse", "origin/master", cwd=master) != candidate:
        raise LocalFlowError("remote master SHA differs after push")
    return {"promoted_sha": candidate, "branch": "master"}
