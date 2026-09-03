"""Run one R7 pytest regression and emit parseable evidence artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _test_id(case: ET.Element, worktree: Path) -> str:
    file_name = case.get("file")
    if file_name:
        path = Path(file_name)
        if path.is_absolute():
            try:
                file_name = path.relative_to(worktree).as_posix()
            except ValueError:
                normalized = path.as_posix()
                marker = "/tests/"
                if marker in normalized:
                    file_name = normalized.split(marker, 1)[1]
                    file_name = f"tests/{file_name}"
                else:
                    file_name = normalized
        else:
            file_name = path.as_posix()
    else:
        file_name = (case.get("classname") or "unknown").replace(".", "/") + ".py"
    return f"{file_name}::{case.get('name', 'unknown')}"


def parse_junit(path: Path, worktree: Path) -> dict:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    totals = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
    failures = []
    for suite in suites:
        for key in totals:
            totals[key] += int(suite.get(key, 0))
        for case in suite.iter("testcase"):
            if case.find("failure") is not None or case.find("error") is not None:
                failures.append(_test_id(case, worktree))
    totals["passed"] = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
    totals["failing_test_ids"] = failures
    return totals


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True)
    parser.add_argument("--worktree", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--python", dest="python_executable", default=sys.executable)
    parser.add_argument(
        "--ignore",
        action="append",
        default=[],
        help="pytest path to exclude; repeat for multiple paths",
    )
    args = parser.parse_args(argv)
    worktree = args.worktree.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    junit = output_dir / f"{args.label}.junit.xml"
    raw = output_dir / f"{args.label}.raw.txt"
    metadata_path = output_dir / f"{args.label}.json"
    base = output_dir / f"{args.label}-basetemp"
    command = [args.python_executable, "-m", "pytest", "-q", "--tb=no", f"--junitxml={junit}", f"--basetemp={base}"]
    for ignored in args.ignore:
        command.extend(["--ignore", ignored])
    env = dict(os.environ)
    env["PYTHONPATH"] = str(worktree)
    started = time.time()
    result = subprocess.run(command, cwd=worktree, env=env, capture_output=True, text=True)
    ended = time.time()
    raw.write_text(
        json.dumps({"command": command, "cwd": str(worktree), "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    parsed = parse_junit(junit, worktree)
    evidence = {
        "label": args.label,
        "command": command,
        "cwd": str(worktree),
        "returncode": result.returncode,
        "started_epoch": started,
        "ended_epoch": ended,
        "junit_path": str(junit),
        "junit_sha256": _sha(junit),
        "raw_path": str(raw),
        "raw_sha256": _sha(raw),
        **parsed,
    }
    metadata_path.write_text(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
