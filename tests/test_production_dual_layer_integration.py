from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from generic_chess.core.pieces import Piece, PieceType
from generic_chess.rules.compiler import compile_semantic_ruleset
from experiments.dual_layer_coverage_certificate import CertificateError, ruleset_coverage_complete
from experiments.production_dual_layer_integration import (
    OUTPUT_ID,
    build_integration_context,
    collect_real_producer_evidence,
    issue_integration_certificate,
    verify_integration_certificate,
)
from test_static_semantic_material_prior_v2c import _synthetic_with_optional_tokens


def _compiled_two_actor_fixture():
    rules = _synthetic_with_optional_tokens()
    board = [list(row) for row in rules.initial_position]
    board[2][3] = Piece(0, "Y", "Y", False)
    board[5][4] = Piece(1, "Y", "Y", False)
    actions = list(rules.semantic_actions)
    for index, action in enumerate(rules.semantic_actions):
        actions.append(replace(action, name=f"duplicate-label-{index}", type_ids=("Y",)))
    drop_allowed = dict(rules.drop_allowed)
    drop_allowed["Y"] = drop_allowed["X"]
    rules = replace(
        rules,
        piece_types=rules.piece_types + (PieceType("Y", "Y", ()),),
        semantic_actions=tuple(actions),
        initial_position=tuple(tuple(row) for row in board),
        drop_allowed=drop_allowed,
    )
    return compile_semantic_ruleset(rules)


@pytest.fixture(scope="module")
def fixture_data():
    compiled = _compiled_two_actor_fixture()
    type_ordinals = {type_id: index for index, type_id in enumerate(compiled.support.type_metadata)}
    candidate_ordinals = [index for index, metadata in enumerate(compiled.support.type_metadata.values())
                          if not metadata.is_anchor]
    support = {
        str(actor): {str(owner): list(range(compiled.support.board_size ** 2)) for owner in (0, 1)}
        for actor in candidate_ordinals
    }
    payload = collect_real_producer_evidence(compiled, ("X", "Y"))
    return compiled, type_ordinals, candidate_ordinals, support, payload


def _contexts(fixture_data):
    compiled, ordinals, candidates, support, payload = fixture_data
    unsupported_actor = ordinals["X"]
    retained_actor = ordinals["Y"]
    excluded = build_integration_context(
        compiled, payload,
        unsupported_actor=unsupported_actor,
        retained_type_ordinals=[retained_actor],
        candidate_type_ordinals=candidates,
        support=support,
    )
    retained = build_integration_context(
        compiled, payload,
        unsupported_actor=unsupported_actor,
        retained_type_ordinals=[unsupported_actor, retained_actor],
        candidate_type_ordinals=candidates,
        support=support,
    )
    return excluded, retained


def test_real_provenance_drives_paired_identifiability_without_waiving_coverage(fixture_data):
    compiled, ordinals, _candidates, _support, payload = fixture_data
    excluded, retained = _contexts(fixture_data)
    excluded_cert = issue_integration_certificate(excluded, compiled)
    retained_cert = issue_integration_certificate(retained, compiled)

    assert excluded_cert["PROVENANCE_GRAPH_COMPLETE"] is True
    assert retained_cert["PROVENANCE_GRAPH_COMPLETE"] is True
    assert excluded_cert["ruleset_coverage_complete"] is False
    assert retained_cert["ruleset_coverage_complete"] is False
    assert ruleset_coverage_complete(excluded["base_context"]) is False
    assert ruleset_coverage_complete(retained["base_context"]) is False
    assert excluded_cert["requested_output_identifiable"] is True
    assert retained_cert["requested_output_identifiable"] is False
    assert excluded["base_context"]["ledger"] == retained["base_context"]["ledger"]
    assert excluded["base_context"]["ledger"][0]["predicate_shape"] == (
        retained["base_context"]["ledger"][0]["predicate_shape"]
    )
    assert excluded["base_context"]["output_spec"]["output_id"] == OUTPUT_ID
    assert excluded["base_context"]["reference_accessed"] is False
    assert verify_integration_certificate(excluded, excluded_cert, compiled)
    assert verify_integration_certificate(retained, retained_cert, compiled)
    assert payload["off_on_digests"]
    assert all(row["off_sha256"] == row["on_sha256"]
               for row in payload["off_on_digests"].values())
    assert ordinals["X"] in excluded["domain_metadata"]["candidate_type_ordinals"]


def test_graph_identifiers_do_not_expose_game_or_type_labels(fixture_data):
    compiled, _ordinals, _candidates, _support, _payload = fixture_data
    excluded, _retained = _contexts(fixture_data)
    graph = excluded["base_context"]["graph"]
    assert all(not any(label in node for label in ("X", "Y", "K")) for node in graph["nodes"])
    assert all(not any(label in " ".join(edge) for label in ("X", "Y", "K"))
               for edge in graph["edges"])
    assert compiled.ruleset_fingerprint == excluded["integration_binding"]["ruleset_fingerprint"]


def test_cross_type_mutation_invalidates_old_proof_and_removes_zero_path(fixture_data):
    compiled, ordinals, _candidates, _support, payload = fixture_data
    excluded, _retained = _contexts(fixture_data)
    old_certificate = issue_integration_certificate(excluded, compiled)
    changed = build_integration_context(
        compiled, payload,
        unsupported_actor=ordinals["X"],
        retained_type_ordinals=[ordinals["Y"]],
        candidate_type_ordinals=fixture_data[2],
        support=fixture_data[3],
        cross_type_edges=[[ordinals["X"], ordinals["Y"]]],
    )
    assert not verify_integration_certificate(changed, old_certificate, compiled)
    mutated_certificate = issue_integration_certificate(changed, compiled)
    assert mutated_certificate["requested_output_identifiable"] is False


def test_missing_provenance_contributor_or_downstream_edge_fails_closed(fixture_data):
    compiled, ordinals, candidates, support, payload = fixture_data
    excluded, _retained = _contexts(fixture_data)
    certificate = issue_integration_certificate(excluded, compiled)

    missing_event = deepcopy(excluded)
    missing_event["producer_payload"]["events"]["u"].pop()
    assert not verify_integration_certificate(missing_event, certificate, compiled)
    with pytest.raises(CertificateError):
        issue_integration_certificate(missing_event, compiled)

    missing_edge = deepcopy(excluded)
    missing_edge["base_context"]["graph"]["edges"].pop()
    assert not verify_integration_certificate(missing_edge, certificate, compiled)
    with pytest.raises(CertificateError):
        issue_integration_certificate(missing_edge, compiled)


def test_all_bound_identities_invalidate_the_old_certificate(fixture_data):
    compiled, ordinals, candidates, support, payload = fixture_data
    excluded, _retained = _contexts(fixture_data)
    certificate = issue_integration_certificate(excluded, compiled)
    binding_fields = (
        "provenance_schema_version", "ruleset_fingerprint", "board_domain",
        "unsupported_ledger_sha256",
        "producer_formula_source_sha256", "formula_identity", "numeric_artifact_sha256",
        "requested_output_identity", "retained_domain_sha256",
        "normalization_aggregation_identity", "graph_sha256",
    )
    for field in binding_fields:
        stale = deepcopy(excluded)
        stale["integration_binding"][field] = f"stale:{field}"
        assert not verify_integration_certificate(stale, certificate, compiled), field

    changed_domain = build_integration_context(
        compiled, payload, unsupported_actor=ordinals["X"],
        retained_type_ordinals=[ordinals["X"], ordinals["Y"]],
        candidate_type_ordinals=candidates, support=support,
    )
    assert not verify_integration_certificate(changed_domain, certificate, compiled)
