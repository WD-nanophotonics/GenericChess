"""Cheap main ordering is confined to exact-root/canonical-replay mode."""
import pytest
from generic_chess.native import native_available, _module, SemanticSearchEngine
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native import semantic as sem
from generic_chess import build_builtin_ruleset, compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.ai.limits import SearchLimits

pytestmark = pytest.mark.skipif(not native_available() or
    getattr(_module(), "SEMANTIC_MAIN_ORDERING_VERSION", 0) < 1,
    reason="main-ordering kernel rebuild required")

@pytest.mark.parametrize("window", [False, True])
def test_main_hint_only_runs_in_exact_replay_mode(window):
    c = compile_ruleset_for_execution(build_builtin_ruleset('western_chess'))
    s = GameSession(c)
    nr = compile_native_semantic_rules(c)
    values = {tid: 0 if tid == 'K' else 100 for tid in nr.type_ids}
    engine = SemanticSearchEngine(c, nr, board_values=values, hand_values=values,
        tt_megabytes=0, ordering_cache_enabled=False)
    before = s.to_record()
    result = engine.search(s, SearchLimits(max_depth=2, max_time_seconds=5,
        quiescence_max_depth=0), root_window_pruning=window)
    assert result.completed_depth == 2 and result.score == 0
    assert result.action in s.legal_actions()
    assert (result.main_binary_order_calls > 0) == window
    assert s.to_record() == before
    raw = sem.semantic_iterative_search(nr, pack_semantic_search_position(c,nr,s),
        2, board_values=values, hand_values=values, root_window_pruning=window)
    assert (raw['main_binary_order_calls'] > 0) == window
    assert raw['score'] == result.score
