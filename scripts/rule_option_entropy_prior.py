"""Reference-blind static rule-option prior (research-only; not an evaluator).

The score is mean one-ply choice entropy over a deliberately sparse,
reproducible RuleSet-derived snapshot ensemble.  See
``docs/research/rule_option_entropy_prior_v0.md`` before changing this file.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from math import log2
from pathlib import Path
from statistics import fmean
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands, Position
from generic_chess.core.semantic_executor import SemanticEngine, SemanticAction
from generic_chess.core.transition import initial_state
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.western_chess import build_western_chess_ruleset


@dataclass(frozen=True)
class PieceLedger:
    type_id: str
    base_type_id: str
    owner_entropy_bits: tuple[float, float]
    empty_snapshot_entropy_bits: tuple[float, float]
    occupied_snapshot_entropy_bits: tuple[float, float]
    mean_quiet_actions: float
    mean_capture_actions: float
    mean_promotion_actions: float
    board_mode_entropy_bits: float
    drop_owner_entropy_bits: tuple[float, float] | None
    final_score_bits: float
    board_sample_count_per_owner: tuple[int, int]
    occupied_sample_count_per_owner: tuple[int, int]


def choice_entropy(action_count: int) -> float:
    """Maximum-entropy choice among distinct immediate legal actions, in bits."""
    if action_count < 0:
        raise ValueError("action_count must be non-negative")
    return log2(1 + action_count)


def _piece_identity(type_id: str, type_metadata, initial_base_types: set[str]) -> tuple[str, bool]:
    if type_metadata[type_id].is_anchor:
        raise ValueError(f"anchor type {type_id!r} has no finite material prior")
    if type_id in initial_base_types:
        return type_id, False
    for base_id, base in type_metadata.items():
        if type_id in base.promotion_target_ids:
            return base_id, True
    return type_id, False


def _base_board(position: Position, type_metadata) -> tuple[Piece | None, ...]:
    """Retain only the two anchors from the declared initial setup."""
    return tuple(
        piece
        if piece is not None and type_metadata[piece.current_type_id].is_anchor
        else None
        for piece in position.board
    )


def _snapshot(
    compiled,
    board: tuple[Piece | None, ...],
    owner: int,
) -> Position:
    width = compiled.support.board_width or compiled.support.board_size
    height = compiled.support.board_height or compiled.support.board_size
    if width is None or height is None:
        raise ValueError("compiled RuleSet does not expose a board shape")
    return Position(
        board=board,
        hands=(Hands.empty(), Hands.empty()),
        side_to_move=owner,
        ruleset_fingerprint=compiled.support.ruleset_fingerprint,
        # No move history is supplied; absent slots resolve to RuleSet defaults.
        aux_state=(),
        board_width=(width if width != height else None),
        board_height=(height if width != height else None),
    )


def _distinct_actor_actions(
    engine: SemanticEngine,
    position: Position,
    source: int | None,
) -> tuple[SemanticAction, ...]:
    """Collapse duplicate declarative patterns into the same move outcome."""
    seen: dict[tuple[int | None, int, str | None, str | None], SemanticAction] = {}
    for action in engine.legal_actions(position):
        if action.source != source:
            continue
        key = (action.source, action.target, action.promotion_target_id, action.actor_type)
        seen.setdefault(key, action)
    return tuple(seen.values())


def _influence_squares(engine: SemanticEngine, type_id: str, owner: int, source: int) -> tuple[int, ...]:
    """Squares on the type's compiled movement paths from this source."""
    geometry_ids = {
        geometry_id
        for pattern in engine.ir.patterns
        if type_id in pattern.type_ids
        for geometry_id in pattern.geometry_ids
    }
    relevant: set[int] = set()
    for geometry_id in geometry_ids:
        geometry = engine.ir.geometry[geometry_id]
        owner_paths = geometry.paths.get(str(owner), {})
        source_paths = owner_paths.get(source, ())
        if source_paths and isinstance(source_paths[0], int):
            relevant.update(source_paths)
        else:
            for path in source_paths:
                relevant.update(path)
    return tuple(sorted(relevant))


def _drop_entropy(
    compiled,
    engine: SemanticEngine,
    base_board: tuple[Piece | None, ...],
    base_type_id: str,
) -> tuple[float, float] | None:
    if compiled.support.type_metadata[base_type_id].is_promotable is False and not any(
        pattern.composition == "augment"
        and base_type_id in pattern.type_ids
        and any(effect.kind == "place" for effect in pattern.effects)
        for pattern in engine.ir.patterns
    ):
        return None

    # A drop mode exists only if the executor actually generates at least one
    # drop from a one-token hand.  Probe both owners, preserving anchor safety.
    entropies: list[float] = []
    for owner in (0, 1):
        hands = [Hands.empty(), Hands.empty()]
        hands[owner] = hands[owner].add(base_type_id)
        width = compiled.support.board_width or compiled.support.board_size
        height = compiled.support.board_height or compiled.support.board_size
        if width is None or height is None:
            raise ValueError("compiled RuleSet does not expose a board shape")
        position = Position(
            board=base_board,
            hands=tuple(hands),
            side_to_move=owner,
            ruleset_fingerprint=compiled.support.ruleset_fingerprint,
            aux_state=(),
            board_width=(width if width != height else None),
            board_height=(height if width != height else None),
        )
        actions = _distinct_actor_actions(engine, position, None)
        count = sum(1 for action in actions if action.actor_type == base_type_id)
        entropies.append(choice_entropy(count))
    if not any(entropy > 0 for entropy in entropies):
        return None
    return entropies[0], entropies[1]


def measure_piece(compiled, engine: SemanticEngine, type_id: str) -> PieceLedger:
    metadata = compiled.support.type_metadata
    base_position = initial_state(compiled).position
    initial_base_types = {
        piece.base_type_id for piece in base_position.board if piece is not None
    }
    base_type_id, promoted = _piece_identity(type_id, metadata, initial_base_types)
    anchors = _base_board(base_position, metadata)
    anchor_squares = {i for i, piece in enumerate(anchors) if piece is not None}
    board_size = len(anchors)

    owner_entropy: list[float] = []
    empty_entropy: list[float] = []
    occupied_entropy: list[float] = []
    quiet_counts: list[int] = []
    capture_counts: list[int] = []
    promotion_counts: list[int] = []
    board_samples: list[int] = []
    occupied_samples: list[int] = []

    for owner in (0, 1):
        square_scores: list[float] = []
        owner_empty: list[float] = []
        owner_occupied: list[float] = []
        owner_quiet: list[int] = []
        owner_captures: list[int] = []
        owner_promotions: list[int] = []
        owner_board_samples = 0
        owner_occupied_samples = 0

        def record_actions(position: Position, actions: tuple[SemanticAction, ...]) -> None:
            for action in actions:
                target_piece = position.board[action.target]
                if target_piece is not None and target_piece.owner != owner:
                    owner_captures.append(1)
                else:
                    owner_quiet.append(1)
                if action.promotion_target_id is not None:
                    owner_promotions.append(1)

        for source in range(board_size):
            if source in anchor_squares:
                continue
            board = list(anchors)
            board[source] = Piece(owner, base_type_id, type_id, promoted)
            empty_position = _snapshot(compiled, tuple(board), owner)
            empty_actions = _distinct_actor_actions(engine, empty_position, source)
            empty_h = choice_entropy(len(empty_actions))
            owner_empty.append(empty_h)
            owner_board_samples += 1
            record_actions(empty_position, empty_actions)

            influence = tuple(
                square
                for square in _influence_squares(engine, type_id, owner, source)
                if square != source and square not in anchor_squares
            )
            contexts: list[float] = []
            for blocker_square in influence:
                for blocker_owner in (0, 1):
                    occupied_board = list(board)
                    occupied_board[blocker_square] = Piece(
                        blocker_owner, base_type_id, type_id, promoted
                    )
                    position = _snapshot(compiled, tuple(occupied_board), owner)
                    actions = _distinct_actor_actions(engine, position, source)
                    contexts.append(choice_entropy(len(actions)))
                    record_actions(position, actions)
                    owner_occupied_samples += 1
                    owner_occupied.append(choice_entropy(len(actions)))
            # Equal weight for the unobstructed snapshot and the mean of the
            # one-occupant movement-influence snapshots; no occupancy rate is
            # inferred from game frequency.
            if contexts:
                square_scores.append((empty_h + fmean(contexts)) / 2)
            else:
                square_scores.append(empty_h)
        owner_entropy.append(fmean(square_scores) if square_scores else 0.0)
        empty_entropy.append(fmean(owner_empty) if owner_empty else 0.0)
        occupied_entropy.append(fmean(owner_occupied) if owner_occupied else 0.0)
        quiet_counts.extend(owner_quiet)
        capture_counts.extend(owner_captures)
        promotion_counts.extend(owner_promotions)
        board_samples.append(owner_board_samples)
        occupied_samples.append(owner_occupied_samples)

    board_mode = fmean(owner_entropy)
    drop_entropy = (
        _drop_entropy(compiled, engine, anchors, base_type_id)
        if type_id == base_type_id
        else None
    )
    score = (
        fmean((board_mode, fmean(drop_entropy)))
        if drop_entropy is not None
        else board_mode
    )
    return PieceLedger(
        type_id=type_id,
        base_type_id=base_type_id,
        owner_entropy_bits=(owner_entropy[0], owner_entropy[1]),
        empty_snapshot_entropy_bits=(empty_entropy[0], empty_entropy[1]),
        occupied_snapshot_entropy_bits=(occupied_entropy[0], occupied_entropy[1]),
        mean_quiet_actions=fmean(quiet_counts) if quiet_counts else 0.0,
        mean_capture_actions=fmean(capture_counts) if capture_counts else 0.0,
        mean_promotion_actions=fmean(promotion_counts) if promotion_counts else 0.0,
        board_mode_entropy_bits=board_mode,
        drop_owner_entropy_bits=drop_entropy,
        final_score_bits=score,
        board_sample_count_per_owner=(board_samples[0], board_samples[1]),
        occupied_sample_count_per_owner=(occupied_samples[0], occupied_samples[1]),
    )


def analyze_ruleset(name: str, builder: Callable):
    ruleset = builder()
    compiled = compile_ruleset_for_execution(ruleset)
    engine = SemanticEngine(compiled)
    metadata = compiled.support.type_metadata
    pieces = [
        measure_piece(compiled, engine, type_id)
        for type_id, piece_type in metadata.items()
        if not piece_type.is_anchor
    ]
    capture_dispositions = sorted(
        {
            effect.disposition
            for pattern in compiled.ir.patterns
            if pattern.target.kind == "target_enemy"
            for effect in pattern.effects
            if effect.kind == "remove"
            and effect.piece_owner == "opponent"
            and effect.disposition is not None
        }
    )

    def conditional_slot(slot):
        readers = []
        writers = []
        for pattern in compiled.ir.patterns:
            if any(guard.slot_id == slot.slot_id for guard in pattern.slot_guards):
                readers.append(pattern.pattern_id)
            if any(effect.slot_id == slot.slot_id for effect in pattern.effects):
                writers.append(pattern.pattern_id)
        return {
            "slot_id": slot.slot_id,
            "value_kind": slot.value_kind,
            "scope": slot.scope,
            "lifetime": slot.lifetime,
            "initial": slot.initial,
            "guarded_patterns": sorted(readers),
            "effect_patterns": sorted(writers),
        }

    return {
        "ruleset_label": name,
        "formula_id": "uniform-one-step-option-entropy-v0",
        "human_values_read": False,
        "complete_games_run": 0,
        "semantic_capture_dispositions": capture_dispositions,
        "conditional_aux_slots_not_varied": [
            conditional_slot(slot)
            for slot in compiled.ir.aux_slots
        ],
        "pieces": [asdict(piece) for piece in pieces],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="write the deterministic ledger JSON")
    args = parser.parse_args()
    report = {
        "experiment": "CAUSAL_DIAGNOSTIC",
        "single_unknown": "whether frozen executable rules support a game-name-independent static material prior",
        "minimal_observation": "Western Chess component ledger, with unchanged Standard Shogi retention ledger",
        "formula": "mean(snapshot log2(1 + distinct immediate legal actions))",
        "rulesets": [
            analyze_ruleset("Western Chess", build_western_chess_ruleset),
            analyze_ruleset("Standard Shogi", build_standard_shogi_ruleset),
        ],
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
