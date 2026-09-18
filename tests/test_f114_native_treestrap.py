import json
from pathlib import Path

from generic_chess.ai.limits import SearchLimits
from generic_chess.learning.material import LearnableMaterialCheckpoint
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.session.session import GameSession


ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT = ROOT / ".generic_chess_flow" / "f109-inputs" / "standard_shogi.json"


def _context():
    payload = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    checkpoint = LearnableMaterialCheckpoint.from_dict(payload.get("checkpoint", payload))
    compiled = compile_semantic_ruleset(build_standard_shogi_ruleset())
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
