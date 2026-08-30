"""F23Y audit-only performance probe for the minimal analytic context.

The module keeps the F23X-R1 mathematics unchanged.  P0 is the corrected R1
context implementation; P1 only removes repeated semantic attack rescans and
reuses one legal-action pass per owner.  No production module is modified.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import multiprocessing
import queue
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generic_chess.ai.alphabeta.native_legality import NativeSemanticLegalityProvider
from generic_chess.ai.alphabeta.search import run_root_search
from generic_chess.ai.alphabeta.statistics import SearchStatistics
from generic_chess.ai.alphabeta.transposition import TranspositionTable
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.profile import build_ruleset_profile
from generic_chess.ai.limits import SearchLimits
from generic_chess.core.actions import action_to_dict
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands, HistoryRecord
from generic_chess.core.semantic_executor import (
    _sources_by_owner_type,
    geometry_candidates,
)
from generic_chess.learning.round5_benchmark import SearchSemanticCompiled
from generic_chess.learning.shogi_rules import gc_action_to_usi, sfen_to_gc_state
from generic_chess.rules.compiler import compile_semantic_ruleset
from generic_chess.rules.schema import RuleSet, RuleTypeRef
from scripts import audit_f23v_minimal_analytic_evaluator as f23v
from scripts import audit_f23v_minimal_analytic_evaluator_r1 as f23vr1
from scripts import audit_f23x_metamorphic_shogi_shadow_r1 as f23x


FIXTURES = ROOT / "tests" / "fixtures"
OUTPUT = FIXTURES / "f23y_context_performance.json"
F23X_R1_REPORT = FIXTURES / "f23x_shogi_shadow_r1.json"
F23X_FIRST_PASS_COMMIT = "1b042de7e1a48bacd9301f506bcd4c3152dd1374"
F22_COMMIT = f23x.F22_COMMIT
FEATURES = f23x.FEATURES
COEFFICIENTS = f23x.COEFFICIENTS
TOLERANCE = 1e-12
TIME_BUDGETS = (0.25, 1.0)
TIME_REPETITIONS = 3
NODE_BUDGETS = (128, 512, 2048)
NODE_WATCHDOG_SECONDS = {128: 30.0, 512: 30.0, 2048: 60.0}
MICRO_REPETITIONS = 5


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha(value: Any) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _action_data(action: Any) -> dict[str, Any]:
    return f23x._data(action)


def _action_key(action: Any) -> str:
    return _json(_action_data(action))


def _compiled(group: str, size: int = 3) -> Any:
    return f23x._compiled(group, size)


def _state(compiled: Any, group: str, name: str, rows: list[str], hands=((), ()), side: int = 0) -> Any:
    return f23x._state(compiled, group, name, rows, hands, side)


def _value(piece: Any, profile: Any) -> float:
    return float(profile.board_value_by_type[piece.current_type_id])


def _relative(values: tuple[float, float], actor: int) -> float:
    delta = values[0] - values[1]
    return delta if actor == 0 else -delta


def _clamp(value: float) -> float:
    return max(-1.0, min(1.0, value))


class InstrumentedContext(f23x.ContextAnalyticEvaluator):
    """P0/P1 context with fine-grained timing and semantic counters."""

    def __init__(self, compiled: Any, mode: str) -> None:
        super().__init__(compiled)
        self.mode = mode
        self.eval_count = 0
        self.total_timings = {key: 0.0 for key in (
            "static_inventory", "legal_actions_owner0", "legal_actions_owner1",
            "classification", "bulk_attack_owner0", "bulk_attack_owner1",
            "attack_check_safety", "feature_aggregation", "total_context",
        )}
        self.semantic_legal_action_enumerations = 0
        self.is_square_attacked_calls = 0

    def _bulk_attacks(self, position: Any, owner: int) -> frozenset[int]:
        engine = self.engine
        if engine is None:
            return frozenset()
        attacked: set[int] = set()
        sources_by_owner_type = _sources_by_owner_type(position)
        for pattern in engine._patterns:
            if pattern.target.kind != "target_enemy":
                continue
            for tid in pattern.type_ids:
                for source, piece in sources_by_owner_type.get((owner, tid), ()):
                    for gid in pattern.geometry_ids:
                        geometry = engine.ir.geometry.get(gid)
                        if geometry is None or geometry.kind == "drop":
                            continue
                        if geometry.atom_source is not None and geometry.atom_source[0] != tid:
                            continue
                        for target, path in geometry_candidates(geometry, str(owner), source):
                            binding = engine._make_binding(
                                pattern, gid, tid, piece, source, target, None, path, position
                            )
                            if engine._path_holds(pattern.path, position, binding, owner) and engine._guards_hold(pattern, position, binding, owner):
                                attacked.add(target)
        return frozenset(attacked)

    def _actions(self, position: Any, owner: int) -> tuple[Any, ...]:
        view = replace(position, side_to_move=owner)
        if self.mode == "P1" and self.engine is not None:
            self.semantic_legal_action_enumerations += 1
            return tuple(self.engine.legal_actions(view))
        self.semantic_legal_action_enumerations += 1
        return tuple(f23vr1._semantic_actions(self.compiled, position, owner))

    def build_context(self, state: Any, actor: int | None = None) -> f23x.EvaluationContextAudit:
        actor = state.position.side_to_move if actor is None else actor
        n = self.compiled.board_size
        area = float(n * n)
        material = [0.0, 0.0]
        mobility = [0.0, 0.0]
        safety = [0.0, 0.0]
        capture_signal = [0.0, 0.0]
        transition = [0.0, 0.0]
        legal: list[tuple[Any, ...]] = []
        captures: list[tuple[Any, ...]] = []
        promotions: list[tuple[Any, ...]] = []
        drops: list[tuple[Any, ...]] = []
        attacks: list[frozenset[int]] = []
        timings = {key: 0.0 for key in self.total_timings}
        total_started = time.perf_counter()

        started = time.perf_counter()
        for piece in state.position.board:
            if piece is not None:
                material[piece.owner] += _value(piece, self.profile)
        for owner, hand in enumerate(state.position.hands):
            for tid, count in hand.counts:
                material[owner] += count * self.profile.hand_value_by_base_type.get(tid, 0)
        timings["static_inventory"] = time.perf_counter() - started

        recent = None
        if getattr(state, "history", ()):
            signature = getattr(state.history[-1], "action_signature", "")
            if signature:
                recent = f23x._target_pair(json.loads(signature).get("to"), n)

        for owner in (0, 1):
            started = time.perf_counter()
            owner_actions = self._actions(state.position, owner)
            timings[f"legal_actions_owner{owner}"] = time.perf_counter() - started
            legal.append(owner_actions)

            attack_started = time.perf_counter()
            if self.mode == "P1":
                owner_attacks = self._bulk_attacks(state.position, owner)
            else:
                owner_attacks = frozenset(
                    index for index in range(n * n)
                    if self.engine is not None and self._counted_attack(state.position, index, owner)
                )
            timings[f"bulk_attack_owner{owner}"] = time.perf_counter() - attack_started
            attacks.append(owner_attacks)

            classification_started = time.perf_counter()
            owner_captures: list[Any] = []
            owner_promotions: list[Any] = []
            owner_drops: list[Any] = []
            for action in owner_actions:
                data = _action_data(action)
                target = f23x._target_pair(data.get("to", data.get("target")), n)
                target_piece = None if target is None else state.position.board[target[1] * n + target[0]]
                if target_piece is not None and target_piece.owner != owner:
                    owner_captures.append(action)
                    capture_signal[owner] += 1.0 + _value(target_piece, self.profile) / max(self.scale, 1.0)
                    if recent == target:
                        capture_signal[owner] += 0.5
                if data.get("promotion_target_id") is not None:
                    owner_promotions.append(action)
                    base = data.get("actor_type_id", data.get("actor_type"))
                    transition[owner] += 1.0 + self.profile.promotion_gain_by_type.get(base, 0) / max(self.scale, 1.0)
                if data.get("source") is None and data.get("kind") in {None, "drop", "semantic_drop"}:
                    owner_drops.append(action)
                    tid = data.get("base_type_id", data.get("actor_type"))
                    if tid is not None:
                        transition[owner] += 1.0 + self.profile.hand_value_by_base_type.get(tid, 0) / max(self.scale, 1.0)
            timings["classification"] += time.perf_counter() - classification_started
            captures.append(tuple(owner_captures))
            promotions.append(tuple(owner_promotions))
            drops.append(tuple(owner_drops))
            mobility[owner] = (len(owner_actions) + len(owner_attacks)) / max(area, 1.0)

        safety_started = time.perf_counter()
        metadata = self.compiled.support.type_metadata if self.engine is not None else self.compiled.types_by_id
        checks: list[bool] = []
        anchors: list[int | None] = []
        anchor_safe: list[bool] = []
        for owner in (0, 1):
            anchor = next((index for index, piece in enumerate(state.position.board) if piece is not None and piece.owner == owner and metadata[piece.current_type_id].is_anchor), None)
            anchors.append(anchor)
            if self.mode == "P1":
                checked = anchor is not None and anchor in attacks[1 - owner]
                safe = anchor is not None and anchor not in attacks[1 - owner]
            else:
                checked = bool(self.engine.in_check(state.position, owner)) if self.engine is not None else False
                if self.engine is not None:
                    safe = anchor is not None and not self._counted_attack(state.position, anchor, 1 - owner)
                else:
                    safe = False
            checks.append(bool(checked))
            anchor_safe.append(bool(safe))
            if checked:
                safety[owner] -= 1.0
            if safe:
                safety[owner] += 0.25
            for index, piece in enumerate(state.position.board):
                if piece is not None and piece.owner == 1 - owner:
                    attacked = index in attacks[owner] if self.mode == "P1" else self._counted_attack(state.position, index, owner)
                    if attacked:
                        safety[owner] += _value(piece, self.profile) / max(self.scale, 1.0) / 4.0
        timings["attack_check_safety"] = time.perf_counter() - safety_started

        context = f23x.EvaluationContextAudit(
            state=state, compiled=self.compiled, actor=actor, scale=self.scale,
            material_values=tuple(material), mobility_values=tuple(mobility),
            safety_values=tuple(safety), capture_values=tuple(capture_signal),
            transition_values=tuple(transition), legal_actions_by_side=tuple(legal),
            captures=tuple(captures), promotions=tuple(promotions), drops=tuple(drops),
            check_status=tuple(checks), anchors=tuple(anchors), anchor_safety=tuple(anchor_safe),
            recent_action_target=recent, timings=timings,
        )
        timings["total_context"] = time.perf_counter() - total_started
        self.eval_count += 1
        for key, value in timings.items():
            self.total_timings[key] += value
        return context

    def _counted_attack(self, position: Any, square: int, owner: int) -> bool:
        self.is_square_attacked_calls += 1
        return bool(self.engine.is_square_attacked(position, square, owner))


class EvaluatorAdapter:
    def __init__(self, evaluator: Any, production: Evaluator | None = None) -> None:
        self.evaluator = evaluator
        self.production = production
        self.calls = 0
        self.seconds = 0.0
        self.context_seconds = 0.0
        self.aggregation_seconds = 0.0

    def evaluate(self, state: Any) -> float:
        started = time.perf_counter()
        if not hasattr(self.evaluator, "build_context"):
            if hasattr(self.evaluator, "score"):
                score = self.evaluator.score(state, state.position.side_to_move)
            else:
                score = self.evaluator.evaluate(state)
            self.calls += 1
            self.seconds += time.perf_counter() - started
            return score
        context_started = time.perf_counter()
        context = self.evaluator.build_context(state, state.position.side_to_move)
        self.context_seconds += time.perf_counter() - context_started
        aggregation_started = time.perf_counter()
        vector = self.evaluator.feature_vector(state, state.position.side_to_move, context)
        score = context.scale * sum(COEFFICIENTS[i] * vector[name] for i, name in enumerate(FEATURES))
        self.aggregation_seconds += time.perf_counter() - aggregation_started
        self.calls += 1
        self.seconds += time.perf_counter() - started
        return score

    def capture_order_value(self, moving_piece: Any, captured_piece: Any) -> int:
        return self.production.capture_order_value(moving_piece, captured_piece) if self.production else 0

    def type_value(self, type_id: str) -> int:
        return self.production.type_value(type_id) if self.production else 0


def _production(compiled: Any) -> Evaluator:
    config = EvaluationConfig()
    evaluator_compiled = getattr(compiled, "_legacy_compiled", compiled)
    return Evaluator(evaluator_compiled, build_ruleset_profile(evaluator_compiled, config), config)


def _descriptor(state: Any, label: str, group: str, action: Any = None) -> dict[str, Any]:
    board = []
    for piece in state.position.board:
        board.append(None if piece is None else {"owner": piece.owner, "base": piece.base_type_id, "current": piece.current_type_id, "promoted": piece.promoted})
    return {"label": label, "group": group, "side_to_move": state.position.side_to_move, "board": board, "hands": [[list(item) for item in hand.counts] for hand in state.position.hands], "history": [item.action_signature for item in getattr(state, "history", ())], "action": None if action is None else _action_data(action)}


def _microbenchmark_states() -> tuple[list[dict[str, Any]], str]:
    f22, _ = f23x._load_f22()
    records: list[dict[str, Any]] = []
    compiled = f23x._certified_compiled()
    for position in f22["positions"]:
        state = sfen_to_gc_state(compiled, position["sfen"])
        records.append({"descriptor": _descriptor(state, position["name"], "SHOGI_LIKE"), "compiled": compiled, "state": state})
        runtime = f23vr1.SearchPathRuntime.from_state(state, compiled)
        for index, action in enumerate(runtime.legal_actions()[:3]):
            with runtime.pushed(action):
                child = f23vr1._child_context(runtime)
                records.append({"descriptor": _descriptor(child, f"{position['name']}:child:{index}", "SHOGI_LIKE", action), "compiled": compiled, "state": child})
    for name, compiled_state, state in f23x._audit_states():
        records.append({"descriptor": _descriptor(state, name, "AUDIT"), "compiled": compiled_state, "state": state})
    frozen = [row["descriptor"] for row in records]
    return records, _sha(frozen)


def _rename_value(value: Any, mapping: dict[str, str]) -> Any:
    if isinstance(value, str):
        return mapping.get(value, value)
    if isinstance(value, list):
        return [_rename_value(item, mapping) for item in value]
    if isinstance(value, tuple):
        return tuple(_rename_value(item, mapping) for item in value)
    if isinstance(value, dict):
        return {key: _rename_value(item, mapping) for key, item in value.items()}
    return value


def _rename_rules(group: str, mapping: dict[str, str]) -> Any:
    source = f23v._rule_set(group, 3)
    types = tuple(replace(item, type_id=mapping[item.type_id], promotion_target_ids=tuple(mapping.get(target, target) for target in item.promotion_target_ids)) for item in source.piece_types)
    initial = tuple(tuple(None if piece is None else replace(piece, base_type_id=mapping[piece.base_type_id], current_type_id=mapping[piece.current_type_id]) for piece in row) for row in source.initial_position)
    drop_allowed = {mapping[key]: value for key, value in source.drop_allowed.items()}
    promotion_allowed = {mapping[key]: value for key, value in source.promotion_allowed.items()}
    promotion_forced = {mapping[key]: value for key, value in source.promotion_forced.items()}
    actions = []
    for action in source.semantic_actions:
        selector = action.replace_selector
        if selector is not None:
            selector = replace(selector, type_ids=tuple(mapping.get(item, item) for item in selector.type_ids))
        effects = []
        for effect in action.effects:
            values = {}
            for field in ("piece_type_ref", "type_ref"):
                ref = getattr(effect, field)
                if ref is not None and ref.kind == "explicit" and ref.type_id is not None:
                    values[field] = replace(ref, type_id=mapping[ref.type_id])
            effects.append(replace(effect, **values))
        actions.append(replace(action, type_ids=tuple(mapping.get(item, item) for item in action.type_ids), replace_selector=selector, effects=tuple(effects), explicit_promotion_type=mapping.get(action.explicit_promotion_type, action.explicit_promotion_type)))
    return replace(source, piece_types=types, initial_position=initial, drop_allowed=drop_allowed, promotion_allowed=promotion_allowed, promotion_forced=promotion_forced, semantic_actions=tuple(actions))


def _rename_state(state: Any, mapping: dict[str, str], fingerprint: str) -> Any:
    board = tuple(None if piece is None else replace(piece, base_type_id=mapping[piece.base_type_id], current_type_id=mapping[piece.current_type_id]) for piece in state.position.board)
    hands = tuple(Hands(tuple(sorted((mapping.get(tid, tid), count) for tid, count in hand.counts))) for hand in state.position.hands)
    position = replace(state.position, board=board, hands=hands, ruleset_fingerprint=fingerprint)
    history = []
    for record in getattr(state, "history", ()):
        try:
            signature = _json(_rename_value(json.loads(record.action_signature), mapping))
        except (TypeError, json.JSONDecodeError):
            signature = record.action_signature
        history.append(replace(record, action_signature=signature))
    if hasattr(state, "__dataclass_fields__"):
        return replace(state, position=position, history=tuple(history))
    return SimpleNamespace(
        position=position,
        ply_count=getattr(state, "ply_count", 0),
        repetition_counts=getattr(state, "repetition_counts", ()),
        terminal_status=getattr(state, "terminal_status", None),
        history=tuple(history),
    )


def _contract_pairs() -> list[tuple[str, str, str, Any, Any, Any]]:
    c_shogi, c_western, c_mixed = (_compiled(name) for name in ("SHOGI_LIKE", "WESTERN_CHESS_LIKE", "MIXED_MECHANIC"))
    pairs = [
        ("M1", "capture_to_hand", "SHOGI_LIKE", c_shogi, _state(c_shogi, "SHOGI_LIKE", "m1b", ["..k", "...", "KRp"]), _state(c_shogi, "SHOGI_LIKE", "m1a", ["..k", "...", "KR."])),
        ("M1", "remove_from_game", "WESTERN_CHESS_LIKE", c_western, _state(c_western, "WESTERN_CHESS_LIKE", "m1b", ["..k", "...", "KRp"]), _state(c_western, "WESTERN_CHESS_LIKE", "m1a", ["..k", "...", "KR."])),
        ("M2", "drop_capable", "SHOGI_LIKE", c_shogi, _state(c_shogi, "SHOGI_LIKE", "m2b", ["..k", "...", "K.."]), _state(c_shogi, "SHOGI_LIKE", "m2a", ["..k", "...", "K.."], ((('P', 1),), ()))),
        ("M2", "no_drop_capability_control", "WESTERN_CHESS_LIKE", c_western, _state(c_western, "WESTERN_CHESS_LIKE", "m2b", ["..k", "...", "K.."]), _state(c_western, "WESTERN_CHESS_LIKE", "m2a", ["..k", "...", "K.."], ((('P', 1),), ()))),
        ("M3", "unblock_semantic_path", "SHOGI_LIKE", c_shogi, _state(c_shogi, "SHOGI_LIKE", "m3b", ["K..", "P..", "R.k"]), _state(c_shogi, "SHOGI_LIKE", "m3a", ["K..", "...", "R.k"])),
        ("M4", "remove_opponent_drop_action", "SHOGI_LIKE", c_shogi, _state(c_shogi, "SHOGI_LIKE", "m4b", ["..k", "...", "K.."], ((), (('P', 1),))), _state(c_shogi, "SHOGI_LIKE", "m4a", ["..k", "...", "K.."])),
        ("M5", "attacked_to_unattacked_anchor", "SHOGI_LIKE", c_shogi, _state(c_shogi, "SHOGI_LIKE", "m5b", ["..k", "...", "Kr."]), _state(c_shogi, "SHOGI_LIKE", "m5a", ["..k", "K..", ".r."])),
        ("M6", "add_opponent_anchor_attack", "SHOGI_LIKE", c_shogi, _state(c_shogi, "SHOGI_LIKE", "m6b", ["..k", "...", "K.."]), _state(c_shogi, "SHOGI_LIKE", "m6a", ["..k", "...", "K.R"])),
        ("M7", "capture_to_hand", "SHOGI_LIKE", c_shogi, _state(c_shogi, "SHOGI_LIKE", "m7b", ["..k", "...", "KR."]), _state(c_shogi, "SHOGI_LIKE", "m7a", ["..k", "...", "KRp"])),
        ("M7", "remove_from_game", "WESTERN_CHESS_LIKE", c_western, _state(c_western, "WESTERN_CHESS_LIKE", "m7b", ["..k", "...", "KR."]), _state(c_western, "WESTERN_CHESS_LIKE", "m7a", ["..k", "...", "KRp"])),
        ("M8", "history_linked_recapture", "SHOGI_LIKE", c_shogi, *f23x._history_pair(c_shogi)),
        ("M9", "positive_gain_promotion", "SHOGI_LIKE", c_shogi, _state(c_shogi, "SHOGI_LIKE", "m9b", ["K..", "P..", "..k"]), _state(c_shogi, "SHOGI_LIKE", "m9a", ["K..", ".P.", "..k"])),
        ("M10", "capture_to_hand_drop", "SHOGI_LIKE", c_shogi, _state(c_shogi, "SHOGI_LIKE", "m10b", ["..k", "...", "K.."]), _state(c_shogi, "SHOGI_LIKE", "m10a", ["..k", "...", "K.."], ((('P', 1),), ()))),
        ("M10", "mixed_mechanic_drop", "MIXED_MECHANIC", c_mixed, _state(c_mixed, "MIXED_MECHANIC", "m10b", ["..k", "...", "K.."]), _state(c_mixed, "MIXED_MECHANIC", "m10a", ["..k", "...", "K.."], ((('P', 1),), ()))),
    ]
    return pairs


def _m9_preflight() -> dict[str, Any]:
    compiled = _compiled("SHOGI_LIKE")
    before = _state(compiled, "SHOGI_LIKE", "m9b", ["K..", "P..", "..k"])
    after = _state(compiled, "SHOGI_LIKE", "m9a", ["K..", ".P.", "..k"])
    evaluator = InstrumentedContext(compiled, "P0")
    before_context, after_context = evaluator.build_context(before), evaluator.build_context(after)
    before_actions = {_action_key(action) for action in before_context.promotions[0]}
    promotions = list(after_context.promotions[0])
    action_data = [_action_data(action) for action in promotions]
    selected = promotions[0] if len(promotions) == 1 else next((item for item in promotions if _action_data(item).get("promotion_target_id")), None)
    data = None if selected is None else _action_data(selected)
    base = None if data is None else data.get("actor_type_id", data.get("actor_type"))
    target = None if data is None else data.get("promotion_target_id")
    gain = None if base is None else evaluator.profile.promotion_gain_by_type.get(base)
    before_vector = evaluator.feature_vector(before, 0, before_context)
    after_vector = evaluator.feature_vector(after, 0, after_context)
    delta = after_vector[FEATURES[4]] - before_vector[FEATURES[4]]
    passed = bool(not before_actions and len(promotions) >= 1 and data is not None and gain is not None and gain > 0 and delta > TOLERANCE)
    return {"passed": passed, "before_promotion_count": len(before_context.promotions[0]), "after_promotion_count": len(promotions), "selected_action": data, "base_type": base, "promotion_target": target, "promotion_gain": gain, "feature_delta": delta, "promotion_action_only_after": not before_actions}


def _rename_preflight() -> dict[str, Any]:
    rows = []
    for contract_id, variant, group, compiled, before, after in _contract_pairs():
        type_ids = tuple(compiled.support.type_metadata)
        mapping = {tid: f"T{index}" for index, tid in enumerate(type_ids)}
        renamed_rules = _rename_rules(group, mapping)
        renamed_compiled = compile_semantic_ruleset(renamed_rules)
        renamed_before = _rename_state(before, mapping, renamed_compiled.ruleset_fingerprint)
        renamed_after = _rename_state(after, mapping, renamed_compiled.ruleset_fingerprint)
        left, right = InstrumentedContext(compiled, "P0"), InstrumentedContext(renamed_compiled, "P0")
        lv_before, lv_after = left.feature_vector(before, 0), left.feature_vector(after, 0)
        rv_before, rv_after = right.feature_vector(renamed_before, 0), right.feature_vector(renamed_after, 0)
        ldelta = lv_after[FEATURES[0]] - lv_before[FEATURES[0]]
        rdelta = rv_after[FEATURES[0]] - rv_before[FEATURES[0]]
        lscore_before, lscore_after = left.score(before, 0), left.score(after, 0)
        rscore_before, rscore_after = right.score(renamed_before, 0), right.score(renamed_after, 0)
        vector_before = lv_before == rv_before
        vector_after = lv_after == rv_after
        passed = bool(vector_before and vector_after and abs(ldelta - rdelta) <= TOLERANCE and abs(lscore_before - rscore_before) <= TOLERANCE and abs(lscore_after - rscore_after) <= TOLERANCE)
        rows.append({"contract": contract_id, "variant": variant, "mapping": mapping, "before_vector_equal": vector_before, "after_vector_equal": vector_after, "delta_equal": abs(ldelta - rdelta) <= TOLERANCE, "score_before_equal": abs(lscore_before - rscore_before) <= TOLERANCE, "score_after_equal": abs(lscore_after - rscore_after) <= TOLERANCE, "passed": passed})
    return {"contract_count": len({row["contract"] for row in rows}), "variant_count": len(rows), "rows": rows, "passed": len({row["contract"] for row in rows}) == 10 and len(rows) == 14 and all(row["passed"] for row in rows)}


def _parity_states() -> list[dict[str, Any]]:
    states, _ = _microbenchmark_states()
    return states


def _context_parity(states: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for item in states:
        compiled, state = item["compiled"], item["state"]
        p0, p1 = InstrumentedContext(compiled, "P0"), InstrumentedContext(compiled, "P1")
        p0_context, p1_context = p0.build_context(state), p1.build_context(state)
        p0_vector, p1_vector = p0.feature_vector(state, state.position.side_to_move, p0_context), p1.feature_vector(state, state.position.side_to_move, p1_context)
        rows.append({"label": item["descriptor"]["label"], "vector_equal": all(abs(p0_vector[name] - p1_vector[name]) <= TOLERANCE for name in FEATURES), "score_equal": abs(p0.score(state, state.position.side_to_move) - p1.score(state, state.position.side_to_move)) <= TOLERANCE})
    return {"state_count": len(rows), "rows": rows, "passed": bool(rows and all(row["vector_equal"] and row["score_equal"] for row in rows))}


def _attack_and_action_parity(states: list[dict[str, Any]]) -> dict[str, Any]:
    attack_rows = []
    action_rows = []
    check_rows = []
    for item in states:
        compiled, state = item["compiled"], item["state"]
        p1 = InstrumentedContext(compiled, "P1")
        context = p1.build_context(state)
        engine = p1.engine
        for owner in (0, 1):
            reference = {index for index in range(compiled.board_size ** 2) if engine.is_square_attacked(state.position, index, owner)}
            bulk = set(p1._bulk_attacks(state.position, owner))
            attack_rows.append({"label": item["descriptor"]["label"], "owner": owner, "mismatch_count": len(reference ^ bulk), "passed": reference == bulk})
            current = tuple(f23vr1._semantic_actions(compiled, state.position, owner))
            cached = tuple(engine.legal_actions(replace(state.position, side_to_move=owner)))
            action_rows.append({"label": item["descriptor"]["label"], "owner": owner, "order_equal": [_action_key(x) for x in current] == [_action_key(x) for x in cached], "set_equal": {_action_key(x) for x in current} == {_action_key(x) for x in cached}})
        for owner in (0, 1):
            anchor = context.anchors[owner]
            expected = False if anchor is None else engine.in_check(state.position, owner)
            derived = False if anchor is None else anchor in p1._bulk_attacks(state.position, 1 - owner)
            check_rows.append({"label": item["descriptor"]["label"], "owner": owner, "engine": expected, "bulk": derived, "passed": expected == derived})
    return {"attack": {"rows": attack_rows, "passed": all(row["passed"] for row in attack_rows)}, "legal_action": {"rows": action_rows, "passed": all(row["order_equal"] and row["set_equal"] for row in action_rows)}, "check": {"rows": check_rows, "passed": all(row["passed"] for row in check_rows)}}


def _metamorphic_parity() -> dict[str, Any]:
    rows = []
    for contract_id, variant, _group, compiled, before, after in _contract_pairs():
        p0, p1 = InstrumentedContext(compiled, "P0"), InstrumentedContext(compiled, "P1")
        b0, a0 = p0.feature_vector(before, 0), p0.feature_vector(after, 0)
        b1, a1 = p1.feature_vector(before, 0), p1.feature_vector(after, 0)
        checks = []
        for name in FEATURES:
            checks.append(abs(b0[name] - b1[name]) <= TOLERANCE and abs(a0[name] - a1[name]) <= TOLERANCE and abs((a0[name] - b0[name]) - (a1[name] - b1[name])) <= TOLERANCE)
        rows.append({"contract": contract_id, "variant": variant, "passed": all(checks), "feature_checks": dict(zip(FEATURES, checks))})
    return {"contract_count": len({row["contract"] for row in rows}), "variant_count": len(rows), "rows": rows, "passed": len({row["contract"] for row in rows}) == 10 and len(rows) == 14 and all(row["passed"] for row in rows)}


def _summary(evaluator: InstrumentedContext, elapsed: list[float]) -> dict[str, Any]:
    return {"calls": evaluator.eval_count, "median_evaluate_seconds": statistics.median(elapsed), "p95_evaluate_seconds": statistics.quantiles(elapsed, n=20, method="inclusive")[18] if len(elapsed) > 1 else elapsed[0], "profile_build_count": evaluator.profile_build_count, "profile_build_seconds": evaluator.profile_build_seconds, "timing_totals": evaluator.total_timings, "semantic_legal_action_enumerations": evaluator.semantic_legal_action_enumerations, "is_square_attacked_calls": evaluator.is_square_attacked_calls}


def _micro_cost(states: list[dict[str, Any]]) -> dict[str, Any]:
    by_mode: dict[str, list[float]] = {"P0": [], "P1": [], "v1": []}
    details: dict[str, Any] = {}
    for mode in ("P0", "P1"):
        evaluators: dict[str, InstrumentedContext] = {}
        elapsed_by_fingerprint: dict[str, list[float]] = {}
        for item in states:
            evaluator = evaluators.setdefault(item["compiled"].ruleset_fingerprint, InstrumentedContext(item["compiled"], mode))
            elapsed = []
            for _ in range(MICRO_REPETITIONS):
                started = time.perf_counter(); evaluator.score(item["state"], item["state"].position.side_to_move); elapsed.append(time.perf_counter() - started)
            by_mode[mode].extend(elapsed)
            elapsed_by_fingerprint.setdefault(item["compiled"].ruleset_fingerprint, []).extend(elapsed)
        details[mode] = {fingerprint: _summary(evaluator, elapsed_by_fingerprint[fingerprint]) for fingerprint, evaluator in evaluators.items()}
    v1_elapsed = []
    for item in states:
        evaluator = _production(item["compiled"])
        for _ in range(MICRO_REPETITIONS):
            started = time.perf_counter(); evaluator.evaluate(item["state"]); v1_elapsed.append(time.perf_counter() - started)
    by_mode["v1"] = v1_elapsed
    summaries = {mode: {"calls": len(values), "median_evaluate_seconds": statistics.median(values), "p95_evaluate_seconds": statistics.quantiles(values, n=20, method="inclusive")[18] if len(values) > 1 else values[0]} for mode, values in by_mode.items()}
    for mode in ("P0", "P1"):
        summaries[mode]["details"] = details[mode]
    summaries["P1"]["speedup_vs_P0"] = summaries["P0"]["median_evaluate_seconds"] / summaries["P1"]["median_evaluate_seconds"] if summaries["P1"]["median_evaluate_seconds"] else None
    return {"state_count": len(states), "state_descriptor_sha256": _sha([item["descriptor"] for item in states]), "summaries": summaries}


def _search_once(compiled: Any, state: Any, evaluator: Any, *, nodes: int | None = None, seconds: float | None = None, provider: Any = None) -> dict[str, Any]:
    stats = SearchStatistics()
    limits = SearchLimits(max_nodes=nodes, max_time_seconds=seconds, quiescence_max_depth=0, deterministic=True)
    started = time.perf_counter()
    action, score, pv, reason = run_root_search(state, compiled, evaluator, TranspositionTable(max_entries=250_000), limits, None, stats, use_tt=True, use_ordering=True, tuning=SearchTuning(), legal_binding_provider=provider)
    wall = time.perf_counter() - started
    return {"selected_move": None if action is None else gc_action_to_usi(action), "score": score, "nodes": stats.nodes, "qnodes": stats.qnodes, "nodes_per_second": (stats.nodes + stats.qnodes) / wall if wall else None, "total_search_wall": wall, "termination_reason": reason, "complete": action is not None and reason in {"node_limit", "time_limit", "completed", "max_depth"}}


def _watchdog_worker(out: Any, sfen: str, mode: str, budget: int) -> None:
    compiled = f23x._certified_compiled()
    state = sfen_to_gc_state(compiled, sfen)
    provider = NativeSemanticLegalityProvider.try_create(compiled)
    production = _production(compiled)
    if mode == "v1":
        evaluator = EvaluatorAdapter(production, production)
    else:
        evaluator = EvaluatorAdapter(InstrumentedContext(compiled, "P1"), production)
    row = _search_once(compiled, state, evaluator, nodes=budget, provider=provider)
    row.update({"mode": mode, "budget": budget, "provider_mode": "NATIVE_PROVIDER_ACTIVE" if provider is not None else "PYTHON_AUTHORITY_FALLBACK", "declared_budget_complete": row["termination_reason"] == "node_limit", "evaluator_calls": evaluator.calls, "evaluator_time": evaluator.seconds, "context_time": evaluator.context_seconds, "aggregation_time": evaluator.aggregation_seconds, "profile_build_count": getattr(evaluator.evaluator, "profile_build_count", None), "profile_build_seconds": getattr(evaluator.evaluator, "profile_build_seconds", None), "timing_totals": getattr(evaluator.evaluator, "total_timings", {})})
    out.put(row)


def _watchdog(sfen: str, mode: str, budget: int) -> dict[str, Any]:
    context = multiprocessing.get_context("spawn")
    out = context.Queue()
    process = context.Process(target=_watchdog_worker, args=(out, sfen, mode, budget))
    process.start(); process.join(NODE_WATCHDOG_SECONDS[budget])
    if process.is_alive():
        process.terminate(); process.join()
        return {"mode": mode, "budget": budget, "complete": False, "declared_budget_complete": False, "termination_reason": "WATCHDOG_TIMEOUT"}
    try:
        return out.get(timeout=1)
    except queue.Empty:
        return {"mode": mode, "budget": budget, "complete": False, "declared_budget_complete": False, "termination_reason": "WORKER_FAILURE"}


def _fixed_time() -> dict[str, Any]:
    f22, references = f23x._load_f22()
    compiled = f23x._certified_compiled()
    rows = []
    for position_index, position in enumerate(f22["positions"]):
        state = sfen_to_gc_state(compiled, position["sfen"])
        for seconds in TIME_BUDGETS:
            for repetition in range(TIME_REPETITIONS):
                order = ("v1", "P1") if (position_index + repetition) % 2 == 0 else ("P1", "v1")
                for mode in order:
                    provider = NativeSemanticLegalityProvider.try_create(compiled)
                    production = _production(compiled)
                    evaluator = EvaluatorAdapter(production, production) if mode == "v1" else EvaluatorAdapter(InstrumentedContext(compiled, "P1"), production)
                    result = _search_once(compiled, state, evaluator, seconds=seconds, provider=provider)
                    result.update({"mode": mode, "position_id": position["name"], "budget_seconds": seconds, "repetition": repetition, "reference_move": references[position["name"]], "reference_top1": result["selected_move"] == references[position["name"]], "provider_mode": "NATIVE_PROVIDER_ACTIVE" if provider is not None else "PYTHON_AUTHORITY_FALLBACK", "evaluator_calls": evaluator.calls, "evaluator_time": evaluator.seconds, "context_time": evaluator.context_seconds, "aggregation_time": evaluator.aggregation_seconds, "profile_build_count": getattr(evaluator.evaluator, "profile_build_count", None), "profile_build_seconds": getattr(evaluator.evaluator, "profile_build_seconds", None), "timing_totals": getattr(evaluator.evaluator, "total_timings", {})})
                    rows.append(result)
    summaries = {}
    paired = {}
    for seconds in TIME_BUDGETS:
        subset = [row for row in rows if row["budget_seconds"] == seconds]
        summaries[str(seconds)] = {}
        for mode in ("v1", "P1"):
            current = [row for row in subset if row["mode"] == mode]
            call_seconds = [row["evaluator_time"] / max(1, row["evaluator_calls"]) for row in current]
            summaries[str(seconds)][mode] = {"runs": len(current), "complete": all(row["complete"] for row in current), "median_nps": statistics.median(row["nodes_per_second"] for row in current), "median_evaluator_fraction": statistics.median(row["evaluator_time"] / row["total_search_wall"] for row in current if row["total_search_wall"]), "evaluator_calls": sum(row["evaluator_calls"] for row in current), "evaluator_time": sum(row["evaluator_time"] for row in current), "median_call_seconds": statistics.median(call_seconds), "p95_call_seconds": statistics.quantiles(call_seconds, n=20, method="inclusive")[18] if len(call_seconds) > 1 else call_seconds[0], "profile_build_seconds": sum(row.get("profile_build_seconds") or 0.0 for row in current), "context_time": sum(row["context_time"] for row in current), "aggregation_time": sum(row["aggregation_time"] for row in current)}
        ratios = []
        for position in f22["positions"]:
            for repetition in range(TIME_REPETITIONS):
                v1 = next(row for row in subset if row["position_id"] == position["name"] and row["repetition"] == repetition and row["mode"] == "v1")
                p1 = next(row for row in subset if row["position_id"] == position["name"] and row["repetition"] == repetition and row["mode"] == "P1")
                ratios.append({"position_id": position["name"], "repetition": repetition, "ratio": p1["nodes_per_second"] / v1["nodes_per_second"] if v1["nodes_per_second"] else None})
        paired[str(seconds)] = {"ratios": ratios, "median_ratio": statistics.median(row["ratio"] for row in ratios if row["ratio"] is not None)}
    for seconds in TIME_BUDGETS:
        candidate = summaries[str(seconds)]["P1"]
        summaries[str(seconds)]["gates"] = {"candidate_evaluator_fraction": candidate["median_evaluator_fraction"], "fraction_passed": candidate["median_evaluator_fraction"] <= 0.25, "paired_median_nps_ratio": paired[str(seconds)]["median_ratio"], "nps_passed": paired[str(seconds)]["median_ratio"] >= 0.65, "all_runs_valid": candidate["complete"] and summaries[str(seconds)]["v1"]["complete"]}
    return {"runs": rows, "summaries": summaries, "paired_ratios": paired, "passed": all(summary["gates"]["fraction_passed"] and summary["gates"]["nps_passed"] and summary["gates"]["all_runs_valid"] for summary in summaries.values())}


def _fixed_node() -> dict[str, Any]:
    f22, references = f23x._load_f22()
    rows = []
    progressive_stop = None
    for budget in NODE_BUDGETS:
        budget_rows = []
        for position in f22["positions"]:
            for mode in ("v1", "P1"):
                row = _watchdog(position["sfen"], mode, budget)
                row.update({"position_id": position["name"], "reference_move": references[position["name"]], "reference_top1": row.get("selected_move") == references[position["name"]] if row.get("complete") else None})
                rows.append(row); budget_rows.append(row)
        if not all(row.get("declared_budget_complete", False) for row in budget_rows):
            progressive_stop = {"budget": budget, "reason": "NOT_COMPLETED_WITHIN_OUTER_WATCHDOG"}
            break
    summary = {}
    for budget in NODE_BUDGETS:
        summary[str(budget)] = {}
        for mode in ("v1", "P1"):
            current = [row for row in rows if row.get("budget") == budget and row.get("mode") == mode]
            summary[str(budget)][mode] = {"runs": len(current), "complete": bool(current) and all(row.get("complete") for row in current), "declared_budget_complete": bool(current) and all(row.get("declared_budget_complete") for row in current), "top1_count": sum(bool(row.get("reference_top1")) for row in current), "median_nodes": statistics.median([row["nodes"] for row in current if row.get("nodes") is not None]) if any(row.get("nodes") is not None for row in current) else None, "median_nps": statistics.median([row["nodes_per_second"] for row in current if row.get("nodes_per_second") is not None]) if any(row.get("nodes_per_second") is not None for row in current) else None, "evaluator_calls": sum(row.get("evaluator_calls", 0) for row in current), "evaluator_time": sum(row.get("evaluator_time", 0.0) for row in current), "context_time": sum(row.get("context_time", 0.0) for row in current), "aggregation_time": sum(row.get("aggregation_time", 0.0) for row in current), "profile_build_counts": sorted({row.get("profile_build_count") for row in current})}
    quality = {"valid": progressive_stop is None, "root_rank_status": "ROOT_RANK_HARNESS_UNAVAILABLE", "top1_delta": None, "controls_passed": None, "passed": False}
    if quality["valid"]:
        quality["top1_delta"] = summary["2048"]["P1"]["top1_count"] - summary["2048"]["v1"]["top1_count"]
        controls = [row for row in f22["agreement"]["rows"] if row.get("high_agreement") or row.get("low_agreement")]
        control_results = []
        for control in controls:
            v1 = next(row for row in rows if row.get("position_id") == control["position_id"] and row.get("budget") == 2048 and row.get("mode") == "v1")
            p1 = next(row for row in rows if row.get("position_id") == control["position_id"] and row.get("budget") == 2048 and row.get("mode") == "P1")
            control_results.append({"position_id": control["position_id"], "v1_top1": v1.get("reference_top1"), "p1_top1": p1.get("reference_top1"), "passed": not v1.get("reference_top1") or p1.get("reference_top1")})
        quality["control_results"] = control_results
        quality["controls_passed"] = all(row["passed"] for row in control_results)
        quality["passed"] = quality["top1_delta"] >= 2 and quality["controls_passed"]
    return {"runs": rows, "summary": summary, "progressive_stop": progressive_stop, "quality_gate": quality}


def _artifact_integrity() -> dict[str, Any]:
    paths = ["docs/architecture/ADR-071-minimal-analytic-metamorphic-shogi-shadow.md", "scripts/audit_f23x_metamorphic_shogi_shadow.py", "tests/fixtures/f23x_shogi_shadow.json", "tests/test_f23x_metamorphic_shogi_shadow.py"]
    result = []
    for path in paths:
        current = (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
        baseline = f23x._git_show(path, F23X_FIRST_PASS_COMMIT).replace(b"\r\n", b"\n")
        result.append({"path": path, "matches": current == baseline})
    return {"baseline_commit": F23X_FIRST_PASS_COMMIT, "files": result, "all_match": all(row["matches"] for row in result)}


def run() -> dict[str, Any]:
    m9 = _m9_preflight()
    rename = _rename_preflight() if m9["passed"] else {"count": 0, "rows": [], "passed": False, "skipped": True}
    states, descriptor_sha = _microbenchmark_states()
    preflight = {"m9_positive_gain": m9, "contract_specific_rename": rename, "microbenchmark": {"state_count": len(states), "descriptor_sha256": descriptor_sha, "descriptors": [item["descriptor"] for item in states]}, "passed": m9["passed"] and rename["passed"]}
    result: dict[str, Any] = {"schema_version": 1, "score_form": "S * sum(feature_i)", "feature_families": list(FEATURES), "coefficients": list(COEFFICIENTS), "f23x_r1_interpretation": {"semantic_direction": "PASS", "real_game_2048_quality": "NOT_EVALUABLE", "fixed_time_performance": "FAIL", "playing_strength": "NOT_RUN", "boundary": "F23Y_MINIMAL_ANALYTIC_EVALUATOR_CONTEXT_PERFORMANCE_PROBE"}, "preflight": preflight, "artifact_integrity": _artifact_integrity(), "production_changed": False}
    if not preflight["passed"]:
        result.update({"status": "FAIL", "selected_boundary": "F23Z_EVALUATOR_REPRESENTATION_REASSESSMENT", "phase_p1": False})
        return result
    context_parity = _context_parity(states)
    semantic_parity = _attack_and_action_parity(states)
    metamorphic = _metamorphic_parity()
    result["p1_parity"] = {"context_math": context_parity, "bulk_semantic": semantic_parity, "metamorphic_delta": metamorphic, "passed": context_parity["passed"] and semantic_parity["attack"]["passed"] and semantic_parity["legal_action"]["passed"] and semantic_parity["check"]["passed"] and metamorphic["passed"]}
    if not result["p1_parity"]["passed"]:
        result.update({"status": "FAIL", "selected_boundary": "F23Z_EVALUATOR_REPRESENTATION_REASSESSMENT", "phase_p1": False})
        return result
    result["micro_cost"] = _micro_cost(states)
    result["fixed_time"] = _fixed_time()
    result["fixed_node"] = _fixed_node()
    candidate_gate = all(result["fixed_time"]["summaries"][str(seconds)]["gates"]["fraction_passed"] and result["fixed_time"]["summaries"][str(seconds)]["gates"]["nps_passed"] for seconds in TIME_BUDGETS)
    if result["fixed_time"]["summaries"]["0.25"]["gates"]["candidate_evaluator_fraction"] > 0.50 or result["fixed_time"]["summaries"]["1.0"]["gates"]["candidate_evaluator_fraction"] > 0.50 or any(result["fixed_time"]["paired_ratios"][str(seconds)]["median_ratio"] < 0.35 for seconds in TIME_BUDGETS):
        boundary = "F23Z_EVALUATOR_REPRESENTATION_REASSESSMENT"
    elif candidate_gate and result["fixed_node"]["quality_gate"]["valid"] and result["fixed_node"]["quality_gate"]["passed"]:
        boundary = "F23Z_STANDARD_SHOGI_BENCHMARK_EXPANSION"
    elif candidate_gate and result["fixed_node"]["progressive_stop"] is not None:
        boundary = "F23Z_EVALUATOR_VALIDATION_DIAGNOSTIC"
    else:
        boundary = "F23Z_EVALUATOR_REPRESENTATION_REASSESSMENT"
    result.update({"status": "PASS" if boundary == "F23Z_STANDARD_SHOGI_BENCHMARK_EXPANSION" else "FAIL", "selected_boundary": boundary, "phase_p1": True, "root_rank_status": "ROOT_RANK_HARNESS_UNAVAILABLE", "native_routing_policy": sorted({row["provider_mode"] for row in result["fixed_time"]["runs"] if row.get("provider_mode")} )})
    return result


def main() -> None:
    result = run()
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "preflight": result["preflight"]["passed"], "p1": result.get("phase_p1", False), "selected": result["selected_boundary"]}))


if __name__ == "__main__":
    main()
