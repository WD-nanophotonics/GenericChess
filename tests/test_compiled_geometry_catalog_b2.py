import hashlib
import json
from dataclasses import replace

import pytest

from generic_chess.core.coordinates import BoardShape
from generic_chess.core.pieces import Piece
from generic_chess.rules.compiler import (
    _compile_geometry_carrier,
    build_geometry_metadata,
    build_legacy_geometry_catalog,
    compile_ruleset,
    compile_semantic_ruleset,
)
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.validation import RuleValidationError
from generic_chess.rules.western_chess import build_western_chess_ruleset
from rule_semantics_ir_fixtures import cannon_ruleset
from test_rectangular_board_geometry_a import _fixture


def _catalog_hash(compiled):
    geometry, legacy_ids = build_legacy_geometry_catalog(compiled)
    payload = {
        "geometries": {
            gid: {
                "geometry_id": item.geometry_id,
                "kind": item.kind,
                "owner_relative": item.owner_relative,
                "offset": item.offset,
                "direction": item.direction,
                "min_steps": item.min_steps,
                "max_steps": item.max_steps,
                "atom_source": item.atom_source,
                "paths": {
                    owner: {
                        str(source): path
                        for source, path in sorted(per_source.items())
                    }
                    for owner, per_source in sorted(item.paths.items())
                },
            }
            for gid, item in sorted(geometry.items())
        },
        "legacy_ids": sorted(
            (type_id, atom_index, geometry_id)
            for (type_id, atom_index), geometry_id in legacy_ids.items()
        ),
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode()).hexdigest()


def _metadata_hash(compiled):
    serialized = json.dumps(
        build_geometry_metadata(compiled), sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


def test_rectangular_carrier_reuses_canonical_legacy_geometry_catalog():
    carrier = _compile_geometry_carrier(_fixture())
    catalog, legacy_ids = build_legacy_geometry_catalog(carrier)
    metadata = build_geometry_metadata(carrier)

    assert set(carrier.types_by_id) == {"K", "P"}
    assert len(catalog) == 6
    assert set(legacy_ids) == {
        ("K", 0), ("K", 1), ("K", 2), ("K", 3), ("K", 4), ("P", 0),
    }
    for geometry in catalog.values():
        assert set(geometry.paths) == {"0", "1"}
        for per_source in geometry.paths.values():
            assert tuple(sorted(per_source)) == tuple(range(90))

    assert catalog[legacy_ids[("K", 0)]].paths["0"][45] == tuple(range(46, 54))
    assert catalog[legacy_ids[("K", 1)]].paths["0"][4] == tuple(
        13 + 9 * step for step in range(9)
    )
    assert catalog[legacy_ids[("K", 2)]].paths["0"][0] == tuple(
        10 * step for step in range(1, 9)
    )
    assert catalog[legacy_ids[("K", 3)]].paths["0"][0] == (19, 38, 57, 76)
    assert catalog[legacy_ids[("K", 4)]].paths["0"][30] == (41,)
    assert catalog[legacy_ids[("K", 4)]].paths["1"][30] == (19,)
    assert catalog[legacy_ids[("P", 0)]].paths["0"][30] == (31,)
    assert catalog[legacy_ids[("P", 0)]].paths["1"][30] == (29,)

    assert metadata["schema"] == "geometry_v1"
    assert metadata["squares"] == 90
    assert len(metadata["types"]["K"]["ray_paths"]["0"]) == 90
    assert metadata["types"]["K"]["ray_paths"]["0"][45][0] == list(range(46, 54))
    assert metadata["types"]["K"]["leap_targets"]["1"][30][4] == [19]


@pytest.mark.parametrize(
    "builder,catalog_sha,metadata_sha",
    (
        (
            build_western_chess_ruleset,
            "38fd369812d4ed42064afb09745cba1ef41ff847bfce86fcfc3430b9d4807422",
            "864feda0a5e7a3028aa693417afc08c280458491b10f441cc4c6294feb471c6e",
        ),
        (
            build_standard_shogi_ruleset,
            "0fddaaec1e37a47bfb5fb8c8346c0e10e10ece5024881916df7c9033ea934175",
            "26cea9229cb779089d3ae6ba7d073ad79be19a77f909308447ad8eda24bd0932",
        ),
    ),
)
def test_square_geometry_catalog_and_metadata_match_frozen_hashes(
    builder, catalog_sha, metadata_sha,
):
    compiled = compile_ruleset(builder(), allow_semantic_actions=True)
    assert _catalog_hash(compiled) == catalog_sha
    assert _metadata_hash(compiled) == metadata_sha


def test_public_compilers_still_reject_rectangular_semantic_execution():
    rules = cannon_ruleset()
    shape = BoardShape(9, 10)
    rows = [[None] * shape.width for _ in range(shape.height)]
    rows[0][0] = Piece(0, "K", "K")
    rows[9][8] = Piece(1, "K", "K")
    rectangular = replace(
        rules,
        board_size=None,
        board_width=shape.width,
        board_height=shape.height,
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"C": ((False,) * shape.area, (False,) * shape.area)},
    )
    with pytest.raises(RuleValidationError, match="RECTANGULAR_EXECUTION_NOT_IN_A_STAGE"):
        compile_ruleset(rectangular, allow_semantic_actions=True)
    with pytest.raises(RuleValidationError, match="RECTANGULAR_EXECUTION_NOT_IN_A_STAGE"):
        compile_semantic_ruleset(rectangular)
