"""H14A audit harness for the F14 public semantic attack/check API.

This phase intentionally records the absence of the public API and freezes the
Python authority.  It must not add a production entry point.
"""

from __future__ import annotations

import json
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "f14_native_semantic_attack_api"
sys.path.insert(0, str(ROOT))

from scripts.audit_f13_native_action_delivers_check import certified_semantic_shogi  # noqa: E402
from generic_chess.native import _module, native_capabilities, native_version  # noqa: E402
from generic_chess.native.compiler import compile_native_semantic_rules  # noqa: E402
import generic_chess.native.semantic as public_semantic  # noqa: E402


BASELINE = {
    "origin/sandbox": "9b745662f13849e50f37c2391da9d039235505af",
    "origin/master": "4f1d03a308f5fd04a01bbd980c7411888ea1ed9d",
    "origin/chat": "d6b0d5720efe23019a7a2b4cce72e05beee2e6c4",
}


def write_json(name: str, value) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    semantic = certified_semantic_shogi()
    compiled = compile_native_semantic_rules(semantic)
    module = _module()
    expected_public = ("is_square_attacked", "in_check")
    write_json("baseline.json", {
        "phase": "H14A",
        "baseline": BASELINE,
        "ruleset_fingerprint": semantic.ruleset_fingerprint,
        "head_expected": BASELINE["origin/sandbox"],
        "native_executable": compiled.native_executable,
        "status": "PASS",
    })
    write_json("environment.json", {
        "python": sys.version,
        "platform": platform.platform(),
        "native_version": native_version(),
        "native_capabilities": native_capabilities(),
    })
    write_json("public_api_before.json", {
        "python_module": "generic_chess.native.semantic",
        "expected_public_names": list(expected_public),
        "present_names": [name for name in expected_public if hasattr(public_semantic, name)],
        "extension_entrypoints_present": {
            name: hasattr(module, name)
            for name in ("semantic_is_square_attacked", "semantic_in_check")
        },
        "status": "PASS" if not any(hasattr(public_semantic, name) for name in expected_public) and not any(hasattr(module, name) for name in ("semantic_is_square_attacked", "semantic_in_check")) else "FAIL",
    })
    write_json("python_attack_contract.json", {
        "authority": ["SemanticEngine.is_square_attacked", "SemanticEngine.in_check"],
        "is_square_attacked": [
            "matching ruleset fingerprint", "square is board index", "by_owner in {0,1}",
            "target_enemy patterns only", "current actor type match", "non-drop geometry",
            "owner-relative compiled paths", "exact target", "path predicates", "state guards",
            "slot guards", "attacker-relative owner perspective", "no S3 recursion", "no S4 recursion",
            "S4-bearing capture patterns contribute S0/S1", "first exact binding wins", "otherwise false",
        ],
        "in_check": "resolve side anchor, then query opponent pseudo-attack; no anchor means false",
    })
    write_json("native_attack_authority.json", {
        "semantic_attacked_by": "generic_chess/_native/native_semantic_runtime.c",
        "internal_in_check": "generic_chess/_native/native_semantic_runtime.c",
        "current_runtime_entrypoint": "gc_semantic_runtime_in_check",
        "legacy_native_attack_is_authority": False,
        "public_api_before": False,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
