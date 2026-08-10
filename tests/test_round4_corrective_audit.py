from dataclasses import replace

from generic_chess.ai.alphabeta.search import _tt_key
from generic_chess.core.position import HistoryRecord
from generic_chess.core.terminal import TerminalStatus, _perpetual_check_result
from generic_chess.learning.shogi_rules import sfen_to_gc_state
from generic_chess.learning.shogi_semantic_rules import (
    build_semantic_shogi_ruleset,
)
from generic_chess.learning.shogi_certification import compute_verdict
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import (
    RuleSet,
    compute_fingerprint,
    ruleset_from_dict,
    ruleset_to_dict,
)
from conftest import king_type, make_ruleset


def test_perpetual_check_accepts_alternating_legal_actor_history():
    # Build three complete cycles with checking moves by player 0 and replies
    # by player 1.  The old implementation incorrectly rejected this shape.
    history = (HistoryRecord("root", -1, "initial", False),) + tuple(
        HistoryRecord(key, actor, f"m{index}", actor == 0)
        for index, (key, actor) in enumerate(
            [("a", 0), ("b", 1), ("root", 0), ("a", 1), ("b", 0), ("root", 1)] * 2
        )
    )
    result = _perpetual_check_result(
        (("root", 4), ("a", 4), ("b", 4)), history, 4
    )
    assert result is not None
    assert result.status is TerminalStatus.PERPETUAL_CHECK
    assert result.winner == 1


def test_ruleset_repetition_policy_is_explicit_and_default_is_legacy_draw():
    default = RuleSet()
    assert default.repetition_policy == "draw"
    assert "repetition_policy" not in ruleset_to_dict(default)
    semantic = build_semantic_shogi_ruleset()
    assert semantic.repetition_policy == "continuous_check_loss"
    assert "repetition_policy" in ruleset_to_dict(semantic)
    assert compute_fingerprint(semantic) == compute_fingerprint(
        ruleset_from_dict(ruleset_to_dict(semantic))
    )


def test_generic_non_shogi_fixture_can_opt_into_history_policy():
    ruleset = make_ruleset(
        4,
        [king_type()],
        lines=["...k", "....", "....", "K..."],
    )
    ruleset = replace(ruleset, repetition_policy="continuous_check_loss")
    from generic_chess.rules.compiler import compile_ruleset

    compiled = compile_ruleset(ruleset)
    assert compiled.repetition_policy == "continuous_check_loss"
    assert "repetition_policy" in ruleset_to_dict(ruleset)
    assert compiled.ruleset_fingerprint == compute_fingerprint(ruleset)


def test_history_context_changes_tt_identity_for_same_position_and_counts():
    compiled = compile_semantic_ruleset(build_semantic_shogi_ruleset())
    state = sfen_to_gc_state(
        compiled, "9/9/9/9/9/9/2K6/3R5/1k7 b - 1"
    )
    a = replace(
        state,
        history=(HistoryRecord("same", -1, "initial", False), HistoryRecord("same", 0, "a", True)),
        repetition_counts=(("same", 2),),
    )
    b = replace(
        state,
        history=(HistoryRecord("same", -1, "initial", False), HistoryRecord("same", 0, "b", False)),
        repetition_counts=(("same", 2),),
    )
    assert _tt_key(a, compiled) != _tt_key(b, compiled)


def test_benchmark_verdict_has_independent_mandatory_gates():
    kwargs = dict(
        move_legality=True,
        transition_parity=True,
        history_terminal=True,
        symmetric_exclusions=True,
        no_unresolved_divergence=True,
        native_fail_closed=True,
    )
    for gate in (
        "move_legality",
        "transition_parity",
        "history_terminal",
        "symmetric_exclusions",
        "no_unresolved_divergence",
    ):
        forced = dict(kwargs)
        forced[gate] = False
        verdict = compute_verdict(**forced)
        assert verdict["SHOGI_ALPHASHO_BENCHMARK_READY"] == "FAIL"
        assert verdict["SHOGI_FULL_RULE_CERTIFICATION"] == "FAIL"
