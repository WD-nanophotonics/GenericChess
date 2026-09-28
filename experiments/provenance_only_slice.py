"""Provenance identity, binding, and verification for a synthetic producer slice."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = 1


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def _event_id(compiled: Any, pattern: Any, geometry_id: str, type_id: str,
              local_event: tuple[Any, ...]) -> tuple[str, dict[str, Any]]:
    pattern_ordinal = next(index for index, item in enumerate(compiled.ir.patterns) if item is pattern)
    geometry_ordinal = pattern.geometry_ids.index(geometry_id)
    type_ordinal = tuple(compiled.support.type_metadata).index(type_id)
    identity = {
        "schema_version": SCHEMA_VERSION,
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "compiled_pattern_ordinal": pattern_ordinal,
        "compiled_geometry_ordinal": geometry_ordinal,
        "actor_type_ordinal": type_ordinal,
        "local_event": _jsonable(local_event),
    }
    return digest(identity), identity


def _record_provenance_witness(witnesses: dict, compiled: Any, pattern: Any,
                               geometry_id: str, type_id: str, component: str,
                               group_key: tuple[Any, ...], cube: tuple,
                               local_event: tuple[Any, ...]) -> None:
    event_id, identity = _event_id(compiled, pattern, geometry_id, type_id, local_event)
    cube_id = digest(_jsonable(cube))
    witnesses[group_key].append({
        "event_id": event_id,
        "identity": identity,
        "component": component,
        "group_id": digest([component, compiled.ruleset_fingerprint, _jsonable(group_key)]),
        "group_key": _jsonable(group_key),
        "cube_id": cube_id,
    })


class ProvenanceSink:
    """Opt-in recorder; producer arithmetic never reads from this sink."""

    def __init__(self) -> None:
        self.events: dict[str, list[dict[str, Any]]] = {"u": [], "c": []}
        self.numeric_enumeration: dict[str, dict[str, dict[str, Any]]] = {
            "u": {}, "c": {},
        }
        self._witnesses: dict[str, dict[tuple[Any, ...], list[dict[str, Any]]]] = {
            "u": defaultdict(list), "c": defaultdict(list),
        }

    def note_numeric_contribution(self, component: str, compiled: Any,
                                  group_key: tuple[Any, ...], cube: tuple) -> None:
        group_id = digest([component, compiled.ruleset_fingerprint, _jsonable(group_key)])
        row = self.numeric_enumeration[component].setdefault(group_id, {
            "group_key": _jsonable(group_key), "cube_ids": [],
        })
        row["cube_ids"].append(digest(_jsonable(cube)))

    def record_contribution(self, *, component: str, compiled: Any, pattern: Any,
                            geometry_id: str, type_id: str, group_key: tuple[Any, ...],
                            cube: tuple, local_event: tuple[Any, ...]) -> None:
        _record_provenance_witness(self._witnesses[component], compiled, pattern,
                                   geometry_id, type_id, component, group_key, cube,
                                   local_event)
        self.events[component].append(self._witnesses[component][group_key][-1])

    def event_groups(self, component: str) -> dict[tuple[Any, ...], list[dict[str, Any]]]:
        return self._witnesses[component]


def _claims(witnesses: dict) -> dict[str, dict[str, Any]]:
    result = {}
    for key, rows in witnesses.items():
        group_id = rows[0]["group_id"]
        event_ids = [row["event_id"] for row in rows]
        cube_ids = [row["cube_id"] for row in rows]
        result[group_id] = {
            "contributor_count": len(rows),
            "event_digest": digest(sorted(event_ids)),
            "cube_witness_digest": digest(sorted(cube_ids)),
            "unique_cube_count": len(set(cube_ids)),
        }
    return result


def _numeric_canonical(u_result: dict, c_result: dict, area: int) -> dict[str, Any]:
    from scripts.audit_static_material_domain_conditional_capability import _source_c_by_square

    u = u_result["u_by_owner_source"]
    c = _source_c_by_square(c_result, area)["c_by_owner_source"]
    b = {owner: [u[owner][i] + c[owner][i] for i in range(area)] for owner in ("0", "1")}
    retained_u = sum((sum(u[o], start=0) for o in ("0", "1")), start=0) / (2 * area)
    retained_c = sum((sum(c[o], start=0) for o in ("0", "1")), start=0) / (2 * area)
    retained_b = retained_u + retained_c

    def fraction(value: Any) -> str:
        return f"{value.numerator}/{value.denominator}"

    return {
        "u_by_owner_source": {o: [fraction(v) for v in u[o]] for o in ("0", "1")},
        "c_by_owner_source": {o: [fraction(v) for v in c[o]] for o in ("0", "1")},
        "b_by_owner_source": {o: [fraction(v) for v in b[o]] for o in ("0", "1")},
        "synthetic_retained_output": {
            "u": fraction(retained_u), "c": fraction(retained_c), "b": fraction(retained_b),
        },
    }


def build_binding(compiled: Any, numeric_artifact: dict[str, Any]) -> dict[str, str]:
    from scripts import audit_static_material_domain_conditional_capability as capability
    from scripts import audit_static_semantic_material_prior_v2a as v2a
    from scripts import audit_static_semantic_material_prior_v2c as v2c
    from scripts import audit_static_semantic_material_prior_v2d as v2d

    source_files = (Path(__file__), Path(capability.__file__), Path(v2a.__file__),
                    Path(v2c.__file__), Path(v2d.__file__))
    source_bundle = [(str(path.relative_to(ROOT)), file_digest(path)) for path in source_files]
    return {
        "schema_version": str(SCHEMA_VERSION),
        "source_bundle_sha256": digest(source_bundle),
        "formula_identity": digest("synthetic-u-plus-c-retained-mean-v1"),
        "ruleset_fingerprint": compiled.ruleset_fingerprint,
        "numeric_artifact_sha256": digest(numeric_artifact),
    }


def build_sidecar(compiled: Any, sink: ProvenanceSink,
                  numeric_artifact: dict[str, Any]) -> dict[str, Any]:
    u_events = sink.events["u"]
    c_events = sink.events["c"]
    dependency_edges = []
    # These downstream edges mirror the unchanged synthetic aggregation nodes.
    u_groups = sink.event_groups("u")
    c_groups = sink.event_groups("c")
    for component, grouped in (("u", u_groups), ("c", c_groups)):
        for key, rows in grouped.items():
            owner, source = key[0], key[1]
            dependency_edges.append({
                "from": rows[0]["group_id"],
                "to": f"{component}:owner={owner}:source={source}",
            })
    for owner in (0, 1):
        for source in range(len(numeric_artifact["b_by_owner_source"][str(owner)])):
            u_node = f"u:owner={owner}:source={source}"
            c_node = f"c:owner={owner}:source={source}"
            b_node = f"b:owner={owner}:source={source}"
            dependency_edges.extend((
                {"from": u_node, "to": b_node},
                {"from": c_node, "to": b_node},
                {"from": u_node, "to": f"u:owner-normalized={owner}",
                 "operation": "source_sum_then_divide_by_board_area"},
                {"from": c_node, "to": f"c:owner-normalized={owner}",
                 "operation": "source_sum_then_divide_by_board_area"},
            ))
        dependency_edges.extend((
            {"from": f"u:owner-normalized={owner}", "to": "u:retained-normalized-mean",
             "operation": "mean_over_two_owners"},
            {"from": f"c:owner-normalized={owner}", "to": "c:retained-normalized-mean",
             "operation": "mean_over_two_owners"},
        ))
    dependency_edges.extend((
        {"from": "u:retained-normalized-mean", "to": "synthetic:retained-output:u",
         "operation": "copy_exact_fraction"},
        {"from": "c:retained-normalized-mean", "to": "synthetic:retained-output:c",
         "operation": "copy_exact_fraction"},
        {"from": "synthetic:retained-output:u", "to": "synthetic:retained-output:b",
         "operation": "exact_add"},
        {"from": "synthetic:retained-output:c", "to": "synthetic:retained-output:b",
         "operation": "exact_add"},
    ))
    return {
        "schema_version": SCHEMA_VERSION,
        "binding": build_binding(compiled, numeric_artifact),
        "events": {"u": u_events, "c": c_events},
        "aggregate_claims": {"u": _claims(u_groups), "c": _claims(c_groups)},
        "numeric_enumeration": {
            component: {
                group_id: {
                    "group_key": row["group_key"],
                    "contributor_count": len(row["cube_ids"]),
                    "cube_witness_digest": digest(sorted(row["cube_ids"])),
                    "unique_cube_count": len(set(row["cube_ids"])),
                }
                for group_id, row in sink.numeric_enumeration[component].items()
            }
            for component in ("u", "c")
        },
        "dependency_edges": dependency_edges,
        "reference_accessed": False,
    }


def verify_component(sidecar: dict, component: str, compiled: Any) -> bool:
    try:
        witnesses = sidecar["events"][component]
        by_group: dict[str, list[dict]] = defaultdict(list)
        for row in witnesses:
            identity = row["identity"]
            expected_id = digest(identity)
            if row["event_id"] != expected_id or identity["ruleset_fingerprint"] != compiled.ruleset_fingerprint:
                return False
            if identity["schema_version"] != SCHEMA_VERSION:
                return False
            if "group_key" not in row:
                return False
            if row["group_id"] != digest([component, compiled.ruleset_fingerprint, row["group_key"]]):
                return False
            by_group[row["group_id"]].append(row)

        numeric_enumeration = sidecar["numeric_enumeration"][component]
        if set(by_group) != set(numeric_enumeration):
            return False
        claims = sidecar["aggregate_claims"][component]
        for group_id, expected in numeric_enumeration.items():
            rows = by_group.get(group_id, [])
            actual_cube_ids = [row["cube_id"] for row in rows]
            if (len(rows) != expected["contributor_count"]
                    or digest(sorted(actual_cube_ids)) != expected["cube_witness_digest"]
                    or len(set(actual_cube_ids)) != expected["unique_cube_count"]):
                return False
            claim = claims.get(group_id)
            if claim != _claims({group_id: rows})[group_id]:
                return False
        return True
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def verify_sidecar(sidecar: dict, expected_binding: dict[str, str],
                   compiled: Any) -> bool:
    if not isinstance(sidecar, dict):
        return False
    if sidecar.get("schema_version") != SCHEMA_VERSION or sidecar.get("reference_accessed") is not False:
        return False
    if sidecar.get("binding") != expected_binding:
        return False
    for component in ("u", "c"):
        if not verify_component(sidecar, component, compiled):
            return False
    return True


@dataclass(frozen=True)
class PrototypeRun:
    numeric_bytes_off: bytes
    numeric_bytes_on: bytes
    numeric_artifact: dict[str, Any]
    sidecar: dict[str, Any]
    u_schema_off: tuple[str, ...]
    u_schema_on: tuple[str, ...]
    c_schema_off: tuple[str, ...]
    c_schema_on: tuple[str, ...]
    compiled: Any


def run_synthetic_fixture(rules: Any, compiled: Any, type_id: str) -> PrototypeRun:
    from scripts import audit_static_material_domain_conditional_capability as capability
    from scripts import audit_static_semantic_material_prior_v2c as v2c
    from scripts import audit_static_semantic_material_prior_v2d as v2d

    token_ledger = v2c._token_state_ledger(compiled)
    measure_u = v2c._event_measure_factory(token_ledger, compiled, type_id)
    area = compiled.support.board_size ** 2
    u_off = capability._source_u_by_square(compiled, type_id, token_ledger)
    c_off = v2d._capture_rows(compiled, type_id, measure_u)
    numeric_off = _numeric_canonical(u_off, c_off, area)

    sink = ProvenanceSink()
    u_on = capability._source_u_by_square(compiled, type_id, token_ledger,
                                          provenance_sink=sink)
    c_on = v2d._capture_rows(compiled, type_id, measure_u, provenance_sink=sink)
    numeric_on = _numeric_canonical(u_on, c_on, area)
    sidecar = build_sidecar(compiled, sink, numeric_on)
    return PrototypeRun(
        numeric_bytes_off=canonical_bytes(numeric_off),
        numeric_bytes_on=canonical_bytes(numeric_on),
        numeric_artifact=numeric_on,
        sidecar=sidecar,
        u_schema_off=tuple(sorted(u_off)),
        u_schema_on=tuple(sorted(u_on)),
        c_schema_off=tuple(sorted(c_off)),
        c_schema_on=tuple(sorted(c_on)),
        compiled=compiled,
    )
