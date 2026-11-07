"""Ready-to-run ordinary movement examples; all values are geometry-derived."""
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import PieceType
from .rules import ModeRules, Placement


def example_rules(*, players=2, width=8, height=None, **settings):
    height = (width if players == 4 else 6) if height is None else height
    king = tuple(LeapAtom((x, y)) for x in (-1, 0, 1) for y in (-1, 0, 1) if x or y)
    knight = tuple(LeapAtom((x, y)) for x, y in ((1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)))
    rook = tuple(RayAtom(v) for v in ((1, 0), (-1, 0), (0, 1), (0, -1)))
    bishop = tuple(RayAtom(v) for v in ((1, 1), (-1, 1), (1, -1), (-1, -1)))
    pieces = (PieceType('K', 'Anchor', king, is_anchor=True), PieceType('F', 'Forward leap', (LeapAtom((0, 1)),)),
              PieceType('N', 'Knight leaps', knight), PieceType('R', 'Orthogonal rays', rook),
              PieceType('B', 'Diagonal rays', bishop), PieceType('Q', 'Combined rays', rook + bishop))
    center = (width - 1) // 2
    formation = (Placement('N', Square(center - 1, 0)), Placement('K', Square(center, 0)), Placement('F', Square(center + 1, 0)))
    return ModeRules(width, height, players, pieces, formation, **settings)
