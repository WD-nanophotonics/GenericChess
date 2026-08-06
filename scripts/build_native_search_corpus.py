"""Regenerate the small fixed-depth search corpus.

Stores only reference metadata (scores, canonical packed actions, terminal),
never the search trees themselves.  Usage::

    python scripts/build_native_search_corpus.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.native_compat import NativeCompatibleEvaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.native.reference import (
    canonical_pack,
    reference_fixed_depth_minimax,
)


def _corpus_fixtures():
    raw = json.loads(
        (
            ROOT
            / "tests"
            / "fixtures"
            / "native_correctness_corpus_v1.json"
        ).read_text(encoding="utf-8")
    )
    return raw["fixtures"][:6]


def main() -> int:
    from generic_chess.ai.benchmark.audit_suite import (
        build_session,
        standard_ruleset_specs,
    )

    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    fixtures = []
    for corpus_fixture in _corpus_fixtures():
        compiled, session = build_session(
            specs[corpus_fixture["ruleset_fixture_id"]],
            tuple(corpus_fixture["action_prefix"]),
        )
        config = EvaluationConfig()
        profile = build_ruleset_profile(compiled, config)
        evaluator = NativeCompatibleEvaluator(compiled, profile, config)
        results = {}
        for depth in (1, 2):
            score, actions, canonical, pv, _nodes = (
                reference_fixed_depth_minimax(
                    session.state, compiled, evaluator, depth
                )
            )
            results[str(depth)] = {
                "score": score,
                "canonical_packed": (
                    canonical_pack(compiled, session.state, canonical)
                    if canonical is not None
                    else None
                ),
                "best_packed": sorted(
                    canonical_pack(compiled, session.state, a)
                    for a in actions
                ),
                "pv_packed": [
                    canonical_pack(compiled, session.state, a) for a in pv
                ],
                "terminal": session.state.terminal_status.status.value,
            }
        fixtures.append(
            {
                "fixture_id": corpus_fixture["fixture_id"],
                "ruleset_fixture_id": corpus_fixture["ruleset_fixture_id"],
                "action_prefix": corpus_fixture["action_prefix"],
                "depth_results": results,
            }
        )
    out = {
        "schema_version": 2,
        "native_schema": "native-0.2.0",
        "fixtures": fixtures,
    }
    path = ROOT / "tests" / "fixtures" / "native_search_corpus_v1.json"
    path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(fixtures)} fixtures)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
