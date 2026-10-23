"""Scoped K+A vs K no-mate certificate; uses committed Core, no game solver.

PRIMARY owns mask sampling/features. This module consumes its frozen rules and
histories, checks a geometric obstruction and binds a distinct truth target.
Static placements are a local terminal test, not natural reachable histories.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
from itertools import permutations
import json
from pathlib import Path
import time

from generic_chess.core.attacks import is_in_check
from generic_chess.core.actions import action_to_dict
from generic_chess.core.movegen import legal_actions_from_position
from generic_chess.core.pieces import Piece
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.transition import legal_successors
from generic_chess.rules.schema import ruleset_from_dict, compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_colour_certificate import KING, distance
from scripts.leaper_design import state_sha
from scripts.leaper_design import offsets
from scripts.research_record import record_value
from scripts.leaper_explorer_truth import load, save, digest
from scripts.leaper_microgames import role_stop_requested
from scripts.leaper_retrograde import fresh_state


def admit(raw, *, require_parity=True):
    fields={'schema_version','board_size','capture_disposition','piece_types',
            'initial_position','promotion_allowed','promotion_forced','drop_allowed',
            'stalemate_result','repetition_limit','max_ply','metadata'}
    if set(raw)!=fields or raw['schema_version']!=1 or raw['metadata']:
        raise ValueError('only explicit plain legacy declaration admitted')
    rule=ruleset_from_dict(raw)
    if rule.board_size!=4 or rule.capture_disposition!='remove_from_game':
        raise ValueError('requires ordinary4x4/remove')
    if rule.promotion_allowed or rule.promotion_forced or any(
        any(m)for pair in rule.drop_allowed.values()for m in pair):
        raise ValueError('no promotion or drops')
    types={p.type_id:p for p in rule.piece_types}
    if set(types)!={'K','A'}or not types['K'].is_anchor or types['A'].is_anchor:
        raise ValueError('exactly K royal and A nonroyal types required')
    for p in types.values():
        if p.is_promotable or p.promotion_target_ids or any(
            a.__class__.__name__!='LeapAtom'for a in p.movement_atoms):
            raise ValueError('plain fixed nonpromoting Leaps required')
    if {a.offset for a in types['K'].movement_atoms}!=KING:
        raise ValueError('King must have all eight neighbour offsets')
    parities={(sum(a.offset)%2)for a in types['A'].movement_atoms}
    if not parities or (require_parity and len(parities)!=1):
        raise ValueError('ordinary offsets must have one parity')
    c=compile_rule(rule);s=c.support
    if (s.stalemate_result!='draw' or s.repetition_policy!='draw' or
        s.max_ply is None or any(getattr(s,n)for n in (
            'automatic_adjudications','consecutive_action_adjudications',
            'no_progress_draw','pass_enabled'))or getattr(c,'repeated_cycle_target_conditions',())):
        raise ValueError('only checkmate wins; finite draw clock and repetition required')
    return rule,c,sorted(parities)


def domain(pos):
    if pos.aux_state or any(h.counts for h in pos.hands)or len(pos.board)!=16:
        raise ValueError('no auxiliary/hand/shape differences')
    kings={};ordinary=[]
    for i,p in enumerate(pos.board):
        if p is None:continue
        if p.owner not in(0,1):raise ValueError('invalid owner')
        if p.promoted or p.current_type_id!=p.base_type_id:
            raise ValueError('promoted/retyped actor outside domain')
        if p.current_type_id=='K':
            if p.owner in kings:raise ValueError('duplicate King')
            kings[p.owner]=i
        elif p.current_type_id=='A':ordinary.append((p.owner,i))
        else:raise ValueError('other actor outside domain')
    if set(kings)!={0,1}or distance(kings[0],kings[1],4)<=1 or len(ordinary)>1:
        raise ValueError('requires two nonadjacent Kings, at most one A')
    return kings,ordinary


def bare_opponent_bound(pos):
    """The bare King can never legally check the other royal King.

    Thus only the side owning the sole ordinary actor can ever win by mate.
    With draw-only other terminals this gives a bound on EVERY continuation,
    independently of A's parity or a minimax strategy. Not a piece price.
    """
    kings,ordinary=domain(pos)
    if not ordinary:return [0,0]
    return [0,1]if ordinary[0][0]==pos.side_to_move else[-1,0]


def escape_table():
    """Pure geometry, independent of engine attack tables/move generation."""
    rows=[]
    for victim,attacker in permutations(range(16),2):
        if distance(victim,attacker,4)<=1:continue
        x,y=victim%4,victim//4
        horizontal=[y*4+nx for nx in (x-1,x+1)if 0<=nx<4]
        vertical=[ny*4+x for ny in (y-1,y+1)if 0<=ny<4]
        for u in horizontal:
            for v in vertical:
                if distance(u,attacker,4)<=1 and distance(v,attacker,4)<=1:
                    raise ValueError('two orthogonal escapes simultaneously guarded')
                rows.append([victim,attacker,u,v])
    return rows


def exhaustive(raw, *, seconds=600):
    """All labelled placements, both A owners, bare King replies only.

    Checkmates can only occur on the bare side: the bare King cannot legally
    check the attacker King. Both ownership orientations are explicitly tested.
    Duplicate initial-layout declarations need not repeat identical geometry.
    """
    start=time.perf_counter();rule,c,parity=admit(raw);template=GameSession(c).state.position
    engine=semantic_engine_for(c)
    geometry=escape_table();counts=Counter();examples={}
    for owner in (0,1):
        for victim,attacker,a in permutations(range(16),3):
            counts['placements']+=1
            if distance(victim,attacker,4)<=1:
                counts['adjacent_king_rejected']+=1;continue
            if time.perf_counter()-start>seconds:raise RuntimeError('LOCAL_CHECK_CAP_UNKNOWN')
            if counts['placements']%128==0 and role_stop_requested():raise RuntimeError('USER_STOP')
            board=[None]*16;board[victim]=Piece(1-owner,'K','K');board[attacker]=Piece(owner,'K','K');board[a]=Piece(owner,'A','A')
            pos=replace(template,board=tuple(board),side_to_move=1-owner)
            domain(pos);counts['admitted_placements']+=1
            if engine is not None:
                for side in (0,1):
                    if engine.in_check(pos,side)!=is_in_check(pos,side,c):
                        raise ValueError('legacy/semantic attack disagreement')
            if is_in_check(pos,owner,c):raise ValueError('nonadjacent bare King checks attacker')
            if not is_in_check(pos,1-owner,c):continue
            counts['checked_placements']+=1
            # Check all actual replies and require an escape from the proof's
            # selected perpendicular pair, including capture of unprotected A.
            u,v=next((u,v)for k,e,u,v in geometry if(k,e)==(victim,attacker))
            actions=list(legal_actions_from_position(pos,c))
            candidates=[z for z in actions if z.to_square.rank*4+z.to_square.file in(u,v)]
            if not candidates:raise ValueError(('geometric escape rejected',owner,victim,attacker,a))
            state=fresh_state(pos,c)
            if state.terminal_status.is_terminal:raise ValueError('checked position falsely terminal')
            actual=list(legal_successors(state,c))
            physical=lambda z:(z.from_square.file,z.from_square.rank,z.to_square.file,z.to_square.rank)
            if {physical(z)for z in actions}!={physical(z)for z,ch in actual}:
                raise ValueError('public runtime/primitive legal reply mismatch')
            counts['actual_Core_successor_edges']+=len(actual)
            for z,ch in actual:
                domain(ch.position)
                if ch.terminal_status.winner is not None:raise ValueError('decisive reply contradicts theorem')
                if not any(p and p.current_type_id=='A'for p in ch.position.board):
                    counts['actual_capture_A_edges']+=1
            counts['legal_replies']+=len(actions)
            counts['proof_pair_replies']+=len(candidates)
            capture=any(z.to_square.rank*4+z.to_square.file==a for z in candidates)
            where='corner'if victim in(0,3,12,15)else'edge'if victim%4 in(0,3)or victim//4 in(0,3)else'interior'
            counts['checked_'+where]+=1
            if capture:counts['capture_A_escape']+=1
            key='capture_A'if capture else where
            examples.setdefault(key,dict(owner=owner,victim=victim,attacker=attacker,A=a,
                geometric_pair=[u,v],replies=[action_to_dict(z)for z in candidates]))
    # Capturing A closes to the bare-King domain, with either player moving.
    for k0,k1 in permutations(range(16),2):
        if distance(k0,k1,4)<=1:continue
        for mover in(0,1):
            board=[None]*16;board[k0]=Piece(0,'K','K');board[k1]=Piece(1,'K','K')
            pos=replace(template,board=tuple(board),side_to_move=mover)
            if is_in_check(pos,mover,c)or not list(legal_actions_from_position(pos,c)):
                raise ValueError('bare-King domain violates safe escape')
            for ac,ch in legal_successors(fresh_state(pos,c),c):
                _,ordinary=domain(ch.position)
                if ordinary or ch.terminal_status.winner is not None:
                    raise ValueError('bare-King closure violated by actual Core')
                counts['bare_King_Core_edges']+=1
            counts['bare_King_placements']+=1
    return dict(fingerprint=compute_fingerprint(rule),parity=parity,counts=dict(counts),
        geometry_digest=digest(geometry),geometry_rows=len(geometry),examples=examples,
        seconds=time.perf_counter()-start,verified=True,
        scope='All distinct 4x4 labelled three-actor placements for both A owners; nonadjacent Kings. Static local terminals, not reachable-history enumeration or policy games.')


def bind(worlds,handoff,verified):
    """Create structural truth rows; preserve original forecast target verbatim."""
    by={r['world']:r for r in handoff['rows']};rows=[]
    for w in worlds:
        h=by[w['world']];raw=w['rule'];rule,c,parities=admit(raw,require_parity=False)
        fp=compute_fingerprint(rule)
        actual_offsets={a.offset for p in rule.piece_types if p.type_id=='A'for a in p.movement_atoms}
        if len(w['masks'])!=1 or actual_offsets!=set(offsets(w['masks'][0]))or w['masks'][0]!=h['family_mask']:
            raise ValueError('mask metadata disagrees with rule')
        if fp!=w['fingerprint']or fp!=h['rule_fingerprint']or digest(raw)!=h['full_rule_json_sha256']:
            raise ValueError('full target rule binding mismatch')
        record=w['initial_record']
        if digest(record)!=h['full_initial_record_json_sha256']:raise ValueError('record binding mismatch')
        session=GameSession.replay(c,deserialize_game_record(json.dumps(record)))
        if state_sha(session.state)!=h['full_state_sha256']or state_sha(session.state)!=digest(w['initial_state']):
            raise ValueError('complete history binding mismatch')
        kings,ordinary=domain(session.state.position)
        if session.state.ply_count!=h['actual_prefix_plies']or rule.max_ply-session.state.ply_count!=h['remaining_rule_plies']:
            raise ValueError('clock binding mismatch')
        if rule.max_ply!=h['actual_rule_max_ply']or rule.repetition_limit!=h['repetition_limit']:
            raise ValueError('clock/repetition declaration mismatch')
        if record_value(session.result)!=h['Core_terminal']or record_value(session.result)!=w['initial_terminal']:
            raise ValueError('literal terminal binding mismatch')
        applicable=len(parities)==1
        if applicable and tuple(w['masks'])not in verified:raise ValueError('missing local proof check')
        terminal=session.state.terminal_status
        if terminal.is_terminal:
            label=0 if terminal.winner is None else 1 if terminal.winner==session.state.position.side_to_move else-1
            coop=terminal.winner is not None;reason='literal_target_terminal'
            bounds=[label,label]
        elif applicable or not ordinary:
            bounds=[0,0];coop=False;reason='single_parity_no_mate'if ordinary else'bare_King_no_mate'
        else:bounds=bare_opponent_bound(session.state.position);coop=None;reason='mixed_parity_bare_opponent_bound'
        if applicable and terminal.winner is not None:raise ValueError('target contradicts theorem')
        choices=[]
        if bounds==[0,0]and not terminal.is_terminal:
            for action,child in legal_successors(session.state,c):
                domain(child.position)
                if child.terminal_status.winner is not None:raise ValueError('decisive successor contradicts theorem')
                choices.append(dict(action=action_to_dict(action),child_state_sha=state_sha(child),bounds=[0,0]))
        rows.append(dict(world=w['world'],mask=w['masks'][0],fingerprint=fp,
            state_sha=state_sha(session.state),record_sha=digest(record),rule_sha=digest(raw),
            ply=session.state.ply_count,remaining=rule.max_ply-session.state.ply_count,
            repetition_limit=rule.repetition_limit,repetition_counts=list(session.state.repetition_counts),
            single_offset_parity=applicable,parities=parities,terminal=terminal.status.value,
            reason=reason,wdl_bounds=bounds,cooperative_decisive=coop,
            fork=False if bounds==[0,0]or terminal.is_terminal else None,action_bounds=choices,
            original_policy_prediction=h['prediction_vector']))
    return dict(format='leaper-single-parity-truth-v1',target='structural/no-decisive-path and literal full-history WDL, separate from finite-policy forecasts',
        source_handoff_digest=digest(handoff),rows=rows,
        counts=dict(Counter(r['reason']for r in rows)),
        scope='No original policy outcomes are filled; no population or blind calibration. The theorem is global within admitted geometry; mapping binds these actual full histories, not old128ply Position labels.')


def main():
    cli=argparse.ArgumentParser();cli.add_argument('--input',required=True);cli.add_argument('--output',required=True)
    args=cli.parse_args();p=Path(args.input);out=Path(args.output);out.mkdir(exist_ok=False,parents=True)
    worlds=load(p/'worlds.json');handoff=load(p/'truth-handoff.json');done={};checks=[]
    for w in worlds:
        key=tuple(w['masks'])
        if key in done:continue
        _,_,parities=admit(w['rule'],require_parity=False)
        if len(parities)!=1:continue
        result=exhaustive(w['rule']);done[key]=result;checks.append(dict(mask=key[0],**result))
        save(out/f'local-mask{key[0]}.json',result)
        print(json.dumps(dict(mask=key[0],counts=result['counts'],seconds=result['seconds'])),flush=True)
    result=bind(worlds,handoff,done);save(out/'truth.json',result)
    save(out/'local-summary.json',dict(checks=checks,truth_digest=digest(result)))
    print(json.dumps(result['counts']))


if __name__=='__main__':main()
