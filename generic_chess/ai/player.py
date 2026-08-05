"""Common Player protocol for Random / AlphaBeta / MCTS / NN players."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from .cancellation import CancellationToken
from .decision import PlayerDecision
from .limits import SearchLimits

if TYPE_CHECKING:
    from ..session.session import GameSession


@runtime_checkable
class Player(Protocol):
    def choose_action(
        self,
        session: "GameSession",
        limits: SearchLimits,
        *,
        cancel_token: CancellationToken | None = None,
    ) -> PlayerDecision:
        ...
