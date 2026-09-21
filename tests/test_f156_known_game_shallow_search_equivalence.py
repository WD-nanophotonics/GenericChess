"""Contract tests for the small F156 known-game equivalence diagnostic."""

from __future__ import annotations

import pytest

from generic_chess.native import native_available


pytestmark = pytest.mark.skipif(
    not native_available(), reason="native extension unavailable"
)


def test_f156_known_game_shallow_search_equivalence_passes():
    from scripts.f156_known_game_shallow_search_equivalence import run_probe

    result = run_probe()
    assert result["classification"] == "KNOWN_GAME_SHALLOW_SEARCH_EQUIVALENCE_PASS", result
    assert result["native_available"] is True
    assert result["run_config"]["depths"] == [1, 2]
    assert result["run_config"]["quiescence_max_depth"] == 0
    assert result["roots"]["shogi_s2"].endswith("repetition count set to 4")
    assert set(result["search"]) == {"western", "shogi"}
    for game in result["search"].values():
        assert set(game["depths"]) == {"1", "2"}
        for rows in game["depths"].values():
            assert len(rows) == 2
            assert rows[0]["python"] == rows[1]["python"]
            assert rows[0]["native"] == rows[1]["native"]
    assert result["terminal"]["w2_checkmate"]["agree"]
    assert result["terminal"]["s2_repetition"]["agree"]
