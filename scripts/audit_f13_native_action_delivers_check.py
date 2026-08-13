"""Audit-only F13 harness.

H13A records the pre-closure gap.  Later phases may reuse the inspection
helpers, but this module never enables a production migration or adds a
public semantic attack/check API.
"""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from generic_chess.learning.round5_corrective_r1 import SearchSemanticCompiled
from generic_chess.learning.shogi_semantic_rules import build_semantic_shogi_ruleset
from generic_chess.native import native_capabilities, native_version
from generic_chess.native.compiler import (
    NativeUnsupportedRuleError,
    build_semantic_compile_payload,
)
from generic_chess.rules.compiler import compile_semantic_ruleset


FINGERPRINT = "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"


def certified_semantic_shogi():
    semantic = compile_semantic_ruleset(build_semantic_shogi_ruleset())
    assert semantic.ruleset_fingerprint == FINGERPRINT
    return SearchSemanticCompiled(
        ir=semantic.ir,
        _legacy_compiled=semantic._legacy_compiled,
        support=semantic.support,
    )


def baseline_gap_report() -> dict:
    semantic = certified_semantic_shogi()
    report = {
        "ruleset_fingerprint": semantic.ruleset_fingerprint,
        "native_version": native_version(),
        "native_capabilities": native_capabilities(),
        "postconditions": [
            {
                "pattern_id": pattern.pattern_id,
                "kinds": [post.kind for post in pattern.postconditions],
                "max_strata": [post.max_stratum for post in pattern.postconditions],
            }
            for pattern in semantic.ir.patterns
            if pattern.postconditions
        ],
        "expected_status": "FAIL_CLOSED_UNSUPPORTED",
    }
    try:
        build_semantic_compile_payload(semantic)
    except NativeUnsupportedRuleError as exc:
        report["observed"] = {
            "status": "FAIL_CLOSED_UNSUPPORTED",
            "exception": type(exc).__name__,
            "message": str(exc),
        }
    else:
        report["observed"] = {"status": "UNEXPECTEDLY_EXECUTABLE"}
    return report


def main() -> int:
    print(json.dumps({
        "python": sys.version,
        "platform": platform.platform(),
        "baseline_gap": baseline_gap_report(),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
