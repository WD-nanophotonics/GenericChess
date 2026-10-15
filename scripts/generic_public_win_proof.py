"""Opt-in bounded all-defense proof over authoritative immutable public states.

Research fallback for no-progress history. Declarations still unsupported.
No approximate halfmove clock, prices, board-only sharing or theoretical rewards.
One public transition/history replay can overrun a deadline; elapsed is reported.
"""
from time import perf_counter
from generic_chess.core.adjudication import IncompleteAdjudicationHistoryError
from generic_chess.core.movegen import legal_actions
from generic_chess.core.terminal import terminal_result
from generic_chess.core.transition import apply_action
from scripts.generic_proof_public_path import PublicProofPath
from scripts.generic_win_proof import (ProofNode,WinCertificate,ProofResult,_Budget,
    _Interrupted,_ordered,_same_state,PROVEN_WIN,UNKNOWN,ALREADY_TERMINAL,
    StrategyCursor,CertificateVerificationError)


def prove_win_public(compiled,state,*,target=None,max_nodes=4096,seconds=1.,max_depth=64,cancel=None,_clock=perf_counter):
    target=state.position.side_to_move if target is None else target
    if type(target) is not int or target not in (0,1):raise ValueError("invalid target")
    if type(max_depth) is not int or not 0<=max_depth<=128:raise ValueError("invalid depth")
    b=_Budget(max_nodes,seconds,cancel,_clock);rt=PublicProofPath(state,compiled);completed=0
    def result(status,reason,tree=None,terminal=None):
        cert=WinCertificate(compiled.ruleset_fingerprint,state,target,tree) if tree is not None else None
        return ProofResult(status,cert,reason,b.nodes,b.elapsed(),completed,rt.pushes,rt.pops,terminal.status.value if terminal else None,terminal.winner if terminal else None,rt.peak_depth)
    def search(depth):
        b.visit();terminal=rt.terminal_status
        if terminal.is_terminal:
            return (True,ProofNode(0,terminal_kind=terminal.status.value)) if terminal.winner==target else (False,None)
        if depth==0:return None,None
        actions=_ordered(rt.legal_actions(checkpoint=b.poll));b.poll()
        if not actions:return None,None
        own=rt.position.side_to_move==target;edges=[];unknown=False
        for action in actions:
            rt.push(action,checkpoint=b.poll)
            try:value,tree=search(depth-1)
            finally:rt.pop()
            if own and value is True:return True,ProofNode(tree.rank+1,((action,tree),))
            if not own and value is False:return False,None
            unknown|=value is None
            if tree is not None:edges.append((action,tree))
        if unknown:return None,None
        if own:return False,None
        return True,ProofNode(1+max(child.rank for _,child in edges),tuple(edges))
    try:
        b.poll()
        if getattr(compiled,"declarations",()):return result(UNKNOWN,"unsupported_declarations")
        actual=terminal_result(state,compiled);b.poll()
        if actual!=state.terminal_status:return result(UNKNOWN,"inconsistent_root_terminal")
        if actual.is_terminal:return result(ALREADY_TERMINAL,"actual_rule_terminal",terminal=actual)
        for depth in range(max_depth+1):
            value,tree=search(depth);b.poll();completed=depth
            if value is True:return result(PROVEN_WIN,"finite_public_all_defense_certificate",tree)
            if value is False:return result(UNKNOWN,"no_forced_win_in_exhausted_tree")
        return result(UNKNOWN,"depth_budget")
    except _Interrupted:return result(UNKNOWN,b.reason)
    except IncompleteAdjudicationHistoryError:return result(UNKNOWN,"incomplete_adjudication_history")
    except NotImplementedError:return result(UNKNOWN,"unsupported_public_semantics")
    finally:rt.assert_balanced()


def verify_public_certificate(compiled,state,certificate,*,max_nodes=65536,seconds=1.,cancel=None,_clock=perf_counter):
    """Independent recursive public replay, not prover/path/cache traversal."""
    b=_Budget(max_nodes,seconds,cancel,_clock);leaves={};reason="verified";valid=False;transitions=0
    def check(current,node):
        nonlocal transitions
        b.visit()
        if not isinstance(node,ProofNode) or type(node.rank) is not int or not 0<=node.rank<=128:return False
        actual=terminal_result(current,compiled);b.poll()
        if actual!=current.terminal_status:return False
        if actual.is_terminal:
            ok=node.rank==0 and not node.edges and node.terminal_kind==actual.status.value and actual.winner==certificate.target
            if ok:leaves[actual.status.value]=leaves.get(actual.status.value,0)+1
            return ok
        if node.rank==0 or node.terminal_kind is not None:return False
        legal=set(legal_actions(current,compiled,checkpoint=b.poll));actions=[a for a,_ in node.edges]
        if not actions or len(set(actions))!=len(actions) or not set(actions)<=legal:return False
        if current.position.side_to_move==certificate.target:
            if len(actions)!=1:return False
        elif set(actions)!=legal:return False
        for action,child in node.edges:
            if not isinstance(child,ProofNode) or child.rank>=node.rank:return False
            b.poll();next_state=apply_action(current,action,compiled);transitions+=1;b.poll()
            if not check(next_state,child):return False
        return node.rank==1+max(child.rank for _,child in node.edges)
    try:
        b.poll()
        if (not isinstance(certificate,WinCertificate) or certificate.ruleset_fingerprint!=compiled.ruleset_fingerprint
            or not _same_state(state,certificate.root) or type(certificate.target) is not int or certificate.target not in (0,1)):
            reason="root_binding_mismatch"
        elif getattr(compiled,"declarations",()):reason="unsupported_declarations"
        else:
            valid=check(state,certificate.tree);b.poll()
            if not valid:reason="invalid_certificate"
    except _Interrupted:reason=b.reason
    except IncompleteAdjudicationHistoryError:reason="incomplete_adjudication_history"
    except (NotImplementedError,ValueError,TypeError,AttributeError):reason="invalid_or_unsupported_certificate"
    return dict(verified=valid and reason=="verified",reason=reason,nodes=b.nodes,seconds=b.elapsed(),terminal_leaves=leaves,public_transitions=transitions)


class PublicStrategyCursor(StrategyCursor):
    """Same full-history/rank execution, independently public-verified first."""
    def __init__(self,compiled,certificate,**kwargs):
        receipt=verify_public_certificate(compiled,certificate.root,certificate,**kwargs)
        if not receipt["verified"]:raise CertificateVerificationError(receipt)
        self.compiled,self.certificate=compiled,certificate
        self.state,self.node=certificate.root,certificate.tree;self.receipt=receipt
