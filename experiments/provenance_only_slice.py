"""Dynamic, synthetic-only provenance instrumentation prototype.

The producer function AST is copied in memory and receives sidecar appends at
the existing numerical group-append statements. No repository producer is
edited. This is intentionally not a production artifact builder.
"""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import inspect
import json
from pathlib import Path
import textwrap
from typing import Any, Callable

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


class _InjectSameLoopWitness(ast.NodeTransformer):
    def __init__(self, component: str):
        self.component = component
        self.insertions = 0

    @staticmethod
    def _expr(source: str) -> ast.stmt:
        return ast.parse(source).body[0]

    def visit_Expr(self, node: ast.Expr):
        node = self.generic_visit(node)
        call = node.value
        if not isinstance(call, ast.Call):
            return node
        source = ast.unparse(node)
        if self.component == "u" and source == "groups[key].append(cube)":
            record = self._expr(
                "_record_provenance_witness(provenance_witnesses, compiled, pattern, gid, "
                "type_id, 'u', key, cube, (owner, source, target, state, "
                "tuple(compiled.support.type_metadata).index(final_type)))"
            )
        elif self.component == "c" and source.startswith("_add_capture_group("):
            record = self._expr(
                "_record_provenance_witness(provenance_witnesses, compiled, pattern, gid, "
                "type_id, 'c', key, capture_cube, (owner, source, target, removed_square, "
                "state, pattern.effects.index(effect), "
                "tuple(tuple(compiled.support.type_metadata).index(t) for t in choices)))"
            )
        else:
            return node
        self.insertions += 1
        return [node, record]

    def visit_Return(self, node: ast.Return):
        node = self.generic_visit(node)
        if not isinstance(node.value, ast.Dict):
            return node
        if self.component == "u":
            groups_expr = "{group_key: tuple(group_cubes) for group_key, group_cubes in groups.items()}"
        else:
            groups_expr = "{group_key: tuple(row['cubes']) for group_key, row in groups.items()}"
        node.value.keys.extend((ast.Constant("_provenance_witnesses"), ast.Constant("_numeric_groups")))
        node.value.values.extend((ast.Call(ast.Name("dict", ast.Load()), [ast.Name("provenance_witnesses", ast.Load())], []),
                                  ast.parse(groups_expr, mode="eval").body))
        return node


def instrument_function(function: Callable, component: str) -> Callable:
    """Compile an in-memory clone with an append adjacent to each cube append."""
    source = textwrap.dedent(inspect.getsource(function))
    module_ast = ast.parse(source)
    fn = next(node for node in module_ast.body if isinstance(node, ast.FunctionDef))
    fn.name = f"_provenance_clone_{component}_{function.__name__}"
    fn.decorator_list = []
    injector = _InjectSameLoopWitness(component)
    fn = injector.visit(fn)
    if injector.insertions == 0:
        raise AssertionError(f"no {component} contribution append found in {function.__name__}")
    fn.body.insert(0, ast.Assign(
        targets=[ast.Name("provenance_witnesses", ast.Store())],
        value=ast.Call(ast.Name("defaultdict", ast.Load()), [ast.Name("list", ast.Load())], []),
    ))
    ast.fix_missing_locations(fn)
    namespace = dict(function.__globals__)
    namespace["_record_provenance_witness"] = _record_provenance_witness
    exec(compile(ast.Module(body=[fn], type_ignores=[]), inspect.getsourcefile(function) or "<producer>", "exec"), namespace)
    clone = namespace[fn.name]
    clone._instrumented_append_count = injector.insertions
    return clone


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


def _normalize_groups(groups: dict, component: str) -> dict[tuple, tuple]:
    if component == "u":
        return groups
    return {key: tuple(cubes) for key, cubes in groups.items()}


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


def build_sidecar(compiled: Any, u_result: dict, c_result: dict,
                  numeric_artifact: dict[str, Any]) -> dict[str, Any]:
    u_events = [row for rows in u_result["_provenance_witnesses"].values() for row in rows]
    c_events = [row for rows in c_result["_provenance_witnesses"].values() for row in rows]
    dependency_edges = []
    # These downstream edges mirror the unchanged synthetic aggregation nodes.
    u_groups = u_result["_provenance_witnesses"]
    c_groups = c_result["_provenance_witnesses"]
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
        "dependency_edges": dependency_edges,
        "reference_accessed": False,
    }


def verify_component(sidecar: dict, component: str, numeric_groups: dict[tuple, tuple],
                     compiled: Any) -> bool:
    try:
        witnesses = sidecar["events"][component]
        by_group: dict[tuple, list[dict]] = defaultdict(list)
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
            key = _freeze(row["group_key"])
            by_group[key].append(row)

        normalized_numeric_groups = {_freeze(_jsonable(key)): cubes for key, cubes in numeric_groups.items()}
        if set(by_group) != set(normalized_numeric_groups):
            return False
        claims = sidecar["aggregate_claims"][component]
        for key, cubes in normalized_numeric_groups.items():
            rows = by_group.get(key, [])
            expected_cube_ids = Counter(digest(_jsonable(cube)) for cube in cubes)
            actual_cube_ids = Counter(row["cube_id"] for row in rows)
            if expected_cube_ids != actual_cube_ids or len(rows) != len(cubes):
                return False
            group_id = rows[0]["group_id"]
            claim = claims.get(group_id)
            if claim != _claims({key: rows})[group_id]:
                return False
        return True
    except (KeyError, TypeError, ValueError, IndexError):
        return False


def verify_sidecar(sidecar: dict, expected_binding: dict[str, str],
                   compiled: Any, u_groups: dict, c_groups: dict) -> bool:
    if not isinstance(sidecar, dict):
        return False
    if sidecar.get("schema_version") != SCHEMA_VERSION or sidecar.get("reference_accessed") is not False:
        return False
    if sidecar.get("binding") != expected_binding:
        return False
    sidecar = deepcopy(sidecar)
    for component, result in (("u", u_groups), ("c", c_groups)):
        if not verify_component(sidecar, component, result, compiled):
            return False
    return True


def _freeze(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((key, _freeze(item)) for key, item in value.items()))
    return value


@dataclass(frozen=True)
class PrototypeRun:
    numeric_bytes_off: bytes
    numeric_bytes_on: bytes
    numeric_artifact: dict[str, Any]
    sidecar: dict[str, Any]
    u_groups: dict[tuple, tuple]
    c_groups: dict[tuple, tuple]
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

    u_instrumented = instrument_function(capability._source_u_by_square, "u")
    c_instrumented = instrument_function(v2d._capture_rows, "c")
    u_on = u_instrumented(compiled, type_id, token_ledger)
    c_on = c_instrumented(compiled, type_id, measure_u)
    numeric_on = _numeric_canonical(u_on, c_on, area)
    binding = build_binding(compiled, numeric_on)
    sidecar = build_sidecar(compiled, u_on, c_on, numeric_on)
    sidecar["binding"] = binding
    return PrototypeRun(
        numeric_bytes_off=canonical_bytes(numeric_off),
        numeric_bytes_on=canonical_bytes(numeric_on),
        numeric_artifact=numeric_on,
        sidecar=sidecar,
        u_groups=u_on["_numeric_groups"],
        c_groups=c_on["_numeric_groups"],
        compiled=compiled,
    )
