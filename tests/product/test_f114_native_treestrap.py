from dataclasses import replace
from generic_chess.ai.limits import SearchLimits
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset

# Native execution here exercises the explicit legacy draw-policy variant.
# Standard Shogi loss-policy support is checked in test_native_terminal_policy_support.
from generic_chess.session.session import GameSession


def _context():
    rules = replace(build_standard_shogi_ruleset(), stalemate_result="draw")
    compiled = compile_semantic_ruleset(rules)
    # Trace behavior is independent of an old trained experiment checkpoint.
    weights = {pt.type_id: 1.0 for pt in rules.piece_types if not pt.is_anchor}
    checkpoint = LearnableMaterialCheckpoint(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        board_weights=weights, hand_weights=weights, reference_median=1.0,
        value_scale=4.0, material_scale=256.0, w_max=10.0,
    )
    native_rules = compile_native_semantic_rules(compiled)
    return compiled, native_rules, checkpoint


def _search(compiled, native_rules, checkpoint, trace_enabled):
    engine = SemanticSearchEngine(compiled, native_rules, checkpoint=checkpoint, tt_megabytes=8)
    return engine.search(
        GameSession(compiled),
        SearchLimits(max_depth=4, max_nodes=128, quiescence_max_depth=0),
        root_window_pruning=True,
        trace_enabled=trace_enabled,
    )


def test_f114_trace_disabled_preserves_search_result():
    compiled, native_rules, checkpoint = _context()
    disabled = _search(compiled, native_rules, checkpoint, False)
    enabled = _search(compiled, native_rules, checkpoint, True)
    assert (disabled.action, disabled.score, disabled.principal_variation,
            disabled.nodes, disabled.completed_depth) == (
        enabled.action, enabled.score, enabled.principal_variation,
        enabled.nodes, enabled.completed_depth,
    )
    assert disabled.training_trace == ()
    assert disabled.training_trace_count == 0
    assert disabled.training_trace_raw_count == 0


def test_f114_trace_is_bounded_and_structured():
    compiled, native_rules, checkpoint = _context()
    result = _search(compiled, native_rules, checkpoint, True)
    assert result.training_trace_enabled is True
    assert result.training_trace_count == len(result.training_trace)
    assert 0 <= result.training_trace_count <= 4096
    assert result.training_trace_raw_count >= result.training_trace_count
    assert result.training_trace
    row = result.training_trace[0]
    assert {
        "position_identity", "side_to_move", "search_ply", "remaining_depth",
        "score_native", "bound_class", "terminal", "board_counts",
        "hand_counts", "dynamic_features", "aux_features", "board_features",
        "alpha_original", "beta_original", "ruleset_fingerprint",
    } <= set(row)
    assert row["ruleset_fingerprint"] == compiled.ruleset_fingerprint
    assert row["bound_class"] in {"EXACT", "LOWER", "UPPER"}
