"""Opt-in separate phase budgets over actual GameSession, never old defaults.

Proof visits, verifier visits and Native/normal visits are distinct counters.
Normal search receives its full predeclared cap regardless of proof use; saved
proof time cannot increase its own wall cap. The total wall deadline still wins.
No shared cache is adopted here. Existing quarter-budget chooser is unchanged.
"""
from dataclasses import dataclass
from math import isfinite
from time import perf_counter
from generic_chess.session.result import SessionStatus
from scripts.generic_win_proof import _Budget, _Interrupted, _same_state, CertificateVerificationError
from scripts.generic_session_win_proof import SessionStrategyCursor, SessionChoice, replay_bound
from scripts.generic_session_proof_player import SessionProofMaterialPlayer, SessionDecision
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn


@dataclass(frozen=True)
class PhaseLimits:
    proof_nodes: int = 16384
    verification_nodes: int = 16384
    proof_seconds: float = 1.5
    verification_seconds: float = .5
    normal_seconds: float = .1

    def __post_init__(self):
        for n in (self.proof_nodes, self.verification_nodes):
            if type(n) is not int or n < 0: raise ValueError('invalid phase node limit')
        for t in (self.proof_seconds, self.verification_seconds, self.normal_seconds):
            if not isfinite(t) or t < 0: raise ValueError('invalid phase seconds')


@dataclass(frozen=True)
class PhaseDecision(SessionDecision):
    phase_limits: tuple = ()


class SessionPhasePlayer(SessionProofMaterialPlayer):
    def __init__(self, compiled, evaluate, *, limits=PhaseLimits(), **kwargs):
        if not isinstance(limits, PhaseLimits): raise ValueError('typed phase limits required')
        kwargs.setdefault('proof_search', prove_session_win_batch_pn)
        super().__init__(compiled, evaluate, **kwargs)
        self.limits = limits

    def choose(self, session, *, max_nodes=4096, seconds=2.25, cancel=None,
            allow_new_proof=True, _clock=perf_counter):
        # max_nodes is explicitly the NORMAL cap here, not a mixed-unit total.
        b = _Budget(max_nodes, seconds, cancel, _clock)
        root_record, root_state, root_result = session.to_record(), session.state, session.result
        choice = None; source = 'NO_CHOICE'; reason = 'disabled'; cause = 'depth_budget'
        proof_nodes = verification_nodes = search_nodes = 0
        admission_seconds = proof_seconds = verification_seconds = normal_seconds = 0.
        normal_receipt = None; rank = None; proof_stats = ()
        limits = self.limits
        phase_limits = (('normal_nodes', max_nodes), ('proof_nodes', limits.proof_nodes),
            ('verification_nodes', limits.verification_nodes), ('total_seconds', seconds),
            ('proof_seconds', limits.proof_seconds), ('verification_seconds', limits.verification_seconds),
            ('normal_seconds', limits.normal_seconds))
        def left(): return max(0., seconds-b.elapsed())
        def out(): return PhaseDecision(choice, source, reason, proof_nodes, verification_nodes,
            search_nodes, b.elapsed(), cause, rank, root_record, root_state, root_result,
            normal_receipt, admission_seconds, proof_seconds, verification_seconds,
            normal_seconds, proof_stats, phase_limits)
        try:
            b.poll()
            if session.compiled.ruleset_fingerprint != self.compiled.ruleset_fingerprint:
                raise ValueError('player/session rules mismatch')
            begin = _clock(); replay_bound(session); admission_seconds = _clock()-begin; b.poll()
            if root_result.status is not SessionStatus.ONGOING:
                source = 'TERMINAL'; cause = 'actual_session_terminal'; return out()
            if self.proof_enabled and self.cursor is not None:
                try: selected = self.cursor.choose(session)
                except ValueError: self.cursor = None; selected = None
                b.poll()
                if selected is not None:
                    choice = selected; source = 'PROOF_CONTINUATION'; reason = 'verified_strategy'
                    cause = 'certificate'; rank = self.cursor.node.rank; return out()
            if self.proof_enabled and not allow_new_proof: reason = 'new_proof_disabled'
            if self.proof_enabled and allow_new_proof:
                result = self.proof_search(session, max_nodes=limits.proof_nodes,
                    seconds=min(limits.proof_seconds, left()), max_depth=self.proof_depth,
                    cancel=cancel, _clock=_clock)
                proof_nodes = result.nodes; proof_seconds = result.seconds; reason = result.reason
                proof_stats = tuple((name, getattr(result, name)) for name in (
                    'frontiers','transitions','iterations','peak_depth','eager_board_successors','claims_assessed') if hasattr(result,name))
                b.poll()
                if result.status == 'PROVEN_WIN':
                    try:
                        cursor = SessionStrategyCursor(session, result.certificate,
                            max_nodes=limits.verification_nodes,
                            seconds=min(limits.verification_seconds, left()), cancel=cancel, _clock=_clock)
                        verification_nodes = cursor.receipt['nodes']; verification_seconds = cursor.receipt['seconds']; b.poll()
                        selected = cursor.choose(session); b.poll()
                        if selected is not None:
                            self.cursor = cursor; choice = selected; source = 'PROOF'
                            cause = 'certificate'; rank = cursor.node.rank; return out()
                        reason = 'verified_no_choice'
                    except CertificateVerificationError as error:
                        verification_nodes = error.receipt['nodes']; verification_seconds = error.receipt['seconds']
                        reason = 'verification_'+error.receipt['reason']
            b.poll()
            normal_receipt = self.normal.choose(session.state, max_nodes=max_nodes,
                seconds=min(limits.normal_seconds, left()), cancel=cancel, _clock=_clock)
            search_nodes = normal_receipt.nodes; normal_seconds = normal_receipt.seconds
            source = normal_receipt.source; cause = normal_receipt.exit_cause
            if normal_receipt.action is not None:
                choice = SessionChoice('ACTION', action=normal_receipt.action)
            b.poll()
        except _Interrupted:
            cause = b.reason
            if cause == 'cancelled': choice = None; rank = None
        except (ValueError, NotImplementedError):
            choice = None; cause = 'unsupported_or_unreplayable_session'
        finally:
            assert _same_state(session.state,root_state) and _same_state(session.to_record(),root_record) and session.result==root_result
        return out()
