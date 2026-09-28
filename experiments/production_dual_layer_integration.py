"""Synthetic integration of real u/c producer lineage into a dual-layer cert."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

from experiments.dual_layer_coverage_certificate import (
    CertificateError,
    issue_certificate,
    verify_certificate,
)
from experiments.provenance_only_slice import (
    ROOT,
    SCHEMA_VERSION,
    ProvenanceSink,
    _board_domain,
    _claims,
    _numeric_canonical,
    canonical_bytes,
    digest,
    file_digest,
    verify_component,
)


PREDICATE_SHAPE = "typed-relational-current-actor-event-count-equals-one"
OUTPUT_ID = "synthetic-retained-type-vector-v1"
FORMULA_ID = "source-support-u-plus-c-owner-mean-v1"


def collect_real_producer_evidence(compiled: Any, type_ids: tuple[str, ...]) -> dict[str, Any]:
    """Run only source-local producer helpers on the provided synthetic IR."""
    from scripts import audit_static_material_domain_conditional_capability as capability
    from scripts import audit_static_semantic_material_prior_v2c as v2c
    from scripts import audit_static_semantic_material_prior_v2d as v2d

    token_ledger = v2c._token_state_ledger(compiled)
    sink = ProvenanceSink()
    numeric_by_actor: dict[str, dict[str, Any]] = {}
    off_on_digests = {}
    for type_id in type_ids:
        actor_ordinal = tuple(compiled.support.type_metadata).index(type_id)
        measure = v2c._event_measure_factory(token_ledger, compiled, type_id)
        u_off = capability._source_u_by_square(compiled, type_id, token_ledger)
        c_off = v2d._capture_rows(compiled, type_id, measure)
        u_on = capability._source_u_by_square(compiled, type_id, token_ledger,
                                              provenance_sink=sink)
        c_on = v2d._capture_rows(compiled, type_id, measure, provenance_sink=sink)
        area = compiled.support.board_area
        numeric_off = _numeric_canonical(u_off, c_off, area)
        numeric_on = _numeric_canonical(u_on, c_on, area)
        off_bytes, on_bytes = canonical_bytes(numeric_off), canonical_bytes(numeric_on)
        if off_bytes != on_bytes:
            raise CertificateError("producer provenance hook changed synthetic numeric bytes")
        if tuple(sorted(u_off)) != tuple(sorted(u_on)) or tuple(sorted(c_off)) != tuple(sorted(c_on)):
            raise CertificateError("producer provenance hook changed output schema")
        numeric_by_actor[str(actor_ordinal)] = numeric_on
        off_on_digests[str(actor_ordinal)] = {
            "off_sha256": hashlib.sha256(off_bytes).hexdigest(),
            "on_sha256": hashlib.sha256(on_bytes).hexdigest(),
        }

    event_rows = {component: list(sink.events[component]) for component in ("u", "c")}
    claims = {}
    enumeration = {}
    for component in ("u", "c"):
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in event_rows[component]:
            grouped[row["group_id"]].append(row)
        claims[component] = _claims(grouped)
        enumeration[component] = {
            group_id: {
                "group_ordinal": row["group_ordinal"],
                "group_key": row["group_key"],
                "contributor_count": len(row["cube_ids"]),
                "cube_witness_digest": digest(sorted(row["cube_ids"])),
                "unique_cube_count": len(set(row["cube_ids"])),
            }
            for group_id, row in sink.numeric_enumeration[component].items()
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "board_domain": _board_domain(compiled),
        "events": event_rows,
        "numeric_enumeration": enumeration,
        "aggregate_claims": claims,
        "numeric_artifact": numeric_by_actor,
        "off_on_digests": off_on_digests,
        "reference_accessed": False,
    }


def _producer_payload_complete(compiled: Any, payload: dict[str, Any]) -> bool:
    if (payload.get("schema_version") != SCHEMA_VERSION
            or payload.get("ruleset_fingerprint") != compiled.ruleset_fingerprint
            or payload.get("board_domain") != _board_domain(compiled)
            or payload.get("reference_accessed") is not False):
        return False
    return all(verify_component(payload, component, compiled) for component in ("u", "c"))


def _source_bundle_sha256() -> str:
    from scripts import audit_static_material_domain_conditional_capability as capability
    from scripts import audit_static_material_v2h_rule_support_source_prior as v2h
    from scripts import audit_static_semantic_material_prior_v2a as v2a
    from scripts import audit_static_semantic_material_prior_v2c as v2c
    from scripts import audit_static_semantic_material_prior_v2d as v2d

    paths = (Path(__file__), Path(capability.__file__), Path(v2h.__file__), Path(v2a.__file__),
             Path(v2c.__file__), Path(v2d.__file__))
    return digest([(str(path.relative_to(ROOT)), file_digest(path)) for path in paths])


def _graph_from_frozen_provenance(compiled: Any, payload: dict[str, Any],
                                  domain: dict[str, Any], support: dict[str, Any],
                                  ledger: list[dict[str, Any]],
                                  cross_type_edges: list[list[int]]) -> dict[str, Any]:
    nodes: set[str] = {"output:retained-vector"}
    edges: set[tuple[str, str]] = set()
    numeric = payload["numeric_artifact"]
    actor_ordinals = {int(key) for key in numeric}

    def edge(source: str, target: str) -> None:
        nodes.update((source, target))
        edges.add((source, target))

    # Actual producer events and group IDs provide the upstream graph.
    for component in ("u", "c"):
        for row in payload["events"][component]:
            actor = row["identity"]["actor_type_ordinal"]
            owner, source = row["group_key"][:2]
            event_node = f"event:{row['event_id']}"
            group_node = f"group:{component}:{row['group_id']}"
            source_node = f"{component}:actor={actor}:owner={owner}:source={source}"
            edge(event_node, group_node)
            edge(group_node, source_node)

    # Frozen synthetic downstream contract: full listed support, owner means,
    # u/c components, b addition, then the metadata-selected retained vector.
    for actor in sorted(actor_ordinals):
        if str(actor) not in support:
            raise CertificateError("frozen support is missing a producer actor")
        for owner in (0, 1):
            support_squares = set(support[str(actor)][str(owner)])
            area = len(numeric[str(actor)]["u_by_owner_source"][str(owner)])
            if any(square < 0 or square >= area for square in support_squares):
                raise CertificateError("support square is outside the numeric source domain")
            for source in range(area):
                u_node = f"u:actor={actor}:owner={owner}:source={source}"
                c_node = f"c:actor={actor}:owner={owner}:source={source}"
                b_node = f"b:actor={actor}:owner={owner}:source={source}"
                nodes.update((u_node, c_node, b_node))
                edge(u_node, b_node)
                edge(c_node, b_node)
                if source in support_squares:
                    edge(u_node, f"u:actor={actor}:owner-normalized={owner}")
                    edge(c_node, f"c:actor={actor}:owner-normalized={owner}")
            edge(f"u:actor={actor}:owner-normalized={owner}",
                 f"u:actor={actor}:retained-normalized-mean")
            edge(f"c:actor={actor}:owner-normalized={owner}",
                 f"c:actor={actor}:retained-normalized-mean")
        edge(f"u:actor={actor}:retained-normalized-mean", f"type-output:actor={actor}:u")
        edge(f"c:actor={actor}:retained-normalized-mean", f"type-output:actor={actor}:c")
        edge(f"type-output:actor={actor}:u", f"type-output:actor={actor}:b")
        edge(f"type-output:actor={actor}:c", f"type-output:actor={actor}:b")
        if actor in domain["retained_type_ordinals"]:
            edge(f"type-output:actor={actor}:b", "output:retained-vector")

    # Unsupported semantics conservatively enter only their compiled actor's
    # real source component nodes. The retained-domain filter is a separate
    # frozen downstream edge, not an anchor/type-name exception.
    for row in ledger:
        actor = row["actor_type_ordinal"]
        if actor not in actor_ordinals:
            raise CertificateError("unsupported actor has no real producer provenance")
        variable = row["variable_id"]
        for component in ("u", "c"):
            area = len(numeric[str(actor)][f"{component}_by_owner_source"]["0"])
            for owner in (0, 1):
                for source in range(area):
                    edge(variable,
                         f"{component}:actor={actor}:owner={owner}:source={source}")

    for source_actor, target_actor in cross_type_edges:
        if source_actor not in actor_ordinals or target_actor not in actor_ordinals:
            raise CertificateError("cross-type mutation references a missing producer actor")
        edge(f"u:actor={source_actor}:owner=0:source=0",
             f"u:actor={target_actor}:owner=0:source=0")

    graph_nodes = sorted(nodes)
    graph_edges = [list(pair) for pair in sorted(edges)]
    return {"nodes": graph_nodes, "edges": graph_edges}


def _build_ledger(compiled: Any, actor_ordinal: int) -> list[dict[str, Any]]:
    variable = "unsupported:" + digest(["unsupported-variable-v1", compiled.ruleset_fingerprint,
                                         actor_ordinal, PREDICATE_SHAPE])
    return [{
        "row_id": digest(["ledger-row-v1", variable]),
        "variable_id": variable,
        "actor_ref": actor_ordinal,
        "actor_type_ordinal": actor_ordinal,
        "predicate_shape": PREDICATE_SHAPE,
        "status": "unsupported",
    }]


def build_integration_context(compiled: Any, payload: dict[str, Any], *,
                              unsupported_actor: int, retained_type_ordinals: list[int],
                              candidate_type_ordinals: list[int], support: dict[str, Any],
                              cross_type_edges: list[list[int]] | None = None) -> dict[str, Any]:
    if not _producer_payload_complete(compiled, payload):
        raise CertificateError("real producer provenance is incomplete")
    ledger = _build_ledger(compiled, unsupported_actor)
    domain = {
        "schema_version": 1,
        "candidate_type_ordinals": sorted(candidate_type_ordinals),
        "retained_type_ordinals": sorted(retained_type_ordinals),
    }
    if (not domain["retained_type_ordinals"]
            or not set(domain["retained_type_ordinals"]) <= set(domain["candidate_type_ordinals"])):
        raise CertificateError("retained output domain must be a nonempty frozen subset")
    mutation_edges = [list(row) for row in (cross_type_edges or [])]
    output_spec = {"output_id": OUTPUT_ID, "nodes": ["output:retained-vector"]}
    normalization = {
        "identity": "source-sum-over-frozen-support-per-owner-then-two-owner-mean-v1",
        "support_identity": digest(support),
        "component_identity": "b=u+c; retained type vector filters by frozen domain metadata",
    }
    graph = _graph_from_frozen_provenance(compiled, payload, domain, support,
                                          ledger, mutation_edges)
    graph_manifest_sha256 = digest(graph)
    numeric_digest = digest(payload["numeric_artifact"])
    ledger_digest = digest(ledger)
    source_bundle = _source_bundle_sha256()
    integration_binding = {
        "provenance_schema_version": SCHEMA_VERSION,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "board_domain": _board_domain(compiled),
        "unsupported_ledger_sha256": ledger_digest,
        "producer_formula_source_sha256": source_bundle,
        "formula_identity": digest(FORMULA_ID),
        "numeric_artifact_sha256": numeric_digest,
        "requested_output_identity": digest(output_spec),
        "retained_domain_sha256": digest(domain),
        "normalization_aggregation_identity": digest(normalization),
        "graph_sha256": graph_manifest_sha256,
    }
    base_context = {
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "formula_identity": integration_binding["formula_identity"],
        "formula_source_sha256": source_bundle,
        "output_spec": output_spec,
        "retained_domain": domain["retained_type_ordinals"],
        "normalization": normalization,
        "graph": graph,
        "ledger": ledger,
        "frozen_ledger_sha256": ledger_digest,
        "reference_accessed": False,
    }
    return {
        "producer_payload": payload,
        "domain_metadata": domain,
        "support_metadata": support,
        "cross_type_edges": mutation_edges,
        "graph_manifest_sha256": graph_manifest_sha256,
        "integration_binding": integration_binding,
        "base_context": base_context,
        "PROVENANCE_GRAPH_COMPLETE": True,
    }


def _context_complete(context: dict[str, Any], compiled: Any) -> bool:
    try:
        payload = context["producer_payload"]
        base = context["base_context"]
        if not _producer_payload_complete(compiled, payload):
            return False
        expected_graph = _graph_from_frozen_provenance(
            compiled, payload, context["domain_metadata"], context["support_metadata"],
            base["ledger"], context["cross_type_edges"])
        if expected_graph != base["graph"] or digest(expected_graph) != context["graph_manifest_sha256"]:
            return False
        expected = build_integration_context(
            compiled, payload,
            unsupported_actor=base["ledger"][0]["actor_type_ordinal"],
            retained_type_ordinals=context["domain_metadata"]["retained_type_ordinals"],
            candidate_type_ordinals=context["domain_metadata"]["candidate_type_ordinals"],
            support=context["support_metadata"],
            cross_type_edges=context["cross_type_edges"],
        )
        return (expected["integration_binding"] == context["integration_binding"]
                and expected["base_context"] == base
                and context.get("PROVENANCE_GRAPH_COMPLETE") is True)
    except (CertificateError, KeyError, TypeError, IndexError):
        return False


def issue_integration_certificate(context: dict[str, Any], compiled: Any) -> dict[str, Any]:
    if not _context_complete(context, compiled):
        raise CertificateError("production provenance graph is incomplete or stale")
    certificate = issue_certificate(context["base_context"])
    certificate["PROVENANCE_GRAPH_COMPLETE"] = True
    certificate["integration_binding_sha256"] = digest(context["integration_binding"])
    certificate["integration_binding"] = context["integration_binding"]
    return certificate


def verify_integration_certificate(context: dict[str, Any], certificate: dict[str, Any],
                                   compiled: Any) -> bool:
    if not _context_complete(context, compiled):
        return False
    try:
        expected = issue_integration_certificate(context, compiled)
    except (CertificateError, KeyError, TypeError):
        return False
    base_expected = issue_certificate(context["base_context"])
    base_projection = {key: certificate.get(key) for key in base_expected}
    return certificate == expected and verify_certificate(context["base_context"], base_projection)
