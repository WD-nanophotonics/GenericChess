"""Build the immutable H50B1-R8 evidence and identity closure fixture."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.audit_h50b1_r6_final import H50A_SHA, R5_SHA, _git_blob_sha
from scripts.audit_h50b1_r7_final import R6_SHA, RESIDUAL_ALLOWLIST
from scripts.run_r7_regression import parse_junit

R7_SHA = "d7c89011dfb9db2e542389b51f067c4d2d092478"
CHECKPOINT = "H50B1-R8_F50_SEMANTIC_NATIVE_CANONICAL_EXECUTION_FINAL"
WORK_ORDER = "GENERICCHESS-F50B1-CORRECTIVE-R8-IMMUTABLE-REGRESSION-EVIDENCE-AND-WORKTREE-IDENTITY-CLOSURE"
H50A_WORKTREE = ROOT / ".generic_chess_flow" / "r7-h50a-baseline"
EVIDENCE_DIR = ROOT / "tests" / "fixtures" / "h50b1_r8_regression_evidence"
R7_FIXTURE = ROOT / "tests" / "fixtures" / "h50b1_r7_final_certification.json"
R8_EVIDENCE_FILES = {
    "h50a": ("h50a.junit.xml", "h50a.json", "h50a.raw.txt"),
    "current_r7": ("current-r7.junit.xml", "current-r7.json", "current-r7.raw.txt"),
}
POST_FREEZE_DIR = EVIDENCE_DIR


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(cwd: Path, *command: str) -> str:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def _metadata(label: str, prefix: Path) -> dict:
    metadata_path = prefix / f"{label}.json"
    value = json.loads(metadata_path.read_text(encoding="utf-8"))
    junit_path = prefix / f"{label}.junit.xml"
    raw_path = prefix / f"{label}.raw.txt"
    parsed = parse_junit(junit_path, prefix)
    for key in ("tests", "passed", "skipped", "failures", "errors", "failing_test_ids"):
        if value[key] != parsed[key]:
            raise AssertionError(f"{label} metadata disagrees with committed JUnit for {key}")
    return {
        **value,
        "evidence_artifacts": {
            "junit": {"path": str(junit_path.relative_to(ROOT)).replace("\\", "/"), "sha256": _sha(junit_path), "bytes": junit_path.stat().st_size},
            "metadata": {"path": str(metadata_path.relative_to(ROOT)).replace("\\", "/"), "sha256": _sha(metadata_path), "bytes": metadata_path.stat().st_size},
            "raw": {"path": str(raw_path.relative_to(ROOT)).replace("\\", "/"), "sha256": _sha(raw_path), "bytes": raw_path.stat().st_size},
        },
    }


def _h50a_identity() -> dict:
    compiler = H50A_WORKTREE / "generic_chess" / "native" / "compiler.py"
    status = _run(H50A_WORKTREE, "git", "status", "--porcelain")
    ignored = _run(H50A_WORKTREE, "git", "status", "--porcelain", "--ignored", "--", "generic_chess")
    declared_source = compiler.read_text(encoding="utf-8")
    match = re.search(r"^SEMANTIC_PAYLOAD_VERSION\s*=\s*(\d+)\s*$", declared_source, re.MULTILINE)
    if match is None:
        raise AssertionError("H50A compiler source has no parseable semantic payload declaration")
    declaration = int(match.group(1))
    if declaration != 2:
        raise AssertionError(f"H50A source declaration drifted: {declaration}")
    head = _run(H50A_WORKTREE, "git", "rev-parse", "HEAD")
    if head != H50A_SHA:
        raise AssertionError(f"H50A worktree identity mismatch: {head}")
    source_sha = _sha(compiler)
    blob_sha = _git_blob_sha(H50A_SHA, "generic_chess/native/compiler.py")
    if source_sha != blob_sha:
        raise AssertionError("H50A compiler source differs from its authority commit")
    generated = []
    for path in sorted(H50A_WORKTREE.glob("generic_chess/_native_core*.pyd")):
        generated.append({"path": str(path.relative_to(H50A_WORKTREE)).replace("\\", "/"), "sha256": _sha(path), "bytes": path.stat().st_size})
    return {
        "head_command": "git rev-parse HEAD",
        "head": head,
        "status_command": "git status --porcelain",
        "status_porcelain": status,
        "ignored_status_command": "git status --porcelain --ignored -- generic_chess",
        "ignored_status_generic_chess": ignored,
        "generated_native_artifacts": generated,
        "compiler_source_path": "generic_chess/native/compiler.py",
        "compiler_source_sha256": source_sha,
        "h50a_git_blob_sha256": blob_sha,
        "h50a_git_blob_object_id": _run(H50A_WORKTREE, "git", "hash-object", "generic_chess/native/compiler.py"),
        "declared_semantic_payload_version": declaration,
        "identity_status": "PASS",
    }


def _post_freeze() -> dict | None:
    metadata = POST_FREEZE_DIR / "current-r8-post-freeze.json"
    if not metadata.is_file():
        return None
    return _metadata("current-r8-post-freeze", POST_FREEZE_DIR)


def build_report() -> dict:
    r7 = json.loads(R7_FIXTURE.read_text(encoding="utf-8"))
    immutable = {label: _metadata(label.replace("_", "-"), EVIDENCE_DIR) for label in R8_EVIDENCE_FILES}
    for label, record in immutable.items():
        expected = r7["isolated_h50a" if label == "h50a" else "current_r7"]
        if record["junit_sha256"] != expected["pytest"]["junit_sha256"] or record["raw_sha256"] != expected["pytest"]["raw_sha256"]:
            raise AssertionError(f"{label} immutable copy does not match accepted R7 evidence")
    current = immutable["current_r7"]
    if set(current["failing_test_ids"]) - RESIDUAL_ALLOWLIST:
        raise AssertionError("R7 current evidence contains an unregistered failure")
    r6_to_head = _run(ROOT, "git", "diff", "--name-only", f"{R6_SHA}..HEAD", "--", "generic_chess").splitlines()
    r5_to_head = _run(ROOT, "git", "diff", "--name-only", f"{R5_SHA}..HEAD", "--", "generic_chess").splitlines()
    r7_to_head = _run(ROOT, "git", "diff", "--name-only", f"{R7_SHA}..HEAD", "--", "generic_chess").splitlines()
    post_freeze = _post_freeze()
    report = {
        "schema": "H50B1-R8-FINAL-IMMUTABLE-EVIDENCE-CERTIFICATION-V1",
        "work_order": WORK_ORDER,
        "checkpoint": CHECKPOINT,
        "parent_sha": R7_SHA,
        "parent_chain": {"R6": R6_SHA, "R5": R5_SHA, "H50A": H50A_SHA},
        "production_code_byte_frozen_at_r5": True,
        "native_payload_version": 4,
        "semantic_differential": r7["semantic_differential"],
        "declaration_controls": r7["declaration_controls"],
        "spatial_selector_controls": r7["spatial_selector_controls"],
        "generic_witness": r7["generic_witness"],
        "abi_measurements": r7["abi_measurements"],
        "scientific_protocol_contract": r7["scientific_protocol_contract"],
        "historical_repair_ledger": r7["historical_repair_ledger"],
        "h50a_identity": _h50a_identity(),
        "isolated_h50a": {"probe": r7["isolated_h50a"]["probe"], "pytest": immutable["h50a"]},
        "current_r7": {"probe": r7["current_r7"]["probe"], "pytest": immutable["current_r7"]},
        "current_r8_post_freeze": {"pytest": post_freeze} if post_freeze is not None else None,
        "immutable_evidence_status": "PASS",
        "cumulative_production_diff": {
            "R5_TO_R8_DIFF": r5_to_head,
            "R6_TO_R8_DIFF": r6_to_head,
            "R7_TO_R8_DIFF": r7_to_head,
            "status": "PASS" if not r5_to_head and not r6_to_head and not r7_to_head else "FAIL",
        },
        "F50B2_status": "NOT_STARTED",
        "promotion": "HOLD",
        "status": "PASS" if not r5_to_head and not r6_to_head and not r7_to_head and post_freeze is not None else "PENDING_POST_FREEZE",
    }
    return report


def main() -> int:
    output = ROOT / "tests" / "fixtures" / "h50b1_r8_final_certification.json"
    report = build_report()
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "identity": report["h50a_identity"]["identity_status"], "post_freeze": report["current_r8_post_freeze"] is not None}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
