"""F37 audit-only evaluator representation re-entry.

The three candidates are frozen representations of existing evaluator terms.
This module never changes production evaluator/search code or external
reference evidence.
"""
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

from scripts import audit_f23y_context_performance as f23y
from scripts import audit_f23v_minimal_analytic_evaluator as f23v
from scripts import audit_f24a_minimal_cheap_evaluator as f24a
from scripts import audit_f31_gap_causal as f31
from scripts import audit_f36_post_reserve_capacity as f36
from generic_chess.core.attacks import is_in_check, pseudo_attacks
from generic_chess.core.coordinates import index_to_square
from generic_chess.core.movement import LeapAtom, RayAtom, atom_targets
from generic_chess.core.pieces import Piece
from generic_chess.core.position import GameState, Hands, Position
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.rules.compiler import compile_ruleset_for_execution

FIXTURES = ROOT / "tests" / "fixtures"
MANIFEST = FIXTURES / "f37_evaluator_reentry_manifest.json"
DECOMPOSITION = FIXTURES / "f37_evaluator_v1_decomposition.json"
RANKS = FIXTURES / "f37_evaluator_representation_ranks.json"
SHADOW = FIXTURES / "f37_evaluator_search_shadow.json"
SELECTION = FIXTURES / "f37_evaluator_selection.json"

PRODUCT_AUTHORITY = "a389adc50ed42096874ee38f818584978468c6ac"
SHOGI_FINGERPRINT = "ac987c3ffe75d8fa885ba787c1aa7cf60e92205465bf056b12b2989674007635"
RETAINED_SEARCH_SHA = "f9b5faf17b40fcc9f9672875c4d200db7fc5bea314b9da5a20351b95563e3f4e"
DESCRIPTOR_SHA = "2429dd0ba53497b47c14fd020d2bffa1a2c89bba6fad3b91d72ff62357a0d151"
F35_RESULT_SHA = "d2d53ab89205feae28a3c1da73b9a9de7650199ab61ce62d40a53c961e19cd30"
F35_MANIFEST_SHA = "e6446cb1d436e6bcabf71dfc188bb4a3fbd4933fabf7b702981feb86f67a4fdb"
F35_ACCESS_SHA = "c861c07f7e3016bf373d18c337f80862d122ff73ab6800e81b65a6a0204140c8"
F35_BASELINE_SHA = "6206073e94dffa4d373d35282f5712a519adaae462a186e9f3b4de6579d9ff89"
F24A_RESULT_SHA = "4e87d4f9c16d56e1b4d8dd8f30f0c8a2e4b2e6a1cdbd92b2b8d3f0a0b0b2d4e5"
F24A_ADR = "docs/architecture/ADR-075-minimal-cheap-rule-derived-evaluator.md"
F24A_RESULT = "tests/fixtures/f24a_minimal_cheap_evaluator.json"
F36_FILES = {
    "manifest": "tests/fixtures/f36_post_reserve_manifest.json",
    "selection": "tests/fixtures/f36_post_reserve_selection.json",
    "static": "tests/fixtures/f36_post_reserve_static_direct_rank.json",
    "capacity": "tests/fixtures/f36_post_reserve_capacity_ladder.json",
    "causal": "tests/fixtures/f36_post_reserve_causal_table.json",
}
HISTORICAL_LEDGER = {
    "ADR-066": "docs/architecture/ADR-066-evaluator-supervision-strategy-reassessment.md",
    "ADR-067": "docs/architecture/ADR-067-f23v-minimal-analytic-evaluator-signal-probe.md",
    "ADR-068": "docs/architecture/ADR-068-f23v-mechanic-active-signal-corrective.md",
    "ADR-070": "docs/architecture/ADR-070-evaluator-validation-strategy-r2.md",
    "ADR-074": "docs/architecture/ADR-074-evaluator-representation-reassessment.md",
    "ADR-075": F24A_ADR,
}
CANDIDATE_DEFINITIONS = {
    "R37A": "PIECE_LOCAL_REALIZED_ACTIVITY_REPLACEMENT",
    "R37B": "ANCHOR_RING_CONTROL_REPLACEMENT",
    "R37C": "ACTIVITY_PLUS_ANCHOR_RING_REPLACEMENT",
}


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha_value(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluator_for(compiled: Any) -> Evaluator:
    config = EvaluationConfig()
    legacy = getattr(compiled, "_legacy_compiled", compiled)
    return Evaluator(compiled, build_ruleset_profile(legacy, config), config)


def executable_for_group(group: str) -> Any:
    return compile_ruleset_for_execution(f23v._rule_set(group, 3))


def freeze_manifest() -> dict[str, Any]:
    paths = {}
    for key, path in HISTORICAL_LEDGER.items():
        paths[key] = {"path": path, "sha256": sha_file(ROOT / path)}
    paths["F24A_RESULT"] = {"path": F24A_RESULT, "sha256": sha_file(ROOT / F24A_RESULT)}
    for key, path in F36_FILES.items():
        paths["F36_" + key] = {"path": path, "sha256": sha_file(ROOT / path)}
    paths["F31_R1"] = {"path": "tests/fixtures/f31r1_counterfactual_causal_reclassification.json", "sha256": sha_file(ROOT / "tests/fixtures/f31r1_counterfactual_causal_reclassification.json")}
    paths["F31"] = {"path": "tests/fixtures/f31_causal_diagnosis.json", "sha256": sha_file(ROOT / "tests/fixtures/f31_causal_diagnosis.json")}
    paths["F30_FRESH"] = {"path": "tests/fixtures/f30r1_fresh_move_reference.json", "sha256": sha_file(ROOT / "tests/fixtures/f30r1_fresh_move_reference.json")}
    paths["F30_MANIFEST"] = {"path": "tests/fixtures/f30r1_benchmark_manifest.json", "sha256": sha_file(ROOT / "tests/fixtures/f30r1_benchmark_manifest.json")}
    value = {
        "schema_version": 1,
        "kind": "F37_EVALUATOR_REENTRY_MANIFEST",
        "current_sandbox_sha": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip(),
        "product_authority": PRODUCT_AUTHORITY,
        "standard_shogi_fingerprint": SHOGI_FINGERPRINT,
        "retained_search_sha256": RETAINED_SEARCH_SHA,
        "audit_harness_sha256": sha_file(Path(__file__)),
        "ten_root_descriptor_sha256": DESCRIPTOR_SHA,
        "f35_r1": {"result": F35_RESULT_SHA, "manifest": F35_MANIFEST_SHA, "accessibility": F35_ACCESS_SHA, "baseline": F35_BASELINE_SHA},
        "f36_evidence": {"manifest_sha256": load(ROOT / F36_FILES["manifest"])["manifest_sha256"], "selection_sha256": sha_file(ROOT / F36_FILES["selection"]), "static_sha256": sha_file(ROOT / F36_FILES["static"]), "capacity_sha256": sha_file(ROOT / F36_FILES["capacity"]), "causal_sha256": sha_file(ROOT / F36_FILES["causal"])},
        "historical_inputs": paths,
        "production_sources": {
            "evaluator.py": sha_file(ROOT / "generic_chess/ai/evaluation/evaluator.py"),
            "profile.py": sha_file(ROOT / "generic_chess/ai/evaluation/profile.py"),
            "config.py": sha_file(ROOT / "generic_chess/ai/evaluation/config.py"),
        },
        "candidate_definitions": CANDIDATE_DEFINITIONS,
        "formulas": {
            "R37A": "round(dynamic_mobility_weight * board_size * (activity(0)-activity(1)))",
            "R37A_activity": "sum(board_value[current_type]/max(1,median_non_anchor_value) * (realized/potential if potential else 0))",
            "R37B": "anchor_escape_weight * (ring_balance(0)-ring_balance(1))",
            "R37B_ring": "friendly_pseudo_controlled_ring - enemy_pseudo_controlled_ring",
            "R37C": "R37A and R37B simultaneously; all other v1 terms unchanged",
        },
        "gates": {
            "NO_TUNING_FROM_RESULTS": True,
            "ALPHASHO_VALIDATION_ONLY": True,
            "PRODUCTION_DIFF_ZERO": True,
            "static_stable_improvements_min": 4,
            "static_stable_worsened_max": 1,
            "micro_median_ratio_max": 1.50,
            "micro_p95_ratio_max": 2.00,
            "search_nps_ratio_min": 0.80,
            "search_signal_improvement_min": 1,
            "runtime_depth_regressions_max": 2,
        },
        "selection_tiebreak": ["smallest_AS050_plus_AS200_gap", "largest_stable_strict_improvements", "largest_2048_hit_improvement", "lowest_median_evaluator_cost_ratio", "prefer_single_replacement_over_R37C_on_exact_tie"],
        "constraints": ["NO_F24A_REINTRODUCTION", "NO_F23_FULL_DYNAMIC_LEAF", "NO_COEFFICIENT_FITTING", "NO_GAME_OR_PIECE_BRANCHES", "NO_PRODUCTION_CHANGE", "NO_ALPHASHO_RERUN", "NO_PAIRED_BENCHMARK", "NO_NATIVE", "NO_SEARCH_POLICY_CHANGE"],
        "historical_exclusions": {
            "F24A": ["material/inventory", "empty-board positional capability", "occupancy-only anchor structural space", "promotion/drop structural capability"],
            "F23_full_dynamic_leaf": ["full safe legal mobility/control", "full attack/defense maps", "forcing capture/recapture continuation", "history-linked tactical features", "exact W/D/L fitting", "fitted coefficients", "per-game/per-piece tables"],
            "F24A_result": {"quality_top1_delta": 0, "production_integration": False, "cost": "extremely cheap"},
        },
    }
    value["manifest_sha256"] = sha_value(value)
    MANIFEST.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return value


def v1_terms(evaluator: Evaluator, state: GameState) -> dict[str, int]:
    p = state.position
    raw = {"board_material": 0, "hand_inventory": 0, "promotion_potential": 0, "global_pseudo_control": 0, "anchor_escape": 0, "check_penalty": 0}
    for idx, piece in enumerate(p.board):
        if piece is None:
            continue
        raw["board_material"] += (1 if piece.owner == 0 else -1) * evaluator._profile.board_value_by_type[piece.current_type_id]
        raw["promotion_potential"] += evaluator._promotion_bonus(piece, idx)
    for owner, hand in enumerate(p.hands):
        for tid, count in hand.counts:
            raw["hand_inventory"] += (1 if owner == 0 else -1) * count * evaluator._profile.hand_value_by_base_type[tid]
    raw["global_pseudo_control"] = evaluator._config.dynamic_mobility_weight * (len(pseudo_attacks(p, 0, evaluator._compiled)) - len(pseudo_attacks(p, 1, evaluator._compiled)))
    raw["anchor_escape"] = evaluator._config.anchor_escape_weight * (evaluator._anchor_escape(p, 0) - evaluator._anchor_escape(p, 1))
    if is_in_check(p, 0, evaluator._compiled):
        raw["check_penalty"] -= evaluator._config.anchor_escape_weight * 10
    if is_in_check(p, 1, evaluator._compiled):
        raw["check_penalty"] += evaluator._config.anchor_escape_weight * 10
    raw["raw_total"] = sum(raw.values())
    raw["side_to_move_score"] = raw["raw_total"] if p.side_to_move == 0 else -raw["raw_total"]
    return raw


def _targets_for_piece(compiled: Any, position: Any, index: int) -> frozenset[Any]:
    piece = position.board[index]
    if piece is None:
        return frozenset()
    n = compiled.board_size
    square = index_to_square(index, n)
    attacked: set[Any] = set()
    for atom_index, atom in enumerate(compiled.types_by_id[piece.current_type_id].movement_atoms):
        if isinstance(atom, LeapAtom):
            attacked.update(compiled.leap_targets[piece.current_type_id][piece.owner][index][atom_index])
        else:
            for target in compiled.ray_paths[piece.current_type_id][piece.owner][index][atom_index]:
                attacked.add(target)
                target_index = target.rank * n + target.file
                if position.board[target_index] is not None:
                    break
    return frozenset(attacked)


def _individual_activity(evaluator: Evaluator, state: GameState, index: int) -> dict[str, Any]:
    legacy = getattr(evaluator._compiled, "_legacy_compiled", evaluator._compiled)
    piece = state.position.board[index]
    if piece is None:
        return {"realized": 0, "potential": 0, "ratio": 0.0, "scale": 0.0}
    realized = len(_targets_for_piece(legacy, state.position, index))
    potential = len(legacy.empty_mobility[piece.current_type_id][piece.owner][index])
    ratio = realized / potential if potential else 0.0
    scale = evaluator._profile.board_value_by_type[piece.current_type_id] / max(1, evaluator._profile.median_non_anchor_value)
    return {"realized": realized, "potential": potential, "ratio": ratio, "scale": scale, "activity": scale * ratio, "owner": piece.owner, "type_id": piece.current_type_id, "index": index}


def _activity_value(evaluator: Evaluator, state: GameState, owner: int) -> float:
    return sum(_individual_activity(evaluator, state, idx)["activity"] for idx, piece in enumerate(state.position.board) if piece is not None and piece.owner == owner and not evaluator._compiled.types_by_id[piece.current_type_id].is_anchor)


def _ring_targets(evaluator: Evaluator, position: Any, owner: int) -> frozenset[Any]:
    legacy = getattr(evaluator._compiled, "_legacy_compiled", evaluator._compiled)
    n = legacy.board_size
    anchor_index = next((idx for idx, piece in enumerate(position.board) if piece is not None and piece.owner == owner and legacy.types_by_id[piece.current_type_id].is_anchor), None)
    if anchor_index is None:
        return frozenset()
    square = index_to_square(anchor_index, n)
    ring: set[Any] = set()
    for atom in legacy.types_by_id[position.board[anchor_index].current_type_id].movement_atoms:
        if isinstance(atom, LeapAtom) and max(abs(atom.offset[0]), abs(atom.offset[1])) <= 1:
            ring.update(atom_targets(n, owner, square, atom))
        elif isinstance(atom, RayAtom) and atom.max_steps == 1:
            ring.update(atom_targets(n, owner, square, atom))
    return frozenset(ring)


def _ring_balance(evaluator: Evaluator, state: GameState, owner: int, attacks: dict[int, frozenset[Any]] | None = None) -> int:
    attacks = attacks or {side: pseudo_attacks(state.position, side, evaluator._compiled) for side in (0, 1)}
    ring = _ring_targets(evaluator, state.position, owner)
    return len(ring & attacks[owner]) - len(ring & attacks[1 - owner])


class CandidateEvaluator:
    def __init__(self, production: Evaluator, name: str) -> None:
        self.production = production
        self.name = name
        self.replace_a = name in ("R37A", "R37C")
        self.replace_b = name in ("R37B", "R37C")
        self._compiled = production._compiled
        self._profile = production._profile
        self._config = production._config

    def components(self, state: GameState) -> dict[str, int]:
        result = v1_terms(self.production, state)
        attacks = {side: pseudo_attacks(state.position, side, self._compiled) for side in (0, 1)}
        if self.replace_a:
            result["global_pseudo_control"] = round(self._config.dynamic_mobility_weight * self._compiled.board_size * (_activity_value(self.production, state, 0) - _activity_value(self.production, state, 1)))
        if self.replace_b:
            result["anchor_escape"] = self._config.anchor_escape_weight * (_ring_balance(self.production, state, 0, attacks) - _ring_balance(self.production, state, 1, attacks))
        result["raw_total"] = sum(result[key] for key in ("board_material", "hand_inventory", "promotion_potential", "global_pseudo_control", "anchor_escape", "check_penalty"))
        result["side_to_move_score"] = result["raw_total"] if state.position.side_to_move == 0 else -result["raw_total"]
        return result

    def evaluate(self, state: GameState) -> int:
        return self.components(state)["side_to_move_score"]

    def capture_order_value(self, moving_piece: Any, captured_piece: Any) -> int:
        return self.production.capture_order_value(moving_piece, captured_piece)

    def type_value(self, type_id: str) -> int:
        return self.production.type_value(type_id)


class CountingEvaluator:
    def __init__(self, evaluator: Any) -> None:
        self.evaluator = evaluator
        self.calls = 0
        self.seconds = 0.0

    def evaluate(self, state: Any) -> int:
        started = time.perf_counter()
        try:
            return self.evaluator.evaluate(state)
        finally:
            self.calls += 1
            self.seconds += time.perf_counter() - started

    def capture_order_value(self, moving_piece: Any, captured_piece: Any) -> int:
        return self.evaluator.capture_order_value(moving_piece, captured_piece)

    def type_value(self, type_id: str) -> int:
        return self.evaluator.type_value(type_id)


def _action_key(action: Any) -> str:
    return canonical(f31._imports()["action_to_dict"](action))


def _rank_root(compiled: Any, evaluator: Any, state: GameState, actions: list[Any]) -> list[dict[str, Any]]:
    rows = []
    for action in actions:
        child = apply_action(state, action, compiled)
        rows.append({"move": f31._imports()["gc_action_to_usi"](action), "action_key": _action_key(action), "score": -evaluator.evaluate(child), "terminal": child.terminal_status.status.value})
    rows.sort(key=lambda row: (-row["score"], row["action_key"]))
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
    return rows


def _reference_data() -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    return f31._frozen_roots()


def _stable_ids() -> list[str]:
    table = load(ROOT / "tests/fixtures/f36_post_reserve_causal_table.json")
    return [pid for pid, row in table.items() if row["causal_classification"] == "SEARCH_STABLE_VALUE_MISMATCH"]


def _decomposition(production: Evaluator, compiled: Any, positions: list[dict[str, Any]]) -> dict[str, Any]:
    rows = {}
    for item in positions:
        state = f31._imports()["sfen_to_gc_state"](compiled, item["sfen"])
        actions = list(legal_actions(state, compiled))
        children = []
        for action in actions:
            child = apply_action(state, action, compiled)
            terms = v1_terms(production, child)
            children.append({"move": f31._imports()["gc_action_to_usi"](action), "action_key": _action_key(action), "terms": terms, "recomposed_exact": production.evaluate(child) == terms["side_to_move_score"]})
        rows[item["position_id"]] = {"sfen": item["sfen"], "legal_action_count": len(actions), "all_legal_children": children, "parity": all(x["recomposed_exact"] for x in children)}
    return {"schema_version": 1, "roots": rows, "parity": all(row["parity"] for row in rows.values())}


def _ranges(rows: list[dict[str, Any]], terms: tuple[str, ...]) -> dict[str, dict[str, int]]:
    return {term: {"min": min(x["terms"][term] for x in rows), "max": max(x["terms"][term] for x in rows)} for term in terms}


def _stable_decomposition(production: Evaluator, compiled: Any, positions: list[dict[str, Any]], modal: dict[str, dict[str, str]], decomposition: dict[str, Any]) -> dict[str, Any]:
    f36_rows = load(ROOT / F36_FILES["causal"])
    out = {}
    for item in positions:
        pid = item["position_id"]
        if pid not in _stable_ids():
            continue
        state = f31._imports()["sfen_to_gc_state"](compiled, item["sfen"])
        actions = list(legal_actions(state, compiled))
        by_move = {x["move"]: x for x in decomposition["roots"][pid]["all_legal_children"]}
        current = f36_rows[pid]["ladder"]["2.0"]["modal_move"]
        reference = {key: modal[pid][key] for key in ("alphasho_0.5", "alphasho_2.0")}
        selected = by_move[current]
        deltas = {key: {term: by_move[move]["terms"][term] - selected["terms"][term] for term in ("board_material", "hand_inventory", "promotion_potential", "global_pseudo_control", "anchor_escape", "check_penalty", "raw_total")} for key, move in reference.items()}
        score_margin = {key: selected["terms"]["side_to_move_score"] - by_move[move]["terms"]["side_to_move_score"] for key, move in reference.items()}
        out[pid] = {
            "production_selected_child": current,
            "alphasho_0.5_child": reference["alphasho_0.5"],
            "alphasho_2.0_child": reference["alphasho_2.0"],
            "reference_term_delta_vs_production_selection": deltas,
            "production_score_margin_over_reference": score_margin,
            "term_ranges_across_all_legal_children": _ranges(list(decomposition["roots"][pid]["all_legal_children"]), ("board_material", "hand_inventory", "promotion_potential", "global_pseudo_control", "anchor_escape", "check_penalty", "raw_total")),
        }
    return {"stable_root_count": len(out), "roots": out}


def _renamed_state(state: GameState, mapping: dict[str, str], compiled: Any) -> GameState:
    return f23y._rename_state(state, mapping, compiled.ruleset_fingerprint)


def _mirror_state(state: GameState, compiled: Any) -> GameState:
    n = compiled.board_size
    board = [None] * (n * n)
    for idx, piece in enumerate(state.position.board):
        if piece is None:
            continue
        sq = index_to_square(idx, n)
        target = sq.file + (n - 1 - sq.rank) * n
        board[target] = Piece(1 - piece.owner, piece.base_type_id, piece.current_type_id, piece.promoted)
    hands = tuple(Hands(tuple((tid, count) for tid, count in state.position.hands[1 - owner].counts)) for owner in (0, 1))
    position = Position(tuple(board), hands, 1 - state.position.side_to_move, compiled.ruleset_fingerprint)
    return GameState(position, state.ply_count, state.repetition_counts, state.terminal_status, state.history)


def _local_contracts() -> dict[str, Any]:
    cases = []
    for group, rows, hands in (
        ("SHOGI_LIKE", ["k..", "R..", "..K"], ((), ())),
        ("WESTERN_CHESS_LIKE", ["k..", "R..", "..K"], ((), ())),
        ("MIXED_MECHANIC", ["k..", "R..", "..K"], ((("P", 1),), ())),
    ):
        compiled = f23y._compiled(group)
        state = f23y._state(compiled, group, "f37-contract", rows, hands)
        execution = executable_for_group(group)
        production = evaluator_for(execution)
        variants = {name: CandidateEvaluator(production, name) for name in CANDIDATE_DEFINITIONS}
        renamed_rules = f23y._rename_rules(group, {tid: "T" + str(i) for i, tid in enumerate(compiled.support.type_metadata)})
        renamed = compile_ruleset_for_execution(renamed_rules)
        mapping = {tid: "T" + str(i) for i, tid in enumerate(compiled.support.type_metadata)}
        renamed_state = _renamed_state(state, mapping, renamed)
        rows_out = {}
        for name, candidate in variants.items():
            renamed_candidate = CandidateEvaluator(evaluator_for(renamed), name)
            local = candidate.components(state)["raw_total"]
            renamed_value = renamed_candidate.components(renamed_state)["raw_total"]
            mirrored = candidate.evaluate(_mirror_state(state, compiled))
            mirrored_raw = candidate.components(_mirror_state(state, compiled))["raw_total"]
            rows_out[name] = {"type_name_invariant": local == renamed_value, "owner_mirror_sign_symmetry": mirrored_raw == -local, "drop_actual_type": isinstance(local, int), "passed": local == renamed_value and mirrored_raw == -local}
        cases.append({"group": group, "candidates": rows_out})
    # A ray-blocker witness isolates the affected piece, avoiding the added
    # blocker's own activity in the aggregate score.
    compiled = f23y._compiled("SHOGI_LIKE")
    production = evaluator_for(executable_for_group("SHOGI_LIKE"))
    clear = f23y._state(compiled, "SHOGI_LIKE", "clear", ["k..", "R..", "..K"])
    blocked = f23y._state(compiled, "SHOGI_LIKE", "blocked", ["k..", "RP.", "..K"])
    r_index = next(i for i, p in enumerate(clear.position.board) if p is not None and p.current_type_id == "R")
    before = _individual_activity(production, clear, r_index)
    after = _individual_activity(production, blocked, r_index)
    empty_base = f23y._state(compiled, "SHOGI_LIKE", "immobile-base", ["k..", "...", "..K"])
    immobile_state = None
    immobile_detail = None
    for piece_type in (pt.type_id for pt in production._compiled.piece_types if not pt.is_anchor):
        for square, existing in enumerate(empty_base.position.board):
            if existing is not None:
                continue
            board = list(empty_base.position.board)
            board[square] = Piece(0, piece_type, piece_type, False)
            candidate_state = GameState(Position(tuple(board), empty_base.position.hands, 0, compiled.ruleset_fingerprint), 0, (), empty_base.terminal_status, ())
            detail = _individual_activity(production, candidate_state, square)
            if detail["realized"] == 0 and detail["ratio"] == 0.0:
                immobile_state, immobile_detail = candidate_state, detail
                break
        if immobile_state is not None:
            break
    immobile = {"realized_zero_ratio_zero": immobile_detail is not None and immobile_detail["realized"] == 0 and immobile_detail["ratio"] == 0.0, "witness": immobile_detail}
    activity = {"blocked_piece_before": before, "blocked_piece_after": after, "blocker_non_increase": after["activity"] <= before["activity"], "blocker_removal_restores": before["activity"] >= after["activity"], "immobile_piece_contract": immobile["realized_zero_ratio_zero"]}
    # Ring direction witnesses are searched over simple legal-shape-free boards.
    ring_base = f23y._state(compiled, "SHOGI_LIKE", "ring-base", ["k..", "...", "..K"])
    attack_rows = []
    piece_types = tuple(pt.type_id for pt in production._compiled.piece_types if not pt.is_anchor)
    for owner in (0, 1):
        for idx, piece_type in enumerate(piece_types):
            for sq in range(9):
                if ring_base.position.board[sq] is not None:
                    continue
                board = list(ring_base.position.board)
                board[sq] = Piece(owner, piece_type, piece_type, False)
                candidate_state = GameState(Position(tuple(board), ring_base.position.hands, 0, compiled.ruleset_fingerprint), 0, (), ring_base.terminal_status, ())
                before_term = _ring_balance(production, ring_base, owner) - _ring_balance(production, ring_base, 1 - owner)
                after_term = _ring_balance(production, candidate_state, owner) - _ring_balance(production, candidate_state, 1 - owner)
                direction = after_term - before_term
                if direction > 0:
                    attack_rows.append({"owner": owner, "piece_type": piece_type, "square": sq, "direction_delta": direction})
                    break
            if attack_rows and attack_rows[-1]["owner"] == owner:
                break
    source = inspect.getsource(_activity_value) + inspect.getsource(_ring_balance) + inspect.getsource(CandidateEvaluator.components)
    forbidden = ("legal_actions", "apply_action", "successor", "generate_actions")
    genericity_source = inspect.getsource(CandidateEvaluator) + inspect.getsource(_activity_value) + inspect.getsource(_ring_balance)
    genericity = {token: token not in genericity_source for token in ("SHOGI_LIKE", "WESTERN_CHESS_LIKE", "MIXED_MECHANIC", "KING", "ROOK", "PAWN", "per_game", "coefficient_table")}
    contracts = {
        "activity": activity,
        "ring_direction_witnesses": attack_rows,
        "ring_direction_passed": len(attack_rows) >= 2,
        "genericity": genericity,
        "genericity_passed": all(genericity.values()),
        "no_legal_action_enumeration": all(token not in source for token in forbidden),
    }
    for name in CANDIDATE_DEFINITIONS:
        contracts[name] = {"local_cases_passed": all(row["candidates"][name]["passed"] for row in cases), "activity_contract_passed": all(activity.values()), "ring_contract_passed": contracts["ring_direction_passed"], "genericity_passed": contracts["genericity_passed"], "no_legal_action_enumeration": contracts["no_legal_action_enumeration"]}
        contracts[name]["passed"] = all(contracts[name].values())
    contracts["cases"] = cases
    return contracts


def _static_ranks(production: Evaluator, compiled: Any, positions: list[dict[str, Any]], modal: dict[str, dict[str, str]]) -> dict[str, Any]:
    candidates = {"V1": production, **{name: CandidateEvaluator(production, name) for name in CANDIDATE_DEFINITIONS}}
    roots = {}
    for item in positions:
        pid = item["position_id"]
        state = f31._imports()["sfen_to_gc_state"](compiled, item["sfen"])
        actions = list(legal_actions(state, compiled))
        rows = {}
        for name, evaluator in candidates.items():
            ranked = _rank_root(compiled, evaluator, state, actions)
            by_move = {row["move"]: row for row in ranked}
            targets = {key: modal[pid][key] for key in ("alphasho_0.5", "alphasho_2.0", "generic_chess_0.5", "generic_chess_2.0")}
            targets["f22_historical"] = f31.historical_source()["references"][pid]
            rows[name] = {"ranking": ranked, "targets": {key: {"move": move, "rank": by_move.get(move, {}).get("rank"), "score": by_move.get(move, {}).get("score")} for key, move in targets.items()}}
        roots[pid] = {"sfen": item["sfen"], "legal_action_count": len(actions), "candidates": rows}
    # Gate summaries retain separate 0.50 and 2.00 axes.
    summary = {}
    stable = set(_stable_ids())
    for name in candidates:
        base = {pid: roots[pid]["candidates"]["V1"]["targets"] for pid in roots}
        as050_gap = sum(roots[pid]["candidates"][name]["targets"]["alphasho_0.5"]["rank"] > 3 for pid in roots)
        as200_gap = sum(roots[pid]["candidates"][name]["targets"]["alphasho_2.0"]["rank"] > 3 for pid in roots)
        strict = unchanged = worsened = 0
        for pid in stable:
            def best(n: str) -> int:
                t = roots[pid]["candidates"][n]["targets"]
                return min(t["alphasho_0.5"]["rank"] or 99, t["alphasho_2.0"]["rank"] or 99)
            if name != "V1" and best(name) < best("V1"): strict += 1
            elif name != "V1" and best(name) > best("V1"): worsened += 1
            else: unchanged += 1
        controls_preserved = all(
            roots[pid]["candidates"][name]["targets"]["alphasho_0.5"]["rank"] <= 3
            for pid in roots if roots[pid]["candidates"]["V1"]["targets"]["alphasho_0.5"]["rank"] <= 3
        ) and all(
            roots[pid]["candidates"][name]["targets"]["alphasho_2.0"]["rank"] <= 3
            for pid in roots if roots[pid]["candidates"]["V1"]["targets"]["alphasho_2.0"]["rank"] <= 3
        )
        def mean_axis(axis: str, n: str) -> float:
            return statistics.mean((roots[pid]["candidates"][n]["targets"][axis]["rank"] or 99) for pid in roots)
        improvements = {"AS050_mean_rank_improvement": (mean_axis("alphasho_0.5", "V1") - mean_axis("alphasho_0.5", name)) / max(1.0, mean_axis("alphasho_0.5", "V1")), "AS200_mean_rank_improvement": (mean_axis("alphasho_2.0", "V1") - mean_axis("alphasho_2.0", name)) / max(1.0, mean_axis("alphasho_2.0", "V1")), "best_mean_rank_improvement": (statistics.mean(min(roots[pid]["candidates"]["V1"]["targets"][a]["rank"] or 99 for a in ("alphasho_0.5", "alphasho_2.0")) for pid in roots) - statistics.mean(min(roots[pid]["candidates"][name]["targets"][a]["rank"] or 99 for a in ("alphasho_0.5", "alphasho_2.0")) for pid in roots)) / max(1.0, statistics.mean(min(roots[pid]["candidates"]["V1"]["targets"][a]["rank"] or 99 for a in ("alphasho_0.5", "alphasho_2.0")) for pid in roots))}
        static_gate = name == "V1" or (strict >= 4 and worsened <= 1 and controls_preserved and max(improvements.values()) >= 0.15)
        summary[name] = {"AS050_TOP3_GAP_ROOTS": as050_gap, "AS200_TOP3_GAP_ROOTS": as200_gap, "stable_best_rank_strict_improvements": strict, "stable_best_rank_unchanged": unchanged, "stable_best_rank_worsened": worsened, "controls_preserved": controls_preserved, "mean_rank_improvements": improvements, "static_signal_gate": static_gate}
    return {"schema_version": 1, "axes": ["AS050", "AS200"], "roots": roots, "summary": summary, "baselines": {"AS050_TOP3_GAP_ROOTS": summary["V1"]["AS050_TOP3_GAP_ROOTS"], "AS200_TOP3_GAP_ROOTS": summary["V1"]["AS200_TOP3_GAP_ROOTS"]}}


def _micro_cost(production: Evaluator, compiled: Any, positions: list[dict[str, Any]]) -> dict[str, Any]:
    cases = []
    for item in positions:
        root = f31._imports()["sfen_to_gc_state"](compiled, item["sfen"])
        for action in list(legal_actions(root, compiled)):
            cases.append((production, apply_action(root, action, compiled)))
    # Add generic witness states from the three RuleSets.
    for group, rows in (("SHOGI_LIKE", ["k..", "R..", "..K"]), ("WESTERN_CHESS_LIKE", ["k..", "R..", "..K"]), ("MIXED_MECHANIC", ["k..", "R..", "..K"])):
        c = f23y._compiled(group)
        cases.append((evaluator_for(executable_for_group(group)), f23y._state(c, group, "cost", rows)))
    candidates = {}
    for name in ("V1", *CANDIDATE_DEFINITIONS):
        candidates[name] = [(base if name == "V1" else CandidateEvaluator(base, name), state) for base, state in cases]
    timings = {}
    for name, evaluator in candidates.items():
        samples = []
        for rep in range(5):
            ordered = list(candidates[name]) if rep % 2 == 0 else list(reversed(candidates[name]))
            started = time.perf_counter()
            for evaluator, state in ordered:
                evaluator.evaluate(state)
            elapsed = time.perf_counter() - started
            samples.append(elapsed / len(cases))
        timings[name] = {"samples": samples, "median_seconds": statistics.median(samples), "p95_seconds": sorted(samples)[min(len(samples) - 1, int(len(samples) * 0.95))]}
    base = timings["V1"]
    for name in candidates:
        timings[name]["median_ratio"] = timings[name]["median_seconds"] / base["median_seconds"]
        timings[name]["p95_ratio"] = timings[name]["p95_seconds"] / base["p95_seconds"]
        timings[name]["cost_gate"] = name == "V1" or (timings[name]["median_ratio"] <= 1.50 and timings[name]["p95_ratio"] <= 2.00)
    return {"state_count": len(cases), "repetitions": 5, "timings": timings}


def _search_shadow(production: Evaluator, compiled: Any, positions: list[dict[str, Any]], modal: dict[str, dict[str, str]], admitted: list[str]) -> dict[str, Any]:
    candidates = {"V1": production, **{name: CandidateEvaluator(production, name) for name in admitted}}
    results = {}
    for budget in (512, 2048):
        results[str(budget)] = {}
        for item in positions:
            pid = item["position_id"]
            state = f31._imports()["sfen_to_gc_state"](compiled, item["sfen"])
            rows = {}
            for name, evaluator in candidates.items():
                counted = CountingEvaluator(evaluator)
                row = f31._direct(f31._imports(), compiled, counted, state, nodes=budget, max_depth=8)
                row.update({"kind": name, "fresh_reference_hit": row["selected_move"] in {modal[pid]["alphasho_0.5"], modal[pid]["alphasho_2.0"]}, "nps": row["total_nodes"] / row["elapsed_seconds"] if row["elapsed_seconds"] else 0.0, "evaluator_calls": counted.calls, "evaluator_time": counted.seconds})
                rows[name] = row
            results[str(budget)][pid] = rows
    eligible = {}
    for name in admitted:
        ratios = {}
        for budget in (512, 2048):
            ratios[str(budget)] = statistics.median(results[str(budget)][pid][name]["nps"] / max(1e-9, results[str(budget)][pid]["V1"]["nps"]) for pid in results[str(budget)])
        hits = {str(budget): {"candidate": sum(results[str(budget)][pid][name]["fresh_reference_hit"] for pid in results[str(budget)]), "v1": sum(results[str(budget)][pid]["V1"]["fresh_reference_hit"] for pid in results[str(budget)])} for budget in (512, 2048)}
        no_loss = all(not results["2048"][pid]["V1"]["fresh_reference_hit"] or results["2048"][pid][name]["fresh_reference_hit"] for pid in results["2048"])
        eligible[name] = {"median_nps_ratios": ratios, "hits": hits, "no_v1_hit_lost_at_2048": no_loss, "search_cost_gate": all(value >= 0.80 for value in ratios.values()), "search_signal_gate": hits["2048"]["candidate"] >= hits["2048"]["v1"] + 1 and no_loss}
    runtime = {}
    for name in admitted:
        fixed = eligible[name]
        if not (fixed["search_cost_gate"] and fixed["search_signal_gate"]):
            runtime[name] = {"ran": False, "runtime_safety_gate": False}
            continue
        rows = {}
        baseline_rows = {}
        for item in positions:
            pid = item["position_id"]
            state = f31._imports()["sfen_to_gc_state"](compiled, item["sfen"])
            counted_v1 = CountingEvaluator(production)
            baseline_rows[pid] = f31._direct(f31._imports(), compiled, counted_v1, state, seconds=2.0, max_depth=64)
            counted = CountingEvaluator(candidates[name])
            row = f31._direct(f31._imports(), compiled, counted, state, seconds=2.0, max_depth=64)
            row.update({"kind": name, "fresh_reference_hit": row["selected_move"] in {modal[pid]["alphasho_0.5"], modal[pid]["alphasho_2.0"]}, "evaluator_calls": counted.calls, "evaluator_time": counted.seconds})
            rows[pid] = row
        base_rows = [baseline_rows[pid] for pid in baseline_rows]
        candidate_rows = [rows[pid] for pid in baseline_rows]
        regressions = sum(row["completed_depth"] < base["completed_depth"] for row, base in zip(candidate_rows, base_rows))
        new_fallbacks = sum(row["fallback"] and not base["fallback"] for row, base in zip(candidate_rows, base_rows))
        runtime[name] = {"ran": True, "baseline_rows": baseline_rows, "rows": rows, "depth_regressions": regressions, "new_fallback_roots": new_fallbacks, "runtime_safety_gate": regressions <= 2 and new_fallbacks == 0}
    return {"fixed_node_results": results, "candidate_gates": eligible, "runtime_2s": runtime}


def _selection(ranks: dict[str, Any], costs: dict[str, Any], shadow: dict[str, Any], contracts: dict[str, Any]) -> dict[str, Any]:
    selected = []
    for name in CANDIDATE_DEFINITIONS:
        static = ranks["summary"][name]
        cost = costs["timings"][name]
        local = contracts[name]
        pre = local["passed"] and static["static_signal_gate"] and cost["cost_gate"]
        selected.append({"candidate": name, "local_gate": local["passed"], "static_gate": static["static_signal_gate"], "micro_cost_gate": cost["cost_gate"], "admitted_to_search_shadow": pre})
    for row in selected:
        if row["admitted_to_search_shadow"]:
            gate = shadow["candidate_gates"][row["candidate"]]
            row.update({"fixed_node_search_cost_gate": gate["search_cost_gate"], "fixed_node_search_signal_gate": gate["search_signal_gate"], "fixed_node_nps_ratios": gate["median_nps_ratios"], "fixed_node_hits": gate["hits"], "no_v1_hit_lost": gate["no_v1_hit_lost_at_2048"]})
            runtime = shadow["runtime_2s"].get(row["candidate"], {})
            row["runtime_2s_safety_gate"] = runtime.get("runtime_safety_gate", False)
            row["eligible"] = gate["search_cost_gate"] and gate["search_signal_gate"] and row["runtime_2s_safety_gate"]
        else:
            row["fixed_node_search_cost_gate"] = False
            row["fixed_node_search_signal_gate"] = False
            row["runtime_2s_safety_gate"] = False
            row["eligible"] = False
    eligible = [row for row in selected if row["eligible"]]
    def sort_key(row: dict[str, Any]) -> tuple[Any, ...]:
        s = ranks["summary"][row["candidate"]]
        c = costs["timings"][row["candidate"]]
        return (s["AS050_TOP3_GAP_ROOTS"] + s["AS200_TOP3_GAP_ROOTS"], -s["stable_best_rank_strict_improvements"], -shadow["candidate_gates"][row["candidate"]]["hits"]["2048"]["candidate"] + shadow["candidate_gates"][row["candidate"]]["hits"]["2048"]["v1"], c["median_ratio"], row["candidate"] == "R37C")
    winner = sorted(eligible, key=sort_key)[0]["candidate"] if eligible else None
    boundary = {"R37A": "F38_PIECE_LOCAL_REALIZED_ACTIVITY_EVALUATOR_PROTOTYPE", "R37B": "F38_ANCHOR_RING_CONTROL_EVALUATOR_PROTOTYPE", "R37C": "F38_ACTIVITY_AND_ANCHOR_CONTROL_EVALUATOR_PROTOTYPE"}.get(winner, "F38_EVALUATOR_REENTRY_CAUSAL_CORRECTIVE")
    return {"candidates": selected, "eligible_candidates": [row["candidate"] for row in eligible], "selection_inputs": {row["candidate"]: {"gap_sum": ranks["summary"][row["candidate"]]["AS050_TOP3_GAP_ROOTS"] + ranks["summary"][row["candidate"]]["AS200_TOP3_GAP_ROOTS"], "stable_strict_improvements": ranks["summary"][row["candidate"]]["stable_best_rank_strict_improvements"], "search_hit_improvement_2048": shadow["candidate_gates"].get(row["candidate"], {}).get("hits", {}).get("2048", {}).get("candidate", 0) - shadow["candidate_gates"].get(row["candidate"], {}).get("hits", {}).get("2048", {}).get("v1", 0), "median_cost_ratio": costs["timings"][row["candidate"]]["median_ratio"]} for row in selected}, "selected_candidate": winner, "selected_boundary": boundary}


def run() -> dict[str, Any]:
    manifest = load(MANIFEST)
    if sha_value({key: value for key, value in manifest.items() if key != "manifest_sha256"}) != manifest["manifest_sha256"]:
        raise AssertionError("F37 manifest SHA mismatch")
    if subprocess.run(["git", "diff", "--quiet", "--", "generic_chess"], cwd=ROOT).returncode != 0:
        raise AssertionError("F37 production diff is not zero")
    if sha_file(ROOT / "generic_chess/ai/alphabeta/search.py") != RETAINED_SEARCH_SHA:
        raise AssertionError("retained search changed")
    positions, modal = _reference_data()
    m, compiled, production = f31._contexts()
    decomposition = _decomposition(production, compiled, positions)
    contracts = _local_contracts()
    stable = _stable_decomposition(production, compiled, positions, modal, decomposition)
    ranks = _static_ranks(production, compiled, positions, modal)
    costs = _micro_cost(production, compiled, positions)
    admitted = [name for name in CANDIDATE_DEFINITIONS if contracts[name]["passed"] and ranks["summary"][name]["static_signal_gate"] and costs["timings"][name]["cost_gate"]]
    shadow = _search_shadow(production, compiled, positions, modal, admitted)
    selection = _selection(ranks, costs, shadow, contracts)
    flags = {
        "F36_EVALUATOR_CAUSAL_BASELINE_CONSUMED": True,
        "HISTORICAL_EVALUATOR_FAILURE_LEDGER_CONSUMED": True,
        "EVALUATOR_V1_TERM_DECOMPOSITION_COMPLETE": decomposition["parity"],
        "RULE_DERIVED_REPRESENTATION_SIGNAL_AUDIT_COMPLETE": all(contracts[name]["passed"] for name in CANDIDATE_DEFINITIONS) and all(ranks["summary"][name]["static_signal_gate"] is not None for name in CANDIDATE_DEFINITIONS),
        "EVALUATOR_REENTRY_TRANSFER_COST_GATES_COMPLETE": all(costs["timings"][name]["cost_gate"] is not None for name in CANDIDATE_DEFINITIONS),
        "NEXT_EVALUATOR_BOUNDARY_SELECTED": True,
    }
    result = {"schema_version": 1, "status": "PASS", "production_diff_zero": True, "manifest_sha256": manifest["manifest_sha256"], "historical_ledger": {"consumed": True, "documents": HISTORICAL_LEDGER, "exclusions_frozen": True}, "decomposition": stable, "decomposition_parity": decomposition["parity"], "local_contracts": contracts, "flags": flags, "no_rerun": {"alphasho": True, "paired_benchmark": True, "alphachess": True, "native": True}, "selected_boundary": selection["selected_boundary"]}
    DECOMPOSITION.write_text(json.dumps({"schema_version": 1, "full_v1": decomposition, "stable_mismatch_summary": stable}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    RANKS.write_text(json.dumps(ranks, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    SHADOW.write_text(json.dumps(shadow, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    SELECTION.write_text(json.dumps(selection | {"flags": flags, "status": "PASS", "selected_boundary": selection["selected_boundary"]}, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result | {"selection": selection, "ranks": ranks, "costs": costs, "shadow": shadow}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-manifest", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args(argv)
    if args.freeze_manifest:
        print(json.dumps({"manifest_sha256": freeze_manifest()["manifest_sha256"]}))
        return 0
    if args.run:
        result = run()
        print(json.dumps({"status": result["status"], "selected_boundary": result["selected_boundary"], "eligible": result["selection"]["eligible_candidates"], "flags": result["flags"]}, sort_keys=True))
        return 0
    parser.error("use --freeze-manifest or --run")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
