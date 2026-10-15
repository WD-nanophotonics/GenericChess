"""Opt-in research GameSession proof/material chooser, with one physical writer.

Existing GameState learners/defaults are unchanged. Unknown proof falls back to
board-only normal search: declarations are supported by the proof arm, NOT
strategically modeled by normal alpha-beta. No draw/WDL reward is inferred.
Use commit_session_decision once, then broadcast observation to all players.
Proof and verification each receive a fixed quarter of the visit/time budget;
unused visits remain available to normal search. Atomic public operations can
overshoot time, and external normal providers can report node overruns.
"""
from copy import copy
from dataclasses import dataclass
from time import perf_counter

from generic_chess.session.result import SessionStatus
from scripts.generic_win_proof import _Budget,_Interrupted,_same_state,CertificateVerificationError
from scripts.generic_proof_player import ProofMaterialPlayer
from scripts.generic_session_win_proof import SessionChoice,SessionStrategyCursor,execute,replay_bound
from scripts.generic_session_win_proof_pn import prove_session_win_pn


@dataclass(frozen=True)
class SessionDecision:
    choice: object | None
    source: str
    proof_reason: str
    proof_nodes: int
    verification_nodes: int
    search_nodes: int
    seconds: float
    exit_cause: str
    proof_rank: int | None
    root_record: object
    root_state: object
    root_result: object
    normal_receipt: object | None = None

    @property
    def nodes(self):return self.proof_nodes+self.verification_nodes+self.search_nodes


class SessionProofMaterialPlayer:
    def __init__(self,compiled,evaluate,*,proof_enabled=True,max_depth=3,
                 proof_depth=64,proof_search=prove_session_win_pn,normal_search=None):
        if type(proof_depth) is not int or not 0<=proof_depth<=128:
            raise ValueError('invalid proof depth')
        self.compiled=compiled;self.proof_enabled=proof_enabled;self.proof_depth=proof_depth
        self.proof_search=proof_search;self.cursor=None
        # Prevent a second proof allocation hidden inside normal fallback.
        self.normal=ProofMaterialPlayer(compiled,evaluate,proof_enabled=False,
                                        max_depth=max_depth,normal_search=normal_search)

    def observe(self,before,choice,after):
        if self.cursor is not None:
            try:self.cursor.observe(before,choice,after)
            except ValueError:self.cursor=None

    def choose(self,session,*,max_nodes=4096,seconds=1.,cancel=None,allow_new_proof=True,_clock=perf_counter):
        b=_Budget(max_nodes,seconds,cancel,_clock)
        root_record=session.to_record();root_state=session.state;root_result=session.result
        choice=None;source='NO_CHOICE';reason='disabled';cause='depth_budget'
        proof_nodes=verification_nodes=search_nodes=0;normal_receipt=None;rank=None
        admission_seconds=proof_seconds=verification_seconds=normal_seconds=0.
        def left():return max(0.,seconds-b.elapsed())
        def out():return SessionDecision(choice,source,reason,proof_nodes,verification_nodes,
            search_nodes,b.elapsed(),cause,rank,root_record,root_state,root_result,normal_receipt,
            admission_seconds,proof_seconds,verification_seconds,normal_seconds)
        try:
            b.poll()
            if session.compiled.ruleset_fingerprint!=self.compiled.ruleset_fingerprint:
                raise ValueError('player/session rules mismatch')
            admission_start=_clock();replay_bound(session);admission_seconds=_clock()-admission_start;b.poll()
            if root_result.status is not SessionStatus.ONGOING:
                source='TERMINAL';cause='actual_session_terminal';return out()
            if self.proof_enabled and self.cursor is not None:
                try:selected=self.cursor.choose(session)
                except ValueError:self.cursor=None;selected=None
                b.poll()
                if selected is not None:
                    choice=selected;source='PROOF_CONTINUATION';reason='verified_strategy'
                    cause='certificate';rank=self.cursor.node.rank;return out()
            if self.proof_enabled and not allow_new_proof:reason='new_proof_disabled'
            if self.proof_enabled and allow_new_proof:
                quarter=max_nodes//4
                result=self.proof_search(session,max_nodes=quarter,
                    seconds=min(1.,seconds/4,left()),max_depth=self.proof_depth,
                    cancel=cancel,_clock=_clock)
                proof_nodes=result.nodes;proof_seconds=result.seconds;reason=result.reason;b.poll()
                if result.status=='PROVEN_WIN':
                    try:
                        cursor=SessionStrategyCursor(session,result.certificate,max_nodes=quarter,
                            seconds=min(seconds/4,left()),cancel=cancel,_clock=_clock)
                        verification_nodes=cursor.receipt['nodes'];verification_seconds=cursor.receipt['seconds'];b.poll()
                        selected=cursor.choose(session);b.poll()
                        if selected is not None:
                            self.cursor=cursor;choice=selected;source='PROOF';cause='certificate'
                            rank=cursor.node.rank;return out()
                        reason='verified_no_choice'
                    except CertificateVerificationError as error:
                        verification_nodes=error.receipt['nodes'];verification_seconds=error.receipt['seconds']
                        reason='verification_'+error.receipt['reason']
            b.poll()
            normal_receipt=self.normal.choose(session.state,
                max_nodes=max(0,max_nodes-proof_nodes-verification_nodes),seconds=left(),
                cancel=cancel,_clock=_clock)
            search_nodes=normal_receipt.nodes;normal_seconds=normal_receipt.seconds
            source=normal_receipt.source;cause=normal_receipt.exit_cause
            if normal_receipt.action is not None:
                choice=SessionChoice('ACTION',action=normal_receipt.action)
            b.poll()
        except _Interrupted:
            cause=b.reason
            if cause=='cancelled':choice=None;rank=None
        finally:
            if (not _same_state(session.state,root_state)
                or not _same_state(session.to_record(),root_record)
                or not _same_state(session.result,root_result)):
                raise RuntimeError('chooser mutated authoritative session')
        return out()


def commit_session_decision(session,decision,players=(),*,cancel=None):
    """Single physical commit; observe both colors afterward, without re-submit.

    Cancellation is checked before committing. A cancel arriving during the
    atomic submit/declare cannot undo a real move; the returned result/record
    remain authoritative. This is not an asynchronous dispatcher/rollback API.
    """
    if not isinstance(decision,SessionDecision) or decision.choice is None:
        raise ValueError('no actionable session decision')
    if (not _same_state(decision.root_state,session.state)
        or not _same_state(decision.root_record,session.to_record())
        or not _same_state(decision.root_result,session.result)):
        raise ValueError('stale session decision')
    if cancel is not None and cancel():raise _Interrupted('cancelled')
    before=copy(session)
    result=execute(session,decision.choice)
    for player in players:player.observe(before,decision.choice,session)
    return result
