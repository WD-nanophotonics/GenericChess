"""Opt-in cached phase policy; historical evidence never replaces current checks.

The original SessionPhasePlayer and its studies are unchanged. This policy pays
bank admission/fill checks AND current cursor checks, under one total deadline.
Normal allocation stays independently capped. Sharing a bank changes a wall
policy and requires a newly declared envelope, schedule and empty-start state.
"""
from dataclasses import dataclass, replace
from time import perf_counter
from scripts.generic_session_phase_player import SessionPhasePlayer, PhaseDecision
from scripts.generic_session_proof_bank import SessionLogicalProofBank
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn

_STATS = ('frontiers', 'transitions', 'iterations', 'peak_depth',
          'eager_board_successors', 'claims_assessed')


@dataclass(frozen=True)
class CachedPhaseDecision(PhaseDecision):
    bank_hit: bool = False
    bank_stored: bool = False
    bank_verification_scope: str = 'NONE'
    bank_query_seconds: float = 0.
    fill_verification_nodes: int = 0
    fill_verification_seconds: float = 0.
    logical_proof_nodes: int = 0
    logical_proof_seconds: float = 0.
    logical_proof_stats: tuple = ()
    logical_status: str = 'NOT_QUERIED'
    logical_reason: str = 'NOT_QUERIED'

    @property
    def nodes(self):
        # Distinct visit units; useful as paid-accounting sum, never normal cap.
        return super().nodes + self.fill_verification_nodes

    @property
    def bank_overhead_seconds(self):
        return max(0., self.bank_query_seconds - self.proof_seconds
                   - self.fill_verification_seconds)


class SessionCachedPhasePlayer(SessionPhasePlayer):
    def __init__(self, compiled, evaluate, *, bank=None, **kwargs):
        if 'proof_search' in kwargs:
            raise ValueError('cached policy solver belongs to its explicit bank')
        if bank is not None and not isinstance(bank, SessionLogicalProofBank):
            raise ValueError('typed logical proof bank required')
        self.bank = bank if bank is not None else SessionLogicalProofBank(
            prove_session_win_batch_pn)
        self._query_context = None
        self._last_query = None
        super().__init__(compiled, evaluate, proof_search=self._query_proof, **kwargs)

    def _query_proof(self, session, *, max_nodes, seconds, max_depth,
                     cancel=None, _clock=perf_counter):
        deadline = self._query_context
        if deadline is None:
            raise ValueError('bank query requires an active policy decision')
        def stopped():
            return ((cancel is not None and cancel()) or _clock() >= deadline)
        q = self.bank.query(session, max_nodes=max_nodes, seconds=seconds,
            max_depth=max_depth, cancel=stopped, _clock=_clock,
            verification_max_nodes=self.limits.verification_nodes,
            verification_seconds=self.limits.verification_seconds)
        self._last_query = q
        r = q.logical_result
        changes = dict(nodes=q.actual_proof_nodes, seconds=q.proof_seconds)
        # A failed fill check cannot be adopted even if a later check might fit.
        if r.status == 'PROVEN_WIN' and not (q.verification and q.verification['verified']):
            changes.update(status='UNKNOWN', certificate=None,
                reason='bank_fill_verification_' + q.verification['reason'])
        # Origin work is retained separately, never charged as current work.
        if q.hit:
            changes.update({n: 0 for n in _STATS if hasattr(r, n)})
        return replace(r, **changes)

    def choose(self, session, *, max_nodes=4096, seconds=2.75, cancel=None,
               allow_new_proof=True, _clock=perf_counter):
        if self._query_context is not None:
            raise ValueError('one active decision per player')
        self._query_context = _clock() + seconds
        self._last_query = None
        try:
            d = super().choose(session, max_nodes=max_nodes, seconds=seconds,
                cancel=cancel, allow_new_proof=allow_new_proof, _clock=_clock)
            q = self._last_query
            values = dict(d.__dict__)
            values['phase_limits'] += (
                ('bank_fill_verification_nodes', self.limits.verification_nodes),
                ('bank_fill_verification_seconds', self.limits.verification_seconds))
            if q is not None:
                r = q.logical_result
                values.update(bank_hit=q.hit, bank_stored=q.stored,
                    bank_verification_scope=q.verification_scope,
                    bank_query_seconds=q.seconds,
                    fill_verification_nodes=q.actual_verification_nodes,
                    fill_verification_seconds=q.verification_seconds,
                    logical_proof_nodes=r.nodes,
                    logical_proof_seconds=q.origin_reference_seconds,
                    logical_proof_stats=tuple((n, getattr(r,n)) for n in _STATS if hasattr(r,n)),
                    logical_status=r.status, logical_reason=r.reason)
            return CachedPhaseDecision(**values)
        finally:
            self._query_context = None
