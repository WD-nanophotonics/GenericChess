"""Literal checkmate gate on the complete public observer, research-only."""
from dataclasses import dataclass
from generic_chess.core.terminal import TerminalStatus
from scripts.public_goal_intervals import PublicGame

@dataclass(frozen=True)
class _UnresolvedTerminal:
    status: object
    winner: int | None
    is_terminal: bool = True
    unresolved: bool = True

def mate_goal_terminal(result):
    if not result.is_terminal or result.status is TerminalStatus.CHECKMATE:
        return result
    return _UnresolvedTerminal(result.status,result.winner)

class MateOnlyPublicGame(PublicGame):
    def terminal(self,state):
        return mate_goal_terminal(super().terminal(state))
