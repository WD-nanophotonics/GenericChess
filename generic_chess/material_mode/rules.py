"""Immutable material-mode rules and exact movement-based prices."""
from __future__ import annotations
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from math import gcd
from generic_chess.core.coordinates import BoardShape, Square, in_bounds
from generic_chess.core.movement import LeapAtom, RayAtom, atom_targets
from generic_chess.core.pieces import PieceType
from generic_chess.rules.schema import atom_from_dict, atom_to_dict


def integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f'{name} must be an integer >= {minimum}')
    return value


def square(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError('square must contain two integer coordinates')
    return Square(integer(value[0], 'file'), integer(value[1], 'rank'))


def decimal_parts(value):
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError('ray multiplier must be a finite nonnegative decimal') from exc
    if not d.is_finite() or d < 0:
        raise ValueError('ray multiplier must be a finite nonnegative decimal')
    text = format(d, 'f')
    if '.' in text:
        text = text.rstrip('0').rstrip('.')
    if d == 0:
        text = '0'
    parts = Decimal(text).as_tuple()
    coefficient = int(''.join(str(x) for x in parts.digits)) * 10 ** max(0, parts.exponent)
    return text, 10 ** max(0, -parts.exponent), coefficient


def format_score(units, scale):
    sign = '-' if units < 0 else ''
    whole, fraction = divmod(abs(units), scale)
    if not fraction:
        return f'{sign}{whole}'
    tail = str(fraction).zfill(len(str(scale)) - 1).rstrip('0')
    return f'{sign}{whole}.{tail}'


@dataclass(frozen=True, slots=True)
class Placement:
    type_id: str
    square: Square


@dataclass(frozen=True, slots=True)
class ModeRules:
    width: int
    height: int
    players: int
    piece_types: tuple[PieceType, ...]
    formation: tuple[Placement, ...]
    ray_multiplier: str = '0.6'
    purchase_penalty: bool = True
    repetition_limit: int = 4
    max_ply: int = 512
    starting_player: int = 0

    def __post_init__(self):
        integer(self.width, 'width', 1)
        integer(self.height, 'height', 1)
        if type(self.players) is not int or self.players not in (2, 4):
            raise ValueError('players must be 2 or 4')
        if self.players == 4 and self.width != self.height:
            raise ValueError('four-player mode requires a square board')
        if type(self.purchase_penalty) is not bool:
            raise ValueError('purchase_penalty must be a boolean')
        integer(self.repetition_limit, 'repetition_limit', 2)
        integer(self.max_ply, 'max_ply', 1)
        integer(self.starting_player, 'starting_player')
        if self.starting_player >= self.players:
            raise ValueError('starting_player is outside the match')
        object.__setattr__(self, 'ray_multiplier', decimal_parts(self.ray_multiplier)[0])
        canonical = []
        for p in self.piece_types:
            if not isinstance(p, PieceType) or type(p.is_anchor) is not bool or not isinstance(p.name, str):
                raise ValueError('catalog entries require a name and boolean anchor flag')
            atoms = []
            for a in p.movement_atoms:
                if isinstance(a, LeapAtom):
                    atoms.append(LeapAtom(tuple(a.offset)))
                elif isinstance(a, RayAtom):
                    atoms.append(RayAtom(tuple(a.direction), a.max_steps))
                else:
                    raise ValueError('only ordinary leap/ray movement is supported')
            canonical.append(replace(p, movement_atoms=tuple(atoms), promotion_target_ids=tuple(p.promotion_target_ids)))
        object.__setattr__(self, 'piece_types', tuple(canonical))
        object.__setattr__(self, 'formation', tuple(self.formation))
        ids = set()
        for piece in self.piece_types:
            if not isinstance(piece.type_id, str) or not piece.type_id or piece.type_id in ids:
                raise ValueError('piece type IDs must be unique nonempty strings')
            ids.add(piece.type_id)
            if piece.is_promotable or piece.promotion_target_ids:
                raise ValueError('promotion is disabled in material mode')
            for atom in piece.movement_atoms:
                if not isinstance(atom, (LeapAtom, RayAtom)):
                    raise ValueError('only ordinary leap/ray movement is supported')
                vector = atom.offset if isinstance(atom, LeapAtom) else atom.direction
                if len(vector) != 2 or any(type(x) is not int for x in vector) or tuple(vector) == (0, 0):
                    raise ValueError('movement requires a nonzero integer vector')
                if isinstance(atom, RayAtom):
                    if gcd(abs(vector[0]), abs(vector[1])) != 1:
                        raise ValueError('ray directions must be primitive')
                    if atom.max_steps is not None:
                        integer(atom.max_steps, 'ray max_steps', 1)
        types = {p.type_id: p for p in self.piece_types}
        for p in self.formation:
            if not isinstance(p, Placement) or not isinstance(p.square, Square):
                raise ValueError('formation requires Placement and Square values')
            if not isinstance(p.type_id, str) or p.type_id not in types or type(p.square.file) is not int or type(p.square.rank) is not int or not in_bounds(p.square, self.shape):
                raise ValueError('formation references an unknown type or outside square')
            if types[p.type_id].is_anchor and p.square.rank != 0:
                raise ValueError('the home anchor must start on the bottom edge')
        if sum(types[p.type_id].is_anchor for p in self.formation) != 1:
            raise ValueError('formation must contain exactly one anchor')

    @property
    def shape(self):
        return BoardShape(self.width, self.height)

    @property
    def score_scale(self):
        return decimal_parts(self.ray_multiplier)[1]

    def to_dict(self):
        return dict(schema_version=1, width=self.width, height=self.height, players=self.players,
                    piece_types=[dict(type_id=p.type_id, name=p.name, is_anchor=p.is_anchor,
                                      movement_atoms=[atom_to_dict(a) for a in p.movement_atoms]) for p in self.piece_types],
                    formation=[dict(type_id=p.type_id, square=[p.square.file, p.square.rank]) for p in self.formation],
                    ray_multiplier=self.ray_multiplier, purchase_penalty=self.purchase_penalty,
                    repetition_limit=self.repetition_limit, max_ply=self.max_ply, starting_player=self.starting_player)

    @classmethod
    def from_dict(cls, data):
        if not isinstance(data, dict) or type(data.get('schema_version')) is not int or data.get('schema_version') != 1:
            raise ValueError('unsupported material rule version')
        pieces = tuple(PieceType(p['type_id'], p['name'], tuple(atom_from_dict(a) for a in p['movement_atoms']),
                                 is_anchor=p.get('is_anchor', False)) for p in data['piece_types'])
        formation = tuple(Placement(p['type_id'], square(p['square'])) for p in data['formation'])
        return cls(data['width'], data['height'], data['players'], pieces, formation,
                   data.get('ray_multiplier', '0.6'), data.get('purchase_penalty', True),
                   data.get('repetition_limit', 4), data.get('max_ply', 512), data.get('starting_player', 0))

    @classmethod
    def from_ruleset(cls, ruleset, *, players=2, **settings):
        """Import ordinary movement and owner-0 formation, without legacy promotions."""
        if ruleset.semantic_actions or ruleset.declarations or ruleset.automatic_adjudications:
            raise ValueError('conditional semantic rules are not ordinary material-mode rules')
        pieces = tuple(replace(p, is_promotable=False, promotion_target_ids=()) for p in ruleset.piece_types)
        formation = tuple(Placement(p.current_type_id, Square(x, y))
                          for y, row in enumerate(ruleset.initial_position) for x, p in enumerate(row)
                          if p is not None and p.owner == 0)
        return cls(ruleset.board_shape.width, ruleset.board_shape.height, players, pieces, formation, **settings)


def price_units(piece, rules):
    """Count capabilities, not current occupancy or conventional chess prices."""
    if piece.is_anchor:
        return 0
    shape = rules.shape
    leaps = {a.offset for a in piece.movement_atoms if isinstance(a, LeapAtom)
             and abs(a.offset[0]) < shape.width and abs(a.offset[1]) < shape.height}
    rays = tuple(a for a in piece.movement_atoms if isinstance(a, RayAtom))
    maximum = max((len({target for ray in rays for target in atom_targets(shape, 0, Square(x, y), ray)})
                   for y in range(shape.height) for x in range(shape.width)), default=0) if rays else 0
    _, scale, coefficient = decimal_parts(rules.ray_multiplier)
    return len(leaps) * scale + maximum * coefficient
