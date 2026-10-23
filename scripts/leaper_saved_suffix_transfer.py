"""Propose saved mate suffixes at other histories of the identical Position.

Position equality proposes a path, never transfers a WDL or truth label. Each
positive must replay from its target full prehistory through actual Core and
reach a decisive terminal before any repetition/stalemate/clock barrier.
Failed paths remain UNKNOWN. No new Player, rule, layout, or graph expansion.
"""
from collections import Counter
from copy import copy,deepcopy
import json
import time

from generic_chess.core.actions import action_from_dict
from generic_chess.core.errors import IllegalActionError
from generic_chess.core.identity import position_identity_key
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_design import state_sha
from scripts.leaper_explorer_truth import digest
from scripts.leaper_cooperative_certificate import root_session
from scripts.leaper_microgames import role_stop_requested


def try_witness(session, actions):
    """Return only the actual terminal observation, with no absence inference."""
    s=copy(session);executed=0
    for raw in actions:
        if s.state.terminal_status.is_terminal:
            break
        try:s.submit(action_from_dict(raw))
        except (IllegalActionError,ValueError)as error:
            return dict(proved=False,status='ILLEGAL_SAVED_SUFFIX_UNKNOWN',executed=executed,error=type(error).__name__)
        executed+=1
    t=s.state.terminal_status
    proved=t.is_terminal and t.winner is not None
    return dict(proved=proved,status=t.status.value,terminal_winner=t.winner,executed=executed,
                final_ply=s.state.ply_count,final_history_id=state_sha(s.state))


def erase_cycles(positions, actions):
    """Chronological loop erasure of a recorded Position path, no new moves."""
    if len(positions)!=len(actions)+1:raise ValueError('path lengths mismatch')
    stack=[positions[0]];indices=[];where={positions[0]:0}
    for i,child in enumerate(positions[1:]):
        if child in where:
            j=where[child]
            for removed in stack[j+1:]:del where[removed]
            stack=stack[:j+1];indices=indices[:j]
        else:
            indices.append(i);where[child]=len(stack);stack.append(child)
    return [actions[i]for i in indices],indices


def shorten_run(truth, proposals):
    """Separate method control on exactly the original frozen proposals."""
    if proposals['input_digest']!=digest(truth):raise ValueError('proposal source mismatch')
    from scripts.leaper_cooperative_truth import admit
    start=time.perf_counter();compiled={};rows=[];stats=Counter();status='COMPLETE'
    for q in proposals['rows']:
        if role_stop_requested():status='USER_STOP';break
        if time.perf_counter()-start>=proposals['caps']['proof_seconds']:status='PROOF_CAP_UNKNOWN';break
        if len(rows)>=proposals['caps']['proposals']:status='PROPOSAL_CAP_UNKNOWN';break
        fp=q['fingerprint']
        if fp not in compiled:
            rule=ruleset_from_dict(truth['rules'][fp]);compiled[fp]=compile_rule(rule);admit(rule,compiled[fp])
        r,s=root_session(truth,q['id'],compiled[fp])
        record=truth['records'][q['source_record_id']]
        source=GameSession.replay(compiled[fp],deserialize_game_record(json.dumps(record|dict(actions=record['actions'][:q['source_ply']]))))
        if state_sha(source.state)!=q['source_id']or source.state.position!=s.state.position:
            raise ValueError('source mismatch')
        original=record['actions'][q['source_ply']:];positions=[source.state.position]
        for action in original:
            source.submit(action_from_dict(action));positions.append(source.state.position);stats['source_suffix_replay_edges']+=1
        assert source.state.terminal_status.winner is not None
        witness,indices=erase_cycles(positions,original)
        result=try_witness(s,witness)
        rows.append(dict(id=q['id'],fingerprint=fp,proposal=q,witness=witness,
                         retained_source_indices=indices,observation=result))
        stats['original_actions']+=len(original);stats['proposed_actions']+=len(witness)
        stats['literal_actions']+=result['executed'];stats['proved'if result['proved']else'unknown']+=1
    return dict(format='leaper-saved-suffix-proofs-v1',method='chronological_loop_erasure',
                input_digest=digest(truth),proposal_digest=digest(proposals),rows=rows,status=status,
                unstarted=[q['id']for q in proposals['rows'][len(rows):]],counts=dict(stats),seconds=time.perf_counter()-start,
                scope='Separate claim-sufficient method on identical frozen165proposals. Only deletes loops from saved source paths and replays targets. Original raw-path failures stay closed/UNKNOWN. No search, graph, rule, Player or TRAIN starts.')


def prepare(truth, *, seconds=180):
    start=time.perf_counter();last=0.;stats=Counter()
    roots={r['id']:r for r in truth['roots']};targets={};witnesses={}
    compiled={fp:compile_rule(ruleset_from_dict(raw))for fp,raw in truth['rules'].items()}
    for rid,record in truth['records'].items():
        c=compiled[record['ruleset_fingerprint']]
        s=GameSession.replay(c,deserialize_game_record(json.dumps(record|dict(actions=[]))))
        prefixes=[]
        for ply,action in enumerate(record['actions']):
            now=time.perf_counter()
            if now-start>=seconds:raise RuntimeError('PREPARATION_CAP_UNKNOWN')
            if now-last>=.2:
                last=now
                if role_stop_requested():raise RuntimeError('USER_STOP')
            hid=state_sha(s.state);pos=s.state.position
            prefixes.append((hid,pos,ply))
            if roots[hid]['cooperative_decisive']is None:targets[hid]=pos
            s.submit(action_from_dict(action));stats['source_actions']+=1
        if s.result.winner is not None:
            stats['decisive_source_records']+=1
            for hid,pos,ply in prefixes:
                proposal=dict(source_record_id=rid,source_id=hid,source_ply=ply,
                              length=len(record['actions'])-ply,winner=s.result.winner)
                old=witnesses.get(pos)
                order=lambda q:(q['length'],q['source_record_id'],q['source_ply'])
                if old is None or order(proposal)<order(old):witnesses[pos]=proposal
        stats['source_records']+=1
    rows=[]
    for hid,pos in sorted(targets.items()):
        if pos not in witnesses:continue
        r=roots[hid];w=witnesses[pos]
        if w['length']>r['rule_remaining']:
            stats['same_position_suffix_exceeds_remaining']+=1;continue
        rows.append(dict(id=hid,fingerprint=r['fingerprint'],position_key=position_identity_key(pos,compiled[r['fingerprint']]),**w))
    return dict(format='leaper-saved-suffix-proposals-v1',input_digest=digest(truth),rows=rows,
                counts=dict(stats),unknown_targets=len(targets),proposals=len(rows),seconds=time.perf_counter()-start,
                selection='All cooperation-UNKNOWN existing histories with an identical-Position original mate suffix fitting remaining rule plies. One shortest saved suffix per Position, deterministic tie-break. No truth-selected TRAIN root or new play layout.',
                caps=dict(proof_seconds=180,proposals=2000),
                scope='Proposals only; no truth inference or history quotient. Clock/repetition and all legal actions are actual Core authority during target replay.')


def run(truth, proposals):
    if proposals['input_digest']!=digest(truth):raise ValueError('proposal source mismatch')
    start=time.perf_counter();compiled={};rows=[];status='COMPLETE';stats=Counter()
    for q in proposals['rows']:
        if role_stop_requested():status='USER_STOP';break
        if time.perf_counter()-start>=proposals['caps']['proof_seconds']:status='PROOF_CAP_UNKNOWN';break
        if len(rows)>=proposals['caps']['proposals']:status='PROPOSAL_CAP_UNKNOWN';break
        fp=q['fingerprint']
        if fp not in compiled:compiled[fp]=compile_rule(ruleset_from_dict(truth['rules'][fp]))
        r,s=root_session(truth,q['id'],compiled[fp])
        if r['cooperative_decisive']is not None:raise ValueError('target is not unknown')
        record=truth['records'][q['source_record_id']]
        if record['ruleset_fingerprint']!=fp:raise ValueError('source rule mismatch')
        source=GameSession.replay(compiled[fp],deserialize_game_record(json.dumps(record|dict(actions=record['actions'][:q['source_ply']]))))
        if state_sha(source.state)!=q['source_id']or source.state.position!=s.state.position:
            raise ValueError('source Position/history proposal mismatch')
        witness=record['actions'][q['source_ply']:]
        if len(witness)!=q['length']or len(witness)>r['rule_remaining']:
            raise ValueError('suffix length mismatch')
        result=try_witness(s,witness)
        rows.append(dict(id=q['id'],fingerprint=fp,proposal=q,observation=result))
        stats['literal_actions']+=result['executed'];stats['proved'if result['proved']else'unknown']+=1
    return dict(format='leaper-saved-suffix-proofs-v1',input_digest=digest(truth),proposal_digest=digest(proposals),
                rows=rows,status=status,unstarted=[q['id']for q in proposals['rows'][len(rows):]],
                counts=dict(stats),seconds=time.perf_counter()-start,
                scope='Literal target-history decisive paths only. Actual failed/drawn paths remain UNKNOWN, not no-mate truth. No minimax WDL, oracle TRAIN selection, new rule/game or Player.')


def apply(truth, packet):
    if packet['input_digest']!=digest(truth):raise ValueError('saved suffix source mismatch')
    out=deepcopy(truth);roots={r['id']:r for r in out['roots']};seen=set()
    for q in packet['rows']:
        if q['id']in seen:raise ValueError('duplicate target')
        seen.add(q['id']);r=roots[q['id']]
        if r['fingerprint']!=q['fingerprint']:raise ValueError('target rule mismatch')
        if type(q['observation']['proved'])is not bool:raise ValueError('boolean proof status required')
        if not q['observation']['proved']:continue
        if r['cooperative_decisive']is False:raise ValueError('contradictory mate path')
        r['cooperative_decisive']=True;r['universal_draw']=False
        r['saved_suffix_basis']='literal_cross_history_replay_same_Position'
    out['saved_suffix_proof_digest']=digest(packet)
    return out


def verify(truth, proposals, packet, *, seconds=180):
    """Directly check every positive path without producer try_witness."""
    if proposals['input_digest']!=digest(truth)or packet['input_digest']!=digest(truth):
        raise ValueError('suffix verification source mismatch')
    if packet['proposal_digest']!=digest(proposals):raise ValueError('proposal binding mismatch')
    by_id={q['id']:q for q in proposals['rows']};compiled={};stats=Counter();start=time.perf_counter()
    for row in packet['rows']:
        if time.perf_counter()-start>=seconds:raise RuntimeError('VERIFICATION_CAP_UNKNOWN')
        if role_stop_requested():raise RuntimeError('USER_STOP')
        q=row['proposal']
        if q!=by_id[row['id']]or row['fingerprint']!=q['fingerprint']:
            raise ValueError('proof proposal mismatch')
        if type(row['observation']['proved'])is not bool:raise ValueError('boolean proof status required')
        if not row['observation']['proved']:continue
        fp=row['fingerprint']
        if fp not in compiled:compiled[fp]=compile_rule(ruleset_from_dict(truth['rules'][fp]))
        r,s=root_session(truth,row['id'],compiled[fp])
        record=truth['records'][q['source_record_id']]
        source=GameSession.replay(compiled[fp],deserialize_game_record(json.dumps(record|dict(actions=record['actions'][:q['source_ply']]))))
        if state_sha(source.state)!=q['source_id']or source.state.position!=s.state.position:
            raise ValueError('positive source/target mismatch')
        original=record['actions'][q['source_ply']:]
        if len(original)!=q['length']or len(original)>r['rule_remaining']:
            raise ValueError('positive length mismatch')
        witness=original
        if packet.get('method')=='chronological_loop_erasure':
            indices=row['retained_source_indices']
            if (any(type(i)is not int or not 0<=i<len(original)for i in indices)
                    or indices!=sorted(set(indices))):raise ValueError('invalid retained source indices')
            witness=[original[i]for i in indices]
            if witness!=row['witness']:raise ValueError('shortened source binding mismatch')
            positions=[source.state.position]
            for a in original:
                source.submit(action_from_dict(a));positions.append(source.state.position)
            current=positions[0];kept=[current]
            for i in indices:
                if positions[i]!=current:raise ValueError('removed segment is not a Position loop')
                current=positions[i+1];kept.append(current)
            if current!=positions[-1]or len(set(kept))!=len(kept):
                raise ValueError('shortened path is not a complete simple Position path')
        executed=0
        for action in witness:
            if s.state.terminal_status.is_terminal:break
            s.submit(action_from_dict(action));executed+=1
        t=s.state.terminal_status
        actual=dict(proved=t.is_terminal and t.winner is not None,status=t.status.value,
                    terminal_winner=t.winner,executed=executed,final_ply=s.state.ply_count,
                    final_history_id=state_sha(s.state))
        if digest(actual)!=digest(row['observation'])or not actual['proved']:
            raise ValueError('literal positive path mismatch')
        stats['positive_roots']+=1;stats['literal_edges']+=executed
    apply(truth,packet)
    return dict(verified=True,counts=dict(stats),seconds=time.perf_counter()-start,
                input_digest=digest(truth),proof_digest=digest(packet),
                scope='All positive paths independently replayed from actual target histories. Failed paths remain UNKNOWN producer observations, not negative reachability proofs.')


def barrier_diagnostics(truth,raw,short):
    """Replay raw failed suffixes in both histories and expose the first barrier."""
    from generic_chess.core.identity import repetition_identity_key
    if raw['input_digest']!=digest(truth)or short['input_digest']!=digest(truth):
        raise ValueError('barrier source mismatch')
    rows=[]
    for q in raw['rows']:
        if q['observation']['proved']:continue
        proposal=q['proposal'];fp=q['fingerprint'];c=compile_rule(ruleset_from_dict(truth['rules'][fp]))
        r,target=root_session(truth,q['id'],c);record=truth['records'][proposal['source_record_id']]
        source=GameSession.replay(c,deserialize_game_record(json.dumps(record|dict(actions=record['actions'][:proposal['source_ply']]))))
        if source.state.position!=target.state.position:raise ValueError('barrier initial Position mismatch')
        witness=record['actions'][proposal['source_ply']:];track=[]
        for i,a in enumerate(witness):
            if target.state.terminal_status.is_terminal:break
            source.submit(action_from_dict(a));target.submit(action_from_dict(a))
            if source.state.position!=target.state.position:raise ValueError('barrier transition Position mismatch')
            key=repetition_identity_key(target.state.position,c)
            track.append(dict(edge=i+1,source_ply=source.state.ply_count,target_ply=target.state.ply_count,
                source_count=dict(source.state.repetition_counts)[key],target_count=dict(target.state.repetition_counts)[key],
                source_terminal=source.state.terminal_status.status.value,target_terminal=target.state.terminal_status.status.value,
                position_key=key))
        if target.state.terminal_status.status.value!='repetition'or not track or track[-1]['target_count']!=4:
            raise ValueError('claimed repetition barrier mismatch')
        if track[-1]['source_count']>=4:raise ValueError('source has the same repetition barrier')
        shortened=next(s for s in short['rows']if s['id']==q['id'])
        rows.append(dict(id=q['id'],fingerprint=fp,source_record_id=proposal['source_record_id'],source_id=proposal['source_id'],
            source_ply=proposal['source_ply'],target_ply=r['ply'],raw_suffix_length=len(witness),
            target_rule_remaining=r['rule_remaining'],terminal_history=state_sha(target.state),barrier=track[-1],
            shortened_length=len(shortened['witness']),shortened_observation=shortened['observation']))
    return dict(input_digest=digest(truth),rows=rows,distinct_terminal_histories=len({r['terminal_history']for r in rows}),
        scope='Five raw-path failures are two terminal-history groups; four unresolved roots share one terminal history. An actual repetition barrier blocks this suffix only, not every cooperative path. One shorter saved-action subsequence rescues one target, four stayUNKNOWN. No episode independence or WDL/policy effect.')
