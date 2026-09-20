"""F135: rebaseline the corrected Standard-Shogi known evaluator schema."""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from pathlib import Path

import numpy as np

try:
    from scripts.f122_reverse_benchmark_known_evaluator_system_identification import (
        COUNTS,
        FrozenBasis,
        _collect_fresh_roots,
        _king_escape_count,
        _action_ranking,
        _json_sha,
        _ranking_summary,
        _search_probe,
        _state_for_side,
        _sort_actions,
        _scalar_metrics,
    )
    from scripts.f123_reverse_benchmark_identifiability_optimizer_diagnosis import (
        _matched_ridge,
        _prepare,
        _proxy_fit,
        _scalar_summary,
    )
    from scripts.f124_reverse_benchmark_stable_convex_solver import _prediction_difference
    from scripts.f125_known_oracle_one_ply_search_compression import _prepare_filtered
    from scripts.f127_shogi_t1_scalar_compression_expanded_control import _pcg_tight
except ModuleNotFoundError as error:
    if error.name != "scripts":
        raise
    from f122_reverse_benchmark_known_evaluator_system_identification import COUNTS, FrozenBasis, _action_ranking, _collect_fresh_roots, _king_escape_count, _json_sha, _ranking_summary, _search_probe, _state_for_side, _sort_actions, _scalar_metrics
    from f123_reverse_benchmark_identifiability_optimizer_diagnosis import _matched_ridge, _prepare, _proxy_fit, _scalar_summary
    from f124_reverse_benchmark_stable_convex_solver import _prediction_difference
    from f125_known_oracle_one_ply_search_compression import _prepare_filtered
    from f127_shogi_t1_scalar_compression_expanded_control import _pcg_tight

from generic_chess.core.identity import position_identity_key
from generic_chess.core.declarations import available_declarations
from generic_chess.core.movegen import legal_actions
from generic_chess.core.terminal import TerminalStatus
from generic_chess.core.transition import apply_action, initial_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset


FAMILY = "standard_shogi"
LEGACY_ORACLE_SHA = "dda316e263a8f6e5a12678199e87cbedea7e4d40358d3087e8c78ddb3894a316"
CORPUS_SHA = "a1cb1bcf2d461c3bddc4f87928ed4d6260673de268356eec5741b9b534d4aa8b"
CORPUS_SEED = 1220201
ROOT_SEED = 1220221
L2 = 1e-6


class CorrectedShogiFrozenBasisV2(FrozenBasis):
    """F122's intended Shogi semantics with one keyed materialization path."""

    SCHEMA = "CorrectedShogiFrozenBasisV2"

    def _add_names_and_weights(self) -> None:
        for type_id in self.material_types:
            self._add(f"material_diff:{type_id}", self.base_values.get(type_id, self.base_values.get(type_id[1:], 100)))
        for type_id in self.board_types:
            for rank in range(self.n):
                for file in range(self.n):
                    self._add(f"occupancy_diff:{type_id}:{file}:{rank}", self._square_bonus(type_id, file, rank))
        for type_id in self.hand_types:
            self._add(f"hand_diff:{type_id}", round(self.base_values[type_id] * 1.05, 8))
        for name, weight in (("mobility_diff", 5.0), ("king_escape_diff", 12.0), ("king_zone_pressure_diff", 8.0), ("current_check_diff", 20.0), ("promotion_potential_diff", 15.0)):
            if name != "promotion_potential_diff":
                self._add(name, weight)
        for type_id in self.hand_types:
            self._add(f"legal_drop_count_diff:{type_id}", 2.0)
        self._add("mean_legal_drop_mobility_diff", 2.0)
        self._add("promotion_potential_diff", 15.0)
        # Restore the contract's exact semantic order: promotion precedes drops.
        promotion = self.names.pop(); promotion_weight = self.weights.pop()
        insert_at = self.names.index("current_check_diff") + 1
        self.names.insert(insert_at, promotion); self.weights.insert(insert_at, promotion_weight)

    def _feature_map(self, state) -> dict[str, float]:
        position = state.position
        side = position.side_to_move
        other = 1 - side
        current_actions, other_actions = self._side_actions(state)
        values: dict[str, float] = {}
        for type_id in self.material_types:
            own = sum(1 for piece in position.board if piece is not None and piece.owner == side and piece.current_type_id == type_id)
            opp = sum(1 for piece in position.board if piece is not None and piece.owner == other and piece.current_type_id == type_id)
            values[f"material_diff:{type_id}"] = float(own - opp)
        for type_id in self.board_types:
            for rank in range(self.n):
                for file in range(self.n):
                    piece = position.board[rank * self.n + file]
                    values[f"occupancy_diff:{type_id}:{file}:{rank}"] = float(0 if piece is None or piece.current_type_id != type_id else (1 if piece.owner == side else -1))
        for type_id in self.hand_types:
            values[f"hand_diff:{type_id}"] = float(position.hands[side].count(type_id) - position.hands[other].count(type_id))
        values["mobility_diff"] = float(len(current_actions) - len(other_actions))
        values["king_escape_diff"] = float(_king_escape_count(state, self.compiled, side, current_actions) - _king_escape_count(_state_for_side(state, other), self.compiled, other, other_actions))
        values["king_zone_pressure_diff"] = float(self._attack_count(position, side) - self._attack_count(position, other))
        values["current_check_diff"] = float(int(self._in_check(position, side)) - int(self._in_check(position, other)))
        values["promotion_potential_diff"] = float(self._promotion_potential(position, side, current_actions) - self._promotion_potential(position, other, other_actions))
        own_drop = {tid: 0 for tid in self.hand_types}; other_drop = {tid: 0 for tid in self.hand_types}
        from generic_chess.core.actions import action_drop_base_type_id, action_is_drop
        for action in current_actions:
            tid = action_drop_base_type_id(action) if action_is_drop(action) else None
            if tid in own_drop: own_drop[tid] += 1
        for action in other_actions:
            tid = action_drop_base_type_id(action) if action_is_drop(action) else None
            if tid in other_drop: other_drop[tid] += 1
        for tid in self.hand_types:
            values[f"legal_drop_count_diff:{tid}"] = float(own_drop[tid] - other_drop[tid])
        own_held = [own_drop[tid] for tid in self.hand_types if position.hands[side].count(tid) > 0]
        other_held = [other_drop[tid] for tid in self.hand_types if position.hands[other].count(tid) > 0]
        values["mean_legal_drop_mobility_diff"] = float((sum(own_held) / len(own_held) if own_held else 0.0) - (sum(other_held) / len(other_held) if other_held else 0.0))
        return values

    def vector(self, state) -> np.ndarray:
        key = str(position_identity_key(state.position, self.compiled))
        cached = self._vector_cache.get(key)
        if cached is not None:
            return cached
        feature_map = self._feature_map(state)
        if len(self.names) != 1086 or len(set(self.names)) != 1086 or set(feature_map) != set(self.names):
            raise AssertionError("CORRECTED_SHOGI_FEATURE_MAP_SCHEMA_FAILURE")
        vector = np.asarray([feature_map[name] for name in self.names], dtype=np.float64)
        if not np.all(np.isfinite(vector)):
            raise AssertionError("CORRECTED_SHOGI_FEATURE_VECTOR_NONFINITE")
        self._vector_cache[key] = vector
        return vector

    def __init__(self, family: str, compiled) -> None:
        super().__init__(family, compiled)
        self.oracle_weight_sha256 = _json_sha({"schema": self.SCHEMA, "names": self.names, "weights": self.weights})

def _write_progress(output: Path, stage: str, payload: dict) -> None:
    path = output.parent / f"{output.stem}.stage-{stage}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _collect_states(compiled) -> list[dict]:
    rows = []; seen = set(); trajectory = 0; lengths = (8, 24, 64, 128, 192, 256)
    while len(rows) < sum(COUNTS.values()):
        rng = random.Random(CORPUS_SEED + trajectory * 7919); state = initial_state(compiled)
        for _ in range(lengths[trajectory % len(lengths)]):
            actions = _sort_actions(legal_actions(state, compiled))
            if not actions: break
            state = apply_action(state, actions[rng.randrange(len(actions))], compiled)
            key = str(position_identity_key(state.position, compiled))
            if key in seen or state.terminal_status.status is not TerminalStatus.ONGOING: continue
            seen.add(key); rows.append({"identity": key, "ordinal": len(rows), "split": "train" if len(rows) < COUNTS["train"] else ("dev" if len(rows) < COUNTS["train"] + COUNTS["dev"] else "holdout"), "trajectory": trajectory, "ply": state.ply_count, "side_to_move": state.position.side_to_move, "state": state})
            if len(rows) >= sum(COUNTS.values()): break
        trajectory += 1
        if trajectory > 2000: raise RuntimeError("F135_CORPUS_GENERATION_EXCEEDED_TRAJECTORY_BOUND")
    if _json_sha([row["identity"] for row in rows]) != CORPUS_SHA: raise RuntimeError("F135_FROZEN_CORPUS_IDENTITY_MISMATCH")
    return rows


def _materialize(rows, basis) -> list[dict]:
    result = []
    for row in rows:
        features = basis.vector(row["state"])
        result.append({**row, "features": features.tolist(), "oracle": float(basis.oracle(features))})
    return result


def _direct_fit(rows, basis) -> dict:
    pack = _prepare(rows, basis) if len(rows) == sum(COUNTS.values()) else _prepare_filtered(rows, [row["oracle"] for row in rows], basis)
    matched = _matched_ridge(pack); pcg, trace = _pcg_tight(pack)
    numerical = {"finite_parameters": bool(np.all(np.isfinite(pcg))), "relative_residual": trace["relative_residual"], "objective_excess": float(0.5 * np.mean((pack["design"]["train"] @ pcg - pack["target"]["train"]) ** 2) + 0.5 * L2 * np.sum(pcg[:-1] ** 2) - (0.5 * np.mean((pack["design"]["train"] @ matched - pack["target"]["train"]) ** 2) + 0.5 * L2 * np.sum(matched[:-1] ** 2))), "prediction_difference": _prediction_difference(pcg, matched, pack)}
    numerical["pass"] = bool(numerical["finite_parameters"] and numerical["relative_residual"] <= 1e-10 and numerical["objective_excess"] <= 1e-10 and numerical["prediction_difference"]["holdout"]["normalized_by_holdout_oracle_std"] <= 1e-8)
    scalar = _scalar_summary(pcg, pack); holdout = scalar["holdout"]
    scalar_gate = bool(holdout["normalized_rmse"] <= 0.05 and holdout["r2"] >= 0.99 and holdout["pearson"] >= 0.995)
    return {"pack": pack, "pcg": pcg, "matched": matched, "trace": trace, "scalar": scalar, "numerical": numerical, "scalar_gate": scalar_gate}


def _action_audit(roots, legacy, corrected) -> dict:
    top = pair = total = 0; regrets = []
    for state in roots:
        actions = _sort_actions(legal_actions(state, corrected.compiled)); old = []; new = []
        for action in actions:
            child = apply_action(state, action, corrected.compiled)
            old.append(-legacy.oracle(legacy.vector(child))); new.append(-corrected.oracle(corrected.vector(child)))
        old_order = sorted(range(len(actions)), key=lambda i: (-old[i], str(actions[i]))); new_order = sorted(range(len(actions)), key=lambda i: (-new[i], str(actions[i])))
        top += int(old_order[0] == new_order[0])
        total += len(actions) * (len(actions) - 1) // 2
        pair += sum((old_order.index(i) < old_order.index(j)) == (new_order.index(i) < new_order.index(j)) for i in range(len(actions)) for j in range(i + 1, len(actions)))
        if old_order[0] != new_order[0]: regrets.append(new[new_order[0]] - new[old_order[0]])
    return {"roots": len(roots), "top_action_agreement": top / len(roots), "pairwise_ordering_agreement": pair / total if total else 1.0, "different_action_roots": len(regrets), "mean_corrected_oracle_regret_raw": float(np.mean(regrets)) if regrets else 0.0, "corrected_oracle_regrets_raw": regrets}


def _selected_surface(states, compiled, basis) -> tuple[list[dict], dict]:
    selected = []
    offset = 0
    for split in ("train", "dev", "holdout"):
        total = COUNTS[split]; requested = {"train": 2048, "dev": 256, "holdout": 256}[split]
        selected.extend({offset + math.floor(index * total / requested) for index in range(requested)}); offset += total
    rows = [row for row in states if row["ordinal"] in selected]
    retained = []
    for row in rows:
        actions = _sort_actions(legal_actions(row["state"], compiled)); children = [(action, apply_action(row["state"], action, compiled)) for action in actions]
        terminal = any(child.terminal_status.status is not TerminalStatus.ONGOING for _, child in children)
        declaration = bool(available_declarations(row["state"], compiled)) or any(bool(available_declarations(child, compiled)) for _, child in children)
        if not terminal and not declaration: retained.append(row)
    materialized = _materialize(retained, basis)
    counts = {split: len([row for row in materialized if row["split"] == split]) for split in ("train", "dev", "holdout")}
    return materialized, {"selected_counts": {"train": 2048, "dev": 256, "holdout": 256}, "retained_counts": counts, "retained_identity_sha256": {split: _json_sha([row["identity"] for row in materialized if row["split"] == split]) for split in ("train", "dev", "holdout")}}


def _schema_witnesses(states, compiled, legacy, corrected) -> dict:
    from generic_chess.core.actions import action_is_drop
    targets = ("mobility_diff", "king_escape_diff", "king_zone_pressure_diff", "current_check_diff", "promotion_potential_diff") + tuple(f"hand_diff:{tid}" for tid in corrected.hand_types) + ("legal_drop_count_diff:P",)
    shifted_names = {"mobility_diff", "king_escape_diff", "king_zone_pressure_diff", "current_check_diff"} | {f"hand_diff:{tid}" for tid in corrected.hand_types}
    witnesses = {}
    for row in states:
        actions = _sort_actions(legal_actions(row["state"], compiled))
        for action in actions:
            child = apply_action(row["state"], action, compiled)
            before = corrected._feature_map(row["state"]); after = corrected._feature_map(child)
            for name in targets:
                delta = after[name] - before[name]
                if name in witnesses or abs(delta) <= 1e-12: continue
                hand_delta = {tid: after[f"hand_diff:{tid}"] - before[f"hand_diff:{tid}"] for tid in corrected.hand_types}
                if name in ("mobility_diff", "king_escape_diff") and any(abs(value) > 1e-12 for value in hand_delta.values()): continue
                ci = corrected.names.index(name); li = legacy.names.index(name)
                corrected_delta = corrected.vector(child)[ci] - corrected.vector(row["state"])[ci]
                legacy_delta = legacy.vector(child)[li] - legacy.vector(row["state"])[li]
                legacy_contract = abs(legacy_delta - delta) > 1e-12 if name in shifted_names else abs(legacy_delta - delta) <= 1e-12
                if abs(corrected_delta - delta) <= 1e-12 and legacy_contract:
                    witnesses[name] = {"identity": row["identity"], "action": str(action), "semantic_delta": float(delta), "corrected_named_slot_delta": float(corrected_delta), "legacy_named_slot_delta": float(legacy_delta), "hand_delta": hand_delta}
            if len(witnesses) == len(targets): break
        if len(witnesses) == len(targets): break
    return {"required_features": list(targets), "witnesses": witnesses, "pass": len(witnesses) == len(targets)}


def _run(output: Path) -> dict:
    started = time.time(); compiled = compile_semantic_ruleset(build_standard_shogi_ruleset()); legacy = FrozenBasis(FAMILY, compiled); corrected = CorrectedShogiFrozenBasisV2(FAMILY, compiled)
    states = _collect_states(compiled); legacy_rows = _materialize(states, legacy); corrected_rows = _materialize(states, corrected)
    corpus = {"counts": COUNTS, "seed": CORPUS_SEED, "identity_sha256": _json_sha([row["identity"] for row in states]), "rows": len(states)}
    schema = {"schema": corrected.SCHEMA, "width": len(corrected.names), "feature_names": corrected.names, "feature_name_sha256": _json_sha(corrected.names), "corrected_oracle_sha256": corrected.oracle_weight_sha256, "legacy_oracle_sha256": legacy.oracle_weight_sha256, "witnesses": _schema_witnesses(states, compiled, legacy, corrected)}
    if legacy.oracle_weight_sha256 != LEGACY_ORACLE_SHA or corpus["identity_sha256"] != CORPUS_SHA or schema["width"] != 1086 or not schema["witnesses"]["pass"]:
        result = {"schema": "F135_CORRECTED_SHOGI_ORACLE_SCHEMA_REBASELINE_V1", "classification": "CORRECTED_SHOGI_ORACLE_SCHEMA_FAILURE", "schema_audit": schema, "corpus": corpus, "runtime_seconds": time.time() - started}; _write_progress(output, "schema", result); return result
    legacy_y = np.asarray([row["oracle"] for row in legacy_rows]); corrected_y = np.asarray([row["oracle"] for row in corrected_rows]); corrected_holdout_std = float(np.std(corrected_y[-COUNTS["holdout"]:])) or 1.0
    legacy_corrected = _scalar_metrics(legacy_y, corrected_y, corrected_holdout_std); legacy_corrected["max_abs_difference"] = float(np.max(np.abs(corrected_y - legacy_y)))
    roots = _collect_fresh_roots(FAMILY, compiled, corrected, ROOT_SEED, {row["identity"] for row in states}, 256); action_audit = _action_audit(roots, legacy, corrected); action_audit["mean_corrected_oracle_regret_normalized"] = action_audit["mean_corrected_oracle_regret_raw"] / corrected_holdout_std
    corrected_fit = _direct_fit(corrected_rows, corrected); fit = _proxy_fit(corrected_fit["pcg"], corrected_fit["pack"]); fit["pcg_model"] = fit.pop("adam_model"); ranking = _action_audit(roots, corrected, corrected) if False else None
    learned_ranking = _ranking_summary(_action_ranking(roots, corrected, fit, "pcg"), corrected_holdout_std); learned_gate = learned_ranking["top1_agreement"] >= 0.90 and learned_ranking["pairwise_ordering_agreement"] >= 0.95 and learned_ranking["mean_regret_normalized"] <= 0.05
    search = _search_probe(roots[:64], corrected, fit, "pcg")
    surface_rows, surface = _selected_surface(states, compiled, corrected); surface_fit = _direct_fit(surface_rows, corrected); surface_report = {"counts": surface, "scalar_metrics": surface_fit["scalar"], "numerical": surface_fit["numerical"], "matched_ridge_scalar_metrics": _scalar_summary(surface_fit["matched"], surface_fit["pack"])}
    result = {"schema": "F135_CORRECTED_SHOGI_ORACLE_SCHEMA_REBASELINE_V1", "baseline": "e13c55d5008e9ee57010e9fd3118a31bac2659d1", "schema_audit": schema, "corpus": corpus, "legacy_vs_corrected": {"legacy_oracle_sha256": LEGACY_ORACLE_SHA, "corrected_oracle_sha256": corrected.oracle_weight_sha256, "legacy_feature_name_sha256": _json_sha(legacy.names), "corrected_feature_name_sha256": _json_sha(corrected.names), "metrics": legacy_corrected}, "legacy_vs_corrected_action": action_audit, "direct_system_identification": {"solver": corrected_fit["trace"], "numerical": corrected_fit["numerical"], "scalar_metrics": corrected_fit["scalar"], "scalar_gate_pass": corrected_fit["scalar_gate"], "action_ranking": {"root_seed": ROOT_SEED, "roots": 256, "metrics": learned_ranking, "gate_pass": learned_gate}, "search_recovery": {"budget_nodes": 2000, "max_depth": 12, "roots": 64, "results": search}}, "f127_fixed_surface_direct_control": surface_report, "classification": "CORRECTED_KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_PASSES" if corrected_fit["numerical"]["pass"] and corrected_fit["scalar_gate"] and learned_gate else "CORRECTED_KNOWN_EVALUATOR_SYSTEM_IDENTIFICATION_FAILS", "runtime_seconds": time.time() - started}
    _write_progress(output, "final", result); return result


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, required=True); args = parser.parse_args(); result = _run(args.output); args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"); print(json.dumps({"classification": result["classification"], "runtime_seconds": result["runtime_seconds"]}, sort_keys=True))


if __name__ == "__main__":
    main()
