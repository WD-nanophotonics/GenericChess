"""Complete semantic qsearch and cache/control boundaries."""
from dataclasses import replace
import pytest
from generic_chess.native import SemanticSearchEngine, native_available, _module
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.ai.limits import SearchLimits
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.cancellation import CancellationToken
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.session.session import GameSession
from test_qsearch_semantic_effects import transform_rules

pytestmark = pytest.mark.skipif(
    not native_available() or getattr(_module(), "SEMANTIC_QSEARCH_VERSION", 0) < 1,
    reason="Native qsearch kernel unavailable; rebuild required")


class Material:
    values = {"K": 0, "A": 100, "B": 900}

    def evaluate(self, state):
        side = state.position.side_to_move
        return sum((1 if p.owner == side else -1) * self.values[p.current_type_id]
                   for p in state.position.board if p is not None) + sum(
            (1 if owner == side else -1) * self.values[tid] * count
            for owner, hand in enumerate(state.position.hands) for tid, count in hand.items())

    def type_value(self, tid):
        return self.values[tid]

    def capture_order_value(self, moving, captured):
        return 10 * self.values[captured.current_type_id] - self.values[moving.current_type_id]


def fixture(kind="transform"):
    return GameSession(compile_ruleset_for_execution(transform_rules(kind, encoding="effect")))


def engine(session, tt=0):
    return SemanticSearchEngine(session.compiled, compile_native_semantic_rules(session.compiled),
        board_values=Material.values, hand_values=Material.values,
        tt_megabytes=tt, ordering_cache_enabled=False)


def limits(q, hard=8, **kwargs):
    return SearchLimits(max_depth=2, max_time_seconds=5,
        quiescence_max_depth=q, quiescence_hard_max_depth=hard, **kwargs)


def normalize(score):
    return score if abs(score) < 50_000_000 else (
        (1 if score > 0 else -1) * (1_000_000_000 - (100_000_000 - abs(score))))


@pytest.mark.parametrize("kind", ["transform", "nochange", "balanced"])
@pytest.mark.parametrize("q", [1, 4])
def test_semantic_q_matches_independent_core_full_effect_policy(kind, q):
    session = fixture(kind)
    before = session.state, session.to_record(), session._search_witnesses
    core = AlphaBetaPlayer(session.compiled, evaluator_override=Material(), use_tt=False,
        use_disk_cache=False, use_ordering=False, use_native_semantic_legality=False,
        tuning=SearchTuning(use_root_tactical=False)).choose_action(session, limits(q))
    native = engine(session).search(session, limits(q), root_window_pruning=True)
    assert core.completed_depth == native.completed_depth == 2
    assert core.score == normalize(native.score)
    assert native.qnodes > 0
    assert before == (session.state, session.to_record(), session._search_witnesses)
    assert native.action in session.legal_actions()


@pytest.mark.parametrize("root_window", [False, True])
def test_warm_tt_separates_reserve_qdepth_and_hard_depth(root_window):
    import json
    from pathlib import Path
    from generic_chess.rules.serialization import deserialize_ruleset
    from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
    from scripts.full_q_refresh_comparison import SearchMetadataAdapter
    from scripts.research_record import record_value
    data = json.loads((Path(__file__).parent / "data/native_q_tt_objective_2401.json").read_text())
    raw = compile_legacy_ruleset_for_semantic_execution(deserialize_ruleset(json.dumps(data["ruleset"])))
    c = SearchMetadataAdapter(ir=raw.ir, _legacy_compiled=raw._legacy_compiled, support=raw.support)
    session = GameSession(c)
    for av in data["walk"]:
        action, = [a for a in session.legal_actions() if record_value(a) == av]
        session.submit(action)
    values = {tid: 0 if m.is_anchor else 100 for tid, m in c.support.type_metadata.items()}
    def make(tt):
        return SemanticSearchEngine(c, compile_native_semantic_rules(c),
            board_values=values, hand_values=values, tt_megabytes=tt, ordering_cache_enabled=False)
    shared = make(1)
    scores = {}
    for q, hard in [(0, 8), (1, 4), (4, 8), (0, 8), (1, 4), (4, 8)]:
        lim = limits(q, hard)
        fresh = make(0).search(session, lim, root_window_pruning=root_window)
        warm = shared.search(session, lim, root_window_pruning=root_window)
        assert warm.completed_depth == fresh.completed_depth == 2
        assert (warm.score, warm.action, warm.declaration_id, warm.principal_variation) == (
            fresh.score, fresh.action, fresh.declaration_id, fresh.principal_variation)
        scores[q] = warm.score
    assert scores[0] != scores[4]  # This fixture actually distinguishes cache objectives.


def test_native_q_stop_preserves_root_and_reports_real_budget():
    session = fixture()
    before = session.state, session.to_record(), session._search_witnesses
    for lim in [limits(4, max_nodes=1), limits(4, quiescence_max_nodes=1), limits(1, 1)]:
        result = engine(session, 1).search(session, lim, root_window_pruning=True)
        assert result.termination_reason in ("node_budget", "qsearch_budget", "qsearch_check_hard_limit")
        assert result.completed_depth < 2
        assert result.action in session.legal_actions()
        assert before == (session.state, session.to_record(), session._search_witnesses)
    token = CancellationToken()
    token.cancel()
    result = engine(session).search(session, limits(4), token)
    assert result.termination_reason == "cancelled" and result.completed_depth == 0
    assert result.qnodes == 0
    assert before == (session.state, session.to_record(), session._search_witnesses)


def test_unsupported_q_capability_requires_rebuild_without_silent_downgrade(monkeypatch):
    session = fixture()
    e = engine(session)
    monkeypatch.setattr(_module(), "SEMANTIC_QSEARCH_VERSION", 0)
    with pytest.raises(ValueError, match="rebuilt Native kernel"):
        e.search(session, limits(1))
    assert e.search(session, limits(0)).qnodes == 0


@pytest.mark.parametrize("depth,ordinary", [(1, 0), (2, 4)])
def test_retained_iteration_reports_actual_q_policy(depth, ordinary):
    session = fixture()
    result = engine(session).search(session, SearchLimits(max_depth=depth,
        max_time_seconds=5, quiescence_max_depth=4, quiescence_hard_max_depth=8))
    assert result.completed_depth == depth
    assert result.result_ordinary_qdepth == ordinary
    assert result.result_check_hard_qdepth == 8

def test_q_node_limit_is_expansion_check_not_quiet_reserve_visit_cap():
    from generic_chess import build_builtin_ruleset
    session = GameSession(compile_ruleset_for_execution(build_builtin_ruleset("western_chess")))
    values = {tid: 0 if m.is_anchor else 100
              for tid, m in session.compiled.support.type_metadata.items()}
    e = SemanticSearchEngine(session.compiled, compile_native_semantic_rules(session.compiled),
        board_values=values, hand_values=values, tt_megabytes=0)
    before = session.state, session.to_record(), session._search_witnesses
    result = e.search(session, SearchLimits(max_depth=1, max_time_seconds=5,
        quiescence_max_depth=4, quiescence_hard_max_depth=8, quiescence_max_nodes=1))
    assert result.completed_depth == 1 and result.result_ordinary_qdepth == 0
    assert result.qnodes > 1
    assert result.termination_reason == "completed"
    assert before == (session.state, session.to_record(), session._search_witnesses)

def test_raw_q_call_rejects_combined_stack_overflow_and_releases_engine():
    from generic_chess.native.compiler import GC_SEM_MAX_PLY
    from generic_chess.native.adapter import pack_semantic_search_position
    session = fixture()
    e = engine(session)
    position = pack_semantic_search_position(session.compiled, e._native_rules, session)
    with pytest.raises(ValueError, match="bounded search stack"):
        _module().semantic_engine_search(e._capsule, position, GC_SEM_MAX_PLY,
            None, 0.0, None, None, False, False, 1, 8, None)
    assert e.search(session, limits(0)).completed_depth == 2
