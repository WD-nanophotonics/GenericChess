"""Piece type and on-board piece data models."""

from __future__ import annotations

from dataclasses import dataclass

from .movement import MovementAtom


@dataclass(frozen=True, slots=True)
class PieceType:
    """A rule-set-level piece definition.

    ``type_id`` uniquely identifies the type inside one RuleSet.  All movement
    atoms are expressed in the owner's relative frame.
    """

    type_id: str
    name: str
    movement_atoms: tuple[MovementAtom, ...]
    is_anchor: bool = False
    is_promotable: bool = False
    promotion_target_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Piece:
    """A concrete piece occupying a square (or implied by a hand entry).

    Invariants enforced by the compiler/validator:
    * ``promoted == False`` => ``current_type_id == base_type_id``
    * ``promoted == True`` => ``current_type_id`` is in
      ``promotion_targets(base_type_id)``
    * anchors always have ``current_type_id == base_type_id`` and
      ``promoted == False``.
    """

    owner: int
    base_type_id: str
    current_type_id: str
    promoted: bool = False
