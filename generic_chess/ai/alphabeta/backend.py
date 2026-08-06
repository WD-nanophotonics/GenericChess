"""Search backend boundary (future native backends plug in here)."""

from __future__ import annotations

from typing import Protocol

from ..cancellation import CancellationToken
from ..decision import PlayerDecision
from .player import AlphaBetaPlayer
from .snapshot import SearchSnapshot


class SearchBackend(Protocol):
    """Protocol implemented by every search backend.

    UI and benchmark code depend only on this boundary, so a future native
    (Cython/Rust/PyO3) implementation can replace the Python one without
    rewriting callers.
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
