"""Isolated material-score game backend: two/four human seats, two-seat AI."""
from generic_chess.core.actions import BoardMove, DropMove
from generic_chess.core.coordinates import Square
from generic_chess.core.movement import LeapAtom, RayAtom
from generic_chess.core.pieces import PieceType
from .rules import ModeRules, Placement, format_score
from .model import BuyPiece, BuyAndDrop, Resign, ModeAction, ModeResult, ModeSnapshot, ModeState, ModePosition, Elimination, PieceView, CatalogEntry, action_to_dict, action_from_dict
from .session import ModeSession
from .ai import BasicTwoPlayer, ModeDecision
from .examples import example_rules

__all__ = ['ModeRules', 'Placement', 'ModeSession', 'ModeAction', 'BuyPiece', 'BuyAndDrop', 'Resign',
           'BoardMove', 'DropMove', 'Square', 'LeapAtom', 'RayAtom', 'PieceType', 'ModeResult', 'ModeSnapshot',
           'ModeState', 'ModePosition', 'Elimination', 'PieceView', 'CatalogEntry', 'BasicTwoPlayer', 'ModeDecision', 'example_rules', 'format_score', 'action_to_dict', 'action_from_dict']
