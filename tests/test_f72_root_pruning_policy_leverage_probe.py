"""Bounded F72 contract and fixed-depth parity checks."""

from pathlib import Path

import pytest

from generic_chess.ai.limits import SearchLimits
from generic_chess.native import native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.semantic_engine import SemanticSearchEngine
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.session.session import GameSession
from scripts import f72_root_pruning_policy_leverage_probe as f72


ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not native_available(), reason="native extension is not built")


def test_f72_scope_is_bounded_and_parity_precedes_policy_probe():
    source = (ROOT / "scripts" / "f72_root_pruning_policy_leverage_probe.py").read_text(
        encoding="utf-8"
    )
    assert f72.WORK_ORDER == "GENERICCHESS-F72-ROOT-PRUNING-POLICY-LEVERAGE-PROBE"
    assert f72.PARENT_SHA == "f193983819f2b3842e18ea714a89ec2268b18b78"
    assert f72.NODES == 2_000
    assert f72.EXPECTED_ROOTS == 20
    assert f72.PARITY_DEPTHS == (1, 2)
    assert source.index("_run_parity_gate") < source.index("_policy_arm")
    assert "final_holdout" not in source
    assert "arena" not in source.lower()
    assert "selfplay" not in source.lower()
    assert "heavy" not in source.lower()


def test_root_pruning_opt_in_preserves_fixed_depth_western_and_shogi_results():
    for ruleset in (build_western_chess_ruleset(), build_standard_shogi_ruleset()):
        compiled = compile_semantic_ruleset(ruleset)
        native = compile_native_semantic_rules(compiled)
        zero = (0,) * len(native.type_ids)
        session = GameSession(compiled)
        full = SemanticSearchEngine(
            compiled, native, board_values=zero, hand_values=zero, tt_megabytes=0
        ).search(
            session,
            SearchLimits(max_depth=2, max_nodes=None, quiescence_max_depth=0),
            root_window_pruning=False,
        )
        pruned = SemanticSearchEngine(
            compiled, native, board_values=zero, hand_values=zero, tt_megabytes=0
        ).search(
            session,
            SearchLimits(max_depth=2, max_nodes=None, quiescence_max_depth=0),
            root_window_pruning=True,
        )
        assert full.root_window_pruning is False
        assert pruned.root_window_pruning is True
        assert (full.action, full.score, full.principal_variation, full.declaration_id) == (
            pruned.action, pruned.score, pruned.principal_variation, pruned.declaration_id
        )
