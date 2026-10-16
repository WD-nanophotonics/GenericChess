"""Opt-in paid graph/full-history/normal contract; no fixed learner adoption.

Graph CANDIDATE never becomes PROVEN_WIN. The returned action is usable only
following independent graph validation AND current cursor validation. All
phases share one caller clock. Work units remain separate; no mixed nodes sum.
"""
from dataclasses import dataclass
from time import perf_counter
from generic_chess.session.result import SessionStatus
from scripts.generic_win_proof import _Budget,_Interrupted,_same_state,CertificateVerificationError
from scripts.generic_session_win_proof import (SessionChoice,SessionStrategyCursor,
    replay_bound,choices,verify_session_certificate)
from scripts.generic_session_proof_player import SessionDecision
from scripts.generic_session_phase_player import PhaseLimits
from scripts.generic_session_win_proof_batch_pn import prove_session_win_batch_pn
from results.dev_aux.task2148.normal import SessionCompleteMaterialSearch
from results.dev_aux.task2199.semantic_graph import (scope_reason,prove_graph,
    verify_graph,GraphStrategyCursor)

class PaidCurrentGraphCursor(GraphStrategyCursor):
    """Same current verifier/positions, retaining rejected work receipts too."""
    def __init__(self,session,certificate,**limits):
        receipt,positions=verify_graph(session,certificate,return_positions=True,**limits)
        if not receipt['verified']:raise CertificateVerificationError(receipt)
        self.certificate=certificate;self.receipt=receipt;self.positions=positions
        self.index=0;self.record=session.to_record();self.state=session.state;self.result=session.result

@dataclass(frozen=True)
class GraphPhaseDecision(SessionDecision):
    graph_positions:int=0
    graph_expanded:int=0
    graph_transitions:int=0
    graph_verifier_visits:int=0
    tree_verifier_visits:int=0
    raw_proofs:tuple=()
    verification_receipts:tuple=()
    phase_limits:tuple=()
    fallback_admission_seconds:float=0.
    cursor_kind:str|None=None
    @property
    def nodes(self):
        raise AttributeError('Distinct graph positions/expansions, tree visits, verifier visits and normal visits; no mixed-unit nodes total')

class PaidGraphPhasePlayer:
    def __init__(self,compiled,evaluate,*,limits=PhaseLimits(),max_depth=3,
                 proof_depth=96,graph_positions=8192,graph_edges=65536,
                 graph_enabled=True,proof_enabled=True):
        if not isinstance(limits,PhaseLimits):raise ValueError('typed phase limits required')
        if type(proof_depth)is not int or not 0<=proof_depth<=128:raise ValueError('invalid proof depth')
        for cap in(graph_positions,graph_edges):
            if type(cap)is not int or cap<0:raise ValueError('invalid graph limit')
        self.compiled=compiled;self.limits=limits;self.proof_depth=proof_depth
        self.graph_positions=graph_positions;self.graph_edges=graph_edges
        self.graph_enabled=graph_enabled;self.proof_enabled=proof_enabled
        self.normal=SessionCompleteMaterialSearch(compiled,evaluate,max_depth=max_depth)
        self.graph_search=prove_graph;self.tree_search=prove_session_win_batch_pn
        self.cursor=None;self.cursor_kind=None
    def observe(self,before,choice,after):
        if self.cursor is not None:
            try:self.cursor.observe(before,choice,after)
            except ValueError:self.cursor=None;self.cursor_kind=None
    def choose(self,session,*,max_nodes=4096,seconds=1.,cancel=None,
               allow_new_proof=True,_clock=perf_counter):
        cancelled=False
        def latched_cancel():
            nonlocal cancelled
            if cancel is not None and cancel():cancelled=True
            return cancelled
        b=_Budget(max_nodes,seconds,latched_cancel,_clock)
        record,state,result=session.to_record(),session.state,session.result
        choice=None;source='NO_CHOICE';reason='disabled';cause='depth_budget';rank=None
        pn=gn=ge=gt=gv=tv=search_nodes=0
        admission=proof_time=verification_time=normal_time=fallback_time=0.
        raw=[];checks=[];normal=None;fallback=None
        limits=self.limits
        phases=(('normal_nodes',max_nodes),('tree_proof_visits',limits.proof_nodes),
            ('graph_positions',self.graph_positions),('graph_edges',self.graph_edges),
            ('verification_visits_per_check',limits.verification_nodes),
            ('total_seconds',seconds),('proof_seconds_shared',limits.proof_seconds),
            ('verification_seconds_shared',limits.verification_seconds),
            ('normal_seconds',limits.normal_seconds))
        def left():return max(0.,seconds-b.elapsed())
        def proof_left():return max(0.,min(limits.proof_seconds-proof_time,left()))
        def verification_left():return max(0.,min(limits.verification_seconds-verification_time,left()))
        def rank_of(cur,kind):return cur.certificate.nodes[cur.index].rank if kind=='GRAPH'else cur.node.rank
        def qualify(cert,kind):
            nonlocal verification_time,gv,tv,reason
            verify=verify_graph if kind=='GRAPH'else verify_session_certificate
            start=_clock();receipt=verify(session,cert,max_nodes=limits.verification_nodes,
                seconds=verification_left(),cancel=latched_cancel,_clock=_clock)
            verification_time+=_clock()-start;checks.append((kind,'INDEPENDENT',receipt))
            if kind=='GRAPH':gv+=receipt['nodes']
            else:tv+=receipt['nodes']
            b.poll()
            if not receipt['verified']:reason='verification_'+receipt['reason'];return None
            # Cursor admission is deliberately repeated and paid. A historical
            # positive receipt never substitutes for current context validation.
            start=_clock()
            try:
                cls=PaidCurrentGraphCursor if kind=='GRAPH'else SessionStrategyCursor
                cur=cls(session,cert,max_nodes=limits.verification_nodes,
                    seconds=verification_left(),cancel=latched_cancel,_clock=_clock)
            except ValueError as error:
                verification_time+=_clock()-start
                receipt=getattr(error,'receipt',None)
                if receipt is not None:
                    checks.append((kind,'CURSOR_REJECTED',receipt))
                    if kind=='GRAPH':gv+=receipt['nodes']
                    else:tv+=receipt['nodes']
                else:checks.append((kind,'CURSOR_REJECTED',dict(reason=str(error),nodes=None)))
                reason='current_cursor_rejected';b.poll();return None
            verification_time+=_clock()-start;checks.append((kind,'CURRENT_CURSOR',cur.receipt))
            if kind=='GRAPH':gv+=cur.receipt['nodes']
            else:tv+=cur.receipt['nodes']
            b.poll();return cur
        try:
            b.poll()
            if session.compiled.ruleset_fingerprint!=self.compiled.ruleset_fingerprint:raise ValueError('foreign_rules')
            start=_clock();replay_bound(session);admission=_clock()-start;b.poll()
            if result.status is not SessionStatus.ONGOING:source='TERMINAL';cause='actual_session_terminal'
            else:
                if self.proof_enabled and self.cursor is not None:
                    try:selected=self.cursor.choose(session)
                    except ValueError:self.cursor=None;self.cursor_kind=None;selected=None
                    b.poll()
                    if selected is not None:
                        choice=selected;source='VERIFIED_'+self.cursor_kind+'_CONTINUATION'
                        reason='current_context_checked';rank=rank_of(self.cursor,self.cursor_kind);cause='certificate'
                if choice is None:
                    start=_clock()
                    # Pay one fully legal typed fallback, including declarations.
                    for candidate in choices(session,b):fallback=candidate;break
                    fallback_time=_clock()-start;b.poll()
                    if self.proof_enabled and allow_new_proof:
                        guard=scope_reason(session.compiled)if self.graph_enabled else'graph_disabled'
                        if guard is None and proof_left()>0:
                            start=_clock();r=self.graph_search(session,max_nodes=self.graph_positions,
                                max_edges=self.graph_edges,seconds=proof_left(),max_depth=self.proof_depth,
                                cancel=latched_cancel,_clock=_clock)
                            proof_time+=_clock()-start;gn=r.positions;ge=r.expanded;gt=r.transitions
                            raw.append(('GRAPH',r.status,r.reason));reason=r.reason;b.poll()
                            if r.status=='CANDIDATE_WIN_GRAPH'and r.certificate is not None:
                                cur=qualify(r.certificate,'GRAPH')
                                if cur is not None:
                                    selected=cur.choose(session);b.poll()
                                    if selected is not None:
                                        self.cursor=cur;self.cursor_kind='GRAPH';choice=selected
                                        source='VERIFIED_GRAPH_STRATEGY';rank=rank_of(cur,'GRAPH');cause='certificate'
                        elif guard is not None:raw.append(('GRAPH','NOT_ADMITTED',guard));reason=guard
                        # Scope/invalid/unfinished graph cannot suppress full-history
                        # proof where time remains. It receives ONLY shared remainder.
                        if choice is None and proof_left()>0:
                            start=_clock();r=self.tree_search(session,max_nodes=limits.proof_nodes,
                                seconds=proof_left(),max_depth=self.proof_depth,cancel=latched_cancel,_clock=_clock)
                            proof_time+=_clock()-start;pn=r.nodes;raw.append(('FULL_HISTORY',r.status,r.reason));reason=r.reason;b.poll()
                            if r.status=='PROVEN_WIN'and r.certificate is not None:
                                cur=qualify(r.certificate,'FULL_HISTORY')
                                if cur is not None:
                                    selected=cur.choose(session);b.poll()
                                    if selected is not None:
                                        self.cursor=cur;self.cursor_kind='FULL_HISTORY';choice=selected
                                        source='VERIFIED_FULL_HISTORY_STRATEGY';rank=rank_of(cur,'FULL_HISTORY');cause='certificate'
                    elif self.proof_enabled:reason='new_proof_disabled'
                    if choice is None:
                        b.poll();start=_clock()
                        normal=self.normal.choose(session,max_nodes=max_nodes,
                            seconds=min(limits.normal_seconds,left()),cancel=latched_cancel,_clock=_clock)
                        normal_time=_clock()-start;search_nodes=normal.nodes
                        choice=normal.choice;source=normal.source;cause=normal.exit_cause;b.poll()
                    if choice is None and fallback is not None and cause in('time_budget','node_budget'):
                        choice=fallback;source='PRECOMPUTED_TYPED_LEGAL_FALLBACK'
        except _Interrupted:
            cause=b.reason
            if cause!='cancelled'and choice is None and fallback is not None:
                choice=fallback;source='PRECOMPUTED_TYPED_LEGAL_FALLBACK'
        except(ValueError,NotImplementedError)as error:
            reason=str(error);cause='unsupported_or_unreplayable_session';choice=None
        finally:
            assert _same_state(session.state,state)and _same_state(session.to_record(),record)and session.result==result
        # One pulse stays latched even if a provider already swallowed interruption.
        if latched_cancel():choice=None;rank=None;cause='cancelled'
        return GraphPhaseDecision(choice,source,reason,pn,gv+tv,search_nodes,b.elapsed(),cause,rank,
            record,state,result,normal,admission,proof_time,verification_time,normal_time,
            (),gn,ge,gt,gv,tv,tuple(raw),tuple(checks),phases,fallback_time,self.cursor_kind)
