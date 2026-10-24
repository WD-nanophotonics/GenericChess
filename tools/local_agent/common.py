from __future__ import annotations

import json
import os
import time
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / ".local_agent"


class LocalFlowError(RuntimeError):
    pass


def run(*args: str, cwd: Path = ROOT, check: bool = True) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, encoding="utf-8",
                            errors="replace", capture_output=True)
    if check and result.returncode:
        raise LocalFlowError(f"{' '.join(args)} failed ({result.returncode}): "
                             f"{result.stderr.strip() or result.stdout.strip()}")
    return result.stdout.strip()


def git(*args: str, cwd: Path = ROOT) -> str:
    return run("git", *args, cwd=cwd)


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise LocalFlowError(f"invalid state: {path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                    sort_keys=True) + "\n", encoding="utf-8")
    # A transient Windows reader can deny replacement after the temp closes.
    # Retry only this same complete file; permanent failures preserve old state.
    for attempt in range(3):
        try:
            os.replace(temporary, path)
            break
        except PermissionError as exc:
            if getattr(exc, "winerror", None) not in (5, 32, 33) or attempt == 2:
                raise
            time.sleep(0.01 * (attempt + 1))
