from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

from generic_chess.core.pieces import Piece
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import RuleSquareRef
from scripts import audit_static_material_domain_conditional_capability as capability
from scripts import audit_static_material_domain_fragmentation as topology_source
from scripts import audit_static_material_v2h_rule_support_source_prior as v2h
from scripts import audit_static_material_v2f_lifetime_reachability as v2f
from scripts import audit_static_semantic_material_prior_v2c as v2c
from scripts import audit_static_semantic_material_prior_v2d as v2d
from tests.test_static_semantic_material_prior_v2a import _synthetic
from experiments.provenance_only_slice import run_synthetic_fixture, verify_sidecar


def _shape_rules(width: int, height: int):
    rules, _compiled = _synthetic(relations=("enemy",), shapes=((1, 0),))
    source_rows = [list(row) for row in rules.initial_position]
    rows = [[None for _ in range(width)] for _ in range(height)]
    for rank, row in enumerate(source_rows):
        for file, piece in enumerate(row):
            rows[rank][file] = piece
    rows[2][2] = Piece(0, "X", "X", False)
    rows[5][5] = Piece(1, "X", "X", False)
    area = width * height
    return replace(
        rules,
        board_size=width if width == height else None,
        board_width=None if width == height else width,
        board_height=None if width == height else height,
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"X": ((False,) * area, (False,) * area)},
    )


def test_synthetic_rectangular_compiled_producer_topology_and_v2h_path():
    compiled = compile_semantic_ruleset(_shape_rules(9, 10))
    shape = compiled.support.board_shape
    assert (shape.width, shape.height, shape.area) == (9, 10, 90)
    assert compiled.support.board_size is None

    token_ledger = v2c._token_state_ledger(compiled)
    assert token_ledger["complete"]
    measure = v2c._event_measure_factory(token_ledger, compiled, "X")
    sink_run = run_synthetic_fixture(_shape_rules(9, 10), compiled, "X")
    assert sink_run.numeric_bytes_off == sink_run.numeric_bytes_on
    assert verify_sidecar(sink_run.sidecar, sink_run.sidecar["binding"], compiled)
    assert sink_run.sidecar["board_domain"] == {
        "board_width": 9,
        "board_height": 10,
        "board_area": 90,
        "index_convention": "rank-major: rank * width + file",
    }

    u = capability._source_u_by_square(compiled, "X", token_ledger)
    c = v2d._capture_rows(compiled, "X", measure)
    c_by_source = capability._source_c_by_square(c, shape.area)["c_by_owner_source"]
    assert all(len(u["u_by_owner_source"][str(owner)]) == 90 for owner in (0, 1))
    assert all(len(c_by_source[str(owner)]) == 90 for owner in (0, 1))
    domain = capability._domain_table(
        shape.area,
        [Fraction(1, 3)] * shape.area,
        [Fraction(1, 6)] * shape.area,
        [list(range(45)), list(range(45, shape.area))],
    )
    assert domain["domain_size_weighted_u_bar_exact"] == "1/3"
    assert domain["domain_size_weighted_c_bar_exact"] == "1/6"
    assert domain["domain_size_weighted_b_bar_exact"] == "1/2"

    # Existing Core semantics define owner-relative squares as 180-degree
    # rotation on BoardShape; fixed refs use width for file and height for rank.
    fixed = RuleSquareRef(kind="fixed", square=(2, 1), owner_relative=True)
    assert v2d.resolve_removed_square(fixed, owner=0, source=0, target=1,
                                      path=(), board_shape=shape) == 11
    assert v2d.resolve_removed_square(fixed, owner=1, source=0, target=1,
                                      path=(), board_shape=shape) == 78

    topology = topology_source._type_topology(compiled, "X", token_ledger)
    supports = {}
    for owner in (0, 1):
        graph, _transition_data = v2f.build_augmented_graph(
            shape.area, ["X"], {"X": topology}, owner)
        support_by_type, _evidence = v2h._support_by_type(
            compiled, ["X"], {"X": topology}, owner)
        supports[str(owner)] = support_by_type["X"]
        assert support_by_type["X"]
        assert all(0 <= square < shape.area for square in support_by_type["X"])
        assert all(len(v2f.summarize_source(graph, "X", source, shape.area)[
                       "reachable_board_squares"]) > 0 for source in range(shape.area))
        for source in range(shape.area):
            summary = v2f.summarize_source(graph, "X", source, shape.area)
            assert Fraction(summary["q_exact"]) == Fraction(
                summary["reachable_board_square_count"], shape.area)

    u_mean = sum((v2h._conditional_mean(u["u_by_owner_source"][owner], supports[owner])
                  for owner in ("0", "1")), Fraction(0)) / 2
    c_mean = sum((v2h._conditional_mean(c_by_source[owner], supports[owner])
                  for owner in ("0", "1")), Fraction(0)) / 2
    b_by_source = {
        owner: [u["u_by_owner_source"][owner][square] + c_by_source[owner][square]
                for square in range(shape.area)]
        for owner in ("0", "1")
    }
    b_mean = sum((v2h._conditional_mean(b_by_source[owner], supports[owner])
                  for owner in ("0", "1")), Fraction(0)) / 2
    assert b_mean == u_mean + c_mean


def test_square_carrier_reproduces_source_producer_numeric_bytes_and_events():
    for n in (8, 9):
        rules = _shape_rules(n, n)
        compiled = compile_semantic_ruleset(rules)
        run = run_synthetic_fixture(rules, compiled, "X")
        assert compiled.support.board_shape.area == n * n
        assert run.numeric_bytes_off == run.numeric_bytes_on
        assert verify_sidecar(run.sidecar, run.sidecar["binding"], compiled)
        assert all(event["identity"]["board_width"] == n
                   and event["identity"]["board_height"] == n
                   for component in ("u", "c") for event in run.sidecar["events"][component])
