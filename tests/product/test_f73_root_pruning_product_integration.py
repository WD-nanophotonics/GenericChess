"""Full-root default after the observed inexact-root-tie counterexample."""

from pathlib import Path

import pytest

from generic_chess.ai.limits import SearchLimits
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.compiler import NativeUnsupportedRuleError
from generic_chess.native.semantic import semantic_iterative_search
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(not native_available(), reason="native extension is not built")


def test_product_engine_defaults_to_full_root_windows():
    source = (ROOT / "generic_chess" / "native" / "semantic_engine.py").read_text(encoding="utf-8")
    assert "root_window_pruning: bool = False" in source
    low_level = (ROOT / "generic_chess" / "native" / "semantic.py").read_text(encoding="utf-8")
    assert "root_window_pruning: bool = False" in low_level


def test_default_product_result_matches_explicit_full_root_mode():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    native = compile_native_semantic_rules(compiled)
    zero = (0,) * len(native.type_ids)
    session = GameSession(compiled)
    limits = SearchLimits(max_depth=2, max_nodes=None, quiescence_max_depth=0)
    default = SemanticSearchEngine(
        compiled, native, board_values=zero, hand_values=zero, tt_megabytes=0
    ).search(session, limits)
    explicit = SemanticSearchEngine(
        compiled, native, board_values=zero, hand_values=zero, tt_megabytes=0
    ).search(session, limits, root_window_pruning=False)
    assert default.root_window_pruning is False
    assert (default.action, default.score, default.principal_variation) == (
        explicit.action, explicit.score, explicit.principal_variation
    )


def test_unverified_root_window_mode_rejected_before_native_execution():
    compiled = compile_semantic_ruleset(build_western_chess_ruleset())
    native = compile_native_semantic_rules(compiled)
    with pytest.raises(NativeUnsupportedRuleError, match="inexact tied bound"):
        semantic_iterative_search(native, None, 3, root_window_pruning=True)
    engine = SemanticSearchEngine(compiled, native, tt_megabytes=0)
    with pytest.raises(NativeUnsupportedRuleError, match="inexact tied bound"):
        engine.search(GameSession(compiled), SearchLimits(max_depth=3, quiescence_max_depth=0),
                      root_window_pruning=True)
