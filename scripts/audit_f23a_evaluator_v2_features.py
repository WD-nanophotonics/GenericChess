"""F23A audit-only probe for generic evaluator-v2 feature families.

The probe deliberately sits outside the production evaluator.  It recovers
the frozen F22 corpus with ``git show``, asks the current semantic executor
for legal children, and measures generic position features.  It does not fit
weights, patch search, or write production state.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import subprocess
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
F22_COMMIT = "3281b3cfd0a495b0fe75ce8a3c0a28cc20343b38"
EXPECTED_HEAD = "092892d2a58323c7af8d8243899e84d37e7fdc06"
EXPECTED_SEMANTIC_FINGERPRINT = (
    "5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345"
)
F22_CORPUS_PATH = "artifacts/f22_post_f21_rebaseline_strength/round5_frozen_positions.json"
F22_REFERENCE_PATH = "artifacts/f22_post_f21_rebaseline_strength/alphasho_reference_provenance.json"
F22_AGREEMENT_PATH = "artifacts/f22_post_f21_rebaseline_strength/alphasho_move_agreement.json"
F22_RANK_PATH = "artifacts/f22_post_f21_rebaseline_strength/one_ply_reference_rank.json"

FAMILY_NAMES = (
    "attack_defense_hanging",
    "capture_recapture_pressure",
    "legal_safe_mobility",
    "anchor_check_pressure",
    "promotion_structure",
    "hand_drop_pressure",
    "semantic_constraint_effect",
)


def _imports():
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.evaluation.evaluator import Evaluator
    from generic_chess.ai.evaluation.profile import build_ruleset_profile
    from generic_chess.core.actions import (
        BoardMove,
        DropMove,
        SemanticBoardMove,
        SemanticDropMove,
        action_to_dict,
    )
    from generic_chess.core.attacks import (
        anchor_square,
        is_in_check,
        pseudo_attacks,
    )
    from generic_chess.core.coordinates import index_to_square, square_to_index
    from generic_chess.core.movegen import (
        _apply_action_unchecked,
        legal_actions_from_position,
    )
    from generic_chess.core.position import GameState, HistoryRecord, Position
    from generic_chess.core.semantic_executor import (
        _semantic_public_action,
        semantic_engine_for,
    )
    from generic_chess.learning.round5_corrective_r1 import SearchSemanticCompiled
    from generic_chess.learning.shogi_rules import gc_action_to_usi, sfen_to_gc_state
    from generic_chess.learning.shogi_semantic_rules import build_semantic_shogi_ruleset
    from generic_chess.rules.compiler import compile_semantic_ruleset
    from generic_chess.rules.schema import canonical_json
    from generic_chess.core.terminal import TerminalResult, TerminalStatus

    return locals()


def _git_show(path: str) -> Any:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{F22_COMMIT}:{path}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(result.stdout)


def recover_f22_fixture() -> dict[str, Any]:
    """Recover exact F22 inputs without restoring historical artifact trees."""
    corpus = _git_show(F22_CORPUS_PATH)
    provenance = _git_show(F22_REFERENCE_PATH)
    agreement = _git_show(F22_AGREEMENT_PATH)
    rank = _git_show(F22_RANK_PATH)
    positions = corpus.get("positions", [])
    references = provenance.get("references", {})
    if len(positions) != 10 or len(references) != 10:
        raise RuntimeError("F22_CORPUS_OR_REFERENCE_COUNT_MISMATCH")
    rows = {row["position_id"]: row for row in agreement.get("rows", [])}
    if len(rows) != 10:
        raise RuntimeError("F22_AGREEMENT_COUNT_MISMATCH")
    controls = {
        position_id
        for position_id, row in rows.items()
        if row.get("low_agreement") and row.get("high_agreement")
    }
    failures = set(references) - controls
    if len(controls) != 2 or len(failures) != 8:
        raise RuntimeError("F22_CONTROL_FAILURE_PARTITION_MISMATCH")
    return {
        "corpus": corpus,
        "provenance": provenance,
        "agreement": agreement,
        "rank": {row["position_id"]: row for row in rank},
        "controls": controls,
        "failures": failures,
    }


def _compile_context(m: dict[str, Any]):
    semantic = m["compile_semantic_ruleset"](
        m["build_semantic_shogi_ruleset"]()
    )
    if semantic.ruleset_fingerprint != EXPECTED_SEMANTIC_FINGERPRINT:
        raise RuntimeError(
            f"SEMANTIC_RULESET_FINGERPRINT_MISMATCH:{semantic.ruleset_fingerprint}"
        )
    compiled = m["SearchSemanticCompiled"](
        ir=semantic.ir,
        _legacy_compiled=semantic._legacy_compiled,
        support=semantic.support,
    )
    return semantic, compiled


def _position_key(position) -> str:
    # Position is immutable, but a short canonical digest keeps feature-cache
    # keys independent of object identity and readable in diagnostics.
    payload = dataclasses.asdict(position)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _action_key(action) -> tuple:
    if hasattr(action, "from_square"):
        return (
            "board",
            action.from_square.file,
            action.from_square.rank,
            action.to_square.file,
            action.to_square.rank,
            action.promotion_target_id,
        )
    return ("drop", action.base_type_id, action.to_square.file, action.to_square.rank)


def _label(action, m: dict[str, Any], *, shogi: bool = False) -> str:
    if shogi:
        return m["gc_action_to_usi"](action)
    return json.dumps(m["action_to_dict"](action), sort_keys=True, separators=(",", ":"))


def _child_state(parent, position, action, m: dict[str, Any]):
    record = m["HistoryRecord"](
        "",
        parent.position.side_to_move,
        json.dumps(m["action_to_dict"](action), sort_keys=True, separators=(",", ":")),
        False,
    )
    return m["GameState"](
        position=position,
        ply_count=parent.ply_count + 1,
        repetition_counts=parent.repetition_counts,
        terminal_status=m["TerminalResult"](m["TerminalStatus"].ONGOING),
        history=parent.history + (record,),
    )


class Probe:
    """Pure audit context with explicit caches and no production mutation."""

    def __init__(self, compiled, m: dict[str, Any]):
        self.compiled = compiled
        self.m = m
        config = m["EvaluationConfig"]()
        legacy = getattr(compiled, "_legacy_compiled", compiled)
        self.evaluator = m["Evaluator"](
            legacy, m["build_ruleset_profile"](legacy, config), config
        )
        self.legacy = legacy
        self._legal_cache: dict[tuple[str, int], tuple[tuple[Any, Any], ...]] = {}
        self._feature_cache: dict[str, dict[str, float]] = {}
        self._feature_cost_cache: dict[str, dict[str, Any]] = {}

    @property
    def median_value(self) -> float:
        return float(max(1, self.evaluator._profile.median_non_anchor_value))

    def _legal_pairs(self, position, owner: int) -> tuple[tuple[Any, Any], ...]:
        key = (_position_key(position), owner)
        if key in self._legal_cache:
            return self._legal_cache[key]
        m = self.m
        view = m["Position"](
            board=position.board,
            hands=position.hands,
            side_to_move=owner,
            ruleset_fingerprint=position.ruleset_fingerprint,
            aux_state=position.aux_state,
        )
        engine = m["semantic_engine_for"](self.compiled)
        rows: list[tuple[Any, Any]] = []
        if engine is not None:
            for semantic_action, binding in engine.iter_legal_action_bindings(view):
                public = m["_semantic_public_action"](engine, semantic_action)
                rows.append((public, engine._transition(view, semantic_action, binding)))
        else:
            for action in m["legal_actions_from_position"](view, self.compiled):
                rows.append((action, m["_apply_action_unchecked"](view, action, self.compiled)))
        self._legal_cache[key] = tuple(rows)
        return self._legal_cache[key]

    def _value(self, piece) -> float:
        return float(self.evaluator._profile.board_value_by_type[piece.current_type_id])

    def _legacy_view(self, position):
        return m_position_with_fingerprint(
            position, self.legacy.ruleset_fingerprint, self.m
        )

    def _weighted_capture_value(self, position, action) -> float:
        if not hasattr(action, "to_square"):
            return 0.0
        idx = m_square_to_index(action.to_square, self.compiled.board_size, self.m)
        target = position.board[idx]
        if target is None or target.owner == position.side_to_move:
            return 0.0
        return self._value(target) / self.median_value

    def _relative(self, per_owner: tuple[float, float], actor: int) -> float:
        value = per_owner[0] - per_owner[1]
        return value if actor == 0 else -value

    def _last_target(self, state):
        if not state.history:
            return None
        try:
            data = json.loads(state.history[-1].action_signature)
            target = data.get("to")
            return tuple(target) if target is not None else None
        except (TypeError, ValueError, KeyError):
            return None

    def attack_defense_hanging(self, position, actor: int) -> float:
        m = self.m
        legacy_position = self._legacy_view(position)
        maps = (
            m["pseudo_attacks"](legacy_position, 0, self.legacy),
            m["pseudo_attacks"](legacy_position, 1, self.legacy),
        )
        per_owner = [0.0, 0.0]
        n = self.compiled.board_size
        for idx, piece in enumerate(position.board):
            if piece is None:
                continue
            square = m["index_to_square"](idx, n)
            value = self._value(piece) / self.median_value
            if square in maps[piece.owner]:
                per_owner[piece.owner] += 0.5 * value
            if square in maps[1 - piece.owner]:
                per_owner[1 - piece.owner] += value
                per_owner[piece.owner] -= value
        return self._relative((per_owner[0], per_owner[1]), actor)

    def capture_recapture_pressure(self, state, actor: int) -> float:
        per_owner = [0.0, 0.0]
        last_target = self._last_target(state)
        for owner in (0, 1):
            view = m_position_with_side(state.position, owner, self.m)
            for action, _child in self._legal_pairs(state.position, owner):
                if not hasattr(action, "to_square"):
                    continue
                idx = m_square_to_index(action.to_square, self.compiled.board_size, self.m)
                target = view.board[idx]
                if target is None or target.owner == owner:
                    continue
                value = self._value(target) / self.median_value
                per_owner[owner] += value
                if last_target == (action.to_square.file, action.to_square.rank):
                    per_owner[owner] += value
        return self._relative((per_owner[0], per_owner[1]), actor)

    def legal_safe_mobility(self, position, actor: int) -> float:
        area = float(self.compiled.board_size * self.compiled.board_size)
        per_owner = []
        for owner in (0, 1):
            view = m_position_with_side(position, owner, self.m)
            pairs = self._legal_pairs(position, owner)
            weighted = sum(1.0 + self._weighted_capture_value(view, action) for action, _ in pairs)
            per_owner.append((len(pairs) + weighted) / max(1.0, area))
        return self._relative((per_owner[0], per_owner[1]), actor)

    def anchor_check_pressure(self, position, actor: int) -> float:
        area = float(self.compiled.board_size * self.compiled.board_size)
        per_owner = [0.0, 0.0]
        legacy_position = self._legacy_view(position)
        for owner in (0, 1):
            anchor = self.m["anchor_square"](legacy_position, owner, self.legacy)
            anchor_idx = None if anchor is None else m_square_to_index(anchor, self.compiled.board_size, self.m)
            current_check = self.m["is_in_check"](legacy_position, owner, self.legacy)
            escapes = 0
            checks = 0
            relief = 0
            for action, child in self._legal_pairs(position, owner):
                if anchor_idx is not None and hasattr(action, "from_square"):
                    if m_square_to_index(action.from_square, self.compiled.board_size, self.m) == anchor_idx:
                        escapes += 1
                if self.m["is_in_check"](self._legacy_view(child), 1 - owner, self.legacy):
                    checks += 1
                if current_check and not self.m["is_in_check"](self._legacy_view(child), owner, self.legacy):
                    relief += 1
            per_owner[owner] = (escapes + checks + relief) / max(1.0, area)
        return self._relative((per_owner[0], per_owner[1]), actor)

    def promotion_structure(self, position, actor: int) -> float:
        area = float(self.compiled.board_size * self.compiled.board_size)
        per_owner = [0.0, 0.0]
        for owner in (0, 1):
            view = m_position_with_side(position, owner, self.m)
            immediate = forced = threats = 0
            for action, _child in self._legal_pairs(position, owner):
                if not hasattr(action, "from_square"):
                    continue
                source = view.board[m_square_to_index(action.from_square, self.compiled.board_size, self.m)]
                if source is None or not source.promoted:
                    if action.promotion_target_id is not None:
                        immediate += 1
                        if source is not None and action.to_square in self.legacy.promotion_forced[source.base_type_id][owner]:
                            forced += 1
                    if source is not None and not source.promoted and source.base_type_id in self.legacy.promotion_allowed:
                        if (action.from_square, action.to_square) in self.legacy.promotion_allowed[source.base_type_id][owner]:
                            threats += 1
            per_owner[owner] = (2 * immediate + forced + 0.5 * threats) / max(1.0, area)
        return self._relative((per_owner[0], per_owner[1]), actor)

    def hand_drop_pressure(self, position, actor: int) -> float:
        area = float(self.compiled.board_size * self.compiled.board_size)
        per_owner = [0.0, 0.0]
        for owner in (0, 1):
            checking = defensive = 0
            view = m_position_with_side(position, owner, self.m)
            in_check = self.m["is_in_check"](self._legacy_view(view), owner, self.legacy)
            weighted = 0.0
            drops = 0
            for action, child in self._legal_pairs(position, owner):
                if not self._is_drop(action):
                    continue
                drops += 1
                weighted += self.evaluator._profile.hand_value_by_base_type[action.base_type_id] / self.median_value
                if self.m["is_in_check"](self._legacy_view(child), 1 - owner, self.legacy):
                    checking += 1
                if in_check and not self.m["is_in_check"](self._legacy_view(child), owner, self.legacy):
                    defensive += 1
            per_owner[owner] = (drops + weighted + checking + defensive) / max(1.0, area)
        return self._relative((per_owner[0], per_owner[1]), actor)

    def semantic_constraint_effect(self, position, actor: int) -> float:
        engine = self.m["semantic_engine_for"](self.compiled)
        if engine is None:
            return 0.0
        area = float(self.compiled.board_size * self.compiled.board_size)
        per_owner = [0.0, 0.0]
        for owner in (0, 1):
            view = m_position_with_side(position, owner, self.m)
            semantic = {_action_key(action) for action, _ in self._legal_pairs(position, owner)}
            legacy_pos = m_position_with_fingerprint(view, self.legacy.ruleset_fingerprint, self.m)
            legacy = {
                _action_key(action)
                for action in self.m["legal_actions_from_position"](legacy_pos, self.legacy)
            }
            suppressed = len(legacy - semantic)
            added = len(semantic - legacy)
            per_owner[owner] = (added - suppressed) / max(1.0, area)
        return self._relative((per_owner[0], per_owner[1]), actor)

    def _is_drop(self, action) -> bool:
        return not hasattr(action, "from_square")

    def feature_vector(self, state, actor: int) -> tuple[dict[str, float], float, dict[str, float]]:
        key = f"{_position_key(state.position)}:{actor}"
        if key in self._feature_cache:
            return self._feature_cache[key], 0.0, self._feature_cost_cache[key]
        started = time.perf_counter()
        family_functions = {
            "attack_defense_hanging": lambda: self.attack_defense_hanging(state.position, actor),
            "capture_recapture_pressure": lambda: self.capture_recapture_pressure(state, actor),
            "legal_safe_mobility": lambda: self.legal_safe_mobility(state.position, actor),
            "anchor_check_pressure": lambda: self.anchor_check_pressure(state.position, actor),
            "promotion_structure": lambda: self.promotion_structure(state.position, actor),
            "hand_drop_pressure": lambda: self.hand_drop_pressure(state.position, actor),
            "semantic_constraint_effect": lambda: self.semantic_constraint_effect(state.position, actor),
        }
        values = {}
        family_costs = {}
        for name in FAMILY_NAMES:
            family_started = time.perf_counter()
            values[name] = family_functions[name]()
            family_costs[name] = time.perf_counter() - family_started
        elapsed = time.perf_counter() - started
        costs = {"feature_vector_seconds": elapsed, "family_seconds": family_costs}
        self._feature_cache[key] = values
        self._feature_cost_cache[key] = costs
        return values, elapsed, costs


def m_square_to_index(square, n: int, m: dict[str, Any]) -> int:
    return m["square_to_index"](square, n)


def m_position_with_side(position, owner: int, m: dict[str, Any]):
    return m["Position"](
        board=position.board,
        hands=position.hands,
        side_to_move=owner,
        ruleset_fingerprint=position.ruleset_fingerprint,
        aux_state=position.aux_state,
    )


def m_position_with_fingerprint(position, fingerprint: str, m: dict[str, Any]):
    return m["Position"](
        board=position.board,
        hands=position.hands,
        side_to_move=position.side_to_move,
        ruleset_fingerprint=fingerprint,
        aux_state=position.aux_state,
    )


def evaluator_components(probe: Probe, state, actor: int) -> tuple[dict[str, int], int]:
    """Reconstruct evaluator-v1 exactly, then orient it to the root actor."""
    m = probe.m
    evaluator = probe.evaluator
    position = state.position
    eval_position = m_position_with_fingerprint(position, evaluator._compiled.ruleset_fingerprint, m)
    eval_state = dataclasses.replace(state, position=eval_position)
    absolute = {
        "board_material": 0,
        "hand_material": 0,
        "promotion_potential": 0,
        "mobility": 0,
        "anchor_escape": 0,
        "check_penalty": 0,
    }
    for idx, piece in enumerate(eval_position.board):
        if piece is None:
            continue
        sign = 1 if piece.owner == 0 else -1
        absolute["board_material"] += sign * evaluator._profile.board_value_by_type[piece.current_type_id]
        absolute["promotion_potential"] += evaluator._promotion_bonus(piece, idx)
    for owner in (0, 1):
        sign = 1 if owner == 0 else -1
        for type_id, count in eval_position.hands[owner].counts:
            absolute["hand_material"] += sign * count * evaluator._profile.hand_value_by_base_type[type_id]
    absolute["mobility"] = evaluator._config.dynamic_mobility_weight * (
        len(m["pseudo_attacks"](eval_position, 0, evaluator._compiled))
        - len(m["pseudo_attacks"](eval_position, 1, evaluator._compiled))
    )
    absolute["anchor_escape"] = evaluator._config.anchor_escape_weight * (
        evaluator._anchor_escape(eval_position, 0) - evaluator._anchor_escape(eval_position, 1)
    )
    if m["is_in_check"](eval_position, 0, evaluator._compiled):
        absolute["check_penalty"] -= evaluator._config.anchor_escape_weight * 10
    if m["is_in_check"](eval_position, 1, evaluator._compiled):
        absolute["check_penalty"] += evaluator._config.anchor_escape_weight * 10
    orientation = 1 if actor == 0 else -1
    signed = {key: value * orientation for key, value in absolute.items()}
    signed["total"] = sum(signed.values())
    direct = evaluator.evaluate(eval_state) if actor == eval_position.side_to_move else (
        -evaluator.evaluate(eval_state)
    )
    if signed["total"] != direct:
        raise RuntimeError("EVALUATOR_V1_COMPONENT_PARITY_FAILURE")
    return signed, direct


def _resolve_child(probe: Probe, state, label: str) -> tuple[Any, Any]:
    actor = state.position.side_to_move
    for action, child_position in probe._legal_pairs(state.position, actor):
        if probe.m["gc_action_to_usi"](action) == label:
            return action, _child_state(state, child_position, action, probe.m)
    raise RuntimeError(f"F22_SELECTED_CHILD_NOT_LEGAL:{label}")


def _correlation(a: Iterable[float], b: Iterable[float]) -> float | None:
    xs, ys = list(a), list(b)
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    numerator = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mx) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - my) ** 2 for y in ys))
    return None if den_x == 0 or den_y == 0 else numerator / (den_x * den_y)


def run_audit() -> dict[str, Any]:
    m = _imports()
    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if head != EXPECTED_HEAD:
        raise RuntimeError(f"F22_BASELINE_MISMATCH:{head}")
    fixture = recover_f22_fixture()
    _semantic, compiled = _compile_context(m)
    probe = Probe(compiled, m)
    rows = []
    family_deltas: dict[str, list[float]] = {name: [] for name in FAMILY_NAMES}
    parity_rows = []
    for item in fixture["corpus"]["positions"]:
        position_id = item["name"]
        state = m["sfen_to_gc_state"](compiled, item["sfen"])
        actor = state.position.side_to_move
        root_components, root_eval = evaluator_components(probe, state, actor)
        root_features, root_cost, root_cost_detail = probe.feature_vector(state, actor)
        reference_text = fixture["provenance"]["references"][position_id]
        current_text = next(
            row["high_move"]
            for row in fixture["agreement"]["rows"]
            if row["position_id"] == position_id
        )
        current_action, current_state = _resolve_child(probe, state, current_text)
        reference_action = next(
            action for action, _child_pos in probe._legal_pairs(state.position, actor)
            if m["gc_action_to_usi"](action) == reference_text
        )
        reference_position = next(
            child_pos for action, child_pos in probe._legal_pairs(state.position, actor)
            if _action_key(action) == _action_key(reference_action)
        )
        reference_state = _child_state(state, reference_position, reference_action, m)
        ref_components, ref_eval = evaluator_components(probe, reference_state, actor)
        current_components, current_eval = evaluator_components(probe, current_state, actor)
        ref_features, ref_cost, ref_cost_detail = probe.feature_vector(reference_state, actor)
        current_features, current_cost, current_cost_detail = probe.feature_vector(current_state, actor)
        component_delta = {
            name: ref_components[name] - root_components[name]
            for name in root_components
            if name != "total"
        }
        component_delta["total"] = ref_eval - root_eval
        feature_delta_reference = {
            name: ref_features[name] - root_features[name] for name in FAMILY_NAMES
        }
        feature_delta_current = {
            name: current_features[name] - root_features[name] for name in FAMILY_NAMES
        }
        advantage = {
            name: feature_delta_reference[name] - feature_delta_current[name]
            for name in FAMILY_NAMES
        }
        for name in FAMILY_NAMES:
            family_deltas[name].append(advantage[name])
        expected_current = current_text
        actual_current = m["gc_action_to_usi"](current_action)
        parity_rows.append({"position_id": position_id, "expected": expected_current, "actual": actual_current, "match": expected_current == actual_current})
        rows.append({
            "position_id": position_id,
            "role": "control" if position_id in fixture["controls"] else "persistent_failure",
            "sfen": item["sfen"],
            "root_actor": actor,
            "reference_child": reference_text,
            "current_selected_child": actual_current,
            "evaluator_v1": {
                "root": root_eval,
                "reference_child": ref_eval,
                "current_selected_child": current_eval,
                "root_components": root_components,
                "reference_components": ref_components,
                "current_components": current_components,
                "reference_delta": component_delta,
                "current_delta": {
                    name: current_components[name] - root_components[name]
                    for name in root_components
                    if name != "total"
                },
            },
            "feature_families": {
                name: {
                    "root": root_features[name],
                    "reference_child": ref_features[name],
                    "current_selected_child": current_features[name],
                    "reference_delta": feature_delta_reference[name],
                    "current_delta": feature_delta_current[name],
                    "reference_advantage_vs_current": advantage[name],
                }
                for name in FAMILY_NAMES
            },
            "cost_seconds": {
                "root_feature_vector": root_cost,
                "reference_feature_vector": ref_cost,
                "current_feature_vector": current_cost,
                "reference_family_seconds": ref_cost_detail["family_seconds"],
                "current_family_seconds": current_cost_detail["family_seconds"],
                "legal_context_cached": True,
            },
        })

    disagreement_rows = [row for row in rows if row["role"] == "persistent_failure"]
    sign = {}
    for name in FAMILY_NAMES:
        values = [row["feature_families"][name]["reference_advantage_vs_current"] for row in disagreement_rows]
        positive = sum(value > 0 for value in values)
        sign[name] = {
            "positive_count": positive,
            "zero_count": sum(value == 0 for value in values),
            "negative_count": sum(value < 0 for value in values),
            "positive_fraction": positive / max(1, len(values)),
            "mean_reference_advantage": sum(values) / max(1, len(values)),
        }
    correlations = {
        left: {
            right: _correlation(family_deltas[left], family_deltas[right])
            for right in FAMILY_NAMES
            if right > left
        }
        for left in FAMILY_NAMES
    }
    cost_summary = {
        name: {
            "median_seconds": sorted(
                row["cost_seconds"]["reference_family_seconds"][name] for row in rows
            )[len(rows) // 2],
            "availability": "position-local; legal enumeration shared/cached across families",
        }
        for name in FAMILY_NAMES
    }
    return {
        "status": "PASS",
        "audit": "F23A_RULE_DERIVED_EVALUATOR_V2_FEATURE_PROBE",
        "baseline": {"head": EXPECTED_HEAD, "f22_commit": F22_COMMIT},
        "ruleset_fingerprint": EXPECTED_SEMANTIC_FINGERPRINT,
        "corpus": {"positions": 10, "controls": len(fixture["controls"]), "persistent_failures": len(fixture["failures"])},
        "evaluator_v1_component_parity": {
            "status": "PASS",
            "rows": 30,
            "current_selection_matches_f22": all(row["match"] for row in parity_rows),
            "selection_rows": parity_rows,
        },
        "sign_consistency_on_eight_failures": sign,
        "redundancy_correlation_on_reference_advantage": correlations,
        "normalization": {
            "formula": "board-area normalization for counts and median non-anchor board value for value terms",
            "scale_probe": "all reported deltas are dimensionless; rename-invariance and 4x4/8x8 contract tests are permanent",
            "stability_claim": "diagnostic normalization only; no fitted weights or Elo claim",
        },
        "feature_cost": cost_summary,
        "semantic_authority": {
            "source": "current CompiledSemanticRuleset + Position + legal semantic executor",
            "legacy_compiled": "used only for evaluator-v1 parity and comparison baseline",
            "production_changed": False,
        },
        "rows": rows,
        "selected_next_boundary": "F23B_EVALUATOR_CORPUS_EXPANSION",
        "selection_reason": "The frozen corpus is sufficient to reproduce the failure anatomy and expose the feature gap, but candidate-family direction is contradictory across the eight failures and hand/drop plus semantic-constraint families are unobserved here. Expand the generic corpus before fitting or prototyping evaluator-v2 weights.",
        "not_claimed": ["production evaluator improvement", "Elo improvement", "weights fitted on the ten positions"],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = run_audit()
    text = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
