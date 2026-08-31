"""GenericChess v0: a deterministic generic chess/shogi-like game engine.

The package is split into three layers:

* ``generic_chess.core`` - the deterministic game kernel (no randomness).
* ``generic_chess.rules`` - RuleSet schema, validation, compiler and serialization.
* ``generic_chess.generation`` - seeded generation of piece rules and setups.

The public API is intentionally small and stable so that future UIs and AI
players only depend on these functions.
"""

from .core.actions import BoardMove, DropMove, action_from_dict, action_to_dict
from .core.attacks import (
    is_in_check,
    is_square_attacked,
    pseudo_attacks,
)
from .core.coordinates import Square
from .core.errors import IllegalActionError, RuleSetMismatchError
from .core.keys import position_key
from .core.movegen import legal_actions
from .core.pieces import Piece, PieceType
from .core.position import GameState, Hands, Position
from .core.terminal import TerminalResult, TerminalStatus
from .generation.generator import generate_game
from .generation.config import GeneratorConfig
from .rules.compiler import compile_ruleset, compile_ruleset_for_execution
from .rules.catalog import build_builtin_ruleset, builtin_ruleset_names
from .rules.western_chess import build_western_chess_ruleset
from .rules.schema import RuleSet
from .rules.serialization import deserialize_ruleset, serialize_ruleset
from .core.transition import apply_action, initial_state, legal_successors
from .core.terminal import terminal_result

__all__ = [
    "compile_ruleset",
    "compile_ruleset_for_execution",
    "build_builtin_ruleset",
    "builtin_ruleset_names",
    "build_western_chess_ruleset",
    "initial_state",
    "legal_actions",
    "legal_successors",
    "apply_action",
    "pseudo_attacks",
    "is_square_attacked",
    "is_in_check",
    "terminal_result",
    "position_key",
    "generate_game",
    "serialize_ruleset",
    "deserialize_ruleset",
    # Types
    "Square",
    "Piece",
    "PieceType",
    "Position",
    "GameState",
    "Hands",
    "BoardMove",
    "DropMove",
    "TerminalResult",
    "TerminalStatus",
    "RuleSet",
    "GeneratorConfig",
    "IllegalActionError",
    "RuleSetMismatchError",
    "action_to_dict",
    "action_from_dict",
]
