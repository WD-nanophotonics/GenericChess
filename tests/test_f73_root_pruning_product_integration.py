"""Product-default integration checks for the F73 retention decision."""

from pathlib import Path

import pytest

from generic_chess.ai.limits import SearchLimits
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not native_available(), reason="native extension is not built")


def test_product_engine_defaults_to_root_pruning_and_audits_pin_legacy_mode():
    source = (ROOT / "generic_chess" / "native" / "semantic_engine.py").read_text(encoding="utf-8")
    assert "root_window_pruning: bool = True" in source
    low_level = (ROOT / "generic_chess" / "native" / "semantic.py").read_text(encoding="utf-8")
    assert "root_window_pruning: bool = False" in low_level
    for path in (
        ROOT / "scripts" / "f59_action_spectrum_diagnosis.py",
        ROOT / "scripts" / "f62_learned_champion_repeatability.py",
        ROOT / "scripts" / "f71_causal_root_hint_probe.py",
    ):
        assert "root_window_pruning=False" in path.read_text(encoding="utf-8")


def test_default_product_result_matches_explicit_enabled_mode():
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
    ).search(session, limits, root_window_pruning=True)
    assert default.root_window_pruning is True
    assert (default.action, default.score, default.principal_variation) == (
        explicit.action, explicit.score, explicit.principal_variation
    )
