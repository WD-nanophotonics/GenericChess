"""Native Phase 1 kernel smoke and API tests (skip when extension is absent)."""

import pytest

from generic_chess.native import (
    native_available,
    native_capabilities,
    native_version,
)

pytestmark = pytest.mark.skipif(
    not native_available(), reason="native extension not built"
)

from generic_chess.generation.config import GeneratorConfig
from generic_chess.generation.generator import generate_game
from generic_chess.native import _module
from generic_chess.native.adapter import (
    native_legal_actions,
    native_make_unmake_roundtrip,
    pack_native_position,
    to_python_action,
)
from generic_chess.native.compiler import (
    NativeUnsupportedRuleError,
    compile_native_rules,
)
from generic_chess.native.reference import python_legal_actions
from generic_chess.session.session import GameSession


def _compiled(size=4, preset="classic_like", seed=7):
    game = generate_game(
        GeneratorConfig(seed=seed, board_size=size, setup_preset=preset)
    )
    return game.compiled_ruleset


def test_native_import_and_capabilities():
    assert native_available()
    assert native_version() != "unavailable"
    caps = native_capabilities()
    assert caps["available"] is True
    assert caps["native_perft"] is True


def test_compile_pack_and_legal_actions():
    compiled = _compiled()
    rules = compile_native_rules(compiled)
    assert rules.fingerprint == compiled.ruleset_fingerprint
    state = GameSession(compiled).state
    pos = pack_native_position(compiled, rules, state)
    nat = {str(to_python_action(rules, a)) for a in native_legal_actions(rules, pos)}
    py = {str(a) for a in python_legal_actions(state, compiled)}
    assert nat == py
    assert nat


def test_perft_matches_python_small_board():
    from generic_chess.native.adapter import native_perft
    from generic_chess.native.reference import python_perft

    for size, depth in ((4, 4), (6, 3)):
        compiled = _compiled(size=size)
        rules = compile_native_rules(compiled)
        state = GameSession(compiled).state
        pos = pack_native_position(compiled, rules, state)
        for d in range(1, depth + 1):
            assert native_perft(rules, pos, d)["nodes"] == python_perft(
                compiled, state, d
            )


def test_make_unmake_roundtrip():
    compiled = _compiled()
    rules = compile_native_rules(compiled)
    state = GameSession(compiled).state
    pos = pack_native_position(compiled, rules, state)
    for action in native_legal_actions(rules, pos):
        result = native_make_unmake_roundtrip(rules, pos, action)
        assert result["make_ok"]
        assert result["hash_after_make_ok"]
        assert result["hash_restored_ok"]
        assert result["state_restored"]


def test_attack_map_matches_python():
    from generic_chess.core.attacks import pseudo_attacks

    compiled = _compiled()
    rules = compile_native_rules(compiled)
    state = GameSession(compiled).state
    pos = pack_native_position(compiled, rules, state)
    for owner in (0, 1):
        nat = {
            sq
            for sq in _module().native_attack_map(rules.capsule, pos, owner)
        }
        py = {
            s.file + s.rank * compiled.board_size
            for s in pseudo_attacks(state.position, owner, compiled)
        }
        assert nat == py


def test_unsupported_rules_raise():
    from generic_chess.rules.schema import RuleSet
    from generic_chess.rules.compiler import compile_ruleset
    from generic_chess.core.pieces import Piece, PieceType
    from generic_chess.core.movement import LeapAtom

    KING = tuple(
        LeapAtom((df, dr))
        for df in (-1, 0, 1)
        for dr in (-1, 0, 1)
        if (df, dr) != (0, 0)
    )
    n = 4
    rows = [[None] * n for _ in range(n)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[3][3] = Piece(1, "K", "K", False)
    mask = (False,) * (n * n)
    # 32 piece types > native cap of 64? use 65 types to exceed.
    types = [PieceType("K", "K", KING, is_anchor=True)]
    for i in range(65):
        types.append(
            PieceType(f"T{i}", f"T{i}", (LeapAtom((0, 1)),))
        )
    ruleset = RuleSet(
        schema_version=1,
        board_size=n,
        piece_types=tuple(types),
        initial_position=tuple(tuple(r) for r in rows),
        drop_allowed={
            f"T{i}": (mask, mask) for i in range(65)
        },
        promotion_allowed={},
        promotion_forced={},
        repetition_limit=4,
        max_ply=512,
        stalemate_result="draw",
    )
    with pytest.raises(NativeUnsupportedRuleError):
        compile_native_rules(compile_ruleset(ruleset))


def test_native_child_snapshot_equals_python_child():
    from generic_chess.core.transition import legal_successors
    from generic_chess.native.adapter import native_child_snapshot
    from generic_chess.native.reference import python_child_snapshot

    compiled = _compiled()
    rules = compile_native_rules(compiled)
    state = GameSession(compiled).state
    pos = pack_native_position(compiled, rules, state)
    for action, child in legal_successors(state, compiled):
        packed = next(
            a
            for a in native_legal_actions(rules, pos)
            if str(to_python_action(rules, a)) == str(action)
        )
        ns = native_child_snapshot(rules, pos, packed)
        ps = python_child_snapshot(state, action, compiled)
        assert ns["side_to_move"] == ps["side_to_move"]
        assert ns["ply"] == ps["ply"]
        assert ns["terminal"] == ps["terminal"]
        assert ns["repetition_count"] == ps["repetition_count"]
