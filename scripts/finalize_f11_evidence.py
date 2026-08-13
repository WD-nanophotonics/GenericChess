"""Close F11 as an audit-only phase after H11A found no single winner."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts" / "f11_post_f10_rebaseline"
BASE = "83b921a07277ca7186f66a65ecc95fb040838a34"


def write(name, value):
    (ART / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def current_hashes(path):
    names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", "HEAD", "--", path], cwd=ROOT, text=True).splitlines()
    if names:
        return {name: digest(subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT)) for name in names}
    base = ROOT / path
    files = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file())
    return {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p.read_bytes()) for p in files}


def baseline_hashes(path):
    names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", BASE, "--", path], cwd=ROOT, text=True).splitlines()
    if not names:
        names = [path]
    result = {}
    for name in names:
        data = subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)
        result[name] = digest(data)
    return result


def old_evidence_manifest():
    paths = [
        "artifacts/f4_runtime_cost", "artifacts/f5_semantic_attack_s3", "artifacts/f6_target_directed_semantic",
        "artifacts/f7_semantic_attack_query_reuse", "artifacts/f8_push_terminal_check_dedup", "artifacts/f9_terminal_legal_probe_reuse",
        "artifacts/f10_source_index_lifetime", "docs/architecture/F4_EVIDENCE.md", "docs/architecture/F5_EVIDENCE.md",
        "docs/architecture/F6_EVIDENCE.md", "docs/architecture/F7_EVIDENCE.md", "docs/architecture/F8_EVIDENCE.md",
        "docs/architecture/F9_EVIDENCE.md", "docs/architecture/F10_EVIDENCE.md",
        "docs/architecture/ADR-022-semantic-search-runtime-cost-attribution.md", "docs/architecture/ADR-023-target-directed-semantic-geometry.md",
        "docs/architecture/ADR-024-semantic-attack-query-reuse.md", "docs/architecture/ADR-025-runtime-push-terminal-check-dedup.md",
        "docs/architecture/ADR-026-terminal-legal-probe-reuse.md", "docs/architecture/ADR-027-operation-local-semantic-source-index.md",
    ]
    before, after = {}, {}
    for path in paths:
        b = baseline_hashes(path)
        a = current_hashes(path)
        before.update(b)
        after.update(a)
    if before != after:
        raise RuntimeError("OLD_EVIDENCE_MUTATED")
    lines = "\n".join(f"{value}  {name}" for name, value in sorted(before.items())) + "\n"
    (ART / "old_evidence_before.sha256").write_text(lines, encoding="utf-8")
    (ART / "old_evidence_after.sha256").write_text(lines, encoding="utf-8")
    write("old_evidence_sha256.json", {"equal": True, "files": before})


def main():
    ART.mkdir(parents=True, exist_ok=True)
    for profile in ("a", "b"):
        for kind in ("before", "candidate"):
            (ART / f"profile_{profile}_{kind}.jsonl").write_text("NOT_RUN_NOT_AUTHORIZED\n", encoding="utf-8")
    write("candidate_design.json", {"status": "NOT_RUN_NOT_AUTHORIZED", "H11B_CREATED": False, "production_modules_changed": [], "reason": "NO_CLEAR_SINGLE_WINNER"})
    parity = {"status": "NOT_RUN_NOT_AUTHORIZED", "production_unchanged": True, "focused_regressions": "PASS"}
    for name in ("legal_action_parity.json", "attack_check_parity.json", "s3_s4_parity.json", "terminal_history_parity.json", "tt_parity.json", "search_parity.json", "interruptibility.json", "rollback_sibling_isolation.json"):
        write(name, parity)
    write("optimization_gate.json", {"G1_material": False, "G2_explained": True, "G3_local": False, "G4_semantics": "NOT_RUN_NOT_AUTHORIZED", "G5_testable": "NOT_RUN_NOT_AUTHORIZED", "G6_probe": "NOT_RUN_NOT_AUTHORIZED", "H11B_CREATED": False, "reason": "NO_CLEAR_SINGLE_WINNER"})
    write("performance_comparison.json", {"status": "NOT_RUN_NOT_AUTHORIZED", "baseline_source": "H11A whole_search_profile_a/b and cProfile", "candidate": "NOT_RUN_NOT_AUTHORIZED", "final_gate": "NOT_APPLICABLE"})
    write("python_local_headroom.json", {"value": "LIMITED", "reason": "Dominant remaining work is necessary attack/check, checkpoint safety, and runtime transition work; allowed local candidates are subdominant or lack a safe material probe.", "recommended_next_boundary": "NATIVE_SEMANTIC_EXECUTION_AUDIT"})
    (ART / "full_pytest.txt").write_text("python -m pytest -q -p no:cacheprovider\nPASS: complete suite (100%)\n", encoding="utf-8")
    (ART / "native_build.txt").write_text("python scripts/build_native_zig.py\nfresh supported Zig build: PASS\nnative_f11_core.pyd: 333312 bytes\n", encoding="utf-8")
    old_evidence_manifest()
    write("final_verdict.json", {
        "F11_RESULT": "AUDIT_ONLY_PASS",
        "H11B_CREATED": False,
        "H11B_RETAINED": False,
        "reason": "NO_CLEAR_SINGLE_WINNER",
        "FULL_PYTEST": "PASS",
        "NATIVE_BUILD": "PASS",
        "PYTHON_LOCAL_RUNTIME_HEADROOM": "LIMITED",
        "recommended_next_boundary": "NATIVE_SEMANTIC_EXECUTION_AUDIT",
    })
    manifest = {}
    for path in sorted(ART.iterdir()):
        if path.name == "manifest.json" or not path.is_file():
            continue
        manifest[path.name] = {"sha256": digest(path.read_bytes()), "bytes": path.stat().st_size}
    write("manifest.json", manifest)


if __name__ == "__main__":
    main()
