"""Opt-in complete-session normal + existing paid proof/bank/fallback policy.

No existing class/default changed. Normal choices remain typed through actual
commit; proof and verification remain independently capped/paid. UNKNOWN never
becomes DRAW. All declaration outcomes retain actual Session semantics.
"""
from time import perf_counter
from generic_chess.session.result import SessionStatus
from scripts.generic_win_proof import _Budget,_Interrupted,_same_state,CertificateVerificationError
from scripts.generic_session_win_proof import SessionStrategyCursor,SessionChoice,replay_bound
from scripts.generic_session_phase_player import SessionPhasePlayer,PhaseDecision
from scripts.generic_session_cached_phase_player import SessionCachedPhasePlayer
from results.dev_aux.task2148.normal import SessionCompleteMaterialSearch
class CompleteSessionPhasePlayer(SessionPhasePlayer):
    def __init__(self,compiled,evaluate,*,max_depth=3,normal_factory=SessionCompleteMaterialSearch,**kwargs):
        if kwargs.get('normal_search')is not None:raise ValueError('explicitnormalfactory, notlegacyexternaladapter')
        super().__init__(compiled,evaluate,max_depth=max_depth,**kwargs)
        self.normal=normal_factory(compiled,evaluate,max_depth=max_depth)
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
            normal_receipt = self.normal.choose(session, max_nodes=max_nodes,
                seconds=min(limits.normal_seconds, left()), cancel=cancel, _clock=_clock)
            search_nodes = normal_receipt.nodes; normal_seconds = normal_receipt.seconds
            source = normal_receipt.source; cause = normal_receipt.exit_cause
            if normal_receipt.choice is not None:
                choice = normal_receipt.choice
            b.poll()
        except _Interrupted:
            cause = b.reason
            if cause == 'cancelled': choice = None; rank = None
        except (ValueError, NotImplementedError):
            choice = None; cause = 'unsupported_or_unreplayable_session'
        finally:
            assert _same_state(session.state,root_state) and _same_state(session.to_record(),root_record) and session.result==root_result
        return out()

class CompleteSessionCachedPlayer(SessionCachedPhasePlayer,CompleteSessionPhasePlayer):
    """MRO keeps existing bank admission/fill/current verification accounting."""
    pass
