"""Opt-in legal fallback, paid inside the original total decision allowance."""
from dataclasses import replace
from time import perf_counter
from generic_chess.session.result import SessionStatus
from scripts.generic_win_proof import _Budget,_Interrupted,_ordered,_same_state
from scripts.generic_session_win_proof import SessionChoice,replay_bound
from scripts.generic_session_cached_phase_player import SessionCachedPhasePlayer

class LegalFallbackPhasePlayer(SessionCachedPhasePlayer):
    def choose(self, session, *, max_nodes=4096, seconds=2.75, cancel=None,
               allow_new_proof=True, _clock=perf_counter):
        began = _clock()
        original_record, original_state, original_result = session.to_record(), session.state, session.result
        fallback = None
        admission_cancelled = False
        admission = _Budget(max_nodes, seconds, cancel, _clock)
        try:
            admission.poll()
            if (session.compiled.ruleset_fingerprint == self.compiled.ruleset_fingerprint
                    and session.result.status is SessionStatus.ONGOING):
                replay_bound(session)
                admission.poll()
                legal = _ordered(session.legal_actions())
                if legal:
                    fallback = SessionChoice('ACTION', action=legal[0])
                admission.poll()
        except _Interrupted:
            admission_cancelled = admission.reason == 'cancelled'
        except (ValueError, NotImplementedError):
            fallback = None
        paid_admission = _clock() - began
        try:
            decision = super().choose(session, max_nodes=max_nodes,
                seconds=max(0., seconds-paid_admission),
                cancel=(lambda: True) if admission_cancelled else cancel,
                allow_new_proof=allow_new_proof, _clock=_clock)
            # A stop always beats fallback, including a stop after parent return.
            cancelled = admission_cancelled or (cancel is not None and cancel())
            limits = tuple((key, seconds if key == 'total_seconds' else value)
                           for key, value in decision.phase_limits)
            limits += (('fallback_admission_seconds', paid_admission),)
            if cancelled or decision.exit_cause == 'cancelled':
                return replace(decision, choice=None, exit_cause='cancelled',
                               seconds=_clock()-began, phase_limits=limits)
            if (decision.choice is None and fallback is not None
                    and decision.exit_cause in ('time_budget', 'node_budget')):
                return replace(decision, choice=fallback,
                    source='PRECOMPUTED_LEGAL_FALLBACK',
                    seconds=_clock()-began, phase_limits=limits)
            return replace(decision, seconds=_clock()-began, phase_limits=limits)
        finally:
            assert (_same_state(session.to_record(), original_record)
                    and _same_state(session.state, original_state)
                    and session.result == original_result)
