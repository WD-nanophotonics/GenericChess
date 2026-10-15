"""Optional proof-number tree over complete public GameSession choices.

Same SessionWinCertificate and independent replay verifier as iterative AND/OR.
No state-only merge, price, heuristic, tablebase or product integration. Each
new tree node owns a shallow GameSession snapshot with immutable full state and
record history. Node counts mean newly inspected tree nodes, NOT repeated DFS
visits; compare wall cost plus frontier/transition counts, never nodes alone.
"""
from copy import copy
from dataclasses import dataclass,field
from time import perf_counter
from generic_chess.session.result import SessionStatus
from scripts.generic_win_proof import _Budget,_Interrupted,_same_state
from scripts.generic_session_win_proof import (SessionProofResult,SessionWinCertificate,
    SessionProofNode,choices,execute,replay_bound)


@dataclass(frozen=True)
class SessionPNResult(SessionProofResult):
    frontiers: int=0
    transitions: int=0
    iterations: int=0
    peak_depth: int=0


@dataclass
class _Node:
    session: object
    depth: int
    pn: float=1
    dn: float=1
    open: bool=True
    edges: list=field(default_factory=list)
    terminal: object|None=None


def prove_session_win_pn(session,*,target=None,max_nodes=4096,seconds=1.,max_depth=8,
                         cancel=None,_clock=perf_counter):
    target=session.state.position.side_to_move if target is None else target
    if type(target) is not int or target not in (0,1):raise ValueError('invalid target')
    if type(max_depth) is not int or not 0<=max_depth<=128:raise ValueError('invalid depth')
    b=_Budget(max_nodes,seconds,cancel,_clock);inf=float('inf')
    frontiers=transitions=iterations=peak=0
    root_state=session.state;root_record=session.to_record();root_result=session.result
    def result(status,reason,tree=None):
        cert=SessionWinCertificate(session.compiled.ruleset_fingerprint,root_record,root_state,target,tree) if tree is not None else None
        # No iterative completed-depth claim: peak_depth is separate metadata.
        return SessionPNResult(status,cert,reason,b.nodes,b.elapsed(),0,frontiers,transitions,iterations,peak)
    def visit(current,depth):
        nonlocal peak
        b.visit();node=_Node(current,depth);terminal=current.result;b.poll();peak=max(peak,depth)
        if terminal.status is not SessionStatus.ONGOING:
            node.open=False;node.terminal=terminal
            node.pn,node.dn=(0,inf) if terminal.winner==target else (inf,0)
        elif depth>=max_depth:
            node.pn=node.dn=inf;node.open=False
        return node
    def update(node):
        if not node.edges:return
        children=[child for _,child in node.edges]
        if node.session.state.position.side_to_move==target:
            node.pn=min(n.pn for n in children);node.dn=sum(n.dn for n in children)
        else:
            node.pn=sum(n.pn for n in children);node.dn=min(n.dn for n in children)
        node.open=node.pn!=0 and node.dn!=0 and any(n.open for n in children)
    def certificate(node):
        b.poll();assert node.pn==0
        if node.terminal is not None:return SessionProofNode(0,terminal=node.terminal)
        edges=node.edges if node.session.state.position.side_to_move!=target else [next((c,n) for c,n in node.edges if n.pn==0)]
        branches=tuple((c,certificate(n)) for c,n in edges)
        return SessionProofNode(1+max(n.rank for _,n in branches),branches)
    try:
        b.poll();replay_bound(session);b.poll()
        if root_result.status is not SessionStatus.ONGOING:return result('ALREADY_TERMINAL','actual_session_terminal')
        root=visit(copy(session),0)
        while root.open and root.pn!=0 and root.dn!=0:
            b.poll();node=root;ancestors=[];iterations+=1
            while node.edges:
                eligible=[(i,c,n) for i,(c,n) in enumerate(node.edges) if n.open]
                assert eligible,'open session node without open child'
                own=node.session.state.position.side_to_move==target
                _,choice,child=min(eligible,key=lambda row:((row[2].pn if own else row[2].dn),row[0]))
                ancestors.append(node);node=child;b.poll()
            edges=[];frontiers+=1;own=node.session.state.position.side_to_move==target
            for choice in choices(node.session,b):
                b.poll();child=copy(node.session);execute(child,choice);transitions+=1;b.poll()
                inspected=visit(child,node.depth+1);edges.append((choice,inspected))
                # Partial OR frontiers are sufficient only with a proved win;
                # partial AND frontiers only with an actual refuting child.
                # A winning AND certificate always exhausts every choice.
                if (own and inspected.pn==0) or (not own and inspected.dn==0):break
            b.poll()
            if edges:node.edges=edges;update(node)
            else:node.pn=node.dn=inf;node.open=False
            for parent in reversed(ancestors):update(parent)
        b.poll()
        if root.pn==0:
            tree=certificate(root);b.poll()
            return result('PROVEN_WIN','finite_session_all_defense_certificate',tree)
        return result('UNKNOWN','no_forced_win_in_exhausted_tree' if root.dn==0 else 'depth_budget')
    except _Interrupted:return result('UNKNOWN',b.reason)
    except (NotImplementedError,ValueError):return result('UNKNOWN','unsupported_or_unreplayable_session')
    finally:
        assert _same_state(session.state,root_state) and _same_state(session.to_record(),root_record) and session.result==root_result
