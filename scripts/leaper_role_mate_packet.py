"""Recompute finite role-coupled static candidates and full-record witnesses."""
from dataclasses import replace
from itertools import permutations
from collections import Counter
import json,hashlib
from scripts import leaper_design as L
from scripts.leaper_parity_scope import xy,adjacent,escapes
from generic_chess.core.attacks import is_in_check
from generic_chess.core.movegen import legal_actions_from_position

def board_position(c,cells):
    k,a,v,b=cells;board=[None]*25
    for square,owner,tid in [(k,0,'K'),(a,0,'A'),(v,1,'K'),(b,1,'B')]:board[square]=L.Piece(owner,tid,tid)
    return replace(c.initial_position,board=tuple(board),side_to_move=1)

def qualify_role_documents(docs):
    j=lambda n:json.loads(docs[n]);raw=j('analysis/role-mate.json');target=j('analysis/role-target.json');world=j('adjacent/inputs.json');expected=[];counts=Counter()
    sha=lambda n:hashlib.sha256(docs[n].encode('utf-8')).hexdigest()
    rp=j('analysis/role-registration.json');wp=j('analysis/role-witness-provenance.json')
    assert rp['input_sha256']==sha('adjacent/inputs.json')and rp['source_sha256']==sha('source/role_mate.py')and target['source_sha256']==sha('source/role_target.py')and wp['source_sha256']==sha('source/role_witness.py')
    assert raw['status']=='CLOSED' and not raw['missing'] and len(raw['rows'])==31
    for k,a,v in permutations(range(25),3):
        counts['three_actor_raw']+=1
        if adjacent(xy(k,5),xy(v,5)):continue
        counts['nonadjacent']+=1
        if (xy(v,5)[0]-xy(a,5)[0],xy(v,5)[1]-xy(a,5)[1]) not in L.offsets(1):continue
        counts['A_checks_K1']+=1
        free=escapes(xy(k,5),xy(a,5),xy(v,5),set(L.offsets(1)),5);assert free
        if len(free)!=1:counts['at_least_two_unblocked_king_escapes']+=1;continue
        b=free[0][1]*5+free[0][0]
        if b in (k,a,v):counts['single_escape_is_occupied_checker']+=1;continue
        expected.append([k,a,v,b]);counts['only_possible_four_actor_mate_candidate']+=1
    assert expected==raw['candidate_placements'] and dict(counts)==raw['geometry_counts']
    reference=L.ruleset_from_dict(world['rule']);carrier_board=[None]*25
    for square,owner,tid in [(0,0,'K'),(1,0,'A'),(24,1,'K'),(23,1,'B')]:carrier_board[square]=L.Piece(owner,tid,tid)
    core_frontiers=0;safe0_exclusions=0;positive=[]
    for mask,row in enumerate(raw['rows'],1):
        assert row['B_mask']==mask
        actual=L.ruleset_from_dict(row['rule']);rr=replace(reference,initial_position=tuple(tuple(carrier_board[5*y:5*y+5])for y in range(5)),initial_setup_options=(),piece_types=tuple(replace(pt,movement_atoms=tuple(L.LeapAtom(o)for o in L.offsets(mask)))if pt.type_id=='B'else pt for pt in reference.piece_types))
        assert L.ruleset_to_dict(actual,include_metadata=True)==L.ruleset_to_dict(rr,include_metadata=True) and L.compute_fingerprint(actual)==row['fingerprint'];c=L.compile_rule(actual);assert len(row['candidates'])==len(expected);mates=[]
        for cells,case in zip(expected,row['candidates']):
            assert case['placement']==cells;p=board_position(c,cells);assert is_in_check(p,1,c);checked0=is_in_check(p,0,c);assert case['previous_mover_in_check']==checked0 and case['admissible_postmove']==(not checked0)
            if checked0:safe0_exclusions+=1;continue
            actions=legal_actions_from_position(p,c);assert L.record_value(actions)==case['actions'];core_frontiers+=1
            assert all(p.board[a.from_square.rank*5+a.from_square.file].current_type_id=='B'for a in actions)
            if not actions:mates.append(cells)
        assert mates==row['mates'] and row['static_mate_possible']==bool(mates)
        if mates:positive.append(mask)
    assert positive==[m for m in range(1,32)if not(m&2)and not(m&4 and m&8)]
    c=L.compile_rule(reference);carrier=next(r for r in raw['rows']if r['B_mask']==10);rr=L.ruleset_from_dict(carrier['rule']);assert L.ruleset_to_dict(replace(rr,initial_position=reference.initial_position,initial_setup_options=reference.initial_setup_options),include_metadata=True)==L.ruleset_to_dict(reference,include_metadata=True)
    assert target['target_fingerprint']==world['fingerprint']==L.compute_fingerprint(reference) and target['carrier_fingerprint']==carrier['fingerprint']
    for case in target['target_candidates']:
        p=board_position(c,case['placement']);safe=not is_in_check(p,0,c);assert case['previous_mover_safe']==safe
        if safe:actions=legal_actions_from_position(p,c);assert actions and L.record_value(actions)==case['actions'];core_frontiers+=1
    bare=Counter()
    for k,a,v in permutations(range(25),3):
        if adjacent(xy(k,5),xy(v,5)) or (xy(v,5)[0]-xy(a,5)[0],xy(v,5)[1]-xy(a,5)[1]) not in L.offsets(1):continue
        board=[None]*25
        for sq,owner,tid in [(k,0,'K'),(a,0,'A'),(v,1,'K')]:board[sq]=L.Piece(owner,tid,tid)
        p=replace(c.initial_position,board=tuple(board),side_to_move=1);actions=legal_actions_from_position(p,c);actual=sorted((z.to_square.file,z.to_square.rank)for z in actions);expected_free=sorted(escapes(xy(k,5),xy(a,5),xy(v,5),set(L.offsets(1)),5));assert actual==expected_free and actual;bare['checked']+=1;bare['defenses']+=len(actions)
    assert dict(bare)==target['bareA']
    witness=j('analysis/role-witness.json');assert witness['status']=='PASS';witness_edges=0
    for row in witness['rows']:
        rr=L.ruleset_from_dict(row['rule']);cc=L.compile_rule(rr);s=L.GameSession.replay(cc,L.deserialize_game_record(json.dumps(row['initial_record'])));assert s.state.ply_count==0 and not s.state.terminal_status.is_terminal;s.submit(L.match_action(s,row['submitted_action']));assert L.record_value(s.state)==row['after_state'] and L.record_value(s.to_record())==row['after_record'] and L.record_value(s.result)==row['result'];assert L.record_value(s.legal_actions())==row['all_defenses'];witness_edges+=1
        for child in row.get('defense_children',[]):
            z=L.GameSession.replay(cc,s.to_record());z.submit(L.match_action(z,child['action']));assert L.record_value(z.state)==child['state'] and L.record_value(z.to_record())==child['record'] and L.record_value(z.result)==child['result'];witness_edges+=1
    assert witness['rows'][0]['result']['status']=='checkmate' and witness['rows'][1]['result']['status']=='ongoing' and len(witness['rows'][1]['all_defenses'])==1
    r8,r10=[L.ruleset_from_dict(row['rule'])for row in witness['rows']]
    assert r8.initial_position==r10.initial_position and r8.initial_setup_options==r10.initial_setup_options==()
    assert L.ruleset_to_dict(replace(r10,initial_position=reference.initial_position,initial_setup_options=reference.initial_setup_options),include_metadata=True)==L.ruleset_to_dict(reference,include_metadata=True)
    newtypes=tuple(next(p for p in r10.piece_types if p.type_id=='B')if p.type_id=='B'else p for p in r8.piece_types);assert L.ruleset_to_dict(replace(r8,piece_types=newtypes),include_metadata=True)==L.ruleset_to_dict(r10,include_metadata=True)
    return dict(status='PASS',geometry_counts=dict(counts),candidate_cases=31*len(expected),core_safe_frontiers=core_frontiers,own_anchor_check_exclusions=safe0_exclusions,bare_target_frontiers=bare['checked'],bare_target_defenses=bare['defenses'],positive_masks=positive,negative_masks=[m for m in range(1,32)if m not in positive],witness_Core_edges=witness_edges,scope='Static role-coupled cage geometry plus all candidate one-ply Core defenses and actual commonfresh witness. Not graph closure/WDL or actual8mu winning strategy. Source capsules are not executed.',new_Player_queries=0)
