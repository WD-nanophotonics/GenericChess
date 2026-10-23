"""Bind a supplied closed Position certificate to admitted full histories.

The verifier never expands its supplied domain: a missing actual successor
rejects it. A separate bounded producer can build one closure from explicitly
supplied frozen histories. Both reuse public Core and the existing repeat4/rank
lemma; neither samples rules or imports old scalar WDL labels.
"""
from __future__ import annotations
from collections import Counter,deque
from copy import copy
from dataclasses import replace
from pathlib import Path
import json
import time

from generic_chess.core.actions import action_to_dict
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import legal_successors
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_single_parity_truth import admit,domain
from scripts.leaper_explorer_truth import digest,save
from scripts.leaper_retrograde import fresh_state,attractor
from scripts.leaper_design import state_sha
from scripts.research_record import record_value
from scripts.leaper_microgames import role_stop_requested
from scripts.generic_session_win_proof import SessionChoice,SessionProofNode,SessionWinCertificate,verify_session_certificate
from scripts.generic_session_certificate_json import export_session_certificate


def compact(position):
    alphabet={(0,'K'):'1',(0,'A'):'2',(1,'K'):'3',(1,'A'):'4'}
    return [position.side_to_move,''.join('0'if p is None else alphabet[p.owner,p.current_type_id]for p in position.board)]


def expand(row,template):
    if (not isinstance(row,list)or len(row)!=2 or type(row[0])is not int or row[0]not in(0,1)
        or not isinstance(row[1],str)or len(row[1])!=16 or set(row[1])-set('01234')):
        raise ValueError('invalid compact physical position')
    alphabet={'1':(0,'K'),'2':(0,'A'),'3':(1,'K'),'4':(1,'A')}
    board=tuple(None if ch=='0'else Piece(*alphabet[ch],alphabet[ch][1])for ch in row[1])
    result=replace(template,board=board,side_to_move=row[0]);domain(result);return result


def build_supplied_domain(worlds,target_worlds,plan,source_packet_digest):
    """Bounded closure of supplied frozen K+A-vs-K histories, no selection.

    Different initial declarations require identical transition-affecting
    fields. The result is checked by check_domain, not transplanted WDL.
    """
    start=time.perf_counter();targets=[w for w in worlds if w['world']in target_worlds]
    if len(targets)!=len(target_worlds):raise ValueError('missing frozen input')
    first=targets[0];_,c,_=admit(first['rule'],require_parity=False);template=c.initial_position
    positions=[];indices={};queue=deque();counts=Counter()
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-start>=plan['graph_cap_seconds']:raise RuntimeError('SUPPLIED_GRAPH_TIME_UNKNOWN')
        if len(positions)>plan['physical_vertex_cap']or counts['Core_edges']>plan['Core_edge_cap']:raise RuntimeError('SUPPLIED_GRAPH_SIZE_UNKNOWN')
    def add(position):
        if position not in indices:
            indices[position]=len(positions);positions.append(position);queue.append(position);guard()
    dynamics=lambda raw:{k:v for k,v in raw.items()if k!='initial_position'}
    for w in targets:
        if dynamics(w['rule'])!=dynamics(first['rule']):raise ValueError('frozen input dynamics differ')
        _,tc,_=admit(w['rule'],require_parity=False)
        s=GameSession.replay(tc,deserialize_game_record(json.dumps(w['initial_record'])))
        if state_sha(s.state)!=digest(w['initial_state']):raise ValueError('source full history not bound')
        add(replace(s.state.position,ruleset_fingerprint=template.ruleset_fingerprint))
    while queue:
        guard();position=queue.popleft();domain(position);s=fresh_state(position,c);counts['Core_vertices']+=1
        if s.terminal_status.is_terminal:
            counts['terminal_'+s.terminal_status.status.value]+=1;continue
        for action,child in legal_successors(s,c):counts['Core_edges']+=1;add(child.position)
    return dict(format='leaper-existing-mask5-H64-closed-domain-v1',source_packet_digest=source_packet_digest,
        source_sha=plan['source_sha'],target_rule=first['rule'],target_worlds=list(target_worlds),
        positions=[compact(p)for p in positions],generation_counts=dict(counts),generation_seconds=time.perf_counter()-start,
        plan=plan,scope='Onlycompleteclosureofalready frozen PRIMARY mask5histories; not newrule/layout sampling, generalgenerator orpolicycampaign.')


def check_domain(certificate,worlds,*,seconds=180,annotate=False):
    """Reconstruct complete edges through actual target Core, no foreign ones."""
    start=time.perf_counter();raw=certificate['target_rule'];rule,c,parity=admit(raw,require_parity=False)
    template=GameSession(c).state.position
    targets=[w for w in worlds if w['world']in certificate['target_worlds']]
    if len(targets)!=len(certificate['target_worlds']):raise ValueError('missing target histories')
    # Initial setups may differ, but every transition-affecting field is equal.
    def dynamics(r):return {k:v for k,v in r.items()if k!='initial_position'}
    for w in targets:
        if dynamics(w['rule'])!=dynamics(raw):raise ValueError('target dynamic declaration mismatch')
    positions=[expand(p,template)for p in certificate['positions']]
    indices={p:i for i,p in enumerate(positions)}
    if len(indices)!=len(positions):raise ValueError('duplicate domain vertex')
    edges=[];actions=[];terms={};counts=Counter()
    for i,pos in enumerate(positions):
        if time.perf_counter()-start>=seconds:raise RuntimeError('REBIND_VERIFY_CAP_UNKNOWN')
        if i%128==0 and role_stop_requested():raise RuntimeError('USER_STOP')
        state=fresh_state(pos,c)
        if state.terminal_status.is_terminal:
            w=state.terminal_status.winner
            terms[i]=0 if w is None else 1 if w==pos.side_to_move else-1
            edges.append(());actions.append(())
            counts['terminal_'+state.terminal_status.status.value]+=1;continue
        children=[];choices=[]
        for ac,ch in legal_successors(state,c):
            if ch.position not in indices:raise ValueError('closure missing actual Core child')
            children.append(indices[ch.position]);choices.append(action_to_dict(ac));counts['Core_edges']+=1
        if not children:raise ValueError('ongoing vertex has no child')
        edges.append(tuple(children));actions.append(tuple(choices))
    # Semantic rebinding does not reuse source rank vectors. The actual target
    # graph is now certified complete. History-specific repetition sinks are
    # computed separately for each full incoming state.
    rows=[];decision_rows={};annotation_cache={}
    for w in targets:
        _,tc,_=admit(w['rule'],require_parity=False)
        if tc.ruleset_fingerprint!=w['fingerprint']:raise ValueError('target fingerprint mismatch')
        target=GameSession.replay(tc,deserialize_game_record(json.dumps(w['initial_record'])))
        domain(target.state.position)
        if state_sha(target.state)!=digest(w['initial_state']):raise ValueError('complete target state mismatch')
        pos=replace(target.state.position,ruleset_fingerprint=template.ruleset_fingerprint)
        if pos not in indices:raise ValueError('target outside supplied component')
        # A fingerprint changes repetition hashes. Map through physical
        # positions and regenerate keys with this target's compiled rule.
        target_keys={repetition_identity_key(replace(p,ruleset_fingerprint=tc.ruleset_fingerprint),tc):i
                     for i,p in enumerate(positions)}
        def annotate_prefix(session):
            """Conditional proof-path diagnostics, never a natural-policy mu."""
            hid=state_sha(session.state)
            if hid in decision_rows:return
            remaining=tc.max_ply-session.state.ply_count
            branches=[]
            for action,ch in legal_successors(session.state,tc):
                j=indices[replace(ch.position,ruleset_fingerprint=template.ruleset_fingerprint)]
                if ch.terminal_status.is_terminal:
                    winner=ch.terminal_status.winner
                    bv=0 if winner is None else 1 if winner==session.state.position.side_to_move else-1
                else:
                    bs=frozenset(target_keys[k]for k,n in ch.repetition_counts if n==3 and k in target_keys)
                    if bs not in annotation_cache:
                        draw=len(positions)
                        ee=[tuple(draw if k in bs and k not in terms else k for k in es)for es in edges]+[()]
                        annotation_cache[bs]=attractor(ee,terms|{draw:0})
                    vv,rr=annotation_cache[bs]
                    bv=-vv[j]if vv[j]and rr[j]<=remaining-1 else 0
                branches.append(dict(action=action_to_dict(action),wdl=bv,child_state_sha=state_sha(ch),
                    terminal=ch.terminal_status.status.value,immediate_target_win=ch.terminal_status.is_terminal and ch.terminal_status.winner==session.state.position.side_to_move))
            best=max(b['wdl']for b in branches)
            decision_rows[hid]=dict(id=hid,world=w['world'],fingerprint=tc.ruleset_fingerprint,
                record=record_value(session.to_record()),ply=session.state.ply_count,remaining=remaining,
                actor=session.state.position.side_to_move,value=best,fork=len({b['wdl']for b in branches})>1,
                immediate_win=any(b['immediate_target_win']for b in branches),actions=branches,
                scope='Existing selected all-defense proof prefix; conditional mechanistic support, not uniform/natural occupation, independent samples or training starts.')
        blocked={target_keys[k]for k,n in target.state.repetition_counts if n==3 and k in target_keys}
        if any(n>=4 for k,n in target.state.repetition_counts):raise ValueError('target already repeats to terminal')
        sink=len(positions)
        ee=[tuple(sink if j in blocked and j not in terms else j for j in es)for es in edges]+[()]
        values,ranks=attractor(ee,terms|{sink:0})
        def value(index,remaining):
            v=values[index];rank=ranks.get(index)
            return v if v and rank<=remaining else 0
        i=indices[pos];remaining=tc.max_ply-target.state.ply_count;v=value(i,remaining)
        branches=[];actual=list(legal_successors(target.state,tc))
        if len(actual)!=len(edges[i]):raise ValueError('history legality differs from admitted position dynamics')
        for ac,ch in actual:
            physical=replace(ch.position,ruleset_fingerprint=template.ruleset_fingerprint)
            j=indices[physical]
            if ch.terminal_status.is_terminal:
                winner=ch.terminal_status.winner
                bv=0 if winner is None else 1 if winner==target.state.position.side_to_move else-1
            else:
                # Child counts may create a new third-visited vertex. The
                # parent attractor suffices only for rank-decreasing decisive
                # paths. Recompute the child's sink set for exact action WDL.
                childblocked={target_keys[k]for k,n in ch.repetition_counts if n==3 and k in target_keys}
                ce=[tuple(sink if k in childblocked and k not in terms else k for k in es)for es in edges]+[()]
                cv,cr=attractor(ce,terms|{sink:0});rank=cr.get(j)
                bv=-cv[j]if cv[j]and rank<=remaining-1 else 0
            branches.append(dict(action=action_to_dict(ac),wdl=bv,child_state_sha=state_sha(ch)))
        if not target.state.terminal_status.is_terminal and v!=max(b['wdl']for b in branches):
            raise ValueError('rank-history action consistency failed')
        certificate_json=None;proof_receipt=None
        if v==1:
            winner=target.state.position.side_to_move;visited=0
            def tree(session,limit):
                nonlocal visited
                visited+=1
                if visited>8192 or time.perf_counter()-start>=seconds:
                    raise RuntimeError('GUIDED_CERTIFICATE_CAP_UNKNOWN')
                if session.result.status.value!='ongoing':
                    if session.result.winner!=winner:raise ValueError('rank path ended without target win')
                    return SessionProofNode(0,terminal=session.result)
                if annotate:annotate_prefix(session)
                index=indices[replace(session.state.position,ruleset_fingerprint=template.ruleset_fingerprint)]
                rank=ranks.get(index)
                if rank is None or not 0<rank<=limit:raise ValueError('rank failed to decrease')
                own=session.state.position.side_to_move==winner;branches=[]
                for action in session.legal_actions():
                    child=copy(session);child.submit(action)
                    j=indices[replace(child.state.position,ruleset_fingerprint=template.ruleset_fingerprint)]
                    if own and not(values[j]==-1 and ranks.get(j,rank)<rank):continue
                    node=tree(child,rank-1);branches.append((SessionChoice('ACTION',action=action),node))
                    if own:break
                if not branches:raise ValueError('rank strategy has no admissible continuation')
                return SessionProofNode(1+max(n.rank for _,n in branches),tuple(branches))
            proof=SessionWinCertificate(tc.ruleset_fingerprint,target.to_record(),target.state,winner,tree(target,remaining))
            proof_receipt=verify_session_certificate(target,proof,max_nodes=8192,seconds=30,cancel=role_stop_requested)
            if not proof_receipt['verified']:raise ValueError(('literal certificate failed',proof_receipt))
            certificate_json=export_session_certificate(target,proof,max_nodes=8192)
        rows.append(dict(world=w['world'],fingerprint=w['fingerprint'],state_sha=state_sha(target.state),
            initial_record=w['initial_record'],root_index=i,blocked=sorted(blocked),remaining=remaining,
            value=v,rank=ranks.get(i),fork=len({b['wdl']for b in branches})>1,actions=branches,
            literal_win_certificate=certificate_json,literal_verification=proof_receipt))
    result=dict(verified=True,vertices=len(positions),counts=dict(counts),rows=rows,
        certificate_digest=digest(certificate),seconds=time.perf_counter()-start,
        scope='Actual target Core closure reverified on supplied existing vertices, no expansion. Repeat4 incoming count3 sinks plus strictly decreasing decisive rank and actual remaining H64 clock. No arbitrary history quotient; no imported scalar oldWDL label.')
    if annotate:result['certificate_decisions']=list(decision_rows.values())
    return result
