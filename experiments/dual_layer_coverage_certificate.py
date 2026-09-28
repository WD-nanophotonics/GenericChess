"""Standalone synthetic prototype; not imported by production gates."""

from __future__ import annotations

import hashlib
import json
from typing import Any


SCHEMA = "dual-layer-coverage-certificate-prototype-v1"
_ROW_STATES = {"modeled", "unsupported", "out_of_scope"}


class CertificateError(ValueError):
    pass


def digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _binding(context: dict[str, Any]) -> dict[str, Any]:
    required = (
        "ruleset_fingerprint", "formula_identity", "formula_source_sha256",
        "output_spec", "retained_domain", "normalization", "graph",
        "ledger", "frozen_ledger_sha256", "reference_accessed",
    )
    if any(key not in context for key in required):
        raise CertificateError("incomplete frozen certificate context")
    output = context["output_spec"]
    if not isinstance(output, dict) or not output.get("output_id"):
        raise CertificateError("requested output must have a frozen identity")
    if not output.get("nodes") or not context["normalization"]:
        raise CertificateError("output nodes and normalization must be explicit")
    if context["reference_accessed"] is not False:
        raise CertificateError("dependency scope must be frozen before references")
    for key in ("ruleset_fingerprint", "formula_identity", "formula_source_sha256"):
        if not context[key]:
            raise CertificateError(f"missing provenance binding: {key}")

    ledger = context["ledger"]
    if not isinstance(ledger, list):
        raise CertificateError("semantic ledger must remain an explicit list")
    if digest(ledger) != context["frozen_ledger_sha256"]:
        raise CertificateError("semantic ledger differs from its frozen identity")
    row_ids: set[str] = set()
    unsupported_variables: set[str] = set()
    for row in ledger:
        if not isinstance(row, dict) or not {"row_id", "variable_id", "actor_ref", "predicate_shape", "status"} <= row.keys():
            raise CertificateError("ledger row has lost required semantic provenance")
        if row["status"] not in _ROW_STATES:
            raise CertificateError("unknown or zero-filled ledger status")
        if row["row_id"] in row_ids:
            raise CertificateError("duplicate ledger row identity")
        row_ids.add(row["row_id"])
        if row["status"] == "unsupported":
            unsupported_variables.add(row["variable_id"])

    graph = context["graph"]
    nodes = graph.get("nodes") if isinstance(graph, dict) else None
    edges = graph.get("edges") if isinstance(graph, dict) else None
    if not isinstance(nodes, list) or not isinstance(edges, list) or len(nodes) != len(set(nodes)):
        raise CertificateError("dependency graph must have unique explicit nodes and edges")
    node_set = set(nodes)
    if not set(output["nodes"]) <= node_set:
        raise CertificateError("requested output node is absent from the frozen graph")
    if not unsupported_variables <= node_set:
        raise CertificateError("unsupported semantic variable is absent from the graph; fail closed")
    if any(not isinstance(edge, list) or len(edge) != 2 or edge[0] not in node_set or edge[1] not in node_set
           for edge in edges):
        raise CertificateError("dependency edge references an unknown graph node")
    if not isinstance(context["retained_domain"], list) or not context["retained_domain"]:
        raise CertificateError("retained output domain must be explicit")

    # Only frozen, output-relevant data are certified. Identifiers are opaque:
    # no rule branches on game names, piece names, or type IDs.
    return {key: context[key] for key in required}


def _dependency_closure(context: dict[str, Any]) -> set[str]:
    graph = context["graph"]
    reverse: dict[str, set[str]] = {node: set() for node in graph["nodes"]}
    for source, destination in graph["edges"]:
        reverse[destination].add(source)
    closure = set(context["output_spec"]["nodes"])
    frontier = list(closure)
    while frontier:
        node = frontier.pop()
        for dependency in reverse[node] - closure:
            closure.add(dependency)
            frontier.append(dependency)
    return closure


def ruleset_coverage_complete(context: dict[str, Any]) -> bool:
    _binding(context)
    return not any(row["status"] == "unsupported" for row in context["ledger"])


def issue_certificate(context: dict[str, Any]) -> dict[str, Any]:
    binding = _binding(context)
    closure = _dependency_closure(context)
    unsupported = sorted(row["variable_id"] for row in context["ledger"]
                         if row["status"] == "unsupported")
    return {
        "schema": SCHEMA,
        "binding_sha256": digest(binding),
        "unsupported_variables": unsupported,
        "dependency_closure": sorted(closure),
        "ruleset_coverage_complete": not unsupported,
        "requested_output_identifiable": not bool(set(unsupported) & closure),
    }


def verify_certificate(context: dict[str, Any], certificate: dict[str, Any]) -> bool:
    try:
        return certificate == issue_certificate(context)
    except (CertificateError, KeyError, TypeError):
        return False
