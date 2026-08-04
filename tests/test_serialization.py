"""RuleSet serialization, fingerprint stability and action serialization."""

from generic_chess.core.actions import BoardMove, DropMove, action_from_dict, action_to_dict
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom
from generic_chess.rules.schema import RuleSet, compute_fingerprint
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset

from conftest import king_type, make_ruleset, T


def _ruleset_with_metadata():
    pawn = T("P", LeapAtom((0, 1)), is_promotable=True, targets=("G",))
    gold = T("G", LeapAtom((1, 0)))
    rs = make_ruleset(8, [king_type(), pawn, gold], auto_promotion=True)
    return rs


def test_round_trip_preserves_fingerprint():
    rs = _ruleset_with_metadata()
    text = serialize_ruleset(rs)
    back = deserialize_ruleset(text)
    assert compute_fingerprint(back) == compute_fingerprint(rs)
    # Compiling the round-tripped ruleset works and keeps the fingerprint.
    from generic_chess.rules.compiler import compile_ruleset

    compiled = compile_ruleset(rs)
    c2 = compile_ruleset(back)
    assert c2.ruleset_fingerprint == compiled.ruleset_fingerprint


def test_serialization_is_canonical_and_stable():
    rs = _ruleset_with_metadata()
    assert serialize_ruleset(rs) == serialize_ruleset(rs)


def test_metadata_does_not_affect_fingerprint():
    rs = _ruleset_with_metadata()
    rs2 = RuleSet(
        schema_version=rs.schema_version,
        board_size=rs.board_size,
        piece_types=rs.piece_types,
        initial_position=rs.initial_position,
        drop_allowed=rs.drop_allowed,
        promotion_allowed=rs.promotion_allowed,
        promotion_forced=rs.promotion_forced,
        repetition_limit=rs.repetition_limit,
        max_ply=rs.max_ply,
        stalemate_result=rs.stalemate_result,
        metadata={"seed": 12345, "display_name": "completely different"},
    )
    assert compute_fingerprint(rs) == compute_fingerprint(rs2)


def test_action_serialization_round_trip():
    bm = BoardMove(Square(1, 0), Square(1, 2), "G")
    dm = DropMove("P", Square(3, 3))
    assert action_from_dict(action_to_dict(bm)) == bm
    assert action_from_dict(action_to_dict(dm)) == dm


def test_fingerprint_is_stable_across_runs():
    rs = _ruleset_with_metadata()
    fp1 = compute_fingerprint(rs)
    fp2 = compute_fingerprint(rs)
    assert fp1 == fp2
    assert isinstance(fp1, str)
    assert len(fp1) == 64  # sha256 hex
