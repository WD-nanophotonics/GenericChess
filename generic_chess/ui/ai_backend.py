"""Frozen UI Test backend: installed alpha-beta through Python Core only."""

from ..ai.alphabeta.player import AlphaBetaPlayer
from ..rules.compiled import CompiledRuleSet


def create_ui_player(compiled: CompiledRuleSet, *, use_disk_cache: bool = True) -> AlphaBetaPlayer:
    """Create a complete player without native binaries or research prototypes.

    Keep search and evaluation defaults from the pinned product baseline. The
    UI owns budget/cancellation and session lifecycle, not engine internals.
    """
    return AlphaBetaPlayer(
        compiled,
        use_disk_cache=use_disk_cache,
        use_native_semantic_legality=False,
    )
