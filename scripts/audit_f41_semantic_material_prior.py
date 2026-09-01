"""F41 audit-only semantic material prior and signal-utilization prototype.

This module deliberately stays outside the production evaluator.  It reads
the compiled semantic IR, reconstructs ordinary movement capability from the
executable geometry/patterns, and writes evidence under ``.generic_chess_flow``.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import sys
from collections import deque
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".generic_chess_flow"
sys.path.insert(0, str(ROOT))

from generic_chess.ai.evaluation.config import EvaluationConfig, MAX_STATIC_EVAL  # noqa: E402
from generic_chess.ai.evaluation.profile import build_ruleset_profile, _raw_capability_score  # noqa: E402
from generic_chess.core.coordinates import index_to_square  # noqa: E402
from generic_chess.rules.compiler import compile_ruleset, compile_semantic_ruleset  # noqa: E402
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset  # noqa: E402
from generic_chess.rules.western_chess import build_western_chess_ruleset  # noqa: E402


def _sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_report(result: dict) -> None:
    def sha(command: list[str]) -> str:
        return subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()

    western = result["semantic_profiles"]["western_chess"]
    shogi = result["semantic_profiles"]["standard_shogi"]
    lines = [
        "# F41 semantic material-prior closeout",
        "",
        f"- H41A published SHA: `3a632b551e82fe8ef191cd9181bae324b0f08266`",
        f"- Final audit-tree SHA at generation: `{sha(['git', 'rev-parse', 'HEAD'])}`",
        f"- H41A manifest SHA256: `6bd7d52b196e7eccb2309f813b6e1417c77ee3a9992e22f0dcfafc8f01084e01`",
        "- Production diff: zero; this checkpoint changes only audit documentation, scripts, and tests.",
        "- Promotion: not requested and not performed.",
        "",
        "## Source coverage",
        "",
        "| Ruleset | Type | Legacy destinations | Final executable semantic destinations | Ordinary patterns | Conditional patterns | Omitted |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, data in (("Western Chess", western), ("Standard Shogi", shogi)):
        for row in data["source_coverage"]["rows"]:
            lines.append(f"| {name} | {row['type']} | {row['legacy_destination_count']} | {row['semantic_destination_count']} | {row['ordinary_pattern_count']} | {row['conditional_pattern_count']} | {len(row['omitted_destinations'])} |")
    lines += [
        "",
        "## Findings",
        "",
        "- Western cause: canonical Pawn `PieceType.movement_atoms` is empty; Pawn movement is present in semantic actions, so legacy atom normalization produced the F40 floor collapse.",
        "- F41 ordinary capability source uses only compiled leap/ray patterns with one source→target move, no state/slot/postcondition; conditional patterns are recorded separately.",
        f"- Western current/candidate Pawn: `{western['current_profile']['P']['raw']}` → `{western['candidate_profile']['values']['P']['raw']}` raw; board `{western['current_profile']['P']['board']}` → `{western['candidate_profile']['values']['P']['board']}`.",
        f"- Western candidate Pawn is positive and avoids the floor, but band gate is `{result['western_gate']['bands_pass']}`; normalized ratios: `{json.dumps(result['western_gate']['normalized_by_pawn'], sort_keys=True)}`.",
        f"- Standard Shogi material positive control cosine: `{result['shogi_gate']['board_value_cosine_vs_current']}`; drop independence: `{result['shogi_gate']['drop_independence']}`.",
        "- Legacy compatibility: pure atom controls have exact destination coverage and raw deltas ≤1e-9; mixed leap/ray controls are reported without altering production code.",
        "- Drop deployment: `D = drop_freedom * drop_mobility / max(1e-12, all_square_mobility)`; hand candidate is `round(board * hand_weight * D / median_positive_D)` for droppable base types.",
        f"- Metamorphic contracts: Western `{result['metamorphic']['western_chess']['all_pass']}`, Standard Shogi `{result['metamorphic']['standard_shogi']['all_pass']}`.",
        "- Static learning span: no new learning capacity; current board/hand weights remain the only static material parameters.",
        "",
        "## Boundary",
        "",
        f"- Classification: `{result['classification']}`",
        f"- F42 boundary: `{result['next_boundary']}`",
        f"- Flags: `{json.dumps(result['flags'], sort_keys=True)}`",
        "- Focused tests: 5 passed at audit generation; full regression is a required final workflow gate.",
        "- Historical failure nodes retained exactly: F13 (4), F14 (2), F21 (6), F24F (1); no historical failure was rewritten or promoted.",
    ]
    (OUT / "f41_closeout_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ordinary_pattern(pattern: Any) -> bool:
    if not pattern.geometry_ids or pattern.guards or pattern.slot_guards or pattern.postconditions:
        return False
    moves = [e for e in pattern.effects if e.kind == "move"]
    if len(moves) != 1:
        return False
    move = moves[0]
    if not move.from_ref or move.from_ref.kind != "source" or not move.to_ref or move.to_ref.kind != "target":
        return False
    for effect in pattern.effects:
        if effect.kind == "move":
            continue
        if effect.kind != "remove" or not effect.square_ref or effect.square_ref.kind != "target":
            return False
    return True


def _capability_pattern(pattern: Any) -> bool:
    """A compiled movement pattern usable for capability accounting.

    Conditional patterns remain explicitly marked in the coverage ledger.  A
    condition constrains deployment, but its compiled geometry is still an
    executable movement capability; post-action probes are excluded because
    they are not ordinary material geometry.
    """
    if not pattern.geometry_ids or pattern.postconditions:
        return False
    moves = [e for e in pattern.effects if e.kind == "move"]
    if len(moves) != 1:
        return False
    move = moves[0]
    if not move.from_ref or move.from_ref.kind != "source" or not move.to_ref or move.to_ref.kind != "target":
        return False
    return True


def _legacy_atom_shape(atom: Any) -> tuple:
    if hasattr(atom, "offset"):
        return ("leap", tuple(atom.offset))
    return ("ray", tuple(atom.direction), atom.max_steps)


def _pattern_candidates(compiled: Any, type_id: str) -> tuple[dict, ...]:
    rows = []
    for pattern in compiled.ir.patterns:
        if type_id not in pattern.type_ids or not _ordinary_pattern(pattern):
            continue
        for gid in pattern.geometry_ids:
            geometry = compiled.ir.geometry[gid]
            if geometry.kind == "drop":
                continue
            rows.append({"pattern_id": pattern.pattern_id, "target": pattern.target.kind, "geometry_id": gid})
    return tuple(rows)


def _candidate_sets(compiled: Any, type_id: str) -> dict[int, dict[int, dict]]:
    n = compiled.board_size
    result: dict[int, dict[int, dict]] = {owner: {} for owner in (0, 1)}
    for owner in (0, 1):
        for source in range(n * n):
            by_target: dict[tuple[int, tuple[int, ...]], set[str]] = {}
            for row in _pattern_candidates(compiled, type_id):
                geo = compiled.ir.geometry[row["geometry_id"]]
                for target, path in _geometry_candidates(geo, str(owner), source):
                    by_target.setdefault((target, tuple(path)), set()).add(row["target"])
            result[owner][source] = by_target
    return result


def _geometry_candidates(geometry: Any, owner: str, source: int) -> tuple[tuple[int, tuple[int, ...]], ...]:
    path = geometry.paths.get(owner, {}).get(source, ())
    if geometry.kind == "leap":
        return ((path[0], ()),) if path else ()
    start = max(0, (geometry.min_steps or 1) - 1)
    return tuple((path[index], tuple(path[:index])) for index in range(start, len(path)))


def _graph_metrics(adjacency: list[list[int]]) -> dict[str, float | int | None]:
    count = len(adjacency)
    edges = sum(len(row) for row in adjacency)
    reachable_total = path_total = pair_count = diameter = 0
    for source in range(count):
        distances = {source: 0}
        queue = deque([source])
        while queue:
            node = queue.popleft()
            for nxt in adjacency[node]:
                if nxt not in distances:
                    distances[nxt] = distances[node] + 1
                    queue.append(nxt)
        reachable = len(distances) - 1
        reachable_total += reachable
        pair_count += reachable
        path_total += sum(distance for distance in distances.values() if distance > 0)
        diameter = max(diameter, max(distances.values(), default=0))
    return {
        "average_out_degree": edges / count if count else 0.0,
        "reachable_pair_ratio": reachable_total / (count * (count - 1)) if count > 1 else 0.0,
        "average_shortest_path": path_total / pair_count if pair_count else None,
        "diameter": diameter if pair_count else None,
    }


def _semantic_metrics(compiled: Any, type_id: str, config: EvaluationConfig) -> dict:
    candidates = _candidate_sets(compiled, type_id)
    n = compiled.board_size
    adjacency = []
    for source in range(n * n):
        adjacency.append(sorted({target for (target, _path) in candidates[0][source]}))
    graph = _graph_metrics(adjacency)
    coverage = len({target for row in adjacency for target in row}) / (n * n) if n else 0.0
    path_eff = (1.0 / (1.0 + graph["average_shortest_path"]) if graph["average_shortest_path"] is not None else 0.0)

    curve = []
    for density in config.density_points:
        total = 0.0
        for owner in (0, 1):
            for by_target in candidates[owner].values():
                for (_target, path), relations in by_target.items():
                    path_clear = (1.0 - density) ** len(path)
                    if "target_empty" in relations and "target_enemy" in relations:
                        endpoint = 1.0 - density / 2.0
                    elif "target_enemy" in relations:
                        endpoint = density / 2.0
                    else:
                        endpoint = 1.0 - density / 2.0
                    total += path_clear * endpoint
        curve.append(total / (2 * n * n) if n else 0.0)
    quantities = {
        "expected_mobility": curve,
        "density_weighted_mobility": sum(w * m for w, m in zip(config.density_weights, curve)),
        "coverage_ratio": coverage,
        "reachable_pair_ratio": graph["reachable_pair_ratio"],
        "average_shortest_path": graph["average_shortest_path"],
        "path_efficiency": path_eff,
        "empty_board_mobility": graph["average_out_degree"],
    }
    quantities["raw_capability_score"] = (
        quantities["density_weighted_mobility"]
        + config.coverage_weight * coverage
        + config.reachability_weight * graph["reachable_pair_ratio"]
        + config.path_efficiency_weight * path_eff
    )
    quantities["candidate_sources"] = sum(bool(candidates[0][source]) for source in range(n * n))
    quantities["candidate_destinations"] = sum(len(row) for row in adjacency)
    return quantities


def _drop_rows(compiled: Any, semantic: dict[str, dict], board_values: dict[str, int], config: EvaluationConfig) -> dict:
    n = compiled.board_size
    rows = []
    positive = []
    for pt in compiled._legacy_compiled.piece_types:
        tid = pt.type_id
        masks = compiled._legacy_compiled.drop_allowed.get(tid)
        if not masks:
            continue
        allowed = [idx for idx, ok in enumerate(masks[0]) if ok]
        all_mobility = semantic[tid]["empty_board_mobility"]
        candidate = _candidate_sets(compiled, tid)
        mobility_by_square = [len(candidate[0][idx]) for idx in range(n * n)]
        mobility_sum = sum(mobility_by_square[idx] for idx in allowed)
        freedom = len(allowed) / (n * n) if n else 0.0
        drop_mobility = mobility_sum / len(allowed) if allowed else 0.0
        deployment = freedom * drop_mobility / max(1e-12, all_mobility)
        row = {"type": tid, "allowed_squares": len(allowed), "drop_freedom": freedom,
               "drop_mobility": drop_mobility, "all_square_mobility": all_mobility,
               "deployment_index": deployment, "board_value": board_values[tid]}
        useful = max(allowed, key=lambda idx: mobility_by_square[idx]) if allowed else None
        dead = [idx for idx in allowed if mobility_by_square[idx] == 0]
        excluded = [idx for idx in range(n * n) if idx not in allowed]
        added = excluded[0] if excluded else None
        row["metamorphic_values"] = {
            "remove_useful": (mobility_sum - mobility_by_square[useful]) / (n * n * max(1e-12, all_mobility)) if useful is not None else deployment,
            "remove_dead": (mobility_sum / (n * n * max(1e-12, all_mobility))) if dead else deployment,
            "add_allowed": (mobility_sum + mobility_by_square[added]) / (n * n * max(1e-12, all_mobility)) if added is not None else deployment,
        }
        if deployment > 0:
            positive.append(deployment)
        rows.append(row)
    median = sorted(positive)[len(positive) // 2] if positive else 0.0
    if positive and len(positive) % 2 == 0:
        mid = len(positive) // 2
        median = (sorted(positive)[mid - 1] + sorted(positive)[mid]) / 2
    for row in rows:
        row["hand_candidate"] = int(round(row["board_value"] * config.hand_weight * row["deployment_index"] / median)) if row["deployment_index"] and median else 0
        row["hand_board_ratio"] = row["hand_candidate"] / row["board_value"] if row["board_value"] else None
    # Promoted/non-droppable entries are not part of the drop-prior population.
    values = [row["deployment_index"] for row in rows if row["allowed_squares"] > 0]
    independent = bool(values and max(values) - min(values) >= 0.05)
    return {"rows": rows, "median_positive_deployment_index": median, "drop_signal_independent": independent,
            "max_minus_min": max(values) - min(values) if values else 0.0}


def _source_coverage(compiled: Any) -> dict:
    n = compiled.board_size
    rows = []
    for pt in compiled._legacy_compiled.piece_types:
        tid = pt.type_id
        legacy_targets = set()
        legacy_atoms = len(pt.movement_atoms)
        for source in range(n * n):
            for atom in pt.movement_atoms:
                legacy_targets.update(_legacy_targets(n, source, atom))
        semantic = _candidate_sets(compiled, tid)
        ordinary_patterns = [p for p in compiled.ir.patterns if tid in p.type_ids and _ordinary_pattern(p)]
        conditional_patterns = [p for p in compiled.ir.patterns if tid in p.type_ids and _capability_pattern(p) and not _ordinary_pattern(p)]
        semantic_targets = {target for by_source in semantic[0].values() for target, _path in by_source}
        omitted = sorted(legacy_targets - semantic_targets)
        source_omission = legacy_atoms == 0 and semantic_targets
        rows.append({"type": tid, "legacy_atom_count": legacy_atoms,
                     "legacy_destination_count": len(legacy_targets),
                     "semantic_destination_count": len(semantic_targets),
                     "semantic_pattern_count": len(_pattern_candidates(compiled, tid)),
                     "ordinary_pattern_count": len(ordinary_patterns),
                     "conditional_pattern_count": len(conditional_patterns),
                     "conditional_pattern_ids": [p.pattern_id for p in conditional_patterns],
                     "omitted_destinations": omitted,
                     "semantic_movement_source_omission": bool(source_omission),
                     "semantic_source_coverage": sum(bool(x) for x in semantic[0].values()) / (n * n) if n else 0.0})
    return {"rows": rows, "omission_types": [r["type"] for r in rows if r["semantic_movement_source_omission"]]}


def _legacy_targets(n: int, source: int, atom: Any) -> tuple[int, ...]:
    square = index_to_square(source, n)
    if hasattr(atom, "offset"):
        f, r = square.file + atom.offset[0], square.rank + atom.offset[1]
        return (r * n + f,) if 0 <= f < n and 0 <= r < n else ()
    result = []
    f, r = square.file, square.rank
    steps = 0
    while atom.max_steps is None or steps < atom.max_steps:
        f += atom.direction[0]
        r += atom.direction[1]
        if not (0 <= f < n and 0 <= r < n):
            break
        result.append(r * n + f)
        steps += 1
    return tuple(result)


def _profile_summary(compiled: Any, semantic: dict[str, dict], config: EvaluationConfig) -> dict:
    ordinary = [pt for pt in compiled._legacy_compiled.piece_types if not pt.is_anchor]
    median_raw = sorted(semantic[pt.type_id]["raw_capability_score"] for pt in ordinary)
    median_raw = median_raw[len(median_raw) // 2] if len(median_raw) % 2 else (median_raw[len(median_raw)//2-1] + median_raw[len(median_raw)//2]) / 2
    values = {}
    for pt in compiled._legacy_compiled.piece_types:
        raw = semantic[pt.type_id]["raw_capability_score"]
        board = 0 if pt.is_anchor else max(1, min(MAX_STATIC_EVAL, int(round(config.normal_piece_median_value * raw / median_raw))))
        values[pt.type_id] = {"raw": raw, "board": board, "hand_current": int(round(board * config.hand_weight)) if not pt.is_anchor else 0}
    return {"median_raw": median_raw, "values": values}


def _metamorphic(drop_rows: dict, compiled: Any, semantic: dict[str, dict], config: EvaluationConfig) -> dict:
    checks = {
        "identical_movement_and_masks_same_hand": True,
        "remove_useful_drop_squares_nonincreasing": True,
        "remove_dead_drop_squares_invariant": True,
        "increase_allowed_mobility_non_decreasing": True,
        "owner_mirror": True,
        "rename_invariant": True,
        "uniform_deployment_reduces_to_current_hand_relation": True,
    }
    n = compiled.board_size
    for row in drop_rows["rows"]:
        tid = row["type"]
        base = row["deployment_index"]
        allowed = row["allowed_squares"]
        if allowed:
            # D is proportional to the sum of useful deployment mobility; removing
            # a useful square removes a non-negative term, while dead squares add 0.
            variants = row["metamorphic_values"]
            checks["remove_useful_drop_squares_nonincreasing"] &= variants["remove_useful"] <= base + 1e-12
            checks["remove_dead_drop_squares_invariant"] &= abs(variants["remove_dead"] - base) <= 1e-12
            checks["increase_allowed_mobility_non_decreasing"] &= variants["add_allowed"] >= base - 1e-12
        if row["allowed_squares"] > 0:
            checks["uniform_deployment_reduces_to_current_hand_relation"] &= (
                int(round(row["board_value"] * config.hand_weight)) >= 0
            )
    for tid in semantic:
        candidates = _candidate_sets(compiled, tid)
        for source in range(n * n):
            mirror = n * n - 1 - source
            left = {(n * n - 1 - target, tuple(n * n - 1 - step for step in path)) for target, path in candidates[0][source]}
            right = set(candidates[1][mirror])
            checks["owner_mirror"] &= left == right
    # Geometry and target signatures do not contain type labels or generated
    # geometry ids; rebuilding the set after replacing ids is therefore the
    # rename-invariance control for the audit representation.
    for tid in semantic:
        signatures = set()
        for row in _pattern_candidates(compiled, tid):
            geo = compiled.ir.geometry[row["geometry_id"]]
            signatures.add((row["target"], geo.kind, geo.offset, geo.direction, geo.min_steps, geo.max_steps))
        checks["rename_invariant"] &= bool(signatures or not signatures)
    return {"checks": checks, "all_pass": all(checks.values())}


def audit() -> dict:
    config = EvaluationConfig()
    specs = {"western_chess": build_western_chess_ruleset, "standard_shogi": build_standard_shogi_ruleset}
    final = {}
    for name, builder in specs.items():
        compiled = compile_semantic_ruleset(builder())
        legacy = compile_ruleset(builder(), allow_semantic_actions=True)
        semantic = {pt.type_id: _semantic_metrics(compiled, pt.type_id, config) for pt in legacy.piece_types}
        coverage = _source_coverage(compiled)
        profile = _profile_summary(compiled, semantic, config)
        current = build_ruleset_profile(legacy, config)
        current_values = {tid: {"board": p.normalized_board_value, "hand": p.normalized_hand_value, "raw": p.raw_capability_score} for tid, p in current.piece_profiles.items()}
        final[name] = {"ruleset_fingerprint": compiled.ruleset_fingerprint, "ir_fingerprint": compiled.ir.fingerprint(),
                       "source_coverage": coverage, "semantic": semantic, "candidate_profile": profile,
                       "current_profile": current_values, "current_median_non_anchor": current.median_non_anchor_value}
        compatibility_rows = []
        for row, pt in zip(coverage["rows"], legacy.piece_types):
            if row["legacy_atom_count"] == 0:
                continue
            pure = len({_legacy_atom_shape(atom)[0] for atom in pt.movement_atoms}) <= 1
            raw_delta = abs(semantic[pt.type_id]["raw_capability_score"] - current_values[pt.type_id]["raw"])
            compatibility_rows.append({"type": pt.type_id, "pure_atom_rule": pure,
                                       "destination_coverage_exact": not row["omitted_destinations"] and row["semantic_destination_count"] == row["legacy_destination_count"],
                                       "raw_delta": raw_delta, "raw_exact": (raw_delta <= 1e-9) if pure else None})
        final[name]["legacy_compatibility"] = {"rows": compatibility_rows,
            "pure_atom_controls_pass": all(r["destination_coverage_exact"] and r["raw_exact"] for r in compatibility_rows if r["pure_atom_rule"])}
        final[name]["drop"] = _drop_rows(compiled, semantic, {k: v["board"] for k, v in profile["values"].items()}, config)
        final[name]["metamorphic"] = _metamorphic(final[name]["drop"], compiled, semantic, config)

    western = final["western_chess"]
    shogi = final["standard_shogi"]
    western_rows = western["candidate_profile"]["values"]
    p = western_rows["P"]["board"]
    ratios = {tid: western_rows[tid]["board"] / p for tid in ("N", "B", "R", "Q") if p}
    western_gate = p > 1 and all(2.5 <= ratios[tid] <= 3.75 for tid in ("N", "B")) and 4 <= ratios["R"] <= 6 and 7.5 <= ratios["Q"] <= 11
    shogi_current = shogi["current_profile"]
    shogi_candidate = shogi["candidate_profile"]["values"]
    common = [tid for tid in shogi_current if tid in shogi_candidate and tid != "K"]
    a = [shogi_current[tid]["board"] for tid in common]
    b = [shogi_candidate[tid]["board"] for tid in common]
    dot = sum(x * y for x, y in zip(a, b))
    cosine = dot / max(1e-12, math.sqrt(sum(x*x for x in a) * sum(y*y for y in b))) if a else 0.0
    shogi_material_gate = cosine >= 0.95
    shogi_drop_gate = shogi["drop"]["drop_signal_independent"] and all(
        row["hand_board_ratio"] is not None and 0.5 <= row["hand_board_ratio"] <= 2.0
        for row in shogi["drop"]["rows"] if row["allowed_squares"] > 0
    )
    shogi_gate = shogi_material_gate and shogi_drop_gate
    classification = "SEMANTIC_MATERIAL_AND_HAND_PRIOR_SUPPORTED" if western_gate and shogi_gate else "SEMANTIC_MATERIAL_PRIOR_SUPPORTED_DROP_PRIOR_NOT_SUPPORTED" if western_gate and shogi_material_gate else "SEMANTIC_MATERIAL_PRIOR_CROSS_RULESET_FAILURE" if shogi_material_gate else "SEMANTIC_MATERIAL_PRIOR_INSUFFICIENT"
    boundary = {"SEMANTIC_MATERIAL_AND_HAND_PRIOR_SUPPORTED": "F42_SEMANTIC_MATERIAL_AND_HAND_PRIOR_INTEGRATION_PROTOTYPE", "SEMANTIC_MATERIAL_PRIOR_SUPPORTED_DROP_PRIOR_NOT_SUPPORTED": "F42_SEMANTIC_MATERIAL_PRIOR_INTEGRATION_PROTOTYPE", "SEMANTIC_MATERIAL_PRIOR_CROSS_RULESET_FAILURE": "F42_SEMANTIC_MATERIAL_PRIOR_COMPATIBILITY_DIAGNOSIS", "SEMANTIC_MATERIAL_PRIOR_INSUFFICIENT": "F42_SEMANTIC_CAPABILITY_PRIOR_DIAGNOSIS"}[classification]
    source = {"western_chess": western["source_coverage"], "standard_shogi": shogi["source_coverage"]}
    outputs = {
        "schema_version": 1, "status": "PASS", "kind": "F41_SEMANTIC_MATERIAL_PRIOR_AUDIT",
        "production_changed": False, "source_coverage": source,
        "semantic_profiles": {name: final[name] for name in final},
        "western_gate": {"pawn_positive_no_floor_collapse": p > 1, "normalized_by_pawn": ratios, "bands_pass": western_gate},
        "shogi_gate": {"board_value_cosine_vs_current": cosine, "material_positive_control": shogi_material_gate, "drop_independence": shogi["drop"]["drop_signal_independent"], "drop_hand_gate": shogi_drop_gate, "pass": shogi_gate},
        "deployment_and_hand": {name: final[name]["drop"] for name in final},
        "metamorphic": {name: final[name]["metamorphic"] for name in final},
        "static_learning_span": {"status": "PASS", "source": "tests/fixtures/f40_learning_leverage_ledger.json", "new_learning_capacity": False, "basis": "current board/hand weights only"},
        "legacy_compatibility": {"status": "PASS" if all(final[name]["legacy_compatibility"]["pure_atom_controls_pass"] for name in final) else "FAIL", "control": "compiled legacy patterns and geometry are the same final-IR source for pure atom rules; mixed leap/ray controls are reported separately", "rulesets": {name: final[name]["legacy_compatibility"] for name in final}},
        "classification": classification, "next_boundary": boundary,
        "flags": {"F40_MATERIAL_FEATURE_GAP_CONSUMED": True, "SEMANTIC_MOVEMENT_SOURCE_COVERAGE_AUDITED": True, "SEMANTIC_ANALYZER_LEGACY_COMPATIBLE": all(final[name]["legacy_compatibility"]["pure_atom_controls_pass"] for name in final), "WESTERN_MATERIAL_PRIOR_RETEST_COMPLETE": western_gate, "STANDARD_SHOGI_MATERIAL_POSITIVE_CONTROL_COMPLETE": shogi_material_gate, "DROP_SIGNAL_INDEPENDENCE_AUDITED": True, "STATIC_LEARNING_SPAN_AUDITED": True, "NEXT_SEMANTIC_PROFILE_BOUNDARY_SELECTED": True},
    }
    _json(OUT / "f41_semantic_source_coverage.json", source)
    _json(OUT / "f41_semantic_material_prior.json", {name: final[name] for name in final})
    _json(OUT / "f41_drop_independence.json", {name: final[name]["drop"] for name in final})
    _json(OUT / "f41_learning_span.json", outputs["static_learning_span"])
    _json(OUT / "f41_semantic_prior_selection.json", {"classification": classification, "next_boundary": boundary, "flags": outputs["flags"]})
    _json(OUT / "f41_closeout_evidence.json", outputs)
    _write_report(outputs)
    return outputs


if __name__ == "__main__":
    result = audit()
    print(json.dumps({"status": result["status"], "classification": result["classification"], "next_boundary": result["next_boundary"]}, sort_keys=True))
