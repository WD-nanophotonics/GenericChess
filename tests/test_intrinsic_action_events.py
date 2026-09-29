from dataclasses import replace
from collections import Counter, defaultdict
from fractions import Fraction

import pytest

from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.ir import geometry_candidates
from generic_chess.rules.schema import RuleActionEffect, RuleSquareRef
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from scripts.audit_static_semantic_material_prior_v2c import (
    _event_measure_factory, _token_state_ledger,
)
from scripts.intrinsic_action_events import (
    collect_intrinsic_board_events, event_cubes_for_candidate,
)
from tests.test_static_semantic_material_prior_v2a import _synthetic


def test_distinct_destinations_survive_shared_off_target_removal():
    rules, _ = _synthetic(relations=("empty", "empty"), shapes=((1, 0), (0, 1)))
    victim = RuleSquareRef(kind="offset_from_source", offset=(1, 1))
    actions = tuple(replace(action, effects=(
        RuleActionEffect("remove", square_ref=victim, disposition="remove_from_game",
                         piece_owner="opponent"), *action.effects,
    )) for action in rules.semantic_actions)
    compiled = compile_semantic_ruleset(replace(rules, semantic_actions=actions))
    source = 2 * 8 + 2
    keys = []
    for action, target in zip(actions, (source + 1, source + 8)):
        pattern = next(row for row in compiled.ir.patterns if row.name == action.name)
        events = event_cubes_for_candidate(compiled, pattern, type_id="X",
                                           owner=0, source=source, target=target, path=())
        assert len(events) == 1
        key, cubes = next(iter(events.items()))
        assert key[3] == target and key[5] == ((source + 9, "remove_from_game"),)
        assert cubes == (((target, ("empty",)), (source + 9, ("enemy",))),)
        keys.append(key)
    assert keys[0] != keys[1]


def test_physical_removal_reference_aliases_have_same_event_identity():
    rules, _ = _synthetic(relations=("enemy", "enemy"), shapes=((1, 0), (1, 0)))
    actions = tuple(replace(action, effects=tuple(replace(effect,
        square_ref=RuleSquareRef(kind="offset_from_target", offset=(0, 0))
        if effect.kind == "remove" and index else effect.square_ref)
        for effect in action.effects)) for index, action in enumerate(rules.semantic_actions))
    compiled = compile_semantic_ruleset(replace(rules, semantic_actions=actions))
    source, target = 2 * 8 + 2, 2 * 8 + 3
    observed = []
    for action in actions:
        pattern = next(row for row in compiled.ir.patterns if row.name == action.name)
        observed.append(event_cubes_for_candidate(compiled, pattern, type_id="X",
                                                   owner=0, source=source, target=target, path=()))
    assert observed[0] == observed[1]
    audit = collect_intrinsic_board_events(compiled, "X")
    matching = [key for key in audit["events"]
                if key[0] == 0 and key[2] == source and key[3] == target
                and key[4] == "enemy" and key[5] == ((target, "remove_from_game"),)]
    assert len(matching) == 1


def test_compiled_cannon_capture_event_preserves_screen_and_target():
    compiled = compile_semantic_ruleset(build_xiangqi_diagnostic_ruleset())
    pattern = next(row for row in compiled.ir.patterns
                   if row.name == "cannon_capture_one_screen")
    source = 4 * compiled.support.board_shape.width + 4
    target, path = next((target, path) for target, path in
                        geometry_candidates(compiled.ir.geometry[pattern.geometry_ids[0]],
                                            "0", source) if len(path) == 2)
    events = event_cubes_for_candidate(compiled, pattern, type_id="C",
                                       owner=0, source=source, target=target, path=path)
    assert len(events) == 1
    key, cubes = next(iter(events.items()))
    assert key[3] == target and key[5] == ((target, "remove_from_game"),)
    assert len(cubes) == 2
    ledger = _token_state_ledger(compiled)
    assert _event_measure_factory(ledger, compiled, "C")(0, "C", list(cubes)) == Fraction(2426, 85173)


def test_all_nonanchor_board_mode_event_coverage_across_three_rulesets():
    for builder in (
        build_western_chess_ruleset,
        build_standard_shogi_ruleset,
        build_xiangqi_diagnostic_ruleset,
    ):
        compiled = compile_semantic_ruleset(builder())
        type_ids = [type_id for type_id, metadata in compiled.support.type_metadata.items()
                    if not metadata.is_anchor]
        for type_id in type_ids:
            audit = collect_intrinsic_board_events(compiled, type_id)
            assert audit["coverage_complete"], (type_id, audit["unsupported_intrinsic"])
            assert audit["events"], type_id
            assert audit["candidate_count"] <= 100_000
        if builder is build_standard_shogi_ruleset:
            gold = collect_intrinsic_board_events(compiled, "G")
            assert gold["excluded_held"] and gold["allowed_drop_squares"] > 0
        elif builder is build_xiangqi_diagnostic_ruleset:
            cannon = collect_intrinsic_board_events(compiled, "C")
            assert not cannon["excluded_held"] and cannon["excluded_disabled_drop"]

    with pytest.raises(RuntimeError, match="candidate budget"):
        collect_intrinsic_board_events(compiled, "R", max_candidates=1)


def test_chess_and_shogi_pawn_promotion_events_keep_resulting_types():
    chess = collect_intrinsic_board_events(
        compile_semantic_ruleset(build_western_chess_ruleset()), "P")
    assert chess["coverage_complete"] and chess["excluded_history"] == (
        "en_passant_left", "en_passant_right")
    assert ("pawn_double_step", "set_token") in chess["excluded_auxiliary_effects"]
    chess_results = Counter(key[6] for key in chess["events"])
    assert chess_results == {"P": 280, "B": 44, "N": 44, "Q": 44, "R": 44}
    assert any(key[0] == 0 and key[2] == 12 and key[3] == 28 for key in chess["events"])
    assert not any(key[0] == 0 and key[2] == 28 and key[3] == 44 for key in chess["events"])

    shogi = collect_intrinsic_board_events(
        compile_semantic_ruleset(build_standard_shogi_ruleset()), "P")
    assert shogi["coverage_complete"] and not shogi["excluded_history"]
    branches = defaultdict(set)
    for key in shogi["events"]:
        branches[key[:6]].add(key[6])
    assert Counter(tuple(sorted(types)) for types in branches.values()) == {
        ("P",): 180, ("P", "TP"): 72, ("TP",): 36,
    }
