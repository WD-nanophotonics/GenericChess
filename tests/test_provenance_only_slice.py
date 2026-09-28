from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import sys

from generic_chess.rules.compiler import compile_semantic_ruleset
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_static_semantic_material_prior_v2d import _synthetic_capture
from experiments.provenance_only_slice import (
    build_binding,
    canonical_bytes,
    digest,
    run_synthetic_fixture,
    verify_sidecar,
)


def _run():
    # Identical semantic descriptions deliberately exercise witness union over
    # one canonical occupancy cube without doubling its numeric probability.
    rules = _synthetic_capture(relations=("enemy", "enemy"), shapes=((1, 0), (1, 0)))
    compiled = compile_semantic_ruleset(rules)
    return run_synthetic_fixture(rules, compiled, "X")


def test_numeric_invariance_and_actual_synthetic_producer_parity():
    run = _run()
    assert run.numeric_bytes_off == run.numeric_bytes_on
    assert canonical_bytes(run.numeric_artifact) == run.numeric_bytes_on
    assert run.u_schema_off == run.u_schema_on
    assert run.c_schema_off == run.c_schema_on
    u_mean = sum((Fraction(value) for owner in ("0", "1")
                  for value in run.numeric_artifact["u_by_owner_source"][owner]), Fraction(0)) / (
                      2 * len(run.numeric_artifact["u_by_owner_source"]["0"]))
    c_mean = sum((Fraction(value) for owner in ("0", "1")
                  for value in run.numeric_artifact["c_by_owner_source"][owner]), Fraction(0)) / (
                      2 * len(run.numeric_artifact["c_by_owner_source"]["0"]))
    assert Fraction(run.numeric_artifact["synthetic_retained_output"]["b"]) == u_mean + c_mean


def test_edge_completeness_and_duplicate_cube_witness_union():
    run = _run()
    assert verify_sidecar(run.sidecar, run.sidecar["binding"], run.compiled)
    for component in ("u", "c"):
        rows = run.sidecar["events"][component]
        assert rows
        assert all(row["identity"]["ruleset_fingerprint"] == run.compiled.ruleset_fingerprint
                   for row in rows)
        assert all(row["event_id"] == digest(row["identity"]) for row in rows)
        assert all(set(row["identity"]) == {
            "schema_version", "ruleset_fingerprint", "compiled_pattern_ordinal",
            "compiled_geometry_ordinal", "actor_type_ordinal", "local_event",
        } for row in rows)
        assert all("X" not in canonical_bytes(row["identity"]).decode("utf-8") for row in rows)

    for component in ("u", "c"):
        enumeration = run.sidecar["numeric_enumeration"][component]
        duplicate_group = next((group_id for group_id, row in enumeration.items()
                                if row["contributor_count"] > row["unique_cube_count"]), None)
        assert duplicate_group is not None, component
        cube_ids = [row["cube_id"] for row in run.sidecar["events"][component]
                    if row["group_id"] == duplicate_group]
        assert len(cube_ids) > len(set(cube_ids)), component


def test_omitted_real_contributor_edge_fails_closed():
    run = _run()
    tampered = deepcopy(run.sidecar)
    tampered["events"]["c"].pop()
    assert not verify_sidecar(tampered, run.sidecar["binding"], run.compiled)


def test_stale_source_formula_ruleset_and_numeric_bindings_fail_closed():
    run = _run()
    for field in ("source_bundle_sha256", "formula_identity", "ruleset_fingerprint"):
        stale = dict(run.sidecar["binding"])
        stale[field] = "stale-" + stale[field]
        assert not verify_sidecar(run.sidecar, stale, run.compiled), field
    changed_artifact = deepcopy(run.numeric_artifact)
    changed_artifact["u_by_owner_source"]["0"][0] = "999/1"
    stale_numeric_binding = build_binding(run.compiled, changed_artifact)
    assert stale_numeric_binding["numeric_artifact_sha256"] != run.sidecar["binding"]["numeric_artifact_sha256"]
    assert not verify_sidecar(run.sidecar, stale_numeric_binding, run.compiled)


def test_dependency_graph_reaches_synthetic_retained_output():
    run = _run()
    edges = run.sidecar["dependency_edges"]
    assert edges
    b_inputs = [edge for edge in edges if edge["to"] == "synthetic:retained-output:b"]
    assert {edge["from"] for edge in b_inputs} == {
        "synthetic:retained-output:u", "synthetic:retained-output:c"}
    area = len(run.numeric_artifact["b_by_owner_source"]["0"])
    for owner in (0, 1):
        for source in range(area):
            b_node = f"b:owner={owner}:source={source}"
            assert {edge["from"] for edge in edges if edge["to"] == b_node} == {
                f"u:owner={owner}:source={source}", f"c:owner={owner}:source={source}"
            }
    assert any(edge["from"] == "u:retained-normalized-mean"
               and edge["to"] == "synthetic:retained-output:u" for edge in edges)
    assert any(edge["from"] == "c:retained-normalized-mean"
               and edge["to"] == "synthetic:retained-output:c" for edge in edges)
    for component in ("u", "c"):
        assert any(edge["to"].startswith(component + ":") for edge in edges)
