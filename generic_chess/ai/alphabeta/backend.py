"""Experimental adapter boundary for search implementations.

Current UI and benchmark production callers still use the public ``Player``
protocol directly; this module is not yet their replacement seam.
"""

from __future__ import annotations

from typing import Protocol

from ..cancellation import CancellationToken
from ..decision import PlayerDecision
from .player import AlphaBetaPlayer
from .snapshot import SearchSnapshot


class SearchBackend(Protocol):
    """Experimental protocol for adapters over a captured search snapshot.

    Production UI and benchmark callers currently depend on ``Player`` and call
    ``choose_action`` directly. A future native implementation can use this
    protocol only after a real caller is routed through it and its progress,
    cancellation, and result contracts are matched.
    """

    def search(
        self,
        snapshot: SearchSnapshot,
        cancel_token: CancellationToken | None = None,
    ) -> PlayerDecision:
        ...


class PythonSearchBackend:
    """Adapter exposing :class:`AlphaBetaPlayer` through ``SearchBackend``."""

    def __init__(self, player: AlphaBetaPlayer) -> None:
        self._player = player

    def search(
        self,
        snapshot: SearchSnapshot,
        cancel_token: CancellationToken | None = None,
    ) -> PlayerDecision:
        return self._player.choose_action(
            snapshot.session,
            snapshot.limits,
            cancel_token=cancel_token,
        )
