"""An already adjudicated child cannot win by declaring after the game ends."""
from dataclasses import replace
import pytest
from conftest import make_ruleset, king_type, T
from generic_chess.core.movement import RayAtom
from generic_chess.rules.schema import RuleDeclaration, RuleDeclarationOutcomeBand, RuleWeightedMaterialMetric
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.native import SemanticSearchEngine, native_available
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.ai.limits import SearchLimits

pytestmark = pytest.mark.skipif(not native_available(), reason="native extension unavailable")


def position(*, max_ply=1000, declaring_owner=1):
    rook = T("R", RayAtom((0, 1)), RayAtom((0, -1)), RayAtom((1, 0)), RayAtom((-1, 0)))
    rules = make_ruleset(4, [king_type(), rook], lines=["k...", "....", ".K..", "...." if max_ply == 1 else "...R"])
    claim = RuleDeclaration(declaration_id="win", owner=declaring_owner,
        require_not_in_check=False, weighted_metric=RuleWeightedMaterialMetric(weights={"K": 1}),
        outcome_bands=(RuleDeclarationOutcomeBand(1, "WIN"),))
    compiled = compile_legacy_ruleset_for_semantic_execution(
        replace(rules, max_ply=max_ply, declarations=(claim,)))
    return GameSession(compiled)


@pytest.mark.parametrize("root_window", [False, True])
@pytest.mark.parametrize("tt_mb", [0, 1])
@pytest.mark.parametrize("boundary", ["mate", "max_ply"])
def test_child_terminal_precedes_opponent_win_claim(boundary, tt_mb, root_window):
    session = position(max_ply=1 if boundary == "max_ply" else 1000)
    before = session.state, session.to_record(), session._search_witnesses
    native = compile_native_semantic_rules(session.compiled)
    values = {tid: 0 if meta.is_anchor else 100
              for tid, meta in session.compiled.support.type_metadata.items()}
    engine = SemanticSearchEngine(session.compiled, native,
        board_values=values, hand_values=values, tt_megabytes=tt_mb, ordering_cache_enabled=False)
    limits = SearchLimits(max_depth=2, max_time_seconds=5,
        quiescence_max_depth=0, quiescence_hard_max_depth=0)
    for _ in range(2):  # Real cold then warm table; no manufactured entries.
        result = engine.search(session, limits, root_window_pruning=root_window)
        assert (session.state, session.to_record(), session._search_witnesses) == before
        assert result.completed_depth == 2
        assert result.declaration_id is None
        if boundary == "mate":
            assert result.score == 100_000_000 - 1
        else:
            assert result.score == 0
        child = position(max_ply=1 if boundary == "max_ply" else 1000)
        child.submit(result.action)
        assert child.result.status.value == ("max_ply" if boundary == "max_ply" else "checkmate")
        assert child.result.winner == (None if boundary == "max_ply" else 0)


def test_ongoing_root_win_claim_still_precedes_search():
    session = position(declaring_owner=0)
    native = compile_native_semantic_rules(session.compiled)
    result = SemanticSearchEngine(session.compiled, native, tt_megabytes=0).search(
        session, SearchLimits(max_depth=2, quiescence_max_depth=0), root_window_pruning=True)
    assert result.declaration_id == "win"
    assert result.action is None
    assert result.score == 100_000_000
