"""Phase 2B: the committed fixed-depth search corpus must match native
output exactly (score, canonical action, terminal)."""

import json
from pathlib import Path

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.native_compat import NativeCompatibleEvaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.native.compiler import compile_native_evaluation, compile_native_rules
from generic_chess.native.reference import canonical_pack
from generic_chess.native.search import native_fixed_depth_search

from native_test_helpers import requires_native


def _corpus():
    return json.loads(
        (
            Path(__file__).resolve().parent.parent
            / "tests"
            / "fixtures"
            / "native_search_corpus_v1.json"
        ).read_text(encoding="utf-8")
    )


@requires_native
def test_search_corpus_matches_native():
    from generic_chess.ai.benchmark.audit_suite import (
        build_session,
        standard_ruleset_specs,
    )

    raw = _corpus()
    assert raw["native_schema"] == "native-0.2.0"
    specs = {s.fixture_id: s for s in standard_ruleset_specs()}
    for fixture in raw["fixtures"]:
        compiled, session = build_session(
            specs[fixture["ruleset_fixture_id"]],
            tuple(fixture["action_prefix"]),
        )
        config = EvaluationConfig()
        profile = build_ruleset_profile(compiled, config)
        evaluator = NativeCompatibleEvaluator(compiled, profile, config)
        rules = compile_native_rules(compiled)
        eval_tables = compile_native_evaluation(rules, profile, config)
        for depth_str, expected in fixture["depth_results"].items():
            depth = int(depth_str)
            result = native_fixed_depth_search(
                compiled, rules, eval_tables, session, depth
            )
            assert result.score == expected["score"], fixture["fixture_id"]
            packed = (
                canonical_pack(compiled, session.state, result.action)
                if result.action is not None
                else None
            )
            assert packed == expected["canonical_packed"], fixture["fixture_id"]
            assert (
                session.state.terminal_status.status.value
                == expected["terminal"]
            )
