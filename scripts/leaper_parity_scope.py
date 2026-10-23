"""Scoped mating-obstruction geometry and Core local checks; no graph solver."""
from __future__ import annotations
import argparse, hashlib, itertools, json, time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_e0_panel import MASKS, rule
from generic_chess.core.attacks import is_in_check
from generic_chess.core.movegen import legal_actions_from_position
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.position import GameState,HistoryRecord
from generic_chess.core.terminal import _terminal_from_parts,TerminalStatus
from tools.local_agent import session
from tools.local_agent.common import write_json

def now(): return datetime.now(timezone.utc).isoformat()
def digest(x): return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def xy(i,n=4): return (i%n,i//n)
def adjacent(a,b): return max(abs(a[0]-b[0]),abs(a[1]-b[1]))<=1

def escapes(k,a,v,offsets,n=4):
    """Independent geometry; postcapture A is absent, kings remain nonadjacent."""
    return tuple(sorted((x,y) for x in range(max(0,v[0]-1),min(n,v[0]+2))
                        for y in range(max(0,v[1]-1),min(n,v[1]+2))
                        if (x,y)!=v and not adjacent((x,y),k)
                        and (a is None or (x,y)==a or (x-a[0],y-a[1]) not in offsets)))

def orthogonally_independent(offsets):
    moves=set(offsets)
    return not any((x+dx,y+dy) in moves for x,y in moves
                   for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)))

def scope_rule(raw,mask, *, allow_offset_independence=False):
    """Exact checked rule template, not a permissive generic semantic recognizer."""
    r=L.ruleset_from_dict(raw)
    canonical=rule(mask,0)
    candidate=replace(r,initial_position=canonical.initial_position)
    if L.ruleset_to_dict(candidate,include_metadata=True)!=L.ruleset_to_dict(canonical,include_metadata=True):
        return False,'semantic_template_mismatch'
    if len({(x+y)%2 for x,y in L.offsets(mask)})==1:return True,'singleparity_exact_template'
    if allow_offset_independence and orthogonally_independent(L.offsets(mask)):
        return True,'orthogonal_offset_independence_exact_template'
    return False,'mixed_parity'

def placement(c,k,a,v):
    board=[None]*16
    for index,owner,tid in ((k,0,'K'),(v,1,'K')):board[index]=L.Piece(owner,tid,tid)
    if a is not None:board[a]=L.Piece(0,'A','A')
    return replace(c.initial_position,board=tuple(board),side_to_move=1)

def local_census(output):
    assert not output.exists();output.mkdir(parents=True)
    masks=[m for m in MASKS if len({(x+y)%2 for x,y in L.offsets(m)})==1]
    plan={'at':now(),'masks':masks,'n':4,'all_labelled_three_piece_placements_per_mask':3360,
          'two_king_placements':240,'positive_control_mask':5,
          'question':'Does independent postcapture geometry match every Core legal escape from all static checked three-piece placements in the exact parity scope?',
          'scope':'Placement census is NOT reachable-history enumeration. No graph transitions, closure/minimax solver, Player calls or old policy refill. Only one-step successors of checked static placements. Negative theorem derives absence of checkmate from geometry plus fixed rule semantics.',
          'stop':'all7*3360 rawplacements+240doubleKing+single mixedpositive or600seconds orFIRST mismatch; incomplete rows retained, no extension',
          'expected_seconds':60,'cap_seconds':600,'source_sha256':L.sha(Path(__file__))}
    write_json(output/'plan.json',plan);start=now();tick=time.perf_counter();rows=[];failure=None
    for mask in masks:
        c=L.compile_rule(rule(mask,0));offsets=set(L.offsets(mask));counts={'mask':mask,'raw':0,'adjacent_kings_excluded':0,'admitted':0,'checked':0,'unchecked':0,'core_escape_edges':0,'captures_A':0,'edge_checked':0,'corner_checked':0,'interior_checked':0};checks=[]
        for k,a,v in itertools.permutations(range(16),3):
            counts['raw']+=1
            if session.stopped() or time.perf_counter()-tick>=600:failure={'reason':'stop_or_cap','mask':mask,'placement':[k,a,v]};break
            if adjacent(xy(k),xy(v)):counts['adjacent_kings_excluded']+=1;continue
            counts['admitted']+=1;p=placement(c,k,a,v)
            geo_check=(xy(v)[0]-xy(a)[0],xy(v)[1]-xy(a)[1]) in offsets
            if geo_check!=is_in_check(p,1,c):failure={'reason':'check_disagreement','mask':mask,'placement':[k,a,v]};break
            if not geo_check:counts['unchecked']+=1;continue
            counts['checked']+=1
            edge=sum(z in (0,3) for z in xy(v));counts[['interior_checked','edge_checked','corner_checked'][edge]]+=1
            expected=escapes(xy(k),xy(a),xy(v),offsets);aa=legal_actions_from_position(p,c);write_json(output/'latest-Core-return.json',{'mask':mask,'placement':[k,a,v],'actions':L.record_value(aa)});actual=tuple(sorted((x.to_square.file,x.to_square.rank) for x in aa));entry={'placement':[k,a,v],'escapes':[list(z) for z in actual]};checks.append(entry)
            if not expected or actual!=expected:failure={'reason':'escape_mismatch','mask':mask,**entry,'expected':expected};break
            key=repetition_identity_key(p,c);terminal=_terminal_from_parts(p,0,((key,1),),c)
            if terminal.status is not TerminalStatus.ONGOING:failure={'reason':'unexpected_checked_terminal','mask':mask,**entry,'terminal':L.record_value(terminal)};break
            s=GameState(p,0,((key,1),),terminal,(HistoryRecord(key,-1,'',False),));children=L.legal_successors(s,c)
            if tuple(sorted((z.to_square.file,z.to_square.rank) for z,_ in children))!=actual:failure={'reason':'successor_disagreement','mask':mask,**entry};break
            for act,ch in children:
                counts['core_escape_edges']+=1
                if (act.to_square.file,act.to_square.rank)==xy(a):
                    counts['captures_A']+=1
                    if any(piece and piece.current_type_id=='A' for piece in ch.position.board):failure={'reason':'capture_failed','mask':mask,**entry};break
                if is_in_check(ch.position,1,c):failure={'reason':'postcapture_or_escape_in_check','mask':mask,**entry};break
            if failure:break
        rows.append({'counts':counts,'checks':checks,'fingerprint':c.initial_position.ruleset_fingerprint})
        write_json(output/'results.json',{'status':'RUNNING','rows':rows,'failure':failure,'started_at':start,'updated_at':now()})
        print(counts,flush=True)
        if failure:break
    two={'raw':0,'adjacent_excluded':0,'admitted':0,'checks':0,'zero_legal':0};c=L.compile_rule(rule(1,0))
    if not failure:
        for k,v in itertools.permutations(range(16),2):
            two['raw']+=1
            if adjacent(xy(k),xy(v)):two['adjacent_excluded']+=1;continue
            two['admitted']+=1;p=placement(c,k,None,v)
            two['checks']+=int(is_in_check(p,0,c) or is_in_check(p,1,c));two['zero_legal']+=int(not legal_actions_from_position(p,c))
        assert two['checks']==two['zero_legal']==0
    result={'status':'FAILED' if failure else 'CLOSED','plan_sha256':L.sha(output/'plan.json'),'rows':rows,'two_kings':two,'failure':failure,'started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'Player_calls':0,'solver_calls':0,'input_reachability_claim':False}
    write_json(output/'results.json',result);print({k:v for k,v in result.items() if k!='rows'},flush=True)
    return result


def bind_histories(source, handoff, output, census):
    import gzip
    from generic_chess.core.semantic_executor import semantic_engine_for
    started=now();tick=time.perf_counter()
    old=L.load(handoff);packet=json.loads(gzip.decompress(source.read_bytes()))
    assert L.sha(source)==old['compressed_source_sha256']
    worlds=packet['runs']['small-interrupted']['files']['inputs.json']['worlds']
    assert len(worlds)==len(old['rows'])==48
    counts={};rows=[]
    for w,prior in zip(worlds,old['rows'],strict=True):
        r=L.ruleset_from_dict(w['rule']);c=L.compile_rule(r);engine=semantic_engine_for(c)
        record=L.deserialize_game_record(json.dumps(w['initial_record']));ss=L.GameSession.replay(c,record)
        assert L.record_value(ss.state)==w['initial_state']
        assert prior['world']==w['world'] and prior['rule_fingerprint']==L.compute_fingerprint(r)==w['fingerprint']
        assert prior['full_state_sha256']==L.state_sha(ss.state)
        assert prior['full_rule_json_sha256']==digest(w['rule']) and prior['full_initial_record_json_sha256']==digest(w['initial_record'])
        mask=w['masks'][0];ok,why=scope_rule(w['rule'],mask)
        pieces=[(i,p.owner,p.current_type_id,p.base_type_id,p.promoted) for i,p in enumerate(ss.state.position.board) if p]
        king_rows=[z for z in pieces if z[2]=='K'];ordinary=[z for z in pieces if z[2]!='K']
        roster_ok=(len(king_rows)==2 and {z[1] for z in king_rows}=={0,1} and len(ordinary)<=1 and all(z[1:]==(0,'A','A',False) for z in ordinary) and not any(h.total() for h in ss.state.position.hands) and not ss.state.position.aux_state)
        assert roster_ok
        assert not adjacent(xy(king_rows[0][0]),xy(king_rows[1][0]))
        assert engine is not None
        terminal=engine.terminal_result(ss.state.position,ss.state.ply_count,ss.state.repetition_counts,ss.state.history)
        assert terminal==ss.state.terminal_status
        applicable=ok and roster_ok
        literal=ss.state.terminal_status.is_terminal
        if literal:
            status='literal_terminal_fact';coop=ss.result.winner is not None;wdl=0 if ss.result.winner is None else 1 if ss.result.winner==ss.state.position.side_to_move else -1
        elif applicable:
            status='theorem_scope_bound_independent_review_pending';coop=False;wdl=0
        elif not ordinary:
            status='twoKing_scope_bound_independent_review_pending';coop=False;wdl=0
        else:status='UNKNOWN';coop='UNKNOWN';wdl='UNKNOWN'
        counts[status]=counts.get(status,0)+1
        row={'world':w['world'],'mask':mask,'source_rule_fingerprint':w['fingerprint'],'source_full_rule_sha256':prior['full_rule_json_sha256'],'source_full_record_sha256':prior['full_initial_record_json_sha256'],'state_sha256':L.state_sha(ss.state),'full_rule':w['rule'],'full_record':w['initial_record'],'full_state':w['initial_state'],'scope_check':why,'scope_applicable':applicable,'roster':pieces,'status':status,'proposed_cooperative_scoring_reachability':coop,'proposed_WDL_for_side_to_move':wdl,'proposed_action_WDL':'ALL_DRAW' if wdl==0 else 'UNKNOWN','initial_terminal':L.record_value(ss.result),'ply':ss.state.ply_count,'remaining_plies':r.max_ply-ss.state.ply_count,'max_ply':r.max_ply,'repetition_counts':L.record_value(ss.state.repetition_counts),'terminal_priority':'noLegal=>checkmate/stalemate before repeat-draw before max-ply; exacttemplate has no declarations/automatic/action/no-progress policies','target':'Existence of scoring continuation fromTHISfullhistory; NOToldfinitepolicyterminalprobability','old_prediction_vector_sha256':digest(prior['prediction_vector']),'old_labels_untouched':True,'certificate':'PARITY-KAK-4X4-v1' if applicable else 'TWO-KING-v1' if not ordinary else 'LITERAL' if literal else None,'source_census_sha256':L.sha(census),'independent_AUX_label':'NOT_IMPORTED','policy_missing_slots':'unchanged1904UNKNOWN'}
        rows.append(row)
        write_json(output,{'schema':'genericchess.structural_forecast.v2','status':'RUNNING','rows':rows,'counts':counts})
    result={'schema':'genericchess.structural_forecast.v2','status':'CLOSED_PROPOSED_LABELS_PENDING_INDEPENDENT_REVIEW','started_at':started,'ended_at':now(),'seconds':time.perf_counter()-tick,'source_packet_sha256':L.sha(source),'old_handoff_sha256':L.sha(handoff),'source_census_sha256':L.sha(census),'source_sha256':L.sha(Path(__file__)),'proof_scope':'Exact4x4singleparityK+AagainstbareK/removal/noaux or hand/promotion; allotherendingsdraw. One-stepfinitegeometryplusanalyticinvariant, no new graph solver. Mixedparity UNKNOWN, positives fromotherstarts not imported. Literalterminalfacts separately specified.','claim_level':'Mathematical theorem plus source-assisted Core binding; not independent oracle calibration or blind generalization. Proposedlabels may be consumed/reviewed by AUX but do not rewrite any old outcome.','counts':counts,'rows':rows,'new_Player_calls':0,'new_solver_calls':0}
    write_json(output,result);return result

def semantic_qualification(census_path, metadata_path, output):
    from generic_chess.core.semantic_executor import semantic_engine_for
    started=now();tick=time.perf_counter();old=L.load(census_path);meta=L.load(metadata_path)
    assert old['status']=='CLOSED' and old['failure'] is None
    rows=[];counts={'saved_parity_checked':0,'added17_checked':0,'semantic_escape_edges':0,'captures_A':0,'mixed_positive_controls':0,'doubleKing_placements':0}
    # A distinct metadata-derived candidate, not a parity counterexample:
    # independent attack targets can have BOTH colours (mask17).
    for mask in [x['counts']['mask'] for x in old['rows']]+[17]:
        c=L.compile_rule(rule(mask,0));engine=semantic_engine_for(c);assert engine is not None
        offsets=set(L.offsets(mask));checks=[]
        if mask==17:
            placement_rows=[(k,a,v) for k,a,v in itertools.permutations(range(16),3)
                 if not adjacent(xy(k),xy(v)) and (xy(v)[0]-xy(a)[0],xy(v)[1]-xy(a)[1]) in offsets]
        else:placement_rows=[tuple(z['placement']) for row in old['rows'] if row['counts']['mask']==mask for z in row['checks']]
        for k,a,v in placement_rows:
            if session.stopped() or time.perf_counter()-tick>180:raise RuntimeError('fixed semantic qualification cap or scoped stop')
            pos=placement(c,k,a,v);key=repetition_identity_key(pos,c);hist=(HistoryRecord(key,-1,'',False),)
            observed={'placement':[k,a,v],'in_check':engine.in_check(pos,1),'terminal':L.record_value(engine.terminal_result(pos,0,((key,1),),hist))}
            write_json(output.with_suffix('.latest.json'),observed)
            assert observed['in_check'] and observed['terminal']['status']=='ongoing'
            state=GameState(pos,0,((key,1),),_terminal_from_parts(pos,0,((key,1),),c),hist)
            children=L.legal_successors(state,c)
            expected=escapes(xy(k),xy(a),xy(v),offsets)
            assert expected and tuple(sorted((a.to_square.file,a.to_square.rank) for a,_ in children))==expected
            for action,ch in children:
                assert not engine.in_check(ch.position,1)
                counts['semantic_escape_edges']+=1
                counts['captures_A']+=int((action.to_square.file,action.to_square.rank)==xy(a))
            # This is a synthetic bookkeeping/precedence check, not a reachable
            # history with exactly these repetition counts or clock length.
            assert engine.terminal_result(pos,64,((key,1),),hist).status is TerminalStatus.MAX_PLY
            assert engine.terminal_result(pos,0,((key,4),),hist).status is TerminalStatus.REPETITION
            assert engine.terminal_result(pos,64,((key,4),),hist).status is TerminalStatus.REPETITION
            checks.append({'placement':[k,a,v],'escapes':[list(z) for z in expected]})
            counts['added17_checked' if mask==17 else 'saved_parity_checked']+=1
        rows.append({'mask':mask,'checks':checks,'actual_execution':'semantic_engine_for(compiled)','fingerprint':c.initial_position.ruleset_fingerprint})
        write_json(output,{'status':'RUNNING','counts':counts,'rows':rows})
    controls=[]
    for z in meta['rows']:
        if not z['geometric_mate_placements']:continue
        c=L.compile_rule(rule(z['mask'],0));e=semantic_engine_for(c);k,a,v=z['first_example'];pos=placement(c,k,a,v);key=repetition_identity_key(pos,c)
        terminal=e.terminal_result(pos,0,((key,1),),(HistoryRecord(key,-1,'',False),))
        controls.append({'mask':z['mask'],'placement':[k,a,v],'terminal':L.record_value(terminal)})
        write_json(output.with_suffix('.controls.json'),{'rows':controls})
        assert terminal.status is TerminalStatus.CHECKMATE and terminal.winner==0
        counts['mixed_positive_controls']+=1
    c=L.compile_rule(rule(1,0));e=semantic_engine_for(c)
    for k,v in itertools.permutations(range(16),2):
        if adjacent(xy(k),xy(v)):continue
        pos=placement(c,k,None,v);key=repetition_identity_key(pos,c)
        assert not e.in_check(pos,0) and not e.in_check(pos,1) and e.has_legal_action(pos)
        assert e.terminal_result(pos,64,((key,1),),(HistoryRecord(key,-1,'',False),)).status is TerminalStatus.MAX_PLY
        counts['doubleKing_placements']+=1
    result={'status':'PASS','started_at':started,'ended_at':now(),'seconds':time.perf_counter()-tick,'counts':counts,'rows':rows,'positive_controls':controls,'source_census_sha256':L.sha(census_path),'source_metadata_sha256':L.sha(metadata_path),'source_sha256':L.sha(Path(__file__)),'scope':'Distinct actual semantic-engine terminal/check/capture/clock/repetition qualification, including new mixedparity17. All positions synthetic local controls; no historygraph/root reachability inferred. Shared compiledCore not independent binary/WDLoracle.'}
    write_json(output,result);return result

if __name__=='__main__':
 p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--bind',action='store_true');p.add_argument('--semantic-qualify',action='store_true');a=p.parse_args()
 if a.semantic_qualify:
  r=semantic_qualification(Path('.local_agent/parity-scope-20261023-3a241d93-final/results.json'),Path('.local_agent/parity-metadata-capacity-3a/results.json'),a.output);print(r['counts'])
 elif a.bind:
  q=Path('docs/research/data/leaper_e0_20261023');r=bind_histories(q/'e0-and-interrupted-panel.json.gz',q/'truth-handoff.json',a.output,Path('.local_agent/parity-scope-20261023-3a241d93-final/results.json'));print(r['counts'])
 else:local_census(a.output)
