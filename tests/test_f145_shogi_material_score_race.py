from types import SimpleNamespace

import pytest

from generic_chess.core.actions import DropMove
from generic_chess.core.coordinates import Square

from scripts import f145_shogi_material_score_race as race


def _fake_compiled():
    return SimpleNamespace(
        board_size=1,
        types_by_id={
            "P": SimpleNamespace(is_anchor=False),
            "K": SimpleNamespace(is_anchor=True),
        },
    )


def test_capture_check_and_plus_two_are_evaluator_independent(monkeypatch):
    compiled = _fake_compiled()
    before = SimpleNamespace(board=(SimpleNamespace(owner=1, current_type_id="P"),))
    after = SimpleNamespace(board=(None,))
    monkeypatch.setattr(race, "is_in_check", lambda position, player, rules: True)

    event = race.score_event(before, DropMove("P", Square(0, 0)), after, 0, compiled)

    assert event == {"capture": 1, "check": 1, "points": 2}


def test_anchor_capture_does_not_score_capture(monkeypatch):
    compiled = _fake_compiled()
    before = SimpleNamespace(board=(SimpleNamespace(owner=1, current_type_id="K"),))
    after = SimpleNamespace(board=(None,))
    monkeypatch.setattr(race, "is_in_check", lambda position, player, rules: False)

    event = race.score_event(before, DropMove("P", Square(0, 0)), after, 0, compiled)

    assert event == {"capture": 0, "check": 0, "points": 0}


def test_threshold_and_terminal_precedence_helpers():
    assert race.SCORE_THRESHOLD == 10
    winner, reason, valid = race._finish_formal(SimpleNamespace(), [4, 7])
    assert (winner, reason, valid) == (1, "score_tiebreak", True)
    winner, reason, valid = race._finish_formal(SimpleNamespace(), [6, 6])
    assert (winner, reason, valid) == (None, "invalid_equal_score_terminal", False)

    checkmate = SimpleNamespace(status=race.SessionStatus.CHECKMATE, winner=0)
    assert race._core_winner(checkmate)
    declaration = SimpleNamespace(status=race.SessionStatus.DECLARATION, winner=1)
    assert race._core_winner(declaration)


def test_process_pair_runner_preserves_role_swap_and_ordering():
    compiled = race._compile()
    openings = race.generate_arena_openings(
        compiled, count=4, seed=1_459_001, min_plies=4, max_plies=4
    ).openings
    values = race.gen0_vector()
    payload = {
        "opening": race._opening_payload(openings[0]),
        "champion": list(values),
        "child": list(values),
        "ordering_values": race._ordering_values(compiled),
        "max_nodes": 16,
    }
    with race.ProcessPoolExecutor(max_workers=2) as pool:
        row = next(pool.map(race._play_pair_task, [payload]))
    with race.ProcessPoolExecutor(max_workers=2) as pool:
        repeat = next(pool.map(race._play_pair_task, [payload]))

    assert [game["child_owner"] for game in row["games"]] == [0, 1]
    assert len(row["games"]) == 2
    assert [game["result"] for game in row["games"]] == [game["result"] for game in repeat["games"]]
    assert [game["plies"] for game in row["games"]] == [game["plies"] for game in repeat["games"]]


@pytest.mark.parametrize("valid_initial", [True, False])
def test_replacement_pool_is_consumed_only_for_invalid_pairs(monkeypatch, valid_initial):
    openings = tuple(
        SimpleNamespace(index=index, opening_seed=index, target_plies=0, actions=(), final_position_key=str(index))
        for index in range(4)
    )

    class FakePool:
        def __init__(self, max_workers):
            self.max_workers = max_workers

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def map(self, function, payloads):
            return [function(payload) for payload in payloads]

    def fake_pair(payload):
        index = payload["opening"]["index"]
        valid = valid_initial if index < 2 else True
        return {"pair_index": index, "valid": valid, "games": [], "pair_score": 0.5 if valid else None}

    monkeypatch.setattr(race, "ProcessPoolExecutor", FakePool)
    monkeypatch.setattr(race, "_play_pair_task", fake_pair)
    result = race.run_pairs((1,), (1,), openings, {}, workers=2, target_pairs=2)

    assert result["attempt_count"] == (2 if valid_initial else 4)
    assert len(result["rows"]) == 2
