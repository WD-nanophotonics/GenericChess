"""F38 audit-only production-shaped R37C prototype and certification harness."""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
FIXTURES = ROOT / "tests" / "fixtures"
H38A_MANIFEST = FIXTURES / "f38_activity_anchor_manifest.json"
H38A_DESCRIPTOR = FIXTURES / "f38_external_holdout_descriptor.json"
IDENTITY = FIXTURES / "f38_activity_anchor_prototype_identity.json"
HOLDOUT_RANKS = FIXTURES / "f38_activity_anchor_holdout_ranks.json"
HOLDOUT_SEARCH = FIXTURES / "f38_activity_anchor_holdout_search.json"
MICRO_COST = FIXTURES / "f38_activity_anchor_micro_cost.json"
SELECTION = FIXTURES / "f38_activity_anchor_selection.json"

from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.core.actions import action_to_dict
from generic_chess.core.attacks import is_in_check, is_square_attacked, pseudo_attacks
from generic_chess.core.coordinates import Square, index_to_square, square_to_index
from generic_chess.core.movement import LeapAtom, RayAtom, atom_targets
from generic_chess.core.movegen import legal_actions
from generic_chess.core.pieces import Piece
from generic_chess.core.position import GameState, Hands, Position
from generic_chess.core.transition import apply_action
from generic_chess.learning.shogi_rules import gc_action_to_usi, gc_to_sfen, sfen_to_gc_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from scripts import audit_f23v_minimal_analytic_evaluator as f23v
from scripts import audit_f23y_context_performance as f23y
from scripts import audit_f31_gap_causal as f31
from scripts import audit_f37_evaluator_reentry as f37


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def sha_value(value: Any) -> str:
    return sha_bytes(canonical(value).encode("utf-8"))


class ProductionShapedR37CPrototype:
    """Independent implementation of the frozen R37C formula.

    It deliberately owns all evaluator terms and delegates only the generic
    rule-derived data (profile/config/compiled rules) to production objects.
    """

    def __init__(self, compiled: Any, profile: Any, config: EvaluationConfig) -> None:
        self._compiled = compiled
        self._legacy = getattr(compiled, "_legacy_compiled", compiled)
        self._profile = profile
        self._config = config
        self._zones = {}
        for pt in self._legacy.piece_types:
            if pt.is_promotable:
                for owner in (0, 1):
                    self._zones[(pt.type_id, owner)] = frozenset(
                        i for i in range(self._legacy.board_size * self._legacy.board_size)
                        if not self._legacy.empty_forward_mobility[pt.type_id][owner][i]
                    )

    def _promotion(self, piece: Any, index: int) -> int:
        if piece.promoted or self._profile.promotion_gain_by_type.get(piece.base_type_id, 0) <= 0:
            return 0
        gain = self._profile.promotion_gain_by_type[piece.base_type_id]
        unit = max(1, gain // 1000)
        zone = self._zones.get((piece.base_type_id, piece.owner))
        if zone is None:
            return 0
        if index in zone:
            bonus = self._config.promotion_potential_weight * unit
        elif any(target in zone for target in self._legacy.empty_forward_mobility[piece.base_type_id][piece.owner][index]):
            bonus = self._config.promotion_potential_weight * unit // 2
        else:
            bonus = 0
        return bonus if piece.owner == 0 else -bonus

    def _piece_targets(self, position: Any, index: int) -> frozenset[Any]:
        piece = position.board[index]
        if piece is None:
            return frozenset()
        targets: set[Any] = set()
        square = index_to_square(index, self._legacy.board_size)
        for atom_index, atom in enumerate(self._legacy.types_by_id[piece.current_type_id].movement_atoms):
            if isinstance(atom, LeapAtom):
                targets.update(self._legacy.leap_targets[piece.current_type_id][piece.owner][index][atom_index])
            else:
                for target in self._legacy.ray_paths[piece.current_type_id][piece.owner][index][atom_index]:
                    targets.add(target)
                    if position.board[target.rank * self._legacy.board_size + target.file] is not None:
                        break
        return frozenset(targets)

    def _activity(self, position: Any, owner: int) -> float:
        total = 0.0
        for index, piece in enumerate(position.board):
            if piece is None or piece.owner != owner or self._legacy.types_by_id[piece.current_type_id].is_anchor:
                continue
            potential = len(self._legacy.empty_mobility[piece.current_type_id][owner][index])
            realized = len(self._piece_targets(position, index))
            ratio = realized / potential if potential else 0.0
            scale = self._profile.board_value_by_type[piece.current_type_id] / max(1, self._profile.median_non_anchor_value)
            total += scale * ratio
        return total

    def _ring(self, position: Any, owner: int) -> frozenset[Any]:
        index = next((i for i, piece in enumerate(position.board) if piece is not None and piece.owner == owner and self._legacy.types_by_id[piece.current_type_id].is_anchor), None)
        if index is None:
            return frozenset()
        square = index_to_square(index, self._legacy.board_size)
        ring: set[Any] = set()
        for atom in self._legacy.types_by_id[position.board[index].current_type_id].movement_atoms:
            if isinstance(atom, LeapAtom) and max(abs(atom.offset[0]), abs(atom.offset[1])) <= 1:
                ring.update(atom_targets(self._legacy.board_size, owner, square, atom))
            elif isinstance(atom, RayAtom) and atom.max_steps == 1:
                ring.update(atom_targets(self._legacy.board_size, owner, square, atom))
        return frozenset(ring)

    def _ring_balance(self, position: Any, owner: int, attacks: dict[int, frozenset[Any]]) -> int:
        ring = self._ring(position, owner)
        return len(ring & attacks[owner]) - len(ring & attacks[1 - owner])

    def components(self, state: GameState) -> dict[str, int]:
        position = state.position
        raw = {"board_material": 0, "hand_inventory": 0, "promotion_potential": 0, "global_pseudo_control": 0, "anchor_escape": 0, "check_penalty": 0}
        for index, piece in enumerate(position.board):
            if piece is None:
                continue
            signed = 1 if piece.owner == 0 else -1
            raw["board_material"] += signed * self._profile.board_value_by_type[piece.current_type_id]
            raw["promotion_potential"] += self._promotion(piece, index)
        for owner, hand in enumerate(position.hands):
            for type_id, count in hand.counts:
                value = self._profile.hand_value_by_base_type[type_id]
                raw["hand_inventory"] += (1 if owner == 0 else -1) * count * value
        attacks = {owner: pseudo_attacks(position, owner, self._compiled) for owner in (0, 1)}
        raw["global_pseudo_control"] = round(self._config.dynamic_mobility_weight * self._legacy.board_size * (self._activity(position, 0) - self._activity(position, 1)))
        raw["anchor_escape"] = self._config.anchor_escape_weight * (self._ring_balance(position, 0, attacks) - self._ring_balance(position, 1, attacks))
        if is_in_check(position, 0, self._compiled):
            raw["check_penalty"] -= self._config.anchor_escape_weight * 10
        if is_in_check(position, 1, self._compiled):
            raw["check_penalty"] += self._config.anchor_escape_weight * 10
        raw["raw_total"] = sum(raw.values())
        raw["side_to_move_score"] = raw["raw_total"] if position.side_to_move == 0 else -raw["raw_total"]
        return raw

    def evaluate(self, state: GameState) -> int:
        return self.components(state)["side_to_move_score"]

    def capture_order_value(self, moving_piece: Any, captured_piece: Any) -> int:
        moving = self._profile.board_value_by_type[moving_piece.current_type_id]
        captured = self._profile.board_value_by_type[captured_piece.current_type_id]
        return captured * 10 - moving // 10

    def type_value(self, type_id: str) -> int:
        return self._profile.board_value_by_type[type_id]


def _context(ruleset: Any | None = None):
    selected = ruleset or build_standard_shogi_ruleset()
    compiled = compile_ruleset_for_execution(selected)
    config = EvaluationConfig()
    profile = build_ruleset_profile(compiled._legacy_compiled, config)
    return compiled, config, profile, Evaluator(compiled, profile, config), ProductionShapedR37CPrototype(compiled, profile, config)


def _rank(compiled: Any, evaluator: Any, state: GameState) -> list[dict[str, Any]]:
    rows = []
    for action in legal_actions(state, compiled):
        child = apply_action(state, action, compiled)
        rows.append({"move": gc_action_to_usi(action), "action_key": canonical(action_to_dict(action)), "score": -evaluator.evaluate(child), "terminal": child.terminal_status.status.value})
    rows.sort(key=lambda row: (-row["score"], row["action_key"]))
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    return rows


def identity_gate() -> dict[str, Any]:
    compiled, _, _, production, prototype = _context()
    oracle = f37.CandidateEvaluator(production, "R37C")
    positions, _ = f31._frozen_roots()
    checked = 0
    mismatches = []
    for item in positions:
        state = sfen_to_gc_state(compiled, item["sfen"])
        states = [state] + [apply_action(state, action, compiled) for action in legal_actions(state, compiled)]
        for candidate_state in states:
            checked += 1
            expected = oracle.evaluate(candidate_state)
            actual = prototype.evaluate(candidate_state)
            if expected != actual:
                mismatches.append({"position_id": item["position_id"], "expected": expected, "actual": actual, "sfen": gc_to_sfen(candidate_state, compiled)})
    witness_rows = []
    for group in ("SHOGI_LIKE", "WESTERN_CHESS_LIKE", "MIXED_MECHANIC"):
        rules = f23v._rule_set(group, 3)
        c, _, _, prod, proto = _context(rules)
        state = f23y._state(c, group, "f38-identity-witness", ["k..", "R..", "..K"], ((('P', 1),), ()) if group == "MIXED_MECHANIC" else ((), ()))
        oracle_witness = f37.CandidateEvaluator(prod, "R37C")
        witness_rows.append({"group": group, "oracle": oracle_witness.evaluate(state), "prototype": proto.evaluate(state), "equal": oracle_witness.evaluate(state) == proto.evaluate(state)})
    prototype_source = inspect.getsource(ProductionShapedR37CPrototype)
    forbidden = ("legal_actions", "apply_action", "successor", "search", "AlphaSho", "Shogi", "WESTERN", "MIXED")
    generic_transfer = {"supported_rule_families": [row["group"] for row in witness_rows], "witness_score_identity": all(row["equal"] for row in witness_rows), "no_dynamic_action_enumeration": all(token not in prototype_source for token in ("legal_actions", "apply_action", "successor")), "no_game_or_piece_branches": all(token not in prototype_source for token in ("AlphaSho", "Shogi", "WESTERN", "MIXED", "per_game", "coefficient_table")), "passed": all(row["equal"] for row in witness_rows) and all(token not in prototype_source for token in ("legal_actions", "apply_action", "successor", "AlphaSho", "Shogi", "WESTERN", "MIXED", "per_game", "coefficient_table"))}
    return {"schema_version": 1, "status": "PASS" if not mismatches and generic_transfer["passed"] else "FAIL", "candidate": "R37C", "implementation_path": "scripts/audit_f38_activity_anchor_prototype.py", "checked_original_roots_and_children": checked, "mismatches": mismatches, "witness_rows": witness_rows, "score_identity": not mismatches and all(row["equal"] for row in witness_rows), "generic_transfer_contract": generic_transfer, "no_candidate_evaluator_implementation_call": "CandidateEvaluator" not in prototype_source, "production_diff_zero": subprocess.run(["git", "diff", "--quiet", "--", "generic_chess"], cwd=ROOT).returncode == 0}


def holdout_ranks() -> dict[str, Any]:
    compiled, _, profile, production, prototype = _context()
    rows = []
    for item in load(H38A_DESCRIPTOR)["positions"]:
        state = sfen_to_gc_state(compiled, item["canonical_state"])
        alpha = item["alphasho_played_move"]
        v1 = _rank(compiled, production, state)
        candidate = _rank(compiled, prototype, state)
        v1_target = next(row for row in v1 if row["move"] == alpha)
        candidate_target = next(row for row in candidate if row["move"] == alpha)
        rows.append({"game_id": item["game_id"], "event_index": item["event_index"], "alphasho_move": alpha, "legal_action_count": len(v1), "v1_rank": v1_target["rank"], "r37c_rank": candidate_target["rank"], "v1_margin_from_top": v1[0]["score"] - v1_target["score"], "r37c_margin_from_top": candidate[0]["score"] - candidate_target["score"], "v1_top1": v1_target["rank"] == 1, "r37c_top1": candidate_target["rank"] == 1, "v1_top3": v1_target["rank"] <= 3, "r37c_top3": candidate_target["rank"] <= 3, "v1_top5": v1_target["rank"] <= 5, "r37c_top5": candidate_target["rank"] <= 5, "rank_delta": v1_target["rank"] - candidate_target["rank"], "classification": "improved" if candidate_target["rank"] < v1_target["rank"] else "worsened" if candidate_target["rank"] > v1_target["rank"] else "unchanged"})
    mean_v1 = statistics.mean(row["v1_rank"] for row in rows)
    mean_candidate = statistics.mean(row["r37c_rank"] for row in rows)
    worsened = sum(row["classification"] == "worsened" for row in rows)
    improved = sum(row["classification"] == "improved" for row in rows)
    summary = {"holdout_size": len(rows), "v1_mean_rank": mean_v1, "r37c_mean_rank": mean_candidate, "mean_rank_improvement_fraction": (mean_v1 - mean_candidate) / max(1.0, mean_v1), "v1_median_rank": statistics.median(row["v1_rank"] for row in rows), "r37c_median_rank": statistics.median(row["r37c_rank"] for row in rows), "v1_top1": sum(row["v1_top1"] for row in rows), "r37c_top1": sum(row["r37c_top1"] for row in rows), "v1_top3": sum(row["v1_top3"] for row in rows), "r37c_top3": sum(row["r37c_top3"] for row in rows), "v1_top5": sum(row["v1_top5"] for row in rows), "r37c_top5": sum(row["r37c_top5"] for row in rows), "improved": improved, "unchanged": len(rows) - improved - worsened, "worsened": worsened, "worsened_by_more_than_3": sum(row["rank_delta"] < -3 for row in rows)}
    gates = {"unique_holdout_minimum": summary["holdout_size"] >= 16, "mean_rank_improvement": summary["mean_rank_improvement_fraction"] >= 0.15, "top3_improvement": summary["r37c_top3"] >= summary["v1_top3"] + 3, "top1_not_lower": summary["r37c_top1"] >= summary["v1_top1"], "worsened_fraction": worsened / len(rows) <= 0.25, "severe_worsened_fraction": summary["worsened_by_more_than_3"] / len(rows) <= 0.10}
    return {"schema_version": 1, "status": "PASS" if all(gates.values()) else "FAIL", "candidate": "R37C", "rows": rows, "summary": summary, "gates": gates}


def _run_search(compiled: Any, evaluator: Any, state: GameState, budget: int) -> dict[str, Any]:
    return f31._direct(f31._imports(), compiled, evaluator, state, nodes=budget, max_depth=64, native_requested=True)


def holdout_search() -> dict[str, Any]:
    compiled, _, _, production, prototype = _context()
    descriptor = load(H38A_DESCRIPTOR)["positions"][:10]
    original_roots, _ = f31._frozen_roots()
    budgets = (512, 2048)
    by_budget = {}
    for budget in budgets:
        rows = []
        for item in descriptor:
            state = sfen_to_gc_state(compiled, item["canonical_state"])
            v1 = _run_search(compiled, production, state, budget)
            candidate = _run_search(compiled, prototype, state, budget)
            rows.append({"game_id": item["game_id"], "alphasho_move": item["alphasho_played_move"], "v1": v1, "r37c": candidate, "v1_alpha_hit": v1["selected_move"] == item["alphasho_played_move"], "r37c_alpha_hit": candidate["selected_move"] == item["alphasho_played_move"], "exact_identity": all(v1[key] == candidate[key] for key in ("selected_move", "score", "pv_head", "completed_depth", "nodes", "qnodes", "termination_reason"))})
        ratios = [row["r37c"]["selected_move"] is not None and row["r37c"]["total_nodes"] / max(1, row["r37c"]["elapsed_seconds"]) / max(1e-9, row["v1"]["total_nodes"] / max(1e-9, row["v1"]["elapsed_seconds"])) for row in rows]
        by_budget[str(budget)] = {"rows": rows, "complete": len(rows) == 10, "median_nps_ratio": statistics.median(ratios), "v1_alpha_hits": sum(row["v1_alpha_hit"] for row in rows), "r37c_alpha_hits": sum(row["r37c_alpha_hit"] for row in rows), "exact_identity_count": sum(row["exact_identity"] for row in rows)}
    original_identity = {}
    for budget in budgets:
        rows = []
        for item in original_roots:
            state = sfen_to_gc_state(compiled, item["sfen"])
            v1 = _run_search(compiled, production, state, budget)
            candidate = _run_search(compiled, prototype, state, budget)
            rows.append({"position_id": item["position_id"], "v1": v1, "r37c": candidate, "exact_identity": all(v1[key] == candidate[key] for key in ("selected_move", "score", "pv_head", "completed_depth", "nodes", "qnodes", "termination_reason"))})
        original_identity[str(budget)] = {"rows": rows, "exact_identity_count": sum(row["exact_identity"] for row in rows), "complete": len(rows) == 10}
    safety_rows = []
    for item in descriptor:
        state = sfen_to_gc_state(compiled, item["canonical_state"])
        v1 = f31._direct(f31._imports(), compiled, production, state, seconds=2.0, max_depth=64, native_requested=True)
        candidate = f31._direct(f31._imports(), compiled, prototype, state, seconds=2.0, max_depth=64, native_requested=True)
        safety_rows.append({"game_id": item["game_id"], "v1": v1, "r37c": candidate, "depth_regression": candidate["completed_depth"] < v1["completed_depth"], "new_fallback": candidate["fallback"] and not v1["fallback"], "legal": candidate["selected_move"] is not None})
    return {"schema_version": 1, "status": "PASS", "candidate": "R37C", "original_ten_root_identity": original_identity, "fixed_node": by_budget, "runtime_2s": {"rows": safety_rows, "depth_regressions": sum(row["depth_regression"] for row in safety_rows), "new_fallback_roots": sum(row["new_fallback"] for row in safety_rows), "runtime_safety_gate": sum(row["depth_regression"] for row in safety_rows) <= 2 and not any(row["new_fallback"] for row in safety_rows) and all(row["legal"] for row in safety_rows)}}


def micro_cost() -> dict[str, Any]:
    compiled, _, profile, production, prototype = _context()
    states = []
    original_roots, _ = f31._frozen_roots()
    for item in original_roots:
        state = sfen_to_gc_state(compiled, item["sfen"])
        states.append((production, prototype, state))
        states.extend((production, prototype, apply_action(state, action, compiled)) for action in legal_actions(state, compiled))
    for item in load(H38A_DESCRIPTOR)["positions"]:
        state = sfen_to_gc_state(compiled, item["canonical_state"])
        states.append((production, prototype, state))
    for group in ("WESTERN_CHESS_LIKE", "MIXED_MECHANIC"):
        rules = f23v._rule_set(group, 3)
        generic_compiled, _, _, generic_production, generic_prototype = _context(rules)
        hands = ((('P', 1),), ()) if group == "MIXED_MECHANIC" else ((), ())
        states.append((generic_production, generic_prototype, f23y._state(generic_compiled, group, "f38-cost-witness", ["k..", "R..", "..K"], hands)))
    samples = {"v1": [], "r37c": []}
    for repetition in range(3):
        ordered = states if repetition % 2 == 0 else list(reversed(states))
        for name, evaluator in (("v1", production), ("r37c", prototype)):
            started = time.perf_counter()
            for v1_evaluator, candidate_evaluator, state in ordered:
                (v1_evaluator if name == "v1" else candidate_evaluator).evaluate(state)
            samples[name].append((time.perf_counter() - started) / len(states))
    median_v1 = statistics.median(samples["v1"])
    p95_v1 = sorted(samples["v1"])[min(len(samples["v1"]) - 1, int(len(samples["v1"]) * 0.95))]
    median_candidate = statistics.median(samples["r37c"])
    p95_candidate = sorted(samples["r37c"])[min(len(samples["r37c"]) - 1, int(len(samples["r37c"]) * 0.95))]
    return {"schema_version": 1, "state_count": len(states), "coverage": {"f37_roots_and_children": len(states) - 22, "holdout_roots": 20, "western_mixed_witnesses": 2}, "repetitions": 3, "samples_seconds_per_state": samples, "median_ratio": median_candidate / median_v1, "p95_ratio": p95_candidate / p95_v1, "gate": median_candidate / median_v1 <= 1.50 and p95_candidate / p95_v1 <= 2.00}


def selection(identity: dict[str, Any], ranks: dict[str, Any], search: dict[str, Any], cost: dict[str, Any]) -> dict[str, Any]:
    identity_pass = identity["score_identity"]
    generic_pass = identity["generic_transfer_contract"]["passed"]
    original_search_identity = all(search["original_ten_root_identity"][str(b)]["complete"] and search["original_ten_root_identity"][str(b)]["exact_identity_count"] == 10 for b in (512, 2048))
    static_pass = ranks["status"] == "PASS"
    cost_pass = cost["gate"]
    search_pass = all(search["fixed_node"][str(b)]["complete"] and search["fixed_node"][str(b)]["median_nps_ratio"] >= 0.85 for b in (512, 2048))
    signal_pass = search["fixed_node"]["2048"]["r37c_alpha_hits"] >= search["fixed_node"]["2048"]["v1_alpha_hits"] + 2 and search["fixed_node"]["2048"]["r37c_alpha_hits"] >= search["fixed_node"]["2048"]["v1_alpha_hits"]
    runtime_pass = search["runtime_2s"]["runtime_safety_gate"]
    all_pass = identity_pass and original_search_identity and static_pass and generic_pass and cost_pass and search_pass and signal_pass and runtime_pass
    boundary = "F39_ACTIVITY_AND_ANCHOR_CONTROL_EVALUATOR_IMPLEMENTATION" if all_pass else "F38A_R37C_PROTOTYPE_PARITY_DIAGNOSIS" if not identity_pass or not original_search_identity or not generic_pass else "F39_EVALUATOR_REENTRY_GENERALIZATION_CORRECTIVE"
    return {"schema_version": 1, "status": "PASS", "candidate": "R37C", "gates": {"exact_identity": identity_pass, "original_ten_root_search_identity": original_search_identity, "holdout_static": static_pass, "generic_transfer": generic_pass, "micro_cost": cost_pass, "search_cost": search_pass, "search_signal": signal_pass, "runtime_2s_safety": runtime_pass}, "F39_IMPLEMENTATION_ELIGIBLE": all_pass, "selected_boundary": boundary}


def _load_h38a() -> dict[str, Any]:
    h38a = load(H38A_MANIFEST)
    if sha_value({k: v for k, v in h38a.items() if k != "manifest_sha256"}) != h38a["manifest_sha256"]:
        raise AssertionError("H38A manifest SHA mismatch")
    return h38a


def complete(identity: dict[str, Any] | None = None, ranks: dict[str, Any] | None = None) -> dict[str, Any]:
    h38a = _load_h38a()
    identity = identity or identity_gate()
    IDENTITY.write_text(json.dumps(identity, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    ranks = ranks or holdout_ranks()
    HOLDOUT_RANKS.write_text(json.dumps(ranks, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    cost = micro_cost()
    MICRO_COST.write_text(json.dumps(cost, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    search = holdout_search()
    HOLDOUT_SEARCH.write_text(json.dumps(search, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    chosen = selection(identity, ranks, search, cost)
    result = {"schema_version": 1, "status": "PASS", "h38a_manifest_sha256": h38a["manifest_sha256"], "h38a_descriptor_sha256": sha_file(H38A_DESCRIPTOR), "identity": identity, "holdout_ranks": ranks, "micro_cost": cost, "holdout_search": search, "selection": chosen, "flags": {"F37_R37C_SELECTION_CONSUMED": True, "R37C_PRODUCTION_SHAPE_SCORE_IDENTITY": identity["score_identity"], "F30_PAIRED_EXTERNAL_HOLDOUT_FROZEN": True, "R37C_GENERIC_TRANSFER_CONTRACT": identity["generic_transfer_contract"]["passed"], "R37C_INDEPENDENT_HOLDOUT_SIGNAL_CERTIFIED": chosen["gates"]["search_signal"], "NEXT_EVALUATOR_IMPLEMENTATION_BOUNDARY_SELECTED": True}, "production_diff_zero": subprocess.run(["git", "diff", "--quiet", "--", "generic_chess"], cwd=ROOT).returncode == 0}
    SELECTION.write_text(json.dumps(chosen, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def run() -> dict[str, Any]:
    return complete()


def search_only() -> dict[str, Any]:
    h38a = _load_h38a()
    identity = load(IDENTITY)
    ranks = load(HOLDOUT_RANKS)
    cost = load(MICRO_COST)
    search = holdout_search()
    HOLDOUT_SEARCH.write_text(json.dumps(search, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    chosen = selection(identity, ranks, search, cost)
    SELECTION.write_text(json.dumps(chosen, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"schema_version": 1, "status": "PASS", "h38a_manifest_sha256": h38a["manifest_sha256"], "identity": identity, "holdout_ranks": ranks, "micro_cost": cost, "holdout_search": search, "selection": chosen}


def identity_only() -> dict[str, Any]:
    h38a = _load_h38a()
    identity = identity_gate()
    IDENTITY.write_text(json.dumps(identity, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"schema_version": 1, "status": "PASS", "h38a_manifest_sha256": h38a["manifest_sha256"], "identity": identity}


def selection_only() -> dict[str, Any]:
    h38a = _load_h38a()
    identity = load(IDENTITY)
    ranks = load(HOLDOUT_RANKS)
    cost = load(MICRO_COST)
    search = load(HOLDOUT_SEARCH)
    chosen = selection(identity, ranks, search, cost)
    SELECTION.write_text(json.dumps(chosen, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"schema_version": 1, "status": "PASS", "h38a_manifest_sha256": h38a["manifest_sha256"], "identity": identity, "holdout_ranks": ranks, "micro_cost": cost, "holdout_search": search, "selection": chosen}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--complete-from-existing", action="store_true")
    parser.add_argument("--search-only", action="store_true")
    parser.add_argument("--identity-only", action="store_true")
    parser.add_argument("--selection-only", action="store_true")
    args = parser.parse_args(argv)
    modes = (args.run, args.complete_from_existing, args.search_only, args.identity_only, args.selection_only)
    if sum(bool(value) for value in modes) != 1:
        parser.error("choose exactly one audit mode")
    if args.identity_only:
        result = identity_only()
    elif args.selection_only:
        result = selection_only()
    elif args.search_only:
        result = search_only()
    elif args.complete_from_existing:
        result = complete(load(IDENTITY), load(HOLDOUT_RANKS))
    else:
        result = run()
    summary = {"status": result["status"], "identity": result["identity"]["status"]}
    if "holdout_ranks" in result:
        summary["holdout_static"] = result["holdout_ranks"]["status"]
    if "selection" in result:
        summary["selected_boundary"] = result["selection"]["selected_boundary"]
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
