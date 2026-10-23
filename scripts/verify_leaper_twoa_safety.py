"""Check finite draw invariants for PRIMARY's exact frozen 5x5 two-A input.

No attractor, producer rank, claimed WDL or foreign adjacency is trusted.
All attacker choices and one defender choice are reconstructed with public
Core. At-most-one-A exits use the checked checkerboard obstruction. The
certificate does not establish a generic Position/history equivalence.
"""
from collections import Counter
from pathlib import Path
import argparse,json,time
from scripts.leaper_explorer_truth import load,digest
from scripts.leaper_cooperative_certificate import decode_position,encode_position
from scripts.leaper_colour_certificate import geometry_table,distance,colour,KING
from scripts.leaper_design import compile_rule,ruleset_from_dict,state_sha
from scripts.leaper_retrograde import fresh_state
from scripts.leaper_microgames import role_stop_requested
from generic_chess.core.transition import legal_successors
from generic_chess.core.actions import action_to_dict,action_from_dict
from generic_chess.core.identity import repetition_identity_key
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record

FINGERPRINT='1988f7df02e58e0d48855e44a576e23b32e90ae5a0353c105615a1f33e946df1'
SOURCE=Path('docs/research/data/leaper_policy_cost_20261024/next-cost-inputs.json')
SOURCE_DIGEST='93498ffff7ccad53b4f435e430735e62e5b705481f148951e5d718f2cbf64d58'


def admission(certificate,source):
    if certificate['format']!='frozen-5x5-mixed-twoA-draw-safety-v1':raise ValueError('unknown certificate format')
    if certificate['source_input_digest']!=SOURCE_DIGEST or digest(source)!=SOURCE_DIGEST:raise ValueError('frozen source differs')
    worlds=source['worlds'];rules=[r['rule']for r in worlds]
    if not rules or any(r!=certificate['rule']for r in rules):raise ValueError('full source rule differs')
    raw=certificate['rule'];rule=ruleset_from_dict(raw);c=compile_rule(rule)
    if c.ruleset_fingerprint!=FINGERPRINT:raise ValueError('frozen rule fingerprint differs')
    # Complete fingerprint equality is supplemented by the proof's premises.
    types={p.type_id:p for p in rule.piece_types}
    if set(types)!={'K','A'}or rule.board_size!=5 or rule.capture_disposition!='remove_from_game':raise ValueError('roster/board/capture outside proof')
    if not types['K'].is_anchor or types['A'].is_anchor:raise ValueError('royal identity differs')
    if any(p.is_promotable or p.promotion_target_ids or any(a.__class__.__name__!='LeapAtom'for a in p.movement_atoms)for p in types.values()):raise ValueError('non-Leap or promotion')
    if {a.offset for a in types['K'].movement_atoms}!=KING or {a.offset for a in types['A'].movement_atoms}!={(-1,-1),(-1,1),(1,-1),(1,1)}:raise ValueError('movement differs')
    if rule.promotion_allowed or rule.promotion_forced or any(any(x)for pair in rule.drop_allowed.values()for x in pair):raise ValueError('promotion/drop differs')
    support=c.support
    if c.max_ply!=64 or c.repetition_limit!=4 or support.stalemate_result!='draw'or support.repetition_policy!='draw':raise ValueError('ending differs')
    if any(getattr(support,k)for k in('automatic_adjudications','consecutive_action_adjudications','no_progress_draw','pass_enabled'))or getattr(c,'repeated_cycle_target_conditions',()):raise ValueError('extra terminal/history effect')
    return c,worlds


def check_position(p):
    if p.aux_state or any(h.counts for h in p.hands)or len(p.board)!=25:raise ValueError('aux/hand/shape outside proof')
    kings={};aa=[]
    for i,z in enumerate(p.board):
        if z is None:continue
        if z.promoted or z.current_type_id!=z.base_type_id or z.owner not in(0,1):raise ValueError('actor outside proof')
        if z.current_type_id=='K':
            if z.owner in kings:raise ValueError('duplicate King')
            kings[z.owner]=i
        elif z.current_type_id=='A'and z.owner==0:aa.append(i)
        else:raise ValueError('opponent is not bare')
    if set(kings)!={0,1}or len(aa)>2 or distance(kings[0],kings[1],5)<=1:raise ValueError('King/A roster differs')
    return kings,aa


def verify(certificate,source,*,seconds=300):
    tick=time.perf_counter();c,worlds=admission(certificate,source);counts=Counter()
    def guard():
        if role_stop_requested():raise RuntimeError('USER_STOP')
        if time.perf_counter()-tick>=seconds:raise RuntimeError('TWOA_SAFETY_READER_CAP_UNKNOWN')
    # The table covers every nonadjacent King pair on a given checked colour.
    # Its opposite-colour escape is empty when all A occupy the checked colour,
    # outside enemy King's coverage and unattackable by any diag1 A.
    for shade in(0,1):
        table=geometry_table(5,shade)
        expected={(k,e)for k in range(25)for e in range(25)if colour(k,5)==shade and distance(k,e,5)>1}
        if len(table)!=len(expected)or {(k,e)for k,e,t in table}!=expected:raise ValueError('incomplete geometry')
        for k,e,t in table:
            if colour(t,5)==shade or abs(t%5-k%5)+abs(t//5-k//5)!=1 or distance(t,e,5)<=1:raise ValueError('invalid safe escape')
        counts['geometry_pairs']+=len(table)
    # Bind all negative same-colour supplied histories; no graph is purchased.
    negative=[];mixed=[]
    for w in worlds:
      for sr in w['roots']:
        s=GameSession.replay(c,deserialize_game_record(json.dumps(sr['record'])));k,aa=check_position(s.state.position)
        if s.result.status.value!='ongoing'or s.state.ply_count!=sr['target']:raise ValueError('source root differs')
        if len({colour(a,5)for a in aa})<=1:negative.append(dict(record=sr['record'],state_sha=state_sha(s.state),value=0,cooperative=False,basis='single-colour closed obstruction'))
        else:mixed.append(sr)
    derived=certificate.get('derived_full_history',False)
    if type(derived)is not bool:raise ValueError('invalid derived-history mode')
    if not derived and len(mixed)!=len(certificate['roots']):raise ValueError('mixed root coverage differs')
    if derived:
        if len(certificate['roots'])!=1:raise ValueError('one derived history required')
        saved=certificate['roots'][0]
        if saved.get('source_record')!=mixed[0]['record']:raise ValueError('derived source record differs')
        if saved['record'].get('initial_setup_key')!=mixed[0]['record'].get('initial_setup_key'):raise ValueError('derived setup differs')
        mixed=[dict(record=saved['record'])]
    positions=[decode_position(x,c.initial_position)for x in certificate['positions']];indices={p:i for i,p in enumerate(positions)}
    if len(indices)!=len(positions):raise ValueError('duplicate safety position')
    rows=certificate['safety_rows']
    if [r['index']for r in rows]!=list(range(len(positions))):raise ValueError('missing/duplicate safety row')
    barriers=set(certificate.get('barriers',[]));root_indices={r['local_root']for r in certificate['roots']}
    if barriers and not derived:raise ValueError('barriers require one bound derived history')
    if any(type(i)is not int or not 0<=i<len(positions)for i in barriers):raise ValueError('invalid barrier')
    if derived:
        incoming=GameSession.replay(c,deserialize_game_record(json.dumps(certificate['roots'][0]['record'])))
        if incoming.result.status.value!='ongoing':raise ValueError('derived root not ongoing')
        pre=dict(incoming.state.repetition_counts)
        if any(pre.get(repetition_identity_key(positions[i],c),0)<3 for i in barriers):raise ValueError('barrier lacks actual prehistory')
    adjacency=[]
    for i,(p,row)in enumerate(zip(positions,rows,strict=True)):
        if i%128==0:guard()
        kings,aa=check_position(p);st=fresh_state(p,c);counts['vertices']+=1
        if 'goal'in row:
            if row['goal']=='single_color_obstruction':
                if len(aa)>1:raise ValueError('not a one-A exit')
                if st.terminal_status.winner is not None:raise ValueError('mate in no-mate exit')
                counts['analytic_exits']+=1
            elif row['goal']=='literal_draw':
                if not st.terminal_status.is_terminal or st.terminal_status.winner is not None:raise ValueError('not literal draw')
                counts['literal_exits']+=1
            elif row['goal']=='prior_arrival_draw':
                if i not in barriers or i in root_indices or st.terminal_status.winner is not None:raise ValueError('invalid future-arrival exit')
                counts['barrier_goals']+=1
            else:raise ValueError('unknown goal')
            if set(row)!={'index','goal'}:raise ValueError('goal annotation differs')
            adjacency.append([]);continue
        if st.terminal_status.is_terminal:raise ValueError('terminal in ongoing invariant')
        actual={digest(action_to_dict(a)):(a,ch)for a,ch in legal_successors(st,c)}
        counts['Core_frontier_edges']+=len(actual)
        selected=[digest(a)for a in row['actions']]
        if len(selected)!=len(set(selected))or not set(selected)<=set(actual):raise ValueError('duplicate/illegal safety action')
        if p.side_to_move==0:
            if set(selected)!=set(actual):raise ValueError('attacker frontier incomplete')
        elif len(selected)!=1:raise ValueError('one defender action required')
        children=[]
        for key in selected:
            a,ch=actual[key];counts['Core_edges']+=1
            if ch.terminal_status.is_terminal and ch.terminal_status.winner is not None:raise ValueError('mate precedes draw')
            if ch.position not in indices:raise ValueError('safety child missing')
            children.append(indices[ch.position])
            if indices[ch.position]in barriers:counts['count3_draw_exits']+=1
        if children!=row['children']:raise ValueError('actual safety frontier differs')
        adjacency.append(children)
    roots=[]
    for sr,saved in zip(mixed,certificate['roots'],strict=True):
        if saved['record']!=sr['record']:raise ValueError('full incoming record differs')
        s=GameSession.replay(c,deserialize_game_record(json.dumps(saved['record'])))
        if state_sha(s.state)!=saved['state_sha']or s.state.position!=positions[saved['local_root']]:raise ValueError('full history root binding differs')
        root=saved['local_root'];start=s.state.ply_count
        path=saved.get('cooperative_path')
        if path is None and not derived:raise ValueError('original mixed root lacks cooperative path')
        if path is not None:
            for a in path:s.submit(action_from_dict(a));counts['cooperative_Core_edges']+=1
            if s.result.status.value!='checkmate'or s.result.winner!=0 or s.state.ply_count>64:raise ValueError('cooperative path did not mate')
        roots.append(dict(state_sha=saved['state_sha'],local_root=root,value=0,cooperative='UNMEASURED'if path is None else True,cooperative_length=None if path is None else s.state.ply_count-start,
            root_ply=start,remaining=64-start,basis='complete attacker / one defender closed safety, analytic exits; bare opponent cannot score'))
    seen={r['local_root']for r in roots};pending=list(seen)
    while pending:
        for j in adjacency[pending.pop()]:
            if j not in seen:seen.add(j);pending.append(j)
    if seen!=set(range(len(positions))):raise ValueError('unreachable safety annotations')
    return dict(verified=True,counts=dict(counts),mixed_roots=roots,same_colour_roots=negative,seconds=time.perf_counter()-tick,
        scope='Exactfrozen5x5diag1twoApublicCore safety and actualfullhistorycooperativepaths. No solverranktrusted, newPlayer, genericPosition/historyquotient, trainingorpolicyutility. Futureclock/repetitionaddonlyDRAWexits; mateprecedencechecked.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--certificate',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=verify(load(a.certificate),load(SOURCE));a.output.write_text(json.dumps(r,indent=2));print(r)
