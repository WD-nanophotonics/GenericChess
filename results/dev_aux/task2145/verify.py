"""Auxiliary opt-in prefix-sharing verifier; no product or reference edits."""
from copy import copy
from time import perf_counter
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_win_proof import _Budget,_Interrupted,_same_state,CertificateVerificationError
from scripts.generic_session_win_proof import (SessionProofNode,SessionWinCertificate,SessionStrategyCursor,choices,execute,replay_bound)

def verify_prefix_session_certificate(session,certificate,*,max_nodes=65536,seconds=1.,cancel=None,_clock=perf_counter):
    """Replay root once; every descendant belongs only to this verifier.

    Induction: replayed root is authoritative; public submit/declare extends an
    already reconstructed immutable prefix. No state/history coalescing occurs.
    GameSession slots hold immutable tuples/state; shallow copies change only
    their own bindings. Prover-owned sessions/caches are never used.
    """
    b=_Budget(max_nodes,seconds,cancel,_clock);valid=False;reason='verified';leaves={};transitions=0
    def check(current,node):
        nonlocal transitions
        b.visit()
        if not isinstance(node,SessionProofNode) or type(node.rank) is not int or not 0<=node.rank<=128:return False
        result=current.result;b.poll()
        if result.status is not SessionStatus.ONGOING:
            ok=node.rank==0 and not node.edges and _same_state(node.terminal,result) and result.winner==certificate.target
            if ok:leaves[result.status.value+':'+str(result.declaration_outcome)]=leaves.get(result.status.value+':'+str(result.declaration_outcome),0)+1
            return ok
        if node.rank==0 or node.terminal is not None:return False
        edges=[c for c,_ in node.edges]
        if not edges or len(set(edges))!=len(edges):return False
        if current.state.position.side_to_move==certificate.target:
            if len(edges)!=1:return False
            # Independent public submit/declare below validates this one edge.
            # Do not enumerate unrelated OR alternatives merely for membership.
        elif set(edges)!=set(choices(current,b)):return False
        for choice,childnode in node.edges:
            if not isinstance(childnode,SessionProofNode) or childnode.rank>=node.rank:return False
            b.poll();child=copy(current);b.poll()
            execute(child,choice);transitions+=1;b.poll()
            if not check(child,childnode):return False
        return node.rank==1+max(n.rank for _,n in node.edges)
    try:
        b.poll();reconstructed=replay_bound(session);b.poll()
        if (not isinstance(certificate,SessionWinCertificate) or type(certificate.target) is not int
            or certificate.target not in (0,1) or certificate.ruleset_fingerprint!=session.compiled.ruleset_fingerprint
            or not _same_state(certificate.root_record,session.to_record()) or not _same_state(certificate.root_state,session.state)):
            reason='root_binding_mismatch'
        else:
            valid=check(reconstructed,certificate.tree);b.poll()
            if not valid:reason='invalid_certificate'
    except _Interrupted:reason=b.reason
    except (NotImplementedError,ValueError,TypeError,AttributeError):reason='invalid_or_unsupported_session'
    return dict(verified=valid and reason=='verified',reason=reason,nodes=b.nodes,seconds=b.elapsed(),terminal_leaves=leaves,session_transitions=transitions,root_replays=1 if 'reconstructed' in locals() else 0,independent_prefix_clones=transitions)


class PrefixSessionStrategyCursor(SessionStrategyCursor):
    def __init__(self,session,certificate,**kwargs):
        self.receipt=verify_prefix_session_certificate(session,certificate,**kwargs)
        if not self.receipt['verified']:raise CertificateVerificationError(self.receipt)
        self.certificate=certificate;self.state=session.state;self.record=session.to_record();self.node=certificate.tree
