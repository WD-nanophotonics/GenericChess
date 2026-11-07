"""Public immutable actions, state and snapshots for the isolated backend."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import TypeAlias
from generic_chess.core.actions import BoardMove, DropMove, action_to_dict as core_action_to_dict, action_from_dict as core_action_from_dict
from generic_chess.core.coordinates import Square
from generic_chess.core.pieces import Piece
from generic_chess.core.position import Hands
from .rules import square


@dataclass(frozen=True, slots=True)
class BuyPiece:
    type_id: str


@dataclass(frozen=True, slots=True)
class BuyAndDrop:
    type_id: str
    to_square: Square


@dataclass(frozen=True, slots=True)
class Resign:
    pass


ModeAction: TypeAlias = BoardMove | DropMove | BuyPiece | BuyAndDrop
RecordAction: TypeAlias = ModeAction | Resign


def action_to_dict(action: RecordAction) -> dict:
    if isinstance(action, BuyPiece):
        return dict(kind='buy', type_id=action.type_id)
    if isinstance(action, BuyAndDrop):
        return dict(kind='buy_drop', type_id=action.type_id, to=[action.to_square.file, action.to_square.rank])
    if isinstance(action, Resign):
        return dict(kind='resign')
    if not isinstance(action, (BoardMove, DropMove)):
        raise ValueError('unsupported material-mode action')
    return core_action_to_dict(action)


def action_from_dict(data: dict) -> RecordAction:
    if not isinstance(data, dict):
        raise ValueError('action must be an object')
    kind = data.get('kind')
    if kind == 'resign':
        return Resign()
    if kind in ('buy', 'buy_drop'):
        tid = data.get('type_id')
        if not isinstance(tid, str) or not tid:
            raise ValueError('purchase requires a type ID')
        return BuyPiece(tid) if kind == 'buy' else BuyAndDrop(tid, square(data.get('to')))
    if kind not in ('board', 'drop'):
        raise ValueError('unsupported material-mode action kind')
    square(data.get('to'))
    if kind == 'board':
        square(data.get('from'))
        if data.get('promotion_target_id') is not None:
            raise ValueError('promotion is disabled')
    return core_action_from_dict(data)


@dataclass(frozen=True, slots=True)
class ModePosition:
    board: tuple[Piece | None, ...]
    hands: tuple[Hands, ...]
    side_to_move: int
    ruleset_fingerprint: str


@dataclass(frozen=True, slots=True)
class ModeResult:
    status: str = 'ongoing'
    winner: int | None = None
    reason: str | None = None
    drawn_players: tuple[int, ...] = ()

    @property
    def terminal(self) -> bool:
        return self.status != 'ongoing'


@dataclass(frozen=True, slots=True)
class Elimination:
    player: int
    reason: str
    ply: int


@dataclass(frozen=True, slots=True)
class ModeState:
    position: ModePosition
    balances: tuple[int, ...]
    active: tuple[bool, ...]
    ply_count: int = 0
    repetition_counts: tuple[tuple[str, int], ...] = ()
    result: ModeResult = ModeResult()
    eliminations: tuple[Elimination, ...] = ()

    @property
    def current_player(self) -> int:
        return self.position.side_to_move


@dataclass(frozen=True, slots=True)
class PieceView:
    type_id: str
    owner: int | None
    former_owner: int | None
    status: str


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    type_id: str
    name: str
    is_anchor: bool
    price: str | None


@dataclass(frozen=True, slots=True)
class ModeSnapshot:
    width: int
    height: int
    players: int
    current_player: int
    ply_count: int
    purchase_penalty: bool
    ray_multiplier: str
    board: tuple[PieceView | None, ...]
    balances: tuple[str, ...]
    hands: tuple[tuple[tuple[str, int], ...], ...]
    active: tuple[bool, ...]
    in_check: tuple[bool, ...]
    catalog: tuple[CatalogEntry, ...]
    result: ModeResult
    eliminations: tuple[Elimination, ...]

    def to_dict(self) -> dict:
        """Fresh JSON-compatible view; mutating this copy cannot mutate the game."""
        import json
        return json.loads(json.dumps(asdict(self)))
