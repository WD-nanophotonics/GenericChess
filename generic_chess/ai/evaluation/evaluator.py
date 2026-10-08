"""Lightweight dynamic evaluator (side-to-move perspective, integer score)."""

from __future__ import annotations

from ...core.attacks import anchor_square, pseudo_attacks
from ...core.coordinates import index_to_square, square_to_index
from ...core.movement import LeapAtom, RayAtom, empty_mobility
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
        self._anchor_steps = {}
        if config.anchor_escape_weight:
            for pt in compiled.piece_types:
                if not pt.is_anchor:
                    continue
                short_atoms = tuple(atom for atom in pt.movement_atoms if (
                    isinstance(atom, LeapAtom) and max(map(abs, atom.offset)) <= 1
                    or isinstance(atom, RayAtom) and atom.max_steps == 1))
                # Common anchors already have exactly this owner-relative,
                # deduplicated geometry. Mixed anchors need only the subset.
                self._anchor_steps[pt.type_id] = (
                    compiled.empty_mobility[pt.type_id]
                    if short_atoms == pt.movement_atoms else tuple(
                        tuple(empty_mobility(compiled.board_size, owner,
                              index_to_square(idx, compiled.board_size), short_atoms)
                              for idx in range(compiled.board_size ** 2))
                        for owner in (0, 1)))
        self._zones: dict[tuple[str, int], frozenset[int]] = {}
        if config.promotion_potential_weight:
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
        score = 0
        for idx, piece in enumerate(position.board):
            if piece is None:
                continue
            value = self._profile.board_value_by_type[piece.current_type_id]
            score += value if piece.owner == 0 else -value
            if self._config.promotion_potential_weight:
                score += self._promotion_bonus(piece, idx)
        for owner in (0, 1):
            for type_id, count in position.hands[owner].counts:
                value = self._profile.hand_value_by_base_type[type_id]
                score += count * value if owner == 0 else -count * value

        attacks = None
        if self._config.dynamic_mobility_weight or self._config.anchor_escape_weight:
            # All three features inspect the same unmodified position.
            attacks = self._attack_maps(state)
        if self._config.dynamic_mobility_weight:
            mob0 = len(attacks[0])
            mob1 = len(attacks[1])
            score += self._config.dynamic_mobility_weight * (mob0 - mob1)
        if self._config.anchor_escape_weight:
            esc0 = self._anchor_escape(position, 0, attacks[1])
            esc1 = self._anchor_escape(position, 1, attacks[0])
            score += self._config.anchor_escape_weight * (esc0 - esc1)
            if anchor_square(position, 0, self._compiled) in attacks[1]:
                score -= self._config.anchor_escape_weight * 10
            if anchor_square(position, 1, self._compiled) in attacks[0]:
                score += self._config.anchor_escape_weight * 10

        return score if position.side_to_move == 0 else -score

    def _attack_maps(self, state: GameState):
        return tuple(pseudo_attacks(state.position, owner, self._compiled)
                     for owner in (0, 1))

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

    def _anchor_escape(self, position: Position, owner: int, opponent_attacks) -> int:
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
        # Preserve this heuristic's empty short-step scope, but use the owner's
        # frame and count each behavioral destination once, not once per atom.
        targets = self._anchor_steps[position.board[anchor_idx].current_type_id][owner][anchor_idx]
        return sum(position.board[square_to_index(target, n)] is None
                   and target not in opponent_attacks
                   for target in targets)

    def capture_order_value(self, moving_piece, captured_piece) -> int:
        moving = self._profile.board_value_by_type[moving_piece.current_type_id]
        captured = self._profile.board_value_by_type[captured_piece.current_type_id]
        return captured * 10 - moving // 10

    def type_value(self, type_id: str) -> int:
        """Board value of a piece type (from the rule-derived profile)."""
        return self._profile.board_value_by_type[type_id]
