"""SearchTuning, benchmark profiles, snapshot and backend boundary."""

import pytest

from generic_chess.ai.alphabeta.backend import PythonSearchBackend
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.snapshot import SearchSnapshot
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.benchmark.profiles import all_profiles, profile_by_name
from generic_chess.ai.limits import SearchLimits
from generic_chess.session.session import GameSession

from ai_fixtures import build_4x4_rooks


def test_tuning_defaults():
    t = SearchTuning()
    assert t.use_pvs is False
    assert t.use_aspiration is False
    assert t.use_staged_move_picker is False
    assert t.use_countermove is False
    assert t.use_mate_distance_pruning is False
    assert t.use_root_tactical is True  # user-confirmed default
    assert t.check_evasion_max_depth == 8
    assert t.aspiration_start_depth == 4
    assert t.history_max == 2**16


def test_profiles_map_to_single_features():
    assert not profile_by_name("baseline").tuning.use_pvs
    assert profile_by_name("pvs").tuning.use_pvs
    assert profile_by_name("pvs").tuning.use_aspiration is False
    assert profile_by_name("pvs_aspiration").tuning.use_aspiration
    assert profile_by_name("staged_picker").tuning.use_staged_move_picker
    assert profile_by_name("countermove").tuning.use_countermove
    assert profile_by_name("mate_distance").tuning.use_mate_distance_pruning
    full = profile_by_name("full_candidate").tuning
    assert (
        full.use_pvs
        and full.use_aspiration
        and full.use_staged_move_picker
        and full.use_countermove
        and full.use_mate_distance_pruning
    )
    names = [p.name for p in all_profiles()]
    assert names == [
        "baseline",
        "pvs",
        "pvs_aspiration",
        "staged_picker",
        "countermove",
        "mate_distance",
        "full_candidate",
    ]


def test_snapshot_is_frozen_and_carries_fields():
    compiled = build_4x4_rooks()
    session = GameSession(compiled)
    snap = SearchSnapshot(
        session=session,
        limits=SearchLimits(max_nodes=10),
        ruleset_fingerprint="fp",
        root_key="rk",
        generation=3,
    )
    with pytest.raises(Exception):
        snap.generation = 4  # frozen dataclass
    assert snap.session is session
    assert snap.limits.max_nodes == 10
    assert snap.generation == 3


def test_python_search_backend_returns_decision():
    compiled = build_4x4_rooks()
    player = AlphaBetaPlayer(compiled, use_disk_cache=False)
    backend = PythonSearchBackend(player)
    session = GameSession(compiled)
    snap = SearchSnapshot(
        session=session,
        limits=SearchLimits(max_depth=1, quiescence_max_depth=0),
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        root_key="root",
        generation=1,
    )
    decision = backend.search(snap)
    assert decision.action is not None
    assert decision.action in session.legal_actions()


def test_statistics_has_lab_fields():
    s = SearchStatistics()
    assert s.q_evasion_truncations == 0
    assert s.q_budget_truncations == 0
    assert s.pvs_null_window_searches == 0
    assert s.aspiration_fail_low == 0
    assert s.root_scan_nodes == 0
    assert s.move_picker_yielded_by_stage == {}
    assert s.ordering_seconds == 0.0
    assert s.countermove_hits == 0
    assert s.mate_pruning_cutoffs == 0
