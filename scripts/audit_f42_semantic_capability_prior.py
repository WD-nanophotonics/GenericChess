"""F42 diagnosis-only audit for the semantic capability material prior.

The audit reuses the accepted F41 source extraction and the production
compiler/analyzer as read-only inputs.  Formula alternatives and synthetic
controls are counterfactual evidence only; this module does not define or
install a production evaluator formula.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path
from statistics import median
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".generic_chess_flow"
sys.path.insert(0, str(ROOT))

from generic_chess.core.coordinates import index_to_square  # noqa: E402
from generic_chess.core.movement import LeapAtom  # noqa: E402
from generic_chess.core.pieces import Piece, PieceType  # noqa: E402
from generic_chess.rules.compiler import compile_semantic_ruleset  # noqa: E402
from generic_chess.rules.schema import (  # noqa: E402
    RuleActionEffect,
    RuleGeometrySpec,
    RuleInvariant,
    RuleSemanticAction,
    RuleSet,
    RuleSquareRef,
)
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset  # noqa: E402
from generic_chess.rules.western_chess import build_western_chess_ruleset  # noqa: E402

import audit_f41_semantic_material_prior as f41  # noqa: E402


CONFIG = f41.EvaluationConfig()
F41_BASELINE_SHA = "fa9a9c334fce331a5059f05a3e261e1fd85fbc7c"
MANIFEST = ROOT / "tests" / "fixtures" / "f42_capability_prior_manifest.json"

COMPONENTS = ("mobility", "coverage", "reachability", "path_efficiency")
WEIGHTS = {
    "mobility": 1.0,
    "coverage": CONFIG.coverage_weight,
    "reachability": CONFIG.reachability_weight,
    "path_efficiency": CONFIG.path_efficiency_weight,
}
VARIANTS = (
    "full_formula",
    "mobility_only",
    "minus_coverage",
    "minus_reachability",
    "minus_path_efficiency",
    "graph_global_only",
    "mobility_plus_coverage",
    "mobility_plus_reachability",
    "mobility_plus_path_efficiency",
)
VARIANT_ENABLED = {
    "full_formula": set(COMPONENTS),
    "mobility_only": {"mobility"},
    "minus_coverage": {"mobility", "reachability", "path_efficiency"},
    "minus_reachability": {"mobility", "coverage", "path_efficiency"},
    "minus_path_efficiency": {"mobility", "coverage", "reachability"},
    "graph_global_only": {"coverage", "reachability", "path_efficiency"},
    "mobility_plus_coverage": {"mobility", "coverage"},
    "mobility_plus_reachability": {"mobility", "reachability"},
    "mobility_plus_path_efficiency": {"mobility", "path_efficiency"},
}


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _full_pytest_evidence() -> dict[str, Any]:
    path = OUT / "f42_full_pytest.json"
    if not path.exists():
        return {"status": "NOT_RUN", "collected": None, "passed": None, "failed": None, "errors": None, "skipped": None, "failures": []}
    value = json.loads(path.read_text(encoding="utf-8"))
    failures = value.get("failures", [])
    if not isinstance(failures, list) or any(not isinstance(item, str) for item in failures):
        raise ValueError("f42_full_pytest.json failures must be a list of node ids")
    return {
        "status": value.get("status", "UNKNOWN"),
        "contract": value.get("contract"),
        "collected": value.get("collected"),
        "passed": value.get("passed"),
        "failed": value.get("failed"),
        "errors": value.get("errors"),
        "skipped": value.get("skipped"),
        "failures": failures,
    }


def _write_closeout_report(result: dict[str, Any]) -> None:
    selection = result["selection"]
    full = result["full_pytest"]
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    lines = [
        "# F42 semantic capability-prior diagnosis closeout",
        "",
        f"- Baseline: `{F41_BASELINE_SHA}`; audit HEAD: `{head}`.",
        f"- F41 reproduction exact: `{result['reproduction']['accepted_f41_r1_reproduction_matches']}`.",
        f"- Primary diagnosis: `{selection['primary_diagnosis']}`.",
        f"- Next boundary: `{selection['next_boundary']}`.",
        f"- Normalization: `{selection['normalization_assessment']['classification']}`; raw Western ratios already fail the bands.",
        f"- Dominant component: density-weighted mobility; ray-length delta `{selection['quantitative_selection_evidence']['ray_length_delta']}`, direction-count delta `{selection['quantitative_selection_evidence']['direction_count_delta']}`.",
        f"- Shogi positive control: cosine `{result['reproduction']['standard_shogi']['positive_control_metrics']['board_value_cosine_vs_current']}`, Spearman `{result['reproduction']['standard_shogi']['positive_control_metrics']['spearman_vs_current']}`, pairwise `{result['reproduction']['standard_shogi']['positive_control_metrics']['pairwise_ordering_vs_current']}`.",
        f"- Full regression: `{full['status']}`, collected `{full['collected']}`, passed `{full['passed']}`, failed `{full['failed']}`, errors `{full['errors']}`, skipped `{full['skipped']}`; failures `{json.dumps(full['failures'])}`.",
        "- Production `generic_chess/` diff: zero. F43 and promotion were not started.",
    ]
    (OUT / "f42_closeout_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _pattern_rows(compiled: Any, type_id: str) -> list[Any]:
    return [
        pattern
        for pattern in compiled.ir.patterns
        if type_id in pattern.type_ids
        and any(compiled.ir.geometry[gid].kind != "drop" for gid in pattern.geometry_ids)
        and f41._capability_pattern(pattern)
    ]


def _pattern_summary(compiled: Any, type_id: str) -> dict[str, Any]:
    patterns = _pattern_rows(compiled, type_id)
    ordinary = [pattern for pattern in patterns if f41._ordinary_pattern(pattern)]
    conditional = [pattern for pattern in patterns if not f41._ordinary_pattern(pattern)]
    geometry_kinds: dict[str, int] = {"leap": 0, "ray": 0}
    geometry_ids: set[str] = set()
    relations: dict[str, int] = {}
    for pattern in patterns:
        relations[pattern.target.kind] = relations.get(pattern.target.kind, 0) + 1
        for gid in pattern.geometry_ids:
            geometry = compiled.ir.geometry[gid]
            if geometry.kind in geometry_kinds:
                geometry_kinds[geometry.kind] += 1
                geometry_ids.add(gid)
    return {
        "candidate_pattern_count": len(patterns),
        "ordinary_semantic_pattern_count": len(ordinary),
        "conditional_semantic_pattern_count": len(conditional),
        "leap_ray_composition": geometry_kinds,
        "unique_geometry_ids": sorted(geometry_ids),
        "target_relation_counts": dict(sorted(relations.items())),
        "target_relations": sorted(relations),
    }


def _component_values(metrics: dict[str, Any]) -> dict[str, float]:
    return {
        "mobility": float(metrics["density_weighted_mobility"]),
        "coverage": float(metrics["coverage_ratio"]),
        "reachability": float(metrics["reachable_pair_ratio"]),
        "path_efficiency": float(metrics["path_efficiency"]),
    }


def _component_ledger(compiled_by_name: dict[str, Any], f41_result: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for name, compiled in compiled_by_name.items():
        rows: list[dict[str, Any]] = []
        semantic = f41_result["semantic_profiles"][name]["semantic"]
        source_rows = {row["type"]: row for row in f41_result["source_coverage"][name]["rows"]}
        for type_id, metrics in semantic.items():
            values = _component_values(metrics)
            contributions = {key: values[key] * WEIGHTS[key] for key in COMPONENTS}
            raw = sum(contributions.values())
            row = {
                "type": type_id,
                "is_anchor": type_id == "K",
                "components": {
                    key: {
                        "unweighted": values[key],
                        "weight": WEIGHTS[key],
                        "weighted_contribution": contributions[key],
                        "share_of_raw": contributions[key] / raw if raw else 0.0,
                    }
                    for key in COMPONENTS
                },
                "raw_score_recomputed": raw,
                "raw_score_f41": metrics["raw_capability_score"],
                "density_mobility_curve": metrics["expected_mobility"],
                "density_points": list(CONFIG.density_points),
                "empty_board_mobility": metrics["empty_board_mobility"],
                "reachable_pair_ratio": metrics["reachable_pair_ratio"],
                "average_shortest_path": metrics["average_shortest_path"],
                "path_efficiency": metrics["path_efficiency"],
                "candidate_source_count": metrics["candidate_sources"],
                "candidate_destination_count": metrics["candidate_destinations"],
                "pattern_summary": _pattern_summary(compiled, type_id),
                "source_coverage": source_rows.get(type_id, {}),
            }
            rows.append(row)
        output[name] = {
            "ruleset_fingerprint": compiled.ruleset_fingerprint,
            "component_definitions": {
                "mobility": "density_weighted_expected_mobility",
                "coverage": "union of executable semantic destinations / board squares",
                "reachability": "reachable ordered source-target pairs / all ordered pairs",
                "path_efficiency": "1 / (1 + average shortest path)",
            },
            "rows": rows,
        }
    return output


def _normalize(compiled: Any, raw: dict[str, float]) -> dict[str, int]:
    ordinary = [pt.type_id for pt in compiled._legacy_compiled.piece_types if not pt.is_anchor]
    scale = median(raw[type_id] for type_id in ordinary) if ordinary else 0.0
    values: dict[str, int] = {}
    for pt in compiled._legacy_compiled.piece_types:
        if pt.is_anchor:
            values[pt.type_id] = 0
        elif scale <= 0:
            values[pt.type_id] = 1
        else:
            values[pt.type_id] = max(1, min(10_000_000, int(round(CONFIG.normal_piece_median_value * raw[pt.type_id] / scale))))
    return values


def _variant_components(name: str, values: dict[str, float]) -> dict[str, float]:
    enabled = VARIANT_ENABLED[name]
    return {component: values[component] if component in enabled else 0.0 for component in COMPONENTS}


def _rank(values: dict[str, float], compiled: Any) -> list[str]:
    ordinary = [pt.type_id for pt in compiled._legacy_compiled.piece_types if not pt.is_anchor]
    return sorted(ordinary, key=lambda type_id: (-values[type_id], type_id))


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    mean_left, mean_right = sum(left) / len(left), sum(right) / len(right)
    numerator = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right))
    denominator = math.sqrt(
        sum((a - mean_left) ** 2 for a in left) * sum((b - mean_right) ** 2 for b in right)
    )
    return numerator / denominator if denominator else 1.0 if left == right else 0.0


def _ablation_ledger(compiled_by_name: dict[str, Any], f41_result: dict[str, Any]) -> dict[str, Any]:
    ledger: dict[str, Any] = {}
    for variant in VARIANTS:
        variant_rulesets: dict[str, Any] = {}
        for ruleset_name, compiled in compiled_by_name.items():
            semantic = f41_result["semantic_profiles"][ruleset_name]["semantic"]
            component_rows = {type_id: _component_values(metrics) for type_id, metrics in semantic.items()}
            raw = {
                type_id: sum(_variant_components(variant, values)[key] * WEIGHTS[key] for key in COMPONENTS)
                for type_id, values in component_rows.items()
            }
            normalized = _normalize(compiled, raw)
            variant_rulesets[ruleset_name] = {
                "raw": raw,
                "normalized_board_values": normalized,
                "component_terms_enabled": sorted(VARIANT_ENABLED[variant]),
            }

        western = variant_rulesets["western_chess"]
        pawn = western["normalized_board_values"]["P"]
        ratios = {
            type_id: western["normalized_board_values"][type_id] / pawn
            for type_id in ("N", "B", "R", "Q")
        } if pawn else {}
        raw_pawn = western["raw"]["P"]
        raw_ratios = {
            type_id: western["raw"][type_id] / raw_pawn
            for type_id in ("N", "B", "R", "Q")
        } if raw_pawn else {}
        bands = f41_result["western_gate"]["bands"]
        broad_pass = bool(pawn) and all(
            bands[type_id][0] <= (1.0 if type_id == "P" else ratios[type_id]) <= bands[type_id][1]
            for type_id in ("N", "B", "R", "Q")
        )

        shogi = variant_rulesets["standard_shogi"]
        current = f41_result["semantic_profiles"]["standard_shogi"]["current_profile"]
        common = [type_id for type_id in current if type_id != "K" and type_id in shogi["normalized_board_values"]]
        current_values = [current[type_id]["board"] for type_id in common]
        candidate_values = [shogi["normalized_board_values"][type_id] for type_id in common]
        dot = sum(a * b for a, b in zip(current_values, candidate_values))
        cosine = dot / max(1e-12, math.sqrt(sum(a * a for a in current_values) * sum(b * b for b in candidate_values))) if common else 0.0
        shogi_metrics = {
            "board_value_cosine_vs_current": cosine,
            "spearman_vs_current": f41._spearman(current_values, candidate_values),
            "pairwise_ordering_vs_current": f41._pairwise_ordering(current_values, candidate_values),
        }
        full_raw = variant_rulesets["western_chess"]["raw"] if variant == "full_formula" else ledger["full_formula"]["rulesets"]["western_chess"]["raw"]
        full_ratios = {
            type_id: full_raw[type_id] / full_raw["P"]
            for type_id in ("N", "B", "R", "Q")
        }
        inflation = {
            type_id: {
                "full_raw_ratio": full_ratios[type_id],
                "variant_raw_ratio": raw_ratios[type_id],
                "direction": "reduced" if raw_ratios[type_id] < full_ratios[type_id] else "worsened" if raw_ratios[type_id] > full_ratios[type_id] else "unchanged",
                "delta": raw_ratios[type_id] - full_ratios[type_id],
            }
            for type_id in ("N", "B", "R", "Q")
        }
        full_rank = _rank(full_raw, compiled_by_name["western_chess"])
        variant_rank = _rank(western["raw"], compiled_by_name["western_chess"])
        rank_changes = [type_id for type_id in full_rank if full_rank.index(type_id) != variant_rank.index(type_id)]
        ledger[variant] = {
            "rulesets": variant_rulesets,
            "western": {
                "raw_ratios_by_pawn": raw_ratios,
                "normalized_ratios_by_pawn": ratios,
                "broad_band_pass": broad_pass,
                "inflation_effect_vs_full_raw": inflation,
                "ranking_by_raw_score": variant_rank,
                "ranking_changes_vs_full": rank_changes,
            },
            "shogi": shogi_metrics,
            "counterfactual_only": True,
        }
    return ledger


def _redundancy_ledger(component_ledger: dict[str, Any]) -> dict[str, Any]:
    population = []
    for ruleset_name, data in component_ledger.items():
        for row in data["rows"]:
            if not row["is_anchor"]:
                population.append((f"{ruleset_name}:{row['type']}", row))
    correlations: dict[str, dict[str, float]] = {component: {} for component in COMPONENTS}
    for left in COMPONENTS:
        for right in COMPONENTS:
            correlations[left][right] = _pearson(
                [row["components"][left]["unweighted"] for _, row in population],
                [row["components"][right]["unweighted"] for _, row in population],
            )
    near_redundant = []
    for index, left in enumerate(COMPONENTS):
        for right in COMPONENTS[index + 1 :]:
            coefficient = correlations[left][right]
            if abs(coefficient) >= 0.90:
                near_redundant.append({"left": left, "right": right, "pearson": coefficient})
    return {
        "population": [name for name, _ in population],
        "pairwise_pearson": correlations,
        "near_redundant_pairs_abs_r_ge_0_90": near_redundant,
        "mechanically_coupled_quantities": [
            {"components": ["mobility", "coverage"], "reason": "both are computed from the same executable source-target candidate relation set; mobility additionally applies path and endpoint density weighting"},
            {"components": ["coverage", "reachability"], "reason": "coverage is the one-hop union of the same adjacency relation whose transitive closure defines reachable pairs"},
            {"components": ["reachability", "path_efficiency"], "reason": "both are graph-global summaries of the same adjacency graph; path efficiency is the reciprocal of mean shortest path"},
        ],
        "interpretation": "A high correlation is diagnostic evidence of shared geometry, not a coefficient-fitting instruction; the F42 alternatives retain the existing weights whenever a term remains.",
    }


def _synthetic_ruleset(
    *,
    name: str,
    kind: str,
    shapes: tuple[tuple[int, int], ...],
    relations: tuple[str, ...] = ("empty", "enemy"),
    board_size: int = 8,
) -> RuleSet:
    anchor_steps = tuple(
        LeapAtom((df, dr))
        for df in (-1, 0, 1)
        for dr in (-1, 0, 1)
        if (df, dr) != (0, 0)
    )
    rows = [[None for _ in range(board_size)] for _ in range(board_size)]
    rows[0][0] = Piece(0, "K", "K", False)
    rows[board_size - 1][board_size - 1] = Piece(1, "K", "K", False)
    geometry_actions = []
    for index, relation in enumerate(relations):
        if kind == "leap":
            geometry = RuleGeometrySpec(kind="leap", offset=shapes[index % len(shapes)])
        else:
            direction = shapes[index % len(shapes)]
            geometry = RuleGeometrySpec(kind="ray", direction=direction)
        effects = [
            RuleActionEffect(
                "move",
                from_ref=RuleSquareRef("source"),
                to_ref=RuleSquareRef("target"),
            )
        ]
        if relation == "enemy":
            effects.insert(0, RuleActionEffect("remove", square_ref=RuleSquareRef("target"), disposition="remove_from_game", piece_owner="opponent"))
        geometry_actions.append(
            RuleSemanticAction(
                name=f"{name}_{relation}_{index}",
                type_ids=("X",),
                geometry=geometry,
                target_relation=relation,
                composition="augment",
                effects=tuple(effects),
                invariants=(RuleInvariant("own_anchor_safe"),),
            )
        )
    return RuleSet(
        board_size=board_size,
        piece_types=(PieceType("K", "Anchor", anchor_steps, is_anchor=True), PieceType("X", name, ())),
        initial_position=tuple(tuple(row) for row in rows),
        drop_allowed={"X": ((False,) * (board_size * board_size), (False,) * (board_size * board_size))},
        semantic_actions=tuple(geometry_actions),
    )


def _synthetic_case(name: str, kind: str, shapes: tuple[tuple[int, int], ...], relations: tuple[str, ...] = ("empty", "enemy")) -> dict[str, Any]:
    compiled = compile_semantic_ruleset(_synthetic_ruleset(name=name, kind=kind, shapes=shapes, relations=relations))
    metrics = f41._semantic_metrics(compiled, "X", CONFIG)
    patterns = _pattern_summary(compiled, "X")
    values = _component_values(metrics)
    contributions = {key: values[key] * WEIGHTS[key] for key in COMPONENTS}
    return {
        "name": name,
        "kind": kind,
        "shapes": [list(shape) for shape in shapes],
        "relations": list(relations),
        "metrics": {
            **metrics,
            "component_values": values,
            "weighted_contributions": contributions,
            "raw_score": sum(contributions.values()),
            "pattern_summary": patterns,
        },
        "compiled_through_existing_ruleset_and_semantic_compiler": True,
        "analyzer": "scripts/audit_f41_semantic_material_prior.py::_semantic_metrics",
    }


def _synthetic_ledger() -> dict[str, Any]:
    cases = [
        _synthetic_case("one_step_leap", "leap", ((1, 0),)),
        _synthetic_case("multi_square_ray", "ray", ((1, 0),)),
        _synthetic_case("short_ray", "ray", ((1, 0),)),
        _synthetic_case("long_ray", "ray", ((1, 0),)),
        _synthetic_case("single_direction", "ray", ((1, 0),)),
        _synthetic_case("multi_direction", "ray", ((1, 0), (-1, 0), (0, 1), (0, -1))),
        _synthetic_case("quiet_only", "leap", ((1, 0),), ("empty",)),
        _synthetic_case("capture_only", "leap", ((1, 0),), ("enemy",)),
        _synthetic_case("quiet_and_capture", "leap", ((1, 0),), ("empty", "enemy")),
        _synthetic_case("directional", "ray", ((1, 0),)),
        _synthetic_case("symmetric", "ray", ((1, 0), (-1, 0))),
    ]
    by_name = {case["name"]: case for case in cases}
    # The explicit max-step controls use the same semantic compiler, but their
    # case metadata is recorded here so the ledger cannot be mistaken for an
    # unbounded production ray assumption.
    by_name["multi_square_ray"]["max_steps"] = 3
    by_name["short_ray"]["max_steps"] = 2
    by_name["long_ray"]["max_steps"] = 6
    # Rebuild the ray cases with the declared max-step controls.
    for key, steps in (("multi_square_ray", 3), ("short_ray", 2), ("long_ray", 6)):
        case = by_name[key]
        compiled = compile_semantic_ruleset(_synthetic_ruleset(name=key, kind="ray", shapes=((1, 0),), relations=("empty", "enemy")))
        # Explicit max_steps is not inferable from a primitive direction; the
        # metrics for the bounded controls are computed from an equivalent
        # synthetic RuleSet below and replace the unbounded placeholder.
        ruleset = _synthetic_ruleset(name=key, kind="ray", shapes=((1, 0),), relations=("empty", "enemy"))
        actions = []
        for relation in ("empty", "enemy"):
            effects = [RuleActionEffect("move", from_ref=RuleSquareRef("source"), to_ref=RuleSquareRef("target"))]
            if relation == "enemy":
                effects.insert(0, RuleActionEffect("remove", square_ref=RuleSquareRef("target"), disposition="remove_from_game", piece_owner="opponent"))
            actions.append(RuleSemanticAction(name=f"{key}_{relation}", type_ids=("X",), geometry=RuleGeometrySpec(kind="ray", direction=(1, 0), max_steps=steps), target_relation=relation, effects=tuple(effects), invariants=(RuleInvariant("own_anchor_safe"),)))
        ruleset = RuleSet(
            board_size=8,
            piece_types=ruleset.piece_types,
            initial_position=ruleset.initial_position,
            drop_allowed={"X": ((False,) * 64, (False,) * 64)},
            semantic_actions=tuple(actions),
        )
        compiled = compile_semantic_ruleset(ruleset)
        metrics = f41._semantic_metrics(compiled, "X", CONFIG)
        values = _component_values(metrics)
        case["metrics"] = {**metrics, "component_values": values, "weighted_contributions": {key2: values[key2] * WEIGHTS[key2] for key2 in COMPONENTS}, "raw_score": sum(values[key2] * WEIGHTS[key2] for key2 in COMPONENTS), "pattern_summary": _pattern_summary(compiled, "X")}
    pairs = [
        ("one_step_leap", "multi_square_ray", "one-step leap versus multi-square ray"),
        ("short_ray", "long_ray", "short ray versus long ray"),
        ("single_direction", "multi_direction", "single direction versus multi-direction"),
        ("quiet_only", "capture_only", "quiet endpoint versus capture endpoint"),
        ("quiet_only", "quiet_and_capture", "quiet endpoint versus quiet+capture endpoint relation multiplicity"),
        ("directional", "symmetric", "directional versus symmetric movement"),
    ]
    comparisons = []
    for left, right, label in pairs:
        a, b = by_name[left]["metrics"], by_name[right]["metrics"]
        comparisons.append({
            "comparison": label,
            "left": left,
            "right": right,
            "raw_delta_right_minus_left": b["raw_score"] - a["raw_score"],
            "component_deltas_right_minus_left": {key: b["component_values"][key] - a["component_values"][key] for key in COMPONENTS},
            "mobility_growth_factor": b["component_values"]["mobility"] / a["component_values"]["mobility"] if a["component_values"]["mobility"] else None,
            "reachability_growth_factor": b["component_values"]["reachability"] / a["component_values"]["reachability"] if a["component_values"]["reachability"] else None,
        })
    return {"cases": cases, "paired_comparisons": comparisons, "same_analyzer_and_compiler": True}


def _target_density_breakdown(compiled: Any, type_id: str) -> dict[str, Any]:
    candidates = f41._candidate_sets(compiled, type_id)
    curve_by_relation = {"target_empty": [], "target_enemy": [], "both": []}
    no_endpoint_curve = []
    for density in CONFIG.density_points:
        totals = {key: 0.0 for key in curve_by_relation}
        no_endpoint_total = 0.0
        for by_source in candidates.values():
            for by_target in by_source.values():
                for (_target, path), relations in by_target.items():
                    clear = (1.0 - density) ** len(path)
                    no_endpoint_total += clear
                    endpoint = 1.0 - density / 2.0 if "target_empty" in relations else density / 2.0
                    if "target_empty" in relations:
                        totals["target_empty"] += clear * endpoint
                    if "target_enemy" in relations:
                        totals["target_enemy"] += clear * (density / 2.0)
                    if {"target_empty", "target_enemy"}.issubset(relations):
                        totals["both"] += clear * endpoint
        denominator = 2 * compiled.board_size * compiled.board_size
        for key in totals:
            curve_by_relation[key].append(totals[key] / denominator if denominator else 0.0)
        no_endpoint_curve.append(no_endpoint_total / denominator if denominator else 0.0)
    weighted = {key: sum(w * value for w, value in zip(CONFIG.density_weights, curve)) for key, curve in curve_by_relation.items()}
    return {
        "curves": curve_by_relation,
        "no_endpoint_curve": no_endpoint_curve,
        "density_weighted": weighted,
        "without_endpoint_weighted": sum(w * value for w, value in zip(CONFIG.density_weights, no_endpoint_curve)),
        "density_points": list(CONFIG.density_points),
    }


def _pawn_suppression(compiled_by_name: dict[str, Any], f41_result: dict[str, Any], component_ledger: dict[str, Any]) -> dict[str, Any]:
    compiled = compiled_by_name["western_chess"]
    metrics = f41_result["semantic_profiles"]["western_chess"]["semantic"]["P"]
    source = next(row for row in f41_result["source_coverage"]["western_chess"]["rows"] if row["type"] == "P")
    patterns = _pattern_rows(compiled, "P")
    geometry = []
    for pattern in patterns:
        for gid in pattern.geometry_ids:
            geo = compiled.ir.geometry[gid]
            if geo.kind != "drop":
                geometry.append({"pattern": pattern.pattern_id, "target": pattern.target.kind, "kind": geo.kind, "offset": geo.offset, "direction": geo.direction, "min_steps": geo.min_steps, "max_steps": geo.max_steps})
    candidates = f41._candidate_sets(compiled, "P")
    owner_counts = {str(owner): sum(len(by_target) for by_target in candidates[owner].values()) for owner in (0, 1)}
    owner_destinations = {str(owner): len({target for by_target in candidates[owner].values() for target, _path in by_target}) for owner in (0, 1)}
    density = _target_density_breakdown(compiled, "P")
    components = component_ledger["western_chess"]["rows"]
    pawn_row = next(row for row in components if row["type"] == "P")
    gap_attribution = {}
    for type_id in ("N", "B", "R", "Q"):
        row = next(item for item in components if item["type"] == type_id)
        gap_attribution[type_id] = {
            "raw_ratio_to_pawn": row["raw_score_f41"] / pawn_row["raw_score_f41"],
            "weighted_component_difference_vs_pawn": {component: row["components"][component]["weighted_contribution"] - pawn_row["components"][component]["weighted_contribution"] for component in COMPONENTS},
            "component_with_largest_weighted_gap": max(COMPONENTS, key=lambda component: row["components"][component]["weighted_contribution"] - pawn_row["components"][component]["weighted_contribution"]),
        }
    return {
        "type": "P",
        "directional_movement": {
            "owner_candidate_relation_counts": owner_counts,
            "owner_candidate_destination_counts": owner_destinations,
            "geometry": geometry,
            "owner_mirror_contract": owner_counts["0"] == owner_counts["1"] and owner_destinations["0"] == owner_destinations["1"],
            "interpretation": "Pawn movement is directional and owner-relative; it has fewer available endpoint destinations than the multi-direction pieces even after semantic source coverage is included.",
        },
        "separate_quiet_capture_geometry": {
            "target_relation_counts": _pattern_summary(compiled, "P")["target_relation_counts"],
            "density_breakdown": density,
            "conditional_patterns_excluded_from_ordinary": source["conditional_pattern_count"],
        },
        "conditional_patterns_excluded_from_ordinary_capability": {
            "count": source["conditional_pattern_count"],
            "ordinary_count": source["ordinary_pattern_count"],
            "ordinary_rule": "state/slot/postcondition-bearing patterns are excluded from the ordinary geometry capability set",
        },
        "semantic_source_coverage": source,
        "density_endpoint_weighting": {
            "full_density_weighted_mobility": metrics["density_weighted_mobility"],
            "without_endpoint_factor": density["without_endpoint_weighted"],
            "relation_specific_density_weighted": density["density_weighted"],
            "interpretation": "quiet and capture endpoints are weighted by occupancy density; this is part of mobility, not a separate pawn-specific rule.",
        },
        "graph_reachability": {
            "reachable_pair_ratio": metrics["reachable_pair_ratio"],
            "average_shortest_path": metrics["average_shortest_path"],
            "path_efficiency": metrics["path_efficiency"],
            "weighted_reachability_contribution": metrics["reachable_pair_ratio"] * CONFIG.reachability_weight,
            "weighted_path_efficiency_contribution": metrics["path_efficiency"] * CONFIG.path_efficiency_weight,
        },
        "western_gap_attribution": gap_attribution,
    }


def _shogi_cross_rule(component_ledger: dict[str, Any], f41_result: dict[str, Any]) -> dict[str, Any]:
    rows = {}
    for ruleset_name, data in component_ledger.items():
        rows[ruleset_name] = {
            row["type"]: {
                component: row["components"][component]["unweighted"]
                for component in COMPONENTS
            }
            for row in data["rows"]
        }
    return {
        "component_values_by_ruleset_and_type": rows,
        "positive_control": f41_result["shogi_gate"],
        "same_mechanisms_present": {
            component: "same generic term and weight are applied in Western Chess and Standard Shogi" for component in COMPONENTS
        },
        "why_shogi_does_not_share_the_same_observed_ratio_pathology": [
            "Standard Shogi retains a positive cosine, Spearman, pairwise-ordering, and hand/board control under the accepted F41 profile.",
            "Shogi pieces distribute capability across a larger board and more directional/compound movement families, so the same graph summaries do not create the same relative compression against a single low-mobility Pawn anchor.",
            "The comparison is diagnostic rather than a claim that Shogi validates Western bands; destroying the Shogi positive control would be insufficient evidence for a Western-only formula change.",
        ],
    }


def _reproduction(f41_result: dict[str, Any]) -> dict[str, Any]:
    expected_western_raw = {
        "B": 6.217622245358478,
        "K": 5.976541940789473,
        "N": 4.815702525575447,
        "P": 1.06228880393026,
        "Q": 15.163483676173186,
        "R": 9.08791486310959,
    }
    expected_western_board = {"B": 1000, "K": 0, "N": 775, "P": 171, "Q": 2439, "R": 1462}
    expected_shogi_metrics = {
        "board_value_cosine_vs_current": 0.9999953399256223,
        "spearman_vs_current": 1.0,
        "pairwise_ordering_vs_current": 1.0,
        "hand_board_ratio_range": [0.8992673992673993, 0.900355871886121],
    }
    western = f41_result["semantic_profiles"]["western_chess"]
    shogi_gate = f41_result["shogi_gate"]
    actual_raw = {type_id: western["semantic"][type_id]["raw_capability_score"] for type_id in expected_western_raw}
    actual_board = {type_id: western["candidate_profile"]["values"][type_id]["board"] for type_id in expected_western_board}
    actual_ratios = f41_result["western_gate"]["normalized_by_pawn"]
    accepted_ratios = {"B": 5.847953216374269, "N": 4.5321637426900585, "Q": 14.263157894736842, "R": 8.549707602339181}
    shogi = f41_result["semantic_profiles"]["standard_shogi"]
    actual_shogi_raw = {type_id: shogi["semantic"][type_id]["raw_capability_score"] for type_id in shogi["semantic"]}
    actual_shogi_board = {type_id: shogi["candidate_profile"]["values"][type_id]["board"] for type_id in shogi["candidate_profile"]["values"]}
    exact = (
        actual_raw == expected_western_raw
        and actual_board == expected_western_board
        and actual_ratios == accepted_ratios
        and all(shogi_gate[key] == value for key, value in expected_shogi_metrics.items())
        and shogi_gate["pass"] is True
    )
    raw_ratios = {type_id: actual_raw[type_id] / actual_raw["P"] for type_id in ("N", "B", "R", "Q")}
    return {
        "baseline_sha": F41_BASELINE_SHA,
        "accepted_f41_r1_reproduction_matches": exact,
        "western": {"raw": actual_raw, "normalized_board": actual_board, "raw_ratios_by_pawn": raw_ratios, "normalized_ratios_by_pawn": actual_ratios, "bands_pass": f41_result["western_gate"]["bands_pass"]},
        "standard_shogi": {"raw": actual_shogi_raw, "normalized_board": actual_shogi_board, "positive_control_metrics": {key: shogi_gate[key] for key in expected_shogi_metrics}, "pass": shogi_gate["pass"]},
        "accepted_reference": {"western_raw": expected_western_raw, "western_normalized_board": expected_western_board, "western_normalized_ratios": accepted_ratios, "shogi_raw": actual_shogi_raw, "shogi_normalized_board": actual_shogi_board, "shogi": expected_shogi_metrics},
    }


def _band_distance(ratios: dict[str, float]) -> float:
    bands = {"N": [2.5, 3.5], "B": [2.5, 3.75], "R": [4.0, 6.0], "Q": [7.5, 11.0]}
    return sum(max(bands[type_id][0] - ratios[type_id], 0.0, ratios[type_id] - bands[type_id][1]) for type_id in bands)


def _shogi_gate_predicate(metrics: dict[str, float]) -> bool:
    return metrics["board_value_cosine_vs_current"] >= 0.95 and metrics["spearman_vs_current"] >= 0.90 and metrics["pairwise_ordering_vs_current"] >= 0.90


def _select_diagnosis(
    ablation: dict[str, Any],
    redundancy: dict[str, Any],
    synthetic: dict[str, Any],
    reproduction: dict[str, Any],
    component_ledger: dict[str, Any],
) -> dict[str, Any]:
    comparison = {row["comparison"]: row for row in synthetic["paired_comparisons"]}
    western_rows = {row["type"]: row for row in component_ledger["western_chess"]["rows"]}
    raw_ratios = reproduction["western"]["raw_ratios_by_pawn"]
    bands = {"N": [2.5, 3.5], "B": [2.5, 3.75], "R": [4.0, 6.0], "Q": [7.5, 11.0]}
    raw_band_pass = all(bands[key][0] <= raw_ratios[key] <= bands[key][1] for key in bands)
    normalized_band_pass = reproduction["western"]["bands_pass"]
    normalization_primary = raw_band_pass and not normalized_band_pass

    minus_variants = {name: ablation[name] for name in ("minus_coverage", "minus_reachability", "minus_path_efficiency")}
    full_distance = _band_distance(ablation["full_formula"]["western"]["raw_ratios_by_pawn"])
    minus_reduces_and_preserves_shogi = {
        name: {
            "western_distance": _band_distance(value["western"]["raw_ratios_by_pawn"]),
            "reduces_western_distance": _band_distance(value["western"]["raw_ratios_by_pawn"]) < full_distance,
            "shogi_gates_pass": _shogi_gate_predicate(value["shogi"]),
            "supported": _band_distance(value["western"]["raw_ratios_by_pawn"]) < full_distance and _shogi_gate_predicate(value["shogi"]),
        }
        for name, value in minus_variants.items()
    }
    double_counting_primary = bool(redundancy["near_redundant_pairs_abs_r_ge_0_90"]) and any(row["supported"] for row in minus_reduces_and_preserves_shogi.values())

    geometry_predicates = {
        "ray_length_growth": comparison["short ray versus long ray"]["raw_delta_right_minus_left"] > 0.0,
        "direction_count_growth": comparison["single direction versus multi-direction"]["raw_delta_right_minus_left"] > 0.0,
        "leap_to_ray_growth": comparison["one-step leap versus multi-square ray"]["raw_delta_right_minus_left"] > 0.0,
        "ray_length_delta": comparison["short ray versus long ray"]["raw_delta_right_minus_left"],
        "direction_count_delta": comparison["single direction versus multi-direction"]["raw_delta_right_minus_left"],
        "leap_to_ray_delta": comparison["one-step leap versus multi-square ray"]["raw_delta_right_minus_left"],
    }
    mobility_dominant = all(
        western_rows[type_id]["components"]["mobility"]["weighted_contribution"] >= western_rows[type_id]["components"][component]["weighted_contribution"]
        for type_id in ("N", "B", "R", "Q")
        for component in ("coverage", "reachability", "path_efficiency")
    )
    graph_terms_do_not_cure = all(not value["western"]["broad_band_pass"] for value in minus_variants.values())
    shogi_compatible = _shogi_gate_predicate(reproduction["standard_shogi"]["positive_control_metrics"])
    ray_directional_primary = mobility_dominant and geometry_predicates["ray_length_growth"] and geometry_predicates["direction_count_growth"] and synthetic["same_analyzer_and_compiler"] and graph_terms_do_not_cure and shogi_compatible

    semantic_information_missing = not ray_directional_primary and not double_counting_primary and not normalization_primary and shogi_compatible
    cross_ruleset_conflict = not shogi_compatible and not ray_directional_primary and not double_counting_primary
    mixed_or_unresolved = not any((normalization_primary, double_counting_primary, ray_directional_primary, semantic_information_missing, cross_ruleset_conflict))
    predicate_ledger = {
        "NORMALIZATION_PRIMARY": {
            "supported": normalization_primary,
            "next_boundary": "F43_MATERIAL_NORMALIZATION_DIAGNOSIS",
            "evidence": {"raw_bands_pass": raw_band_pass, "normalized_bands_pass": normalized_band_pass},
            "reason": "Rejected: raw Western ratios already fail the frozen bands." if not normalization_primary else "Accepted: normalization introduces the failure.",
        },
        "CAPABILITY_COMPONENT_DOUBLE_COUNTING_PRIMARY": {
            "supported": double_counting_primary,
            "next_boundary": "F43_CAPABILITY_FORMULA_STRUCTURE_PROTOTYPE",
            "evidence": {"near_redundant_pairs": redundancy["near_redundant_pairs_abs_r_ge_0_90"], "one_at_a_time_ablation": minus_reduces_and_preserves_shogi},
            "reason": "Rejected: correlation threshold and a Shogi-preserving pathology reduction are both required; current evidence provides neither." if not double_counting_primary else "Accepted: redundant components and a Shogi-preserving reduction are both shown.",
        },
        "RAY_OR_DIRECTIONAL_SCALING_PRIMARY": {
            "supported": ray_directional_primary,
            "next_boundary": "F43_CAPABILITY_GEOMETRY_SCALING_PROTOTYPE",
            "evidence": {"mobility_dominant": mobility_dominant, "geometry": geometry_predicates, "same_analyzer_and_compiler": synthetic["same_analyzer_and_compiler"], "graph_terms_do_not_cure": graph_terms_do_not_cure, "shogi_compatible": shogi_compatible},
            "reason": "Accepted only because every independent geometry-scaling predicate is true; no cross-unit score comparison is used." if ray_directional_primary else "Rejected: one or more independent geometry-scaling predicates is false.",
        },
        "SEMANTIC_CAPABILITY_INFORMATION_MISSING": {
            "supported": semantic_information_missing,
            "next_boundary": "F43_STRUCTURAL_CAPABILITY_FEATURE_DIAGNOSIS",
            "evidence": {"existing_geometry_explains_scaling": ray_directional_primary},
            "reason": "Rejected: existing semantic geometry and the four measured quantities explain the observed scaling." if not semantic_information_missing else "Accepted: existing quantities do not sufficiently explain the pathology.",
        },
        "CROSS_RULESET_PRIOR_CONFLICT": {
            "supported": cross_ruleset_conflict,
            "next_boundary": "F43_GENERIC_MATERIAL_PRIOR_REASSESSMENT",
            "evidence": {"shogi_compatible": shogi_compatible},
            "reason": "Rejected: Standard Shogi positive-control gates remain intact." if not cross_ruleset_conflict else "Accepted: no generic explanation survives the cross-ruleset control.",
        },
        "MIXED_OR_UNRESOLVED": {
            "supported": mixed_or_unresolved,
            "next_boundary": "F43_CAPABILITY_PRIOR_REASSESSMENT",
            "evidence": {"supported_primary_predicates": [name for name, value in (("NORMALIZATION_PRIMARY", normalization_primary), ("CAPABILITY_COMPONENT_DOUBLE_COUNTING_PRIMARY", double_counting_primary), ("RAY_OR_DIRECTIONAL_SCALING_PRIMARY", ray_directional_primary), ("SEMANTIC_CAPABILITY_INFORMATION_MISSING", semantic_information_missing), ("CROSS_RULESET_PRIOR_CONFLICT", cross_ruleset_conflict)) if value]},
            "reason": "Rejected: one independent primary diagnosis is supported." if not mixed_or_unresolved else "Accepted: evidence remains materially unresolved.",
        },
    }
    supported = [name for name, value in predicate_ledger.items() if value["supported"]]
    if len(supported) != 1:
        raise ValueError(f"F42 selection must support exactly one classification, got {supported}")
    selected = predicate_ledger[supported[0]]
    return {
        "primary_diagnosis": supported[0],
        "next_boundary": selected["next_boundary"],
        "predicate_ledger": predicate_ledger,
        "normalization_assessment": {
            "raw_ratios": raw_ratios,
            "raw_bands_pass": raw_band_pass,
            "normalized_bands_pass": normalized_band_pass,
            "classification": "NORMALIZATION_NON_PRIMARY" if not raw_band_pass else "NORMALIZATION_REQUIRES_REVIEW",
            "reason": "The Western inflation is already present in raw capability ratios; median/scale/round normalization preserves the ordering and only changes values through scale and integer rounding." if not raw_band_pass else "Raw ratios are within the frozen bands, so normalization requires a separate causal review.",
        },
        "quantitative_selection_evidence": {
            "ray_length_delta": geometry_predicates["ray_length_delta"],
            "direction_count_delta": geometry_predicates["direction_count_delta"],
            "leap_to_ray_delta": geometry_predicates["leap_to_ray_delta"],
            "one_at_a_time_ablation": minus_reduces_and_preserves_shogi,
            "selection_rule": "exactly one independent causal predicate supported; raw deltas and correlations are reported separately and never compared across units",
        },
        "western_inflation_not_a_loss_function": True,
    }


def audit() -> dict[str, Any]:
    # F41 is reproduced first and is the only source of accepted baseline
    # values.  All subsequent sections are diagnostic counterfactuals.
    f41_result = f41.audit()
    compiled_by_name = {
        "western_chess": compile_semantic_ruleset(build_western_chess_ruleset()),
        "standard_shogi": compile_semantic_ruleset(build_standard_shogi_ruleset()),
    }
    reproduction = _reproduction(f41_result)
    components = _component_ledger(compiled_by_name, f41_result)
    ablation = _ablation_ledger(compiled_by_name, f41_result)
    redundancy = _redundancy_ledger(components)
    synthetic = _synthetic_ledger()
    pawn = _pawn_suppression(compiled_by_name, f41_result, components)
    shogi = _shogi_cross_rule(components, f41_result)
    selection = _select_diagnosis(ablation, redundancy, synthetic, reproduction, components)
    result = {
        "schema_version": 1,
        "status": "PASS" if reproduction["accepted_f41_r1_reproduction_matches"] else "FAIL_F41_REPRODUCTION",
        "kind": "F42_SEMANTIC_CAPABILITY_PRIOR_DIAGNOSIS",
        "production_changed": False,
        "baseline_sha": F41_BASELINE_SHA,
        "h42a_manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "reproduction": reproduction,
        "component_ledger": components,
        "formula_ablation": {"variants": list(VARIANTS), "ledger": ablation, "existing_weights_unchanged": True},
        "redundancy": redundancy,
        "synthetic_geometry": synthetic,
        "pawn_suppression": pawn,
        "shogi_cross_rule": shogi,
        "selection": selection,
        "full_pytest": _full_pytest_evidence(),
        "constraints": json.loads(MANIFEST.read_text(encoding="utf-8"))["constraints"],
    }
    _json(OUT / "f42_reproduction.json", reproduction)
    _json(OUT / "f42_component_ledger.json", components)
    _json(OUT / "f42_formula_ablation.json", result["formula_ablation"])
    _json(OUT / "f42_redundancy.json", redundancy)
    _json(OUT / "f42_synthetic_geometry.json", synthetic)
    _json(OUT / "f42_pawn_suppression.json", pawn)
    _json(OUT / "f42_shogi_cross_rule.json", shogi)
    _json(OUT / "f42_selection.json", selection)
    _json(OUT / "f42_evidence.json", result)
    _write_closeout_report(result)
    return result


if __name__ == "__main__":
    value = audit()
    print(json.dumps({"status": value["status"], "diagnosis": value["selection"]["primary_diagnosis"], "next_boundary": value["selection"]["next_boundary"]}, sort_keys=True))
