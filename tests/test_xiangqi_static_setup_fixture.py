"""Incomplete, test-only Xiangqi geometry fixture; not a playable RuleSet.

Initial placement follows the World Xiangqi Federation's introductory board
diagram. Movement atoms provide only a candidate-geometry upper bound. See
fixture metadata for legality and game-rule consequences deliberately omitted.
"""

from collections import Counter

from generic_chess.core.coordinates import BoardShape
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.compiler import (
    _compile_geometry_carrier,
    build_legacy_geometry_catalog,
    compile_ruleset,
)
from generic_chess.rules.schema import RuleSet, compute_fingerprint
from generic_chess.rules.serialization import deserialize_ruleset, serialize_ruleset
from generic_chess.rules.validation import RuleValidationError


OMITTED_RULE_SEMANTICS = (
    "capture-target semantics and legal-action conditions",
    "palace confinement for general and advisors",
    "elephant river restriction",
    "horse-leg blockers",
    "elephant-eye blockers",
    "cannon legality/execution beyond compile-only path diagnostics",
    "soldier lateral movement after crossing the river",
    "facing-generals prohibition and check legality",
    "stalemate, repetition, and perpetual-check/chase adjudication",
)

ORTHOGONAL = ((1, 0), (-1, 0), (0, 1), (0, -1))
DIAGONAL = ((1, 1), (1, -1), (-1, 1), (-1, -1))
HORSE_OFFSETS = (
    (2, 1), (2, -1), (-2, 1), (-2, -1),
    (1, 2), (1, -2), (-1, 2), (-1, -2),
)
MOVEMENT_ATOMS = {
    "G": tuple(LeapAtom(offset) for offset in ORTHOGONAL),
    "A": tuple(LeapAtom(offset) for offset in DIAGONAL),
    "E": tuple(LeapAtom((2 * df, 2 * dr)) for df, dr in DIAGONAL),
    "R": tuple(RayAtom(direction) for direction in ORTHOGONAL),
    "H": tuple(LeapAtom(offset) for offset in HORSE_OFFSETS),
    "C": tuple(RayAtom(direction) for direction in ORTHOGONAL),
    "P": (LeapAtom((0, 1)),),
}


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
        PieceType(
            type_id,
            name,
            MOVEMENT_ATOMS[type_id],
            is_anchor=(type_id == "G"),
        )
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
        capture_disposition="remove_from_game",
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
    assert {
        piece_type.type_id: len(piece_type.movement_atoms)
        for piece_type in rules.piece_types
    } == {"G": 4, "A": 4, "E": 4, "R": 4, "H": 8, "C": 4, "P": 1}
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
    assert {
        type_id: len(piece_type.movement_atoms)
        for type_id, piece_type in carrier.types_by_id.items()
    } == {"G": 4, "A": 4, "E": 4, "R": 4, "H": 8, "C": 4, "P": 1}

    # Candidate geometry is inspectable, but public executable compilation
    # must continue to reject rectangular boards before execution.
    try:
        compile_ruleset(rules)
    except RuleValidationError as exc:
        assert "RECTANGULAR_EXECUTION_NOT_IN_A_STAGE" in {
            issue.code for issue in exc.issues
        }
    else:
        raise AssertionError("public compiler unexpectedly accepted a 9x10 board")


def test_xiangqi_candidate_geometry_catalog_is_lossless_on_9x10():
    rules = _build_incomplete_static_xiangqi_setup_fixture()
    carrier = _compile_geometry_carrier(rules)
    geometry, legacy_ids = build_legacy_geometry_catalog(carrier)
    shape = BoardShape(9, 10)

    assert len(geometry) == sum(map(len, MOVEMENT_ATOMS.values())) == 29
    assert set(legacy_ids) == {
        (type_id, atom_index)
        for type_id, atoms in MOVEMENT_ATOMS.items()
        for atom_index in range(len(atoms))
    }
    by_type = {
        type_id: tuple(
            geometry[legacy_ids[(type_id, atom_index)]]
            for atom_index in range(len(atoms))
        )
        for type_id, atoms in MOVEMENT_ATOMS.items()
    }
    for type_id, atoms in MOVEMENT_ATOMS.items():
        assert tuple(item.atom_source for item in by_type[type_id]) == tuple(
            (type_id, atom_index) for atom_index in range(len(atoms))
        )
        for item, atom in zip(by_type[type_id], atoms):
            assert item.kind == ("ray" if isinstance(atom, RayAtom) else "leap")
            assert item.owner_relative is True
            assert set(item.paths) == {"0", "1"}
            for owner in ("0", "1"):
                assert set(item.paths[owner]) == set(range(shape.area))
                assert all(
                    0 <= target < shape.area
                    for path in item.paths[owner].values()
                    for target in path
                )

    def targets(type_id: str, owner: int, source: int) -> set[int]:
        return {
            target
            for item in by_type[type_id]
            for target in item.paths[str(owner)][source]
        }

    def index(file: int, rank: int) -> int:
        return rank * shape.width + file

    # Compare every owner/source/atom entry against the primitive's exact
    # coordinate rule, not just representative unions.
    for type_id, atoms in MOVEMENT_ATOMS.items():
        for atom_index, atom in enumerate(atoms):
            item = by_type[type_id][atom_index]
            raw_df, raw_dr = (
                atom.direction if isinstance(atom, RayAtom) else atom.offset
            )
            for owner in (0, 1):
                df, dr = (raw_df, raw_dr) if owner == 0 else (-raw_df, -raw_dr)
                for rank in range(shape.height):
                    for file in range(shape.width):
                        path = []
                        next_file, next_rank = file + df, rank + dr
                        while (
                            0 <= next_file < shape.width
                            and 0 <= next_rank < shape.height
                            and (
                                not isinstance(atom, RayAtom)
                                or atom.max_steps is None
                                or len(path) < atom.max_steps
                            )
                        ):
                            path.append(index(next_file, next_rank))
                            if not isinstance(atom, RayAtom):
                                break
                            next_file += df
                            next_rank += dr
                        assert item.paths[str(owner)][index(file, rank)] == tuple(path)

    center = index(4, 4)
    symmetric_center_targets = {
        "G": {index(4, 3), index(4, 5), index(3, 4), index(5, 4)},
        "A": {index(3, 3), index(3, 5), index(5, 3), index(5, 5)},
        "E": {index(2, 2), index(2, 6), index(6, 2), index(6, 6)},
        "R": {
            *(index(file, 4) for file in range(9) if file != 4),
            *(index(4, rank) for rank in range(10) if rank != 4),
        },
        "C": {
            *(index(file, 4) for file in range(9) if file != 4),
            *(index(4, rank) for rank in range(10) if rank != 4),
        },
        "H": {
            index(6, 5), index(6, 3), index(2, 5), index(2, 3),
            index(5, 6), index(5, 2), index(3, 6), index(3, 2),
        },
    }
    for type_id, expected in symmetric_center_targets.items():
        assert targets(type_id, 0, center) == expected
        assert targets(type_id, 1, center) == expected

    assert targets("P", 0, center) == {index(4, 5)}
    assert targets("P", 1, center) == {index(4, 3)}

    corner = index(0, 0)
    assert targets("G", 0, corner) == targets("G", 1, corner) == {
        index(1, 0), index(0, 1)
    }
    assert targets("A", 0, corner) == targets("A", 1, corner) == {index(1, 1)}
    assert targets("E", 0, corner) == targets("E", 1, corner) == {index(2, 2)}
    assert targets("H", 0, corner) == targets("H", 1, corner) == {
        index(2, 1), index(1, 2)
    }
    edge_ray_targets = {
        *(index(file, 0) for file in range(1, 9)),
        *(index(0, rank) for rank in range(1, 10)),
    }
    for type_id in ("R", "C"):
        assert targets(type_id, 0, corner) == edge_ray_targets
        assert targets(type_id, 1, corner) == edge_ray_targets

    assert targets("P", 0, index(4, 0)) == {index(4, 1)}
    assert targets("P", 1, index(4, 9)) == {index(4, 8)}
