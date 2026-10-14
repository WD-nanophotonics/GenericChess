"""The diagnostic estimate must count target data rather than square source rows.

These are metadata-only compiled-IR variations, never gameplay inputs.
"""
from dataclasses import replace

from generic_chess.native.compiler import build_semantic_compile_payload
from generic_chess.rules.compiler import compile_semantic_ruleset
from rule_semantics_ir_fixtures import castling_ruleset


def estimate_for_paths(paths):
    compiled = compile_semantic_ruleset(castling_ruleset())
    geometries = dict(compiled.ir.geometry)
    key = next(iter(geometries))
    geometries[key] = replace(geometries[key], paths={"0": paths, "1": {}})
    compiled = replace(compiled, ir=replace(compiled.ir, geometry=geometries))
    payload, report = build_semantic_compile_payload(compiled)
    return payload, report.estimated_bytes


def test_an_extra_uint16_target_increases_the_estimate_by_two_bytes():
    _, short = estimate_for_paths({0: (1,)})
    _, long = estimate_for_paths({0: (1, 2)})
    assert long - short == 2


def test_independent_source_records_add_linearly_in_the_estimate():
    _, empty = estimate_for_paths({})
    _, first = estimate_for_paths({0: (1,)})
    _, second = estimate_for_paths({2: (3,)})
    _, both = estimate_for_paths({0: (1,), 2: (3,)})
    assert both - empty == (first - empty) + (second - empty)
