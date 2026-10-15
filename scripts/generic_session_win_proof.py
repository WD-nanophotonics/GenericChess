"""Optional finite rule-win trees over real GameSession ACTION/DECLARATION choices.

No board-action encoding of claims, material input, TT or state-only merging.
All owned declarations (including LOSS) are included at defender nodes. A
resignation is dominated in a forced-win query and omitted for either player.
RESTART/NO_CONTEST is terminal with no winner, never a win or continued game.
Only sessions reproducible from the public GameRecord are admitted. One public
submit/declare/replay is atomic; budgets poll before/after and report actual cost.
"""
from copy import copy
from dataclasses import dataclass
from time import perf_counter
from generic_chess.session.session import GameSession
from generic_chess.session.result import SessionStatus
from scripts.generic_win_proof import _Budget,_Interrupted,_same_state,_ordered,CertificateVerificationError


@dataclass(frozen=True)
class SessionChoice:
    kind: str
    action: object | None = None
    declaration_id: str | None = None


@dataclass(frozen=True)
class SessionProofNode:
    rank: int
    edges: tuple = ()
    terminal: object | None = None


@dataclass(frozen=True)
class SessionWinCertificate:
    ruleset_fingerprint: str
    root_record: object
    root_state: object
    target: int
    tree: SessionProofNode


@dataclass(frozen=True)
class SessionProofResult:
    status: str
    certificate: object | None
    reason: str
    nodes: int
    seconds: float
    completed_depth: int


def choices(session,budget):
    budget.poll()
    if session.result.status is not SessionStatus.ONGOING:return
    # An OR node may finish after a real claim without needing a board frontier.
    # Exhaustion at an AND node still includes every owned claim and board move.
    for declaration in sorted(session.compiled.declarations,key=lambda d:d.declaration_id):
        budget.poll()
        if declaration.owner==session.state.position.side_to_move:
            yield SessionChoice('DECLARATION',declaration_id=declaration.declaration_id)
    budget.poll()
    actions=_ordered(session.legal_actions());budget.poll()
    for action in actions:
        budget.poll();yield SessionChoice('ACTION',action=action)


def execute(session,choice):
    if not isinstance(choice,SessionChoice):raise ValueError('typed choice required')
    if choice.kind=='ACTION' and choice.action is not None and choice.declaration_id is None:
        session.submit(choice.action)
    elif choice.kind=='DECLARATION' and choice.action is None and isinstance(choice.declaration_id,str):
        session.declare(choice.declaration_id)
    else:raise ValueError('invalid or mixed session choice')
    return session.result


def replay_bound(session):
    clone=GameSession.replay(session.compiled,session.to_record())
    if not _same_state(clone.state,session.state) or clone.result!=session.result:
        raise ValueError('session record does not bind authoritative state/result')
    return clone


def prove_session_win(session,*,target=None,max_nodes=4096,seconds=1.,max_depth=8,cancel=None,_clock=perf_counter):
    target=session.state.position.side_to_move if target is None else target
    if type(target) is not int or target not in (0,1):raise ValueError('invalid target')
    if type(max_depth) is not int or not 0<=max_depth<=128:raise ValueError('invalid depth')
    b=_Budget(max_nodes,seconds,cancel,_clock);completed=0
    root_record=session.to_record();root_state=session.state;root_result=session.result
    def out(status,reason,node=None):
        cert=SessionWinCertificate(session.compiled.ruleset_fingerprint,root_record,root_state,target,node) if node is not None else None
        return SessionProofResult(status,cert,reason,b.nodes,b.elapsed(),completed)
    def search(current,depth):
        b.visit();result=current.result;b.poll()
        if result.status is not SessionStatus.ONGOING:
            return (True,SessionProofNode(0,terminal=result)) if result.winner==target else (False,None)
        if depth==0:return None,None
        own=current.state.position.side_to_move==target;edges=[];unknown=False
        for choice in choices(current,b):
            b.poll();child=copy(current);execute(child,choice);b.poll()
            value,node=search(child,depth-1)
            if own and value is True:return True,SessionProofNode(node.rank+1,((choice,node),))
            if not own and value is False:return False,None
            unknown|=value is None
            if node is not None:edges.append((choice,node))
        if unknown:return None,None
        if own or not edges:return False,None
        return True,SessionProofNode(1+max(n.rank for _,n in edges),tuple(edges))
    try:
        b.poll();replay_bound(session);b.poll()
        if root_result.status is not SessionStatus.ONGOING:return out('ALREADY_TERMINAL','actual_session_terminal')
        for depth in range(max_depth+1):
            value,node=search(session,depth);b.poll();completed=depth
            if value is True:return out('PROVEN_WIN','finite_session_all_defense_certificate',node)
            if value is False:return out('UNKNOWN','no_forced_win_in_exhausted_tree')
        return out('UNKNOWN','depth_budget')
    except _Interrupted:return out('UNKNOWN',b.reason)
    except (NotImplementedError,ValueError):return out('UNKNOWN','unsupported_or_unreplayable_session')
    finally:
        assert _same_state(session.state,root_state) and session.to_record()==root_record and session.result==root_result


def verify_session_certificate(session,certificate,*,max_nodes=65536,seconds=1.,cancel=None,_clock=perf_counter):
    """Independent edge replay through GameSession.replay, not prover copies."""
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
            b.poll();child=GameSession.replay(current.compiled,current.to_record());b.poll()
            execute(child,choice);transitions+=1;b.poll()
            if not check(child,childnode):return False
        return node.rank==1+max(n.rank for _,n in node.edges)
    try:
        b.poll();replay_bound(session);b.poll()
        if (not isinstance(certificate,SessionWinCertificate) or type(certificate.target) is not int
            or certificate.target not in (0,1) or certificate.ruleset_fingerprint!=session.compiled.ruleset_fingerprint
            or not _same_state(certificate.root_record,session.to_record()) or not _same_state(certificate.root_state,session.state)):
            reason='root_binding_mismatch'
        else:
            valid=check(session,certificate.tree);b.poll()
            if not valid:reason='invalid_certificate'
    except _Interrupted:reason=b.reason
    except (NotImplementedError,ValueError,TypeError,AttributeError):reason='invalid_or_unsupported_session'
    return dict(verified=valid and reason=='verified',reason=reason,nodes=b.nodes,seconds=b.elapsed(),terminal_leaves=leaves,session_transitions=transitions)


class SessionStrategyCursor:
    def __init__(self,session,certificate,**kwargs):
        self.receipt=verify_session_certificate(session,certificate,**kwargs)
        if not self.receipt['verified']:raise CertificateVerificationError(self.receipt)
        self.certificate=certificate;self.state=session.state;self.record=session.to_record();self.node=certificate.tree

    def _bind(self,session):
        if (session.compiled.ruleset_fingerprint!=self.certificate.ruleset_fingerprint
            or not _same_state(session.to_record(),self.record) or not _same_state(session.state,self.state)):
            raise ValueError('session strategy state/record mismatch')

    def choose(self,session):
        self._bind(session)
        if session.result.status is not SessionStatus.ONGOING or session.state.position.side_to_move!=self.certificate.target or not self.node.edges:return None
        return self.node.edges[0][0]

    def observe(self,before,choice,after):
        """Observe ONE already committed public edge; never mutate either session.

        The owner executes once, then supplies immutable pre/post snapshots to
        every player. Replaying the expected edge checks the full record, Core
        history and Session-only result (claims need not change Core state).
        An invalid observation leaves this cursor untouched.
        """
        self._bind(before)
        matches=[n for c,n in self.node.edges if c==choice]
        if len(matches)!=1:raise ValueError('choice outside proved session strategy')
        expected=copy(before);execute(expected,choice)
        if (after.compiled.ruleset_fingerprint!=self.certificate.ruleset_fingerprint
            or not _same_state(expected.state,after.state)
            or not _same_state(expected.to_record(),after.to_record())
            or not _same_state(expected.result,after.result)):
            raise ValueError('committed session edge mismatch')
        self.state=after.state;self.record=after.to_record();self.node=matches[0]

    def commit(self,session,choice):
        self._bind(session);matches=[n for c,n in self.node.edges if c==choice]
        if len(matches)!=1:raise ValueError('choice outside proved session strategy')
        result=execute(session,choice);self.state=session.state;self.record=session.to_record();self.node=matches[0]
        return result
