"""Pinned sandbox production alpha-beta through Python Core only."""

from ..ai.alphabeta.player import AlphaBetaPlayer
from ..rules.compiled import CompiledRuleSet
from .material_values import UIMaterialProfileCache


ENGINE_BASE_SHA = "ff073a3b57b46873ccb23078fa7d950a40133891"
ENGINE_LABEL = "Core q4 · 2026-11-06"


def create_ui_player(compiled: CompiledRuleSet, *, use_disk_cache: bool = True) -> AlphaBetaPlayer:
    """Create a complete player without native binaries or research prototypes.

    Keep the pinned search and dynamic evaluation terms. Standard Chess/Shogi
    receive fixed human material prices through the public profile interface;
    generated/custom rules retain the default rule-derived prices.
    """
    return AlphaBetaPlayer(
        compiled,
        use_disk_cache=use_disk_cache,
        profile_cache=UIMaterialProfileCache(use_disk=use_disk_cache),
        use_native_semantic_legality=False,
    )
