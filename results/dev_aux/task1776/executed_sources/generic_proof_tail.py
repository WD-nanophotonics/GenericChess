"""Frozen horizon admission for physically executing an existing win strategy.

No new proof is attempted at/after the horizon. The bound comes from the
already verified finite tree, never from prices, a table or a predicted score.
"""
from dataclasses import dataclass
from scripts.generic_win_proof import _same_state


@dataclass
class CertifiedTail:
    owner: int
    initial_rank: int
    remaining_rank: int
    cursor: object

    @classmethod
    def admit(cls, state, players, *, max_rank=64):
        if type(max_rank) is not int or not 0 <= max_rank <= 128:
            raise ValueError('invalid tail rank cap')
        if state.terminal_status.is_terminal:
            return None
        candidates=[]
        for side, player in sorted(players.items()):
            cursor=player.cursor
            if not player.proof_enabled or cursor is None:
                continue
            if not _same_state(cursor.state, state):
                continue
            rank=cursor.node.rank
            if cursor.certificate.target != side or not 0 < rank <= max_rank:
                continue
            candidates.append((side, cursor))
        if len(candidates)>1:
            raise ValueError('conflicting certified winners')
        if not candidates:
            return None
        owner,cursor=candidates[0]
        return cls(owner,cursor.node.rank,cursor.node.rank,cursor)

    def choose(self, state):
        """Only the certified owner's turn; defenders retain normal play."""
        return self.cursor.choose(state)

    def observed(self, state):
        """Called AFTER players.observe and the public committed transition."""
        if not _same_state(self.cursor.state, state):
            raise ValueError('tail lost full state/history binding')
        rank=self.cursor.node.rank
        if not 0 <= rank < self.remaining_rank:
            raise ValueError('tail rank did not decrease')
        self.remaining_rank=rank
        if state.terminal_status.is_terminal:
            if state.terminal_status.winner != self.owner:
                raise ValueError('actual terminal contradicts certified winner')
        elif rank==0:
            raise ValueError('exhausted tail without actual win')
