"""Cheap contracts for the non-public Western qualification control."""

from __future__ import annotations

import json

from generic_chess.rules.schema import compute_fingerprint, ruleset_to_dict
from scripts.audit_f24g_canonical_western_perft import CANONICAL_CORPUS, perft, position_from_fen
from scripts.audit_f24f_western_chess_perft import standard_engine
from scripts.f94_r5_western_qualification_control import (
    QUALIFICATION_CONTROL_NAME,
    QUALIFICATION_CHECKPOINT_ID,
    QUALIFICATION_RULESET_FINGERPRINT,
    QUALIFICATION_REPETITION_LIMIT,
    PRODUCTION_RULESET_FINGERPRINT,
    build_western_chess_qualification_control,
    compile_western_chess_qualification_control,
)
from scripts.f94_r5_western_qualification_prep import build_prep
from generic_chess.core.identity import position_identity_key
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.semantic_executor import semantic_engine_for
from scripts.audit_f24f_western_chess_perft import position_from_fen as production_position_from_fen


def test_control_is_not_public_and_has_exactly_one_gameplay_delta():
    from generic_chess.rules.catalog import builtin_ruleset_names
    from generic_chess.rules.western_chess import build_western_chess_ruleset

    production = build_western_chess_ruleset()
    control = build_western_chess_qualification_control()
    left = ruleset_to_dict(production, include_metadata=True)
    right = ruleset_to_dict(control, include_metadata=True)
    assert builtin_ruleset_names() == ("western_chess", "standard_shogi")
    assert QUALIFICATION_CONTROL_NAME not in builtin_ruleset_names()
    assert compute_fingerprint(production) == PRODUCTION_RULESET_FINGERPRINT
    assert [key for key in left if left[key] != right[key]] == ["repetition_limit"]
    assert control.repetition_limit == QUALIFICATION_REPETITION_LIMIT
    assert control.repetition_policy == production.repetition_policy
    assert control.max_ply == production.max_ply
    assert compute_fingerprint(control) != PRODUCTION_RULESET_FINGERPRINT
    assert compute_fingerprint(control) == QUALIFICATION_RULESET_FINGERPRINT


def test_control_preserves_f24g_canonical_perft_counts():
    compiled, _ = standard_engine()
    control = compile_western_chess_qualification_control()
    engine = semantic_engine_for(control)
    for _label, fen, expected in CANONICAL_CORPUS:
        position = position_from_fen(fen, control)
        for depth, wanted in enumerate(expected, 1):
            assert perft(engine, position, depth) == wanted


def test_control_reaches_five_occurrences_before_max_ply():
    control = compile_western_chess_qualification_control()
    engine = semantic_engine_for(control)
    position = production_position_from_fen(
        "1n2k3/8/8/8/8/8/1N6/4K3 w - - 0 1", control
    )
    counts = {(position_identity_key(position, control)): 1}
    cycle = (("b2", "c4"), ("b8", "c6"), ("c4", "b2"), ("c6", "b8"))
    for _ in range(4):
        for source, target in cycle:
            action = next(
                item for item in engine.legal_actions(position)
                if item.source == _square(source) and item.target == _square(target)
            )
            position = engine.apply(position, action)
            key = position_identity_key(position, control)
            counts[key] = counts.get(key, 0) + 1
    current_key = position_identity_key(position, control)
    result = engine.terminal_result(
        position, 16, tuple(sorted(counts.items()))
    )
    assert counts[current_key] == 5
    assert result.status is TerminalStatus.REPETITION
    assert 16 < control.support.max_ply
    assert control.ruleset_fingerprint == QUALIFICATION_RULESET_FINGERPRINT


def test_qualification_prep_is_result_free_and_disjoint(tmp_path):
    payload = build_prep(output=tmp_path / "qualification-prep.json")
    assert payload["schema"] == "generic-chess-f94-r5-western-qualification-control-prep-v1"
    assert payload["status"] == "PREP_FROZEN"
    assert payload["result_free"] is True
    assert payload["not_public_builtin"] is True
    assert payload["tape_seeds"] == [9601, 9602, 9603]
    assert not set(payload["tape_seeds"]) & set(payload["disjoint_from_tape_seeds"])
    assert payload["qualification_control"]["gameplay_delta"] == ["repetition_limit: 100000 -> 5"]
    assert payload["qualification_control"]["evaluator_identity"] == "learnable-material-v1"
    assert payload["qualification_control"]["qualification_checkpoint_id"] == QUALIFICATION_CHECKPOINT_ID
    assert json.loads((tmp_path / "qualification-prep.json").read_text(encoding="utf-8")) == payload


def _square(name: str) -> int:
    return (ord(name[0]) - ord("a")) + 8 * (int(name[1]) - 1)
