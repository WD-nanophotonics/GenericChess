"""Opt-in composed proof scheduler; all phases share one query budget.

A graph non-win is only a scheduling UNKNOWN. Positive graph strategies must
produce real Session certificates. Guard failure may fall back to original PN
with the REMAINING resources; failed construction never gets a new budget.
Independent certificate verification remains the caller's responsibility.
"""
from dataclasses import replace
from time import perf_counter
from results.dev_aux.task2072.no_win_filter import CompleteGraphNoWinFilter
from results.dev_aux.task2086.rank_certificate import RankCertificateProvider
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from scripts.generic_session_win_proof import SessionProofResult
from scripts.generic_win_proof import _Budget, _Interrupted

class CompositeProvider:
    def __init__(self, teacher, *, fallback=prove_session_win_batch_pn, rank=None):
        self.rank = RankCertificateProvider(teacher) if rank is None else rank
        self.fallback = fallback
        self.negative = CompleteGraphNoWinFilter(teacher, solver=self._positive)
        self.trace = []

    def _positive(self, session, *, target, max_nodes, seconds, max_depth,
                  cancel=None, _clock=perf_counter):
        b = _Budget(max_nodes, seconds, cancel, _clock)
        used = 0
        def unknown(reason):
            return SessionProofResult('UNKNOWN', None, reason, used, b.elapsed(), 0)
        try:
            b.poll()
            r = self.rank(session, target=target, max_nodes=max_nodes,
                          seconds=max(0., seconds-b.elapsed()), max_depth=max_depth,
                          cancel=cancel, _clock=_clock)
            used = r.nodes
            self.trace.append(dict(phase='rank', status=r.status, reason=r.reason,
                                   nodes=r.nodes, seconds=r.seconds))
            if r.status == 'PROVEN_WIN':
                b.poll()
                return replace(r, nodes=used, seconds=b.elapsed())
            b.poll()
            if used >= max_nodes:
                return unknown('node_budget')
            f = self.fallback(session, target=target, max_nodes=max_nodes-used,
                              seconds=max(0., seconds-b.elapsed()), max_depth=max_depth,
                              cancel=cancel, _clock=_clock)
            used += f.nodes
            self.trace.append(dict(phase='fallback', status=f.status, reason=f.reason,
                                   nodes=f.nodes, seconds=f.seconds))
            b.poll()
            return replace(f, nodes=used, seconds=b.elapsed())
        except _Interrupted:
            return unknown(b.reason)

    def __call__(self, session, **kwargs):
        self.trace = []
        r = self.negative(session, **kwargs)
        if not self.trace:
            self.trace.append(dict(phase='negative_or_interrupt', status=r.status,
                                   reason=r.reason, nodes=r.nodes, seconds=r.seconds))
        return r
