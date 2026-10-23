"""No-mate certificate for a frozen plain-Leaper colour invariant.

If every ordinary piece remains on one checkerboard colour, a checked King
has an empty orthogonal escape on the other colour which is not controlled
by the other, nonadjacent King. Ordinary colour-preserving Leaps cannot attack
that destination. A finite geometry table checks the boundary cases. This
proves absence of mate, not just failure to find a mate in a bounded search.

Scope: the legacy plain-Leaper rule admitted below, one adjacent-step King per
seat, no drops/promotion/aux/effects, removal captures and draw-only remaining
terminal conditions. This is a truth certificate, not a production evaluator.
"""
from __future__ import annotations

import argparse
from collections import Counter
from itertools import product
from pathlib import Path
import time

from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.core.actions import action_from_dict
from generic_chess.core.transition import legal_successors
from generic_chess.core.attacks import is_in_check
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_design import state_sha
from scripts.leaper_microgames import role_stop_requested

KING={(dx,dy)for dx,dy in product((-1,0,1),repeat=2)if dx or dy}
ORTH=((-1,0),(0,-1),(0,1),(1,0))


def colour(i,width):return (i%width+i//width)%2


def distance(a,b,width):
    return max(abs(a%width-b%width),abs(a//width-b//width))


def admit(raw):
    allowed={'schema_version','board_size','capture_disposition','piece_types',
             'initial_position','promotion_allowed','promotion_forced','drop_allowed',
             'stalemate_result','repetition_limit','max_ply','metadata'}
    if set(raw)!=allowed or raw['schema_version']!=1 or raw['metadata']:
        raise ValueError('only explicit plain legacy rule fields admitted')
    rule=ruleset_from_dict(raw);c=compile_rule(rule);width=rule.board_size
    if width!=4 or rule.capture_disposition!='remove_from_game':
        raise ValueError('certificate scope requires4x4/remove')
    if rule.promotion_allowed or rule.promotion_forced or any(
        any(mask)for masks in rule.drop_allowed.values()for mask in masks):
        raise ValueError('promotion/drop outside colour invariant')
    anchors=[p for p in rule.piece_types if p.is_anchor]
    if len(anchors)!=1 or anchors[0].type_id!='K':raise ValueError('single K type required')
    for p in rule.piece_types:
        if p.is_promotable or p.promotion_target_ids:raise ValueError('promotion outside scope')
        if any(a.__class__.__name__!='LeapAtom'for a in p.movement_atoms):
            raise ValueError('plain Leaps required')
        offsets={tuple(a.offset)for a in p.movement_atoms}
        if p.is_anchor:
            if offsets!=KING:raise ValueError('adjacent-step King required')
        elif any((dx+dy)%2 for dx,dy in offsets):
            raise ValueError('ordinary move changes colour')
    support=c.support
    if support.stalemate_result!='draw' or support.repetition_policy!='draw' or support.max_ply is None:
        raise ValueError('only finite draw clocks/repetition/stalemate admitted')
    if any(getattr(support,name)for name in ('automatic_adjudications',
              'consecutive_action_adjudications','no_progress_draw','pass_enabled')):
        raise ValueError('extra action/terminal semantics outside scope')
    if getattr(c,'repeated_cycle_target_conditions',()):raise ValueError('cycle-result effects outside scope')
    return rule,c


def geometry_table(width,shade):
    rows=[]
    for king,enemy in product(range(width*width),repeat=2):
        if colour(king,width)!=shade or distance(king,enemy,width)<=1:continue
        choices=[]
        for dx,dy in ORTH:
            x,y=king%width+dx,king//width+dy
            if 0<=x<width and 0<=y<width:
                target=y*width+x
                if distance(target,enemy,width)>1:choices.append(target)
        if not choices:raise ValueError('geometry has a possible trapped King')
        rows.append([king,enemy,min(choices)])
    return rows


def invariant(position,width,shade):
    kings={}
    for i,pc in enumerate(position.board):
        if not pc:continue
        if pc.current_type_id=='K':
            if pc.owner in kings:raise ValueError('multiple anchors')
            kings[pc.owner]=i
        elif colour(i,width)!=shade:raise ValueError('ordinary piece outside invariant colour')
    if set(kings)!={0,1} or distance(kings[0],kings[1],width)<=1:
        raise ValueError('missing/adjacent King')
    if position.aux_state or any(hand.counts for hand in position.hands):
        raise ValueError('aux/hand state outside scope')
    return kings


def propose(truth,fp):
    rule,c=admit(truth['rules'][fp]);initial=GameSession(c).state
    shades={colour(i,4)for i,pc in enumerate(initial.position.board)if pc and pc.current_type_id!='K'}
    if len(shades)!=1:raise ValueError('initial ordinary pieces do not share one colour')
    shade=next(iter(shades));invariant(initial.position,4,shade)
    return dict(format='leaper-colour-certificate-v1',fingerprint=fp,
          truth_digest=digest(truth),ordinary_colour=shade,
          geometry=geometry_table(4,shade),
          claim='No legal continuation from the original initial history can reach checkmate. Captures only remove ordinary pieces; every remaining piece preserves its colour. Checked Kings on that colour always have a geometrically safe empty opposite-colour escape. Other terminals are draws and max128 is finite, so every complete legal continuation is DRAW.',
          scope='This frozen4x4 plain-Leaper rule/initial invariant only; not all placements of this same rule, other rules, arbitrary history policies or source-cap completion.')


def verify(truth,certificate,*,seconds=120):
    started=time.perf_counter();fp=certificate['fingerprint'];raw=truth['rules'][fp]
    if certificate['truth_digest']!=digest(truth)or compute_fingerprint(ruleset_from_dict(raw))!=fp:
        raise ValueError('rule/truth binding mismatch')
    rule,c=admit(raw);shade=certificate['ordinary_colour']
    if type(shade)is not int or shade not in(0,1):raise ValueError('invalid invariant colour')
    # Independently check table completeness and each proposed escape, rather
    # than regenerating the proposer's selected minimum target.
    required={(k,e)for k,e in product(range(16),repeat=2)
              if colour(k,4)==shade and distance(k,e,4)>1}
    entries=certificate['geometry'];pairs={(k,e)for k,e,_ in entries}
    if len(entries)!=len(pairs)or pairs!=required:raise ValueError('incomplete escape table')
    for k,e,target in entries:
        if type(target)is not int or not 0<=target<16:raise ValueError('invalid escape square')
        if abs(target%4-k%4)+abs(target//4-k//4)!=1 or colour(target,4)==shade or distance(target,e,4)<=1:
            raise ValueError('unsafe escape square')
    invariant(GameSession(c).state.position,4,shade)
    counts=Counter();seen={};records=[]
    expected={r['id']:r for r in truth['roots']if r['fingerprint']==fp}
    for rid,record in truth['records'].items():
        if record['ruleset_fingerprint']!=fp:continue
        s=GameSession.replay(c,deserialize_game_record(__import__('json').dumps(record|dict(actions=[]))))
        for action in record['actions']:
            if time.perf_counter()-started>=seconds:raise RuntimeError('VERIFICATION_CAP_UNKNOWN')
            if role_stop_requested():raise RuntimeError('USER_STOP')
            hid=state_sha(s.state);invariant(s.state.position,4,shade)
            if hid not in expected:raise ValueError('missing source full history')
            if hid not in seen:
                kings=invariant(s.state.position,4,shade)
                if s.result.winner is not None:raise ValueError('source contradicts no-win proof')
                if is_in_check(s.state.position,s.state.position.side_to_move,c):
                    king=kings[s.state.position.side_to_move];enemy=kings[1-s.state.position.side_to_move]
                    target=next(t for k,e,t in entries if (k,e)==(king,enemy))
                    if not any(ch.position.board[target] is not None and
                         ch.position.board[target].current_type_id=='K'and
                         ch.position.board[target].owner==s.state.position.side_to_move
                         for _,ch in legal_successors(s.state,c)):
                        raise ValueError('abstract escape rejected by actual Core')
                    counts['checked_histories_with_core_escape']+=1
                legal=0
                for _,child in legal_successors(s.state,c):
                    invariant(child.position,4,shade)
                    if child.terminal_status.winner is not None:raise ValueError('decisive edge contradicts proof')
                    legal+=1
                if not legal:raise ValueError('source ongoing root has no action')
                old=expected[hid]
                if old['wdl_bounds']not in([0,0],[-1,1])or old['wdl_fork']is True:
                    raise ValueError('certificate contradicts existing scoped WDL')
                seen[hid]=legal;counts['legal_action_bindings']+=legal
            s.submit(action_from_dict(action));counts['record_actions']+=1
        if s.result.winner is not None or not s.state.terminal_status.is_terminal:
            raise ValueError('source record is not completed draw')
        counts['records']+=1;records.append(rid)
        counts['record_terminal_'+s.state.terminal_status.status.value]+=1
    if set(seen)!=set(expected):raise ValueError('source coverage incomplete')
    return dict(verified=True,fingerprint=fp,certificate_digest=digest(certificate),
          geometry_pairs=len(entries),counts=dict(counts),histories=len(seen),
          new_wdl_labels=sum(expected[h]['wdl_bounds']==[-1,1]for h in seen),
          bound_histories=sorted(seen),records=sorted(records),
          seconds=time.perf_counter()-started,
          scope='Abstract no-mate proof from parsed parity/King/terminal conditions plus complete finite geometry table. All listed source histories/full records and actual one-ply choices physically checked through shared Core. Future closure follows the invariant induction, not an enumerated full game graph. Original bounded searches remain UNKNOWN.')


if __name__=='__main__':
    cli=argparse.ArgumentParser();cli.add_argument('--truth',required=True);cli.add_argument('--fingerprint',required=True);cli.add_argument('--output',required=True)
    args=cli.parse_args();truth=load(args.truth);out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    cert=propose(truth,args.fingerprint);save(out/'certificate.json',cert)
    receipt=verify(truth,cert);save(out/'verification.json',receipt)
    print(__import__('json').dumps({k:v for k,v in receipt.items()if k not in('bound_histories','records')}))
