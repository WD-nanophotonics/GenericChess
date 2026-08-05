"""Lightweight dynamic evaluator (side-to-move perspective, integer score)."""

from __future__ import annotations

from ...core.attacks import is_in_check, is_square_attacked, pseudo_attacks
from ...core.coordinates import Square, square_to_index
from ...core.movement import LeapAtom, RayAtom
from ...core.position import Position
from ...core.position import GameState
from ...rules.compiled import CompiledRuleSet
from .config import EvaluationConfig
from .profile import RuleSetEvaluationProfile


class Evaluator:
    """Static-profile lookup + cheap dynamic terms. No per-node rule analysis."""

    def __init__(
        self,
        compiled: CompiledRuleSet,
        profile: RuleSetEvaluationProfile,
        config: EvaluationConfig,
    ) -> None:
        self._compiled = compiled
        self._profile = profile
        self._config = config
        self._zones: dict[tuple[str, int], frozenset[int]] = {}
        for pt in compiled.piece_types:
            if not pt.is_promotable:
                continue
            for owner in (0, 1):
                zone = frozenset(
                    idx
                    for idx in range(compiled.board_size * compiled.board_size)
                    if not compiled.empty_forward_mobility[pt.type_id][owner][idx]
                )
                self._zones[(pt.type_id, owner)] = zone

    def evaluate(self, state: GameState) -> int:
        position = state.position
        n = self._compiled.board_size
        score = 0
        for idx, piece in enumerate(position.board):
            if piece is None:
                continue
            value = self._profile.board_value_by_type[piece.current_type_id]
            score += value if piece.owner == 0 else -value
            score += self._promotion_bonus(piece, idx)
        for owner in (0, 1):
            for type_id, count in position.hands[owner].counts:
                value = self._profile.hand_value_by_base_type[type_id]
                score += count * value if owner == 0 else -count * value

        mob0 = len(pseudo_attacks(position, 0, self._compiled))
        mob1 = len(pseudo_attacks(position, 1, self._compiled))
        score += self._config.dynamic_mobility_weight * (mob0 - mob1)
        esc0 = self._anchor_escape(position, 0)
        esc1 = self._anchor_escape(position, 1)
        score += self._config.anchor_escape_weight * (esc0 - esc1)
        if is_in_check(position, 0, self._compiled):
            score -= self._config.anchor_escape_weight * 10
        if is_in_check(position, 1, self._compiled):
            score += self._config.anchor_escape_weight * 10

        return score if position.side_to_move == 0 else -score

    def _promotion_bonus(self, piece, idx: int) -> int:
        base = piece.base_type_id
        if piece.promoted or base not in self._profile.promotion_gain_by_type:
            return 0
        gain = self._profile.promotion_gain_by_type[base]
        if gain <= 0:
            return 0
        unit = max(1, gain // 1000)
        owner = piece.owner
        zone = self._zones.get((base, owner))
        if zone is None:
            return 0
        weight = self._config.promotion_potential_weight
        if idx in zone:
            bonus = weight * unit
        else:
            forward = self._compiled.empty_forward_mobility[base][owner][idx]
            if any(t in zone for t in forward):
                bonus = weight * unit // 2
            else:
                bonus = 0
        return bonus if owner == 0 else -bonus

    def _anchor_escape(self, position: Position, owner: int) -> int:
        n = self._compiled.board_size
        anchor_idx = None
        for idx, piece in enumerate(position.board):
            if (
                piece is not None
                and piece.owner == owner
                and self._compiled.types_by_id[piece.current_type_id].is_anchor
            ):
                anchor_idx = idx
                break
        if anchor_idx is None:
            return 0
        anchor_type = self._compiled.types_by_id[
            position.board[anchor_idx].current_type_id
        ]
        square = Square(anchor_idx % n, anchor_idx // n)
        escapes = 0
        for atom in anchor_type.movement_atoms:
            if isinstance(atom, LeapAtom) and max(abs(atom.offset[0]), abs(atom.offset[1])) <= 1:
                target = Square(square.file + atom.offset[0], square.rank + atom.offset[1])
                if 0 <= target.file < n and 0 <= target.rank < n:
                    tidx = square_to_index(target, n)
                    if (
                        position.board[tidx] is None
                        and not is_square_attacked(position, target, 1 - owner, self._compiled)
                    ):
                        escapes += 1
            elif isinstance(atom, RayAtom) and atom.max_steps == 1:
                target = Square(square.file + atom.direction[0], square.rank + atom.direction[1])
                if 0 <= target.file < n and 0 <= target.rank < n:
                    tidx = square_to_index(target, n)
                    if (
                        position.board[tidx] is None
                        and not is_square_attacked(position, target, 1 - owner, self._compiled)
                    ):
                        escapes += 1
        return escapes

    def capture_order_value(self, moving_piece, captured_piece) -> int:
        moving = self._profile.board_value_by_type[moving_piece.current_type_id]
        captured = self._profile.board_value_by_type[captured_piece.current_type_id]
        return captured * 10 - moving // 10
