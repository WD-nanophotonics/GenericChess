"""Experimental batched-public-Core forward model, independently Session-verified.

Search internals are immutable full GameState + exact GameRecord, NOT injected
GameSession snapshots. Board children use public legal_successors; declaration
assessment uses public Core and constructs a candidate Session result/record.
That model is NOT final authority: actual public GameSession replay verification
must qualify every returned witness before use. No product/default adoption.
An eager public board batch may overcompute and atomically overrun a deadline;
actual counts and time expose that cost. Claims still precede board generation.
"""
from dataclasses import dataclass,field
from time import perf_counter
from generic_chess.session.result import SessionStatus
from scripts.generic_win_proof import _Budget,_Interrupted,_same_state
from scripts.generic_session_win_proof import (SessionProofResult,SessionWinCertificate,
    SessionProofNode,SessionChoice,replay_bound)
from scripts.generic_win_proof import _ordered




from dataclasses import replace
from generic_chess.core.transition import legal_successors
from generic_chess.core.declarations import assess_declaration
from generic_chess.session.record import DeclarationRecord
from generic_chess.session.result import SessionResult,session_result_from_terminal

@dataclass(frozen=True)
class _Forward:
    compiled: object
    state: object
    record: object
    result: object
    def to_record(self):return self.record


def _children(current,b,cost):
    b.poll()
    for declaration in sorted(current.compiled.declarations,key=lambda d:d.declaration_id):
        if declaration.owner!=current.state.position.side_to_move:continue
        b.poll();a=assess_declaration(current.state,current.compiled,declaration.declaration_id);cost[1]+=1;b.poll()
        terminal=SessionResult(SessionStatus.DECLARATION,
            a.actor if a.outcome=='WIN' else 1-a.actor if a.outcome=='LOSS' else None,
            declaration_id=a.declaration_id,declared_by=a.actor,declaration_outcome=a.outcome,declaration_score=a.weighted_score)
        record=replace(current.record,schema_version=3 if current.record.initial_setup_key is not None else 2,
            declaration=DeclarationRecord(a.declaration_id,a.actor,a.outcome,a.weighted_score))
        yield SessionChoice('DECLARATION',declaration_id=a.declaration_id),_Forward(current.compiled,current.state,record,terminal)
    b.poll();batch=legal_successors(current.state,current.compiled);cost[0]+=len(batch);b.poll()
    order={action:i for i,action in enumerate(_ordered(action for action,_ in batch))}
    for action,state in sorted(batch,key=lambda pair:order[pair[0]]):
        b.poll();record=replace(current.record,actions=current.record.actions+(action,))
        yield SessionChoice('ACTION',action=action),_Forward(current.compiled,state,record,session_result_from_terminal(state.terminal_status))

@dataclass(frozen=True)
class SessionPNResult(SessionProofResult):
    frontiers: int=0
    transitions: int=0
    iterations: int=0
    peak_depth: int=0


@dataclass(frozen=True)
class SessionBatchPNResult(SessionPNResult):
    eager_board_successors: int=0
    claims_assessed: int=0


@dataclass
class _Node:
    session: object
    depth: int
    pn: float=1
    dn: float=1
    open: bool=True
    edges: list=field(default_factory=list)
    terminal: object|None=None


def prove_session_win_batch_pn(session,*,target=None,max_nodes=4096,seconds=1.,max_depth=8,
                         cancel=None,_clock=perf_counter,_children_factory=None):
    target=session.state.position.side_to_move if target is None else target
    if type(target) is not int or target not in (0,1):raise ValueError('invalid target')
    if type(max_depth) is not int or not 0<=max_depth<=128:raise ValueError('invalid depth')
    b=_Budget(max_nodes,seconds,cancel,_clock);inf=float('inf')
    frontiers=transitions=iterations=peak=0;cost=[0,0]
    root_state=session.state;root_record=session.to_record();root_result=session.result
    def result(status,reason,tree=None):
        cert=SessionWinCertificate(session.compiled.ruleset_fingerprint,root_record,root_state,target,tree) if tree is not None else None
        # No iterative completed-depth claim: peak_depth is separate metadata.
        return SessionBatchPNResult(status,cert,reason,b.nodes,b.elapsed(),0,frontiers,transitions,iterations,peak,*cost)
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
        root=visit(_Forward(session.compiled,root_state,root_record,root_result),0)
        while root.open and root.pn!=0 and root.dn!=0:
            b.poll();node=root;ancestors=[];iterations+=1
            while node.edges:
                eligible=[(i,c,n) for i,(c,n) in enumerate(node.edges) if n.open]
                assert eligible,'open session node without open child'
                own=node.session.state.position.side_to_move==target
                _,choice,child=min(eligible,key=lambda row:((row[2].pn if own else row[2].dn),row[0]))
                ancestors.append(node);node=child;b.poll()
            edges=[];frontiers+=1;own=node.session.state.position.side_to_move==target
            for choice,child in (_children if _children_factory is None else _children_factory)(node.session,b,cost):
                transitions+=1;b.poll()
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
