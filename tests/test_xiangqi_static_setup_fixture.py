"""Incomplete, test-only Xiangqi setup fixture; not a playable RuleSet.

Initial placement follows the World Xiangqi Federation's introductory board
diagram. All movement atoms are intentionally empty. See fixture metadata for
the rule consequences deliberately omitted at this setup-only stage.
"""

from collections import Counter

from generic_chess.core.coordinates import BoardShape
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.compiler import _compile_geometry_carrier
from generic_chess.rules.schema import RuleSet, compute_fingerprint
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset


OMITTED_RULE_SEMANTICS = (
    "all piece movement and capture patterns",
    "palace confinement for general and advisors",
    "elephant river restriction and horse-leg/elephant-eye blocking",
    "cannon screen captures",
    "soldier forward/lateral movement by river side",
    "facing-generals prohibition and check legality",
    "stalemate, repetition, and perpetual-check/chase adjudication",
)


def _build_incomplete_static_xiangqi_setup_fixture() -> RuleSet:
    """Return only board dimensions, type identities, anchors, and initial men."""
    shape = BoardShape(9, 10)
    names = {
        "G": "General",
        "A": "Advisor",
        "E": "Elephant",
        "R": "Chariot",
        "H": "Horse",
        "C": "Cannon",
        "P": "Pawn",
    }
    piece_types = tuple(
        PieceType(type_id, name, (), is_anchor=(type_id == "G"))
        for type_id, name in names.items()
    )
    rows = [[None for _ in range(shape.width)] for _ in range(shape.height)]
    back_rank = ("R", "H", "E", "A", "G", "A", "E", "H", "R")
    for file, type_id in enumerate(back_rank):
        rows[0][file] = Piece(0, type_id, type_id)
        rows[9][file] = Piece(1, type_id, type_id)
    for file in (1, 7):
        rows[2][file] = Piece(0, "C", "C")
        rows[7][file] = Piece(1, "C", "C")
    for file in (0, 2, 4, 6, 8):
        rows[3][file] = Piece(0, "P", "P")
        rows[6][file] = Piece(1, "P", "P")
    no_drops = (False,) * shape.area
    return RuleSet(
        board_size=None,
        board_width=shape.width,
        board_height=shape.height,
        piece_types=piece_types,
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={
            type_id: (no_drops, no_drops)
            for type_id in names
            if type_id != "G"
        },
        metadata={
            "fixture_status": "incomplete_static_fixture",
            "fixture_omissions": list(OMITTED_RULE_SEMANTICS),
        },
    )


def test_incomplete_xiangqi_setup_roundtrips_and_builds_compile_only_carrier():
    rules = _build_incomplete_static_xiangqi_setup_fixture()
    shape = BoardShape(9, 10)
    assert rules.board_shape == shape
    assert len(rules.initial_position) == 10
    assert all(len(row) == 9 for row in rules.initial_position)
    assert sum(piece is not None for row in rules.initial_position for piece in row) == 32

    counts_by_owner = {owner: Counter() for owner in (0, 1)}
    coordinates_by_owner = {owner: {} for owner in (0, 1)}
    for rank, row in enumerate(rules.initial_position):
        for file, piece in enumerate(row):
            if piece is None:
                continue
            counts_by_owner[piece.owner][piece.base_type_id] += 1
            coordinates_by_owner[piece.owner].setdefault(piece.base_type_id, set()).add(
                (file, rank)
            )

    expected_counts = Counter(
        {"G": 1, "A": 2, "E": 2, "R": 2, "H": 2, "C": 2, "P": 5}
    )
    assert counts_by_owner == {0: expected_counts, 1: expected_counts}
    assert coordinates_by_owner[0] == {
        "R": {(0, 0), (8, 0)},
        "H": {(1, 0), (7, 0)},
        "E": {(2, 0), (6, 0)},
        "A": {(3, 0), (5, 0)},
        "G": {(4, 0)},
        "C": {(1, 2), (7, 2)},
        "P": {(0, 3), (2, 3), (4, 3), (6, 3), (8, 3)},
    }
    for owner in (0, 1):
        assert len(coordinates_by_owner[owner]) == 7
        assert sum(counts_by_owner[owner].values()) == 16
    for type_id in expected_counts:
        mirrored = {
            (shape.width - 1 - file, shape.height - 1 - rank)
            for file, rank in coordinates_by_owner[0][type_id]
        }
        assert mirrored == coordinates_by_owner[1][type_id]

    anchor_type_ids = {
        piece_type.type_id
        for piece_type in rules.piece_types
        if piece_type.is_anchor
    }
    anchors = {
        piece.owner: piece
        for row in rules.initial_position
        for piece in row
        if piece is not None and piece.base_type_id in anchor_type_ids
    }
    assert anchor_type_ids == {"G"}
    assert set(anchors) == {0, 1}
    assert anchors[0].base_type_id == anchors[1].base_type_id == "G"
    assert all(not piece_type.movement_atoms for piece_type in rules.piece_types)
    assert not rules.semantic_actions
    assert not rules.promotion_allowed
    assert not rules.promotion_forced
    assert all(not any(mask) for masks in rules.drop_allowed.values() for mask in masks)
    assert tuple(rules.metadata["fixture_omissions"]) == OMITTED_RULE_SEMANTICS

    serialized = serialize_ruleset(rules)
    restored = deserialize_ruleset(serialized)
    assert restored == rules
    assert serialize_ruleset(restored) == serialized
    assert compute_fingerprint(restored) == compute_fingerprint(rules)

    carrier = _compile_geometry_carrier(rules)
    restored_carrier = _compile_geometry_carrier(restored)
    assert carrier.board_shape == shape
    assert carrier.ruleset_fingerprint == compute_fingerprint(rules)
    assert restored_carrier.board_shape == carrier.board_shape
    assert restored_carrier.ruleset_fingerprint == carrier.ruleset_fingerprint
    assert carrier.initial_position.board_width == shape.width
    assert carrier.initial_position.board_height == shape.height
    assert len(carrier.initial_position.board) == shape.area == 90
    assert all(
        not piece_type.movement_atoms for piece_type in carrier.types_by_id.values()
    )
