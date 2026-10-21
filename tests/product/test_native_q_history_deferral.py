"""Physical q-terminal/history cases that unsafe quiet omission would change."""
import json
import pytest
from conftest import make_ruleset
from generic_chess.core.pieces import PieceType
from generic_chess.core.movement import LeapAtom
from generic_chess.core.transition import apply_action
from generic_chess.core.identity import position_identity_key
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.native import native_available, SemanticSearchEngine
from generic_chess.native.compiler import compile_native_semantic_rules
from generic_chess.native.adapter import pack_semantic_search_position
from generic_chess.native.mirror import expected_snapshot, pack_semantic_action
from generic_chess.native import semantic as sem
from generic_chess.session.session import GameSession
from generic_chess.ai.limits import SearchLimits
from test_native_pending_continuation import session_after

pytestmark = pytest.mark.skipif(not native_available(), reason="Native unavailable")


def cycle(*, max_ply=512, repetition=4, prefix=0):
    k = PieceType("K", "Anchor", (), is_anchor=True)
    f = PieceType("F", "F", (LeapAtom((0, 1)), LeapAtom((0, -1))))
    g = PieceType("G", "G", (LeapAtom((0, 1)), LeapAtom((0, -1))))
    z = PieceType("Z", "Z", ())
    zero = (False,) * 16
    rules = make_ruleset(4, [k, f, g, z], ["Z..k", "...g", "F...", "K..z"],
                        drop_all={"F": zero, "G": zero, "Z": zero},
                        max_ply=max_ply, repetition_limit=repetition)
    current = GameSession(compile_legacy_ruleset_for_semantic_execution(rules))
    for _ in range(prefix):
        action, = current.legal_actions()
        current.submit(action)
    return current


def checked_replay(current, nr, result):
    state = current.state
    witnesses = list(current._search_witnesses)
    native = pack_semantic_search_position(current.compiled, nr, current)
    for action in result.principal_variation:
        native = sem.make_checked(nr, native, pack_semantic_action(nr, state.position, action))
        state = apply_action(state, action, current.compiled)
        witnesses.append(state.position)
        actual = sem.snapshot(nr, native)
        expected = expected_snapshot(state.position, nr, current.compiled)
        for field in ("board", "hands", "aux_state", "side"):
            assert json.dumps(actual[field], sort_keys=True) == json.dumps(expected[field], sort_keys=True)
        assert actual["history_exact"] and actual["history_events_exact"]
        assert actual["ply"] == state.ply_count
        assert ["".join(f"{v:016x}" for v in h) for h in actual["history"]] == [
            str(position_identity_key(w, current.compiled)) for w in witnesses]
        assert actual["history_events"] == tuple(
            (255 if e.actor < 0 else e.actor, bool(e.gave_check)) for e in state.history)
        assert sem.terminal_status(nr, native) == {
            "status": state.terminal_status.status.value, "winner": state.terminal_status.winner}


@pytest.mark.parametrize("root_window", (False, True))
@pytest.mark.parametrize("boundary", ("max_ply", "repetition"))
def test_quiet_terminal_changes_q_value_and_preserves_full_history(boundary, root_window):
    current = cycle(max_ply=3, repetition=100) if boundary == "max_ply" else cycle(prefix=8)
    values = {"K": 0, "Z": 0, "F": 20, "G": 100} if boundary == "max_ply" else {
        "K": 0, "Z": 0, "F": 100, "G": 20}
    depth = 2 if boundary == "max_ply" else 3
    nr = compile_native_semantic_rules(current.compiled)
    before = current.state, current._search_witnesses
    result = SemanticSearchEngine(current.compiled, nr, board_values=values,
        hand_values=values, tt_megabytes=0, ordering_cache_enabled=False).search(
            current, SearchLimits(max_depth=depth, max_nodes=4096,
                quiescence_max_depth=1, quiescence_hard_max_depth=4),
            root_window_pruning=root_window)
    # Omitting the last quiet terminal would leave a nonzero material bound.
    assert result.completed_depth == depth and result.result_ordinary_qdepth == 1
    assert result.score == 0
    checked_replay(current, nr, result)
    assert (current.state, current._search_witnesses) == before


@pytest.mark.parametrize("tt_mb", (0, 1))
@pytest.mark.parametrize("q", (1, 4))
def test_pending_rule_limit_continuation_keeps_full_q_history(tt_mb, q):
    current = session_after(("e2e4", "d7d5", "f1b5", "c7c6"))
    nr = compile_native_semantic_rules(current.compiled)
    before = current.state, current._search_witnesses
    engine = SemanticSearchEngine(current.compiled, nr, tt_megabytes=tt_mb)
    for _ in range(2):
        result = engine.search(current, SearchLimits(max_depth=2, max_nodes=256,
            quiescence_max_depth=q, quiescence_hard_max_depth=8), root_window_pruning=True)
        checked_replay(current, nr, result)
        assert result.action in current.legal_actions()
        assert (current.state, current._search_witnesses) == before


def test_real_long_high_threshold_history_remains_complete():
    current = cycle(max_ply=1024, repetition=10000, prefix=512)
    nr = compile_native_semantic_rules(current.compiled)
    values = {"K": 0, "Z": 0, "F": 20, "G": 100}
    before = current.state, current._search_witnesses
    result = SemanticSearchEngine(current.compiled, nr, board_values=values,
        hand_values=values, tt_megabytes=0, ordering_cache_enabled=False).search(
            current, SearchLimits(max_depth=3, max_nodes=1024,
                quiescence_max_depth=4, quiescence_hard_max_depth=8), root_window_pruning=True)
    assert result.completed_depth == 3
    checked_replay(current, nr, result)
    assert (current.state, current._search_witnesses) == before
