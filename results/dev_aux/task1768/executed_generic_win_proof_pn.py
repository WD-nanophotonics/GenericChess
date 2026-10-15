"""Optional best-first proof-number TREE search; same checked win certificates.

No transposition merging, material input or game-specific ordering. Research
alternative to iterative AND/OR, not a player/default change. Node counts mean
newly visited tree nodes here; compare wall cost, not counts alone, across engines.
"""
from dataclasses import dataclass,field
from time import perf_counter
from generic_chess.core.actions import Action
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalStatus,terminal_result
from generic_chess.core.adjudication import IncompleteAdjudicationHistoryError
from scripts.generic_win_proof import (
    ProofNode,WinCertificate,ProofResult,_Budget,_Interrupted,_ordered,_unsupported,
    PROVEN_WIN,UNKNOWN,ALREADY_TERMINAL,
)


@dataclass
class _Node:
    actor: int
    pn: int=1
    dn: int=1
    open: bool=True
    edges: list=field(default_factory=list)
    terminal_kind: str|None=None


def prove_win_pn(compiled,state,*,target=None,max_nodes=4096,seconds=1.,max_depth=64,
                 cancel=None,_clock=perf_counter):
    target=state.position.side_to_move if target is None else target
    if target not in (0,1):raise ValueError('target must be player0 or1')
    if type(max_depth) is not int or not 0<=max_depth<=128:raise ValueError('max_depth must be in[0,128]')
    b=_Budget(max_nodes,seconds,cancel,_clock);rt=None;inf=max_nodes+1
    peak=0
    def result(status,reason,tree=None,terminal=None):
        cert=WinCertificate(compiled.ruleset_fingerprint,state,target,tree) if tree else None
        return ProofResult(status,cert,reason,b.nodes,b.elapsed(),peak,
                           rt.pushes if rt else 0,rt.pops if rt else 0,
                           terminal.status.value if terminal else None,terminal.winner if terminal else None)
    def visit():
        b.visit();n=_Node(rt.position.side_to_move);t=rt.terminal_status
        if t.is_terminal:
            n.open=False;n.terminal_kind=t.status.value
            n.pn,n.dn=(0,inf) if t.winner==target else (inf,0)
        return n
    def update(n):
        if not n.edges:return
        children=[x for _,x in n.edges]
        if n.actor==target:
            n.pn=min(x.pn for x in children);n.dn=min(inf,sum(x.dn for x in children))
        else:
            n.pn=min(inf,sum(x.pn for x in children));n.dn=min(x.dn for x in children)
        n.open=n.pn!=0 and n.dn!=0 and any(x.open for x in children)
    def certificate(n):
        assert n.pn==0
        if n.terminal_kind is not None:return ProofNode(0,terminal_kind=n.terminal_kind)
        edges=n.edges if n.actor!=target else [next((a,x) for a,x in n.edges if x.pn==0)]
        branches=tuple((a,certificate(x)) for a,x in edges)
        return ProofNode(1+max(x.rank for _,x in branches),branches)
    try:
        b.poll()
        if _unsupported(compiled):return result(UNKNOWN,_unsupported(compiled))
        rt=SearchPathRuntime.from_state(state,compiled);rt.terminal_status=terminal_result(state,compiled);b.poll()
        if rt.terminal_status!=state.terminal_status:return result(UNKNOWN,'inconsistent_root_terminal')
        if rt.terminal_status.is_terminal:return result(ALREADY_TERMINAL,'actual_rule_terminal',terminal=rt.terminal_status)
        root=visit()
        while root.pn!=0 and root.dn!=0 and root.open:
            b.poll();node=root;ancestors=[];depth=0;pushed=0
            try:
                while node.edges:
                    eligible=[(i,a,x) for i,(a,x) in enumerate(node.edges) if x.open]
                    if not eligible:raise AssertionError('open proof node without open child')
                    _,action,child=min(eligible,key=lambda row:((row[2].pn if node.actor==target else row[2].dn),row[0]))
                    ancestors.append(node);rt.push(action,checkpoint=b.poll);pushed+=1;node=child;depth+=1
                peak=max(peak,depth)
                if depth>=max_depth:
                    # Unknown, not disproved. Both infinities prevent using a
                    # depth cutoff as either a win or a refutation certificate.
                    node.pn=node.dn=inf;node.open=False
                else:
                    actions=_ordered(rt.legal_actions(checkpoint=b.poll));b.poll()
                    if not actions:
                        node.pn=node.dn=inf;node.open=False
                    else:
                        edges=[]
                        for action in actions:
                            rt.push(action,checkpoint=b.poll)
                            try:edges.append((action,visit()))
                            finally:rt.pop()
                        # Install only complete frontiers, never partial ANDs.
                        node.edges=edges;update(node)
                for parent in reversed(ancestors):update(parent)
            finally:
                for _ in range(pushed):rt.pop()
        b.poll()
        if root.pn==0:return result(PROVEN_WIN,'finite_all_defense_certificate',certificate(root))
        return result(UNKNOWN,'no_forced_win_in_exhausted_tree' if root.dn==0 else 'depth_budget')
    except _Interrupted:return result(UNKNOWN,b.reason)
    except IncompleteAdjudicationHistoryError:return result(UNKNOWN,'incomplete_adjudication_history')
    except NotImplementedError:return result(UNKNOWN,'unsupported_runtime_semantics')
    finally:
        if rt is not None:rt.assert_balanced()
