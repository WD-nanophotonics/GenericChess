"""Small all-defense proofs for the observed one-orbit defensive escape."""
from copy import copy
from collections import Counter
from pathlib import Path
import json,time
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_h6_initial_truth import admit,history_solver
from scripts.leaper_cooperative_certificate import decode_position
from scripts.generic_session_win_proof import SessionChoice,SessionProofNode,SessionWinCertificate,verify_session_certificate
from scripts.generic_session_certificate_json import export_session_certificate,decode_session_certificate
from scripts.leaper_design import physical_action_key,state_sha
from scripts.research_record import record_value
from generic_chess.core.actions import action_to_dict
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_microgames import role_stop_requested


def extract(directory,adjacency,*,seconds=120):
    start=time.perf_counter();directory=Path(directory);source=load(directory/'inputs.json.gz');output=[]
    for pair in adjacency['pairs']:
        selected=[r for r in pair['rows']if r['left_WDL']==-1 and r['right_WDL']==0]
        family=next(f for f in source['families']if f['family']==pair['left_family'])
        first=next(r for r in source['rows']if r['family']==family['family']);c=admit(family,first)
        domain=load(directory/f"domain{family['family']}.json.gz");positions=[decode_position(p,c.initial_position)for p in domain['positions']];indices={p:i for i,p in enumerate(positions)}
        edges=domain['edges'];terms={int(k):v for k,v in domain['terminals'].items()};solve,work=history_solver(edges,terms,[p.side_to_move for p in positions],lambda n:None)
        for row in selected:
            root=GameSession.replay(c,deserialize_game_record(json.dumps(row['left_record'])));charged=0;target=1
            def node(session,remaining,prior):
                nonlocal charged
                if time.perf_counter()-start>=seconds or charged>=8192:raise RuntimeError('EXTRACT_CAP_UNKNOWN')
                charged+=1
                if session.result.status.value!='ongoing':
                    if session.result.winner!=target:raise ValueError('strategy did not reach actual target win')
                    return SessionProofNode(0,terminal=session.result)
                if remaining<=0:raise ValueError('unclosed strategy at H6')
                i=indices[session.state.position];visited=tuple(sorted((*prior,i)));branches=[]
                own=session.state.position.side_to_move==target
                for action in session.legal_actions():
                    child=copy(session);child.submit(action);j=indices[child.state.position]
                    if own and solve(j,remaining-1,visited)[0]!=-1:continue
                    sub=node(child,remaining-1,visited);branches.append((SessionChoice('ACTION',action=action),sub))
                    if own:break
                if not branches:raise ValueError('no rank-consistent strategy edge')
                return SessionProofNode(1+max(n.rank for a,n in branches),tuple(branches))
            certificate=SessionWinCertificate(c.ruleset_fingerprint,root.to_record(),root.state,target,node(root,6,()))
            receipt=verify_session_certificate(root,certificate,max_nodes=8192,seconds=30)
            if not receipt['verified']:raise ValueError('independent literal certificate failed')
            output.append(dict(left_id=row['left_id'],right_id=row['right_id'],placement=row['placement'],
                left_forced_loss_certificate=export_session_certificate(root,certificate,max_nodes=8192),
                independent_verification=receipt,right_draw_escapes=row['new_best_escapes']))
    return dict(format='leaper-H6-onebit-literal-certificates-v1',adjacency_digest=digest(adjacency),rows=output,
        verified_nodes=sum(r['independent_verification']['nodes']for r in output),
        verified_transitions=sum(r['independent_verification']['session_transitions']for r in output),
        seconds=time.perf_counter()-start,scope='All16observed LOSS-to-DRAW roots: actual oldrule full-history all-defense mate certificates forseat1; newrule literal capture reaches independently closed no-mate subdomain. Proof extraction from already solved labels,not a newsearch/Player campaign.')


def physical_position(position):
    """Cross-rule comparison coordinate, never an authoritative state ID."""
    raw=record_value(position)
    raw.pop('ruleset_fingerprint')
    return raw


def physical_actions(session):
    """Only admitted plain-Leaper actions; preserve each rule's public object."""
    out={}
    for action in session.legal_actions():
        key=physical_action_key(action,{'K':'K','A':'A','B':'B'})
        if key in out:raise ValueError('ambiguous physical action mapping')
        out[key]=action
    return out


def repetition_partition(session):
    """Compare equality patterns, not hashes belonging to different rules."""
    first={}
    return [first.setdefault(h.position_key,i) for i,h in enumerate(session.state.history)]


def dual_replay(directory,certificates,adjacency,*,seconds=120,max_nodes=8192):
    """Rebind a finite existing proof, without finding any new strategy edges.

    Every prefix is replayed from its own complete GameRecord. A mapped edge
    is selected from that rule's actual legal actions, never by editing an
    opaque pattern/geometry ID. The existing independent verifier decides if
    a rebound subtree still covers all defender choices and actual terminals.
    Physical prefix equality does not assert equivalence of the two games.
    """
    tick=time.perf_counter();directory=Path(directory)
    source=load(directory/'inputs.json.gz');counts=Counter();output=[]
    if certificates['adjacency_digest']!=digest(adjacency):raise ValueError('certificate adjacency mismatch')
    roots={r['state_sha256']:r for r in source['rows']}
    families={f['family']:f for f in source['families']}
    pair_rows={r['left_id']:(pair,r) for pair in adjacency['pairs'] for r in pair['rows']}
    expected={r['left_id'] for _,r in pair_rows.values() if r['left_WDL']==-1 and r['right_WDL']==0}
    actual=[r['left_id']for r in certificates['rows']]
    if len(actual)!=len(set(actual))or set(actual)!=expected:raise ValueError('source certificate support changed')
    for row in certificates['rows']:
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds:raise RuntimeError('DUAL_REPLAY_CAP_UNKNOWN')
        pair,paired=pair_rows[row['left_id']]
        if row['right_id']!=paired['right_id']or row['placement']!=paired['placement']:
            raise ValueError('pair/root binding mismatch')
        leftsource=roots[row['left_id']];rightsource=roots[row['right_id']]
        lc=admit(families[leftsource['family']],leftsource)
        rc=admit(families[rightsource['family']],rightsource)
        left,cert=decode_session_certificate(lc,row['left_forced_loss_certificate'],max_nodes=max_nodes)
        receipt=verify_session_certificate(left,cert,max_nodes=max_nodes,seconds=seconds)
        if not receipt['verified']or state_sha(left.state)!=row['left_id']:raise ValueError('source certificate not valid')
        right=GameSession.replay(rc,deserialize_game_record(json.dumps(rightsource['full_record'])))
        if state_sha(right.state)!=row['right_id']:raise ValueError('right full history mismatch')
        nodes=[]
        def visit(ls,rs,node,path,physical_prefix):
            counts['prefix_nodes']+=1
            if role_stop_requested():raise RuntimeError('USER_STOP')
            if counts['prefix_nodes']>max_nodes or time.perf_counter()-tick>=seconds:raise RuntimeError('DUAL_REPLAY_CAP_UNKNOWN')
            # Replay full records afresh: no source history is overwritten.
            ls=GameSession.replay(lc,ls.to_record());rs=GameSession.replay(rc,rs.to_record())
            if physical_position(ls.state.position)!=physical_position(rs.state.position):raise ValueError('mapped physical transition differs')
            same_rep=repetition_partition(ls)==repetition_partition(rs)
            same_clock=ls.state.ply_count==rs.state.ply_count
            if not same_rep or not same_clock:raise ValueError('mapped history/clock diverges')
            la=physical_actions(ls);ra=physical_actions(rs);mapped=[];missing=[]
            for choice,childnode in node.edges:
                if choice.kind!='ACTION':raise ValueError('plain-Leaper proof contains declaration')
                key=physical_action_key(choice.action,{'K':'K','A':'A','B':'B'})
                if key not in la or la[key]!=choice.action:raise ValueError('source edge not its actual public action')
                if key not in ra:
                    missing.append(list(key));continue
                ll=copy(ls);rr=copy(rs);ll.submit(la[key]);rr.submit(ra[key]);counts['paired_transitions']+=1
                if la[key]!=ra[key]:counts['public_action_rebindings']+=1
                sub=visit(ll,rr,childnode,path+[list(key)],physical_prefix+[physical_position(ll.state.position)])
                if sub is not None:mapped.append((SessionChoice('ACTION',action=ra[key]),sub))
            rebound=None
            if not missing and len(mapped)==len(node.edges):
                rebound=SessionProofNode(node.rank,tuple(mapped),node.terminal)
            if rebound is None:
                check=dict(verified=False,reason='unmappable_source_edges',nodes=0,session_transitions=0)
            else:
                reboundcert=SessionWinCertificate(rc.ruleset_fingerprint,rs.to_record(),rs.state,cert.target,rebound)
                check=verify_session_certificate(rs,reboundcert,max_nodes=max_nodes,seconds=seconds)
            added=sorted(set(ra)-set(la));removed=sorted(set(la)-set(ra))
            counts['added_legal_actions']+=len(added);counts['removed_legal_actions']+=len(removed)
            counts['rebound_subtree_verified']+=check['verified']
            counts['same_terminal_result']+=ls.result==rs.result
            counts['same_check_history']+=[h.gave_check for h in ls.state.history]==[h.gave_check for h in rs.state.history]
            nodes.append(dict(prefix=path,ply=ls.state.ply_count,rank=node.rank,
                left_record=record_value(ls.to_record()),right_record=record_value(rs.to_record()),
                left_state_sha=state_sha(ls.state),right_state_sha=state_sha(rs.state),
                physical_history_sha=digest(physical_prefix),repetition_partition=repetition_partition(ls),
                right_repetition_partition=repetition_partition(rs),same_clock=same_clock,
                left_actor_history=[h.actor for h in ls.state.history],right_actor_history=[h.actor for h in rs.state.history],
                left_check_history=[h.gave_check for h in ls.state.history],right_check_history=[h.gave_check for h in rs.state.history],
                left_terminal=record_value(ls.result),right_terminal=record_value(rs.result),
                added_actions=[action_to_dict(ra[k])for k in added],removed_actions=[action_to_dict(la[k])for k in removed],
                missing_proof_actions=missing,rebound_verified=check['verified'],rebound_reason=check['reason'],
                rebound_certificate=export_session_certificate(rs,reboundcert,max_nodes=max_nodes) if rebound is not None else None))
            return rebound
        mapped=visit(left,right,cert.tree,[],[physical_position(left.state.position)])
        direct=verify_session_certificate(right,cert,max_nodes=max_nodes,seconds=seconds)
        if direct['verified']or direct['reason']!='root_binding_mismatch':raise ValueError('cross-rule source cert accepted')
        output.append(dict(left_id=row['left_id'],right_id=row['right_id'],placement=row['placement'],
            source_verified=True,direct_transfer_reason=direct['reason'],nodes=sorted(nodes,key=lambda n:(n['ply'],n['prefix'])),
            root_rebound_verified=nodes[-1]['rebound_verified']))
    return dict(format='leaper-H6-pair-prefix-rebinding-v1',source_certificate_digest=digest(certificates),
        adjacency_digest=digest(adjacency),counts=dict(counts),rows=output,seconds=time.perf_counter()-tick,
        scope='Only existing16certificate trees/80prefixes/64edges, no new strategy search or graph. Each rule retains its own literal public actions, full records and state hashes. Rebound subtree verification is conditional at that exact reachable prefix, not root game equivalence, global history quotient or general monotonicity.')


if __name__=='__main__':
    import argparse
    cli=argparse.ArgumentParser();cli.add_argument('--directory',required=True);cli.add_argument('--adjacency',required=True);cli.add_argument('--output',required=True);cli.add_argument('--dual-certificates');a=cli.parse_args()
    r=dual_replay(a.directory,load(a.dual_certificates),load(a.adjacency)) if a.dual_certificates else extract(a.directory,load(a.adjacency))
    save(a.output,r);print(json.dumps({k:v for k,v in r.items()if k!='rows'}))
