"""Freeze the raw rule-only movement-domain topology before V2D comparison."""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / ".generic_chess_flow/static-material-domain-fragmentation-topology.json"
FREEZE = ROOT / ".generic_chess_flow/static-material-domain-fragmentation-freeze.json"
FILES = (
    "docs/architecture/ADR-128-static-material-domain-fragmentation-diagnostic.md",
    "scripts/audit_static_material_domain_fragmentation.py",
    "scripts/freeze_static_material_domain_fragmentation.py",
    "tests/test_static_material_domain_fragmentation.py",
    ".generic_chess_flow/static-semantic-material-prior-v2c-freeze.json",
    ".generic_chess_flow/static-semantic-material-prior-v2c-board.json",
    ".generic_chess_flow/static-semantic-material-prior-v2d-freeze.json",
    ".generic_chess_flow/static-semantic-material-prior-v2d-capture-affordance.json",
)
V2C_FREEZE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2c-freeze.json"
V2D_FREEZE = ROOT / ".generic_chess_flow/static-semantic-material-prior-v2d-freeze.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fraction(text: str) -> Fraction:
    numerator, denominator = text.split("/", 1)
    return Fraction(int(numerator), int(denominator))


def _canonical_sha(value: Any) -> str:
    payload = json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _verify_source_freezes() -> None:
    for freeze_path in (V2C_FREEZE, V2D_FREEZE):
        freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
        if freeze.get("human_metrics_computed") is not False or freeze.get("reference_data_read") is not False:
            raise RuntimeError(f"Baseline is not a pre-reference freeze: {freeze_path.name}")
        for relative, expected in freeze.get("sha256", {}).items():
            path = ROOT / relative
            if not path.is_file() or _sha(path) != expected:
                raise RuntimeError(f"Baseline freeze hash mismatch: {relative}")


def freeze() -> dict[str, Any]:
    _verify_source_freezes()
    candidate = json.loads(RAW.read_text(encoding="utf-8"))
    required_false = (
        "human_reference_imported", "v2d_residuals_imported", "material_formula_modified",
        "v2e_transition_value_used", "transport_efficiency_used", "piece_specific_logic",
        "game_specific_logic",
    )
    if any(candidate.get(key) is not False for key in required_false):
        raise RuntimeError("Rule-only candidate has a forbidden input or modification flag")
    if candidate.get("coverage_complete") is not True:
        raise RuntimeError("Topology coverage is incomplete")

    graph_manifest: dict[str, Any] = {}
    for ruleset, ruleset_data in sorted(candidate["rulesets"].items()):
        area = int(ruleset_data["board_area"])
        graph_manifest[ruleset] = {}
        for type_id, piece in sorted(ruleset_data["pieces"].items()):
            if piece.get("coverage_complete") is not True or piece.get("unsupported_semantics"):
                raise RuntimeError(f"Incomplete semantic coverage: {ruleset}/{type_id}")
            owner_manifest = {}
            owner_d: list[Fraction] = []
            owner_f: list[Fraction] = []
            owner_largest: list[Fraction] = []
            owner_components: list[int] = []
            for owner in ("0", "1"):
                graph = piece["owner_graphs"][owner]
                edges = graph["directed_edges"]
                if edges != [list(edge) for edge in sorted({tuple(edge) for edge in edges})]:
                    raise RuntimeError(f"Noncanonical directed edges: {ruleset}/{type_id}/{owner}")
                edge_sha = _canonical_sha(edges)
                if graph["directed_edge_sha256"] != edge_sha:
                    raise RuntimeError(f"Directed-edge digest mismatch: {ruleset}/{type_id}/{owner}")
                rows = graph["directed_edge_rows"]
                if any(row.get("event_probability_positive") is not True
                       or len(row.get("witness_empty_own_enemy_counts", ())) != 3
                       or sum(row["witness_empty_own_enemy_counts"]) != area - 1
                       for row in rows):
                    raise RuntimeError(f"Positive-probability witness missing: {ruleset}/{type_id}/{owner}")
                memberships = graph["component_membership"]
                flattened = [square for component in memberships for square in component]
                if sorted(flattened) != list(range(area)):
                    raise RuntimeError(f"Component memberships do not partition board: {ruleset}/{type_id}/{owner}")
                if memberships != sorted((sorted(set(row)) for row in memberships), key=lambda row: (row[0], len(row))):
                    raise RuntimeError(f"Component membership is not canonical: {ruleset}/{type_id}/{owner}")
                sizes = [len(row) for row in memberships]
                if sizes != graph["component_sizes"]:
                    raise RuntimeError(f"Component sizes mismatch: {ruleset}/{type_id}/{owner}")
                d = sum((Fraction(size, area) ** 2 for size in sizes), Fraction(0))
                f = 1 - d
                largest = Fraction(max(sizes), area)
                if (_fraction(graph["same_domain_probability_d_exact"]) != d
                        or _fraction(graph["fragmentation_f_exact"]) != f
                        or _fraction(graph["largest_component_fraction_exact"]) != largest):
                    raise RuntimeError(f"Component statistic mismatch: {ruleset}/{type_id}/{owner}")
                owner_d.append(d)
                owner_f.append(f)
                owner_largest.append(largest)
                owner_components.append(len(sizes))
                owner_manifest[owner] = {
                    "directed_edge_sha256": edge_sha,
                    "directed_edge_count": len(edges),
                    "component_membership_sha256": _canonical_sha(memberships),
                    "component_sizes": sizes,
                    "component_count": len(sizes),
                    "largest_component_fraction_exact": f"{largest.numerator}/{largest.denominator}",
                    "same_domain_probability_d_exact": f"{d.numerator}/{d.denominator}",
                    "fragmentation_f_exact": f"{f.numerator}/{f.denominator}",
                }
            averaged = piece["owner_averaged"]
            if (_fraction(averaged["same_domain_probability_d_mean_exact"]) != sum(owner_d) / 2
                    or _fraction(averaged["fragmentation_f_mean_exact"]) != sum(owner_f) / 2
                    or _fraction(averaged["largest_component_fraction_mean_exact"]) != sum(owner_largest) / 2
                    or _fraction(averaged["component_count_mean_exact"]) != Fraction(sum(owner_components), 2)):
                raise RuntimeError(f"Owner average was not derived from separate graphs: {ruleset}/{type_id}")
            graph_manifest[ruleset][type_id] = owner_manifest

    files = {relative: _sha(ROOT / relative) for relative in FILES}
    output = {
        "schema_version": 1,
        "kind": "STATIC_MATERIAL_DOMAIN_FRAGMENTATION_PRE_V2D_REFERENCE_FREEZE",
        "classification": candidate["classification"],
        "baseline": "frozen V2D B0=U+C; V2E excluded",
        "human_reference_read": False,
        "v2d_validation_residuals_read": False,
        "topology_candidate_sha256": _sha(RAW),
        "sha256": files,
        "graphs": graph_manifest,
    }
    FREEZE.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def main() -> int:
    result = freeze()
    print(json.dumps({"freeze": str(FREEZE), "topology_candidate_sha256": result["topology_candidate_sha256"],
                      "rulesets": {key: len(value) for key, value in result["graphs"].items()},
                      "reference_data_read": result["human_reference_read"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
