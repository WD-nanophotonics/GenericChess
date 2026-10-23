"""Local conservation qualification for a single board/hand/promoting entity.

No history graph, minimax solver or Player. Enumerates a fixed STATIC domain
and each Core successor once, proving an explicit sufficient invariant only.
"""
from __future__ import annotations
import itertools,json,time,hashlib
from dataclasses import replace
from datetime import datetime,timezone
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_e0_panel import rule
from scripts.leaper_parity_scope import xy,adjacent,escapes,orthogonally_independent,digest
from generic_chess.core.movement import LeapAtom
from generic_chess.core.pieces import PieceType
from generic_chess.core.position import Hands,GameState,HistoryRecord,count_entities
from generic_chess.core.identity import repetition_identity_key
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.core.coordinates import Square
from generic_chess.core.actions import action_to_dict
from generic_chess.core.terminal import TerminalStatus
from tools.local_agent.common import write_json
from tools.local_agent import session

def now():return datetime.now(timezone.utc).isoformat()
def definition():
    r=rule(1,0);king=r.piece_types[0]
    a=PieceType('A','A',tuple(LeapAtom(z) for z in L.offsets(1)),is_promotable=True,promotion_target_ids=('P',))
    p=PieceType('P','P',tuple(LeapAtom(z) for z in L.offsets(2)))
    all_pairs=frozenset((Square(x,y),Square(u,v)) for x,y,u,v in itertools.product(range(4),repeat=4))
    return replace(r,piece_types=(king,a,p),capture_disposition='capture_to_hand',drop_allowed={'A':((True,)*16,)*2,'P':((False,)*16,)*2},promotion_allowed={'A':(all_pairs,all_pairs)},promotion_forced={'A':(frozenset(),frozenset())})

def admit_rule(r):
    """Sufficient source-assisted condition, not a complete semantic theorem API.

    This recognizes only ordinary RuleSet lowering; DSL effects/guards/extra
    goals fail closed. A successful result still needs a validated full history.
    """
    from dataclasses import fields
    from generic_chess.core.movement import LeapAtom
    known={'schema_version','board_size','piece_types','initial_position','drop_allowed',
        'promotion_allowed','promotion_forced','repetition_limit','repetition_policy',
        'max_ply','stalemate_result','semantic_actions','semantic_dsl_version',
        'declarations','automatic_adjudications','metadata','board_width','board_height',
        'capture_disposition','pass_enabled','consecutive_action_adjudications',
        'initial_setup_options','repeated_cycle_target_conditions','no_progress_draw'}
    if {f.name for f in fields(r)}!=known:return False,'unreviewed_RuleSet_field'
    if r.schema_version!=1:return False,'unsupported_schema'
    shape=r.board_shape
    if min(shape.width,shape.height)<2:return False,'thin_board'
    if shape.width!=shape.height:return False,'unsupported_rectangular_execution'
    if not isinstance(r.max_ply,int) or isinstance(r.max_ply,bool) or r.max_ply<1:return False,'no_finite_clock'
    if r.capture_disposition not in ('remove_from_game','capture_to_hand'):return False,'entity_count_not_bound'
    for name in ('semantic_actions','declarations','automatic_adjudications',
                 'consecutive_action_adjudications','repeated_cycle_target_conditions',
                 'no_progress_draw'):
        if getattr(r,name):return False,'unsupported_'+name
    if r.repetition_policy!='draw' or r.stalemate_result!='draw':return False,'non_draw_other_terminal'
    if not r.piece_types:return False,'no_types'
    kings=set(L.offsets(3));anchors=[]
    for t in r.piece_types:
        if not all(isinstance(a,LeapAtom) for a in t.movement_atoms):return False,'non_fixed_Leap_'+t.type_id
        offsets={tuple(a.offset) for a in t.movement_atoms}
        if t.is_anchor:
            if offsets!=kings or t.is_promotable or t.promotion_target_ids:return False,'nonstandard_royal_'+t.type_id
            anchors.append(t.type_id)
        elif not orthogonally_independent(offsets):return False,'adjacent_attack_targets_'+t.type_id
    if not anchors:return False,'no_royal_type'
    # Cross-type unions need NOT be independent: a single entity has only one
    # CURRENT type at a time. All reachable declared targets are conservatively
    # checked above; no reachability solver or silent type truncation is used.
    return True,'fixed_royals_per_current_type_independence_finite_draw_clock'

def admit_position(pos,r):
    ok,reason=admit_rule(r)
    if not ok:return ok,reason
    types={t.type_id:t for t in r.piece_types};shape=r.board_shape
    if len(pos.board)!=shape.area or pos.aux_state:return False,'state_shape_or_aux'
    anchors=[];ordinary=0
    for index,p in enumerate(pos.board):
        if p is None:continue
        if p.owner not in (0,1) or p.base_type_id not in types or p.current_type_id not in types:return False,'invalid_piece_identity'
        if types[p.current_type_id].is_anchor:
            if p.base_type_id!=p.current_type_id or p.promoted:return False,'royal_type_change'
            anchors.append((index,p.owner))
        else:
            if types[p.base_type_id].is_anchor:return False,'ordinary_from_royal'
            ordinary+=1
    for h in pos.hands:
        for tid,count in h.items():
            if tid not in types or types[tid].is_anchor or type(count) is not int or count<0:return False,'invalid_hand'
            ordinary+=count
    if len(anchors)!=2 or {owner for _,owner in anchors}!={0,1}:return False,'royal_count'
    a,b=[(i%shape.width,i//shape.width) for i,_ in anchors]
    if adjacent(a,b):return False,'adjacent_royals'
    if ordinary>1:return False,'more_than_one_physical_ordinary'
    return True,'sufficient_domain_replay_and_terminal_binding_still_required'

def domain_specs():
    for k,v in itertools.permutations(range(16),2):
        if adjacent(xy(k),xy(v)):continue
        for mover in (0,1):
            for owner in (0,1):
                for a in range(16):
                    if a in (k,v):continue
                    for tid in ('A','P'):yield (k,v,mover,owner,a,tid)
                yield(k,v,mover,owner,None,'A')

def position(c,spec):
    k,v,mover,owner,a,tid=spec;board=[None]*16
    board[k]=L.Piece(0,'K','K');board[v]=L.Piece(1,'K','K')
    hands=[Hands.empty(),Hands.empty()]
    if a is None:hands[owner]=Hands((('A',1),))
    else:board[a]=L.Piece(owner,'A',tid,tid=='P')
    return replace(c.initial_position,board=tuple(board),hands=tuple(hands),side_to_move=mover)

def closed(position):
    ps=[(i,p) for i,p in enumerate(position.board) if p]
    kk=[(i,p) for i,p in ps if p.current_type_id=='K'];aa=[p for _,p in ps if p.current_type_id!='K']
    if len(kk)!=2 or {p.owner for _,p in kk}!={0,1} or adjacent(xy(kk[0][0]),xy(kk[1][0])):return False
    if any(p.base_type_id!='K' or p.promoted for _,p in kk):return False
    if len(aa)>1 or count_entities(position)!=3 or position.aux_state:return False
    if any(p.base_type_id!='A' or p.current_type_id not in ('A','P') or p.promoted!=(p.current_type_id=='P') for p in aa):return False
    if any(t!='A' or count!=1 for h in position.hands for t,count in h.items()):return False
    return True

def run(output):
    assert not output.exists();output.mkdir();tick=time.perf_counter();started=now();r=definition();c=L.compile_rule(r);e=semantic_engine_for(c);assert e is not None
    assert all(orthogonally_independent(L.offsets(m)) for m in (1,2))
    write_json(output/'rule.json',L.ruleset_to_dict(r,include_metadata=True))
    plan={'started_at':started,'changed_premise':'Singleordinary BOARD actor exclusion may be unnecessarily strict. Capture-to-hand, drops and optionalA->P promotion conserve ONE physicalordinaryentity; eachcurrenttype hasorthogonallyindependentfixedLeapattacks. Proofreplies areKingmoves, not restricted A moves.','question':'Does actualCore preserve the3entity invariant and admit a Kingescape in everycheckedstaticstate, including base/current/hands, without new scoringterminals?', 'source_sha256':L.sha(Path(__file__)),'fingerprint':L.compute_fingerprint(r),'expected_seconds':'Preflightfirst128admittedstates then scaleactualtotalquerytime*1.5 plus recording; hardcap1800s andmax18096rawstaticstates; ifforecast>=7200stopbeforefullrun. No guesses overridingmeasuredcost.','cap_seconds':1800,'scope':'STATICone-step domain; no fullhistory graph/Player/learning/fitness. Exclude sources withtheNONMOVINGKing alreadyincheck; retainedexcludedcounts. Newliteralvalidationtransitionsnotclaimedreachablefrominitialmu. Optionalpromotion samephysicalentity, capture resets base inhand, drops consumehand.','stop':'completefixedlocaldomain or1800s orfirstsemanticsmismatch; keepmissingUNKNOWN/no refill.'};write_json(output/'plan.json',plan)
    rows=[];cnt={'raw':0,'excluded_nonmoving_check':0,'admitted':0,'checked':0,'actions':0,'captures':0,'drops':0,'promotions':0,'terminal_draw_sources':0,'terminal_scoring_sources':0};failure=None;pre_tick=time.perf_counter();pre_states=0
    for spec in domain_specs():
        if session.stopped() or time.perf_counter()-tick>=1800:failure={'reason':'cap_or_stop','next_spec':spec};break
        pos=position(c,spec);cnt['raw']+=1
        if e.in_check(pos,1-pos.side_to_move):cnt['excluded_nonmoving_check']+=1;continue
        cnt['admitted']+=1;assert closed(pos)
        key=repetition_identity_key(pos,c);hist=(HistoryRecord(key,-1,'',False),);term=e.terminal_result(pos,0,((key,1),),hist)
        source={'spec':spec,'terminal':L.record_value(term)}
        if term.is_terminal:
            cnt['terminal_draw_sources']+=int(term.winner is None);cnt['terminal_scoring_sources']+=int(term.winner is not None)
            if term.winner is not None:failure={'reason':'scoring_terminal',**source};break
            source['actions']=[];rows.append(source);continue
        checked=e.in_check(pos,pos.side_to_move);cnt['checked']+=int(checked)
        state=GameState(pos,0,((key,1),),term,hist);children=L.legal_successors(state,c)
        # Retain returned decisions BEFORE interpretation/assertion.
        write_json(output/'latest-return.json',{'spec':spec,'children':[{'action':L.record_value(a),'state':L.record_value(ch)} for a,ch in children]})
        if checked and not children:failure={'reason':'no_evasion',**source};break
        actions=[]
        for action,ch in children:
            cnt['actions']+=1;raw=action_to_dict(action);actions.append(raw)
            if not closed(ch.position) or ch.terminal_status.winner is not None:failure={'reason':'closure_or_scoring_child',**source,'child':L.record_value(ch),'action':raw};break
            if raw['kind'] in ('drop','semantic_drop'):cnt['drops']+=1
            if raw.get('promotion_target_id') is not None:cnt['promotions']+=1
            before=sum(1 for p in pos.board if p);after=sum(1 for p in ch.position.board if p)
            if after<before:cnt['captures']+=1
        source['actions']=actions;source['checked']=checked;rows.append(source)
        if failure:break
        if cnt['admitted']==128:
            pre_states=cnt['admitted'];pre_s=time.perf_counter()-pre_tick;forecast=pre_s*(18096/pre_states)*1.5
            write_json(output/'preflight.json',{'admitted':pre_states,'actual_seconds':pre_s,'raw_total_static_domain':18096,'max_forecast_seconds':forecast,'basis':'first128admittedsourceincludesALLsemantic children andrecording for each, not only coldrootcalls; distributionmaydiffer later, frozen1800cap unchanged'})
            print('preflight',pre_s,forecast,flush=True)
            if forecast>=7200:failure={'reason':'necessity_threshold_preflight'};break
        if cnt['admitted']%256==0:
            write_json(output/'progress.json',{'started_at':started,'at':now(),'counts':cnt,'seconds':time.perf_counter()-tick});print(cnt,flush=True)
            write_json(output/'partial-rows.json',{'rows':rows})
    result={'status':'FAILED_OR_INCOMPLETE' if failure else 'CLOSED','failure':failure,'started_at':started,'ended_at':now(),'seconds':time.perf_counter()-tick,'counts':cnt,'rows':rows,'source_sha256':L.sha(Path(__file__)),'rule_sha256':L.sha(output/'rule.json'),'new_Player_calls':0,'new_solver_calls':0,'scope':'Complete STATICone-stepcheckonly ifCLOSED; nothistoryreachability or independentengine. Sourceassistedconservation+geometricproof maylabel applicablecompletehistories, butmust separatelybindactualrules.'}
    write_json(output/'results.json',result);print({k:v for k,v in result.items() if k!='rows'},flush=True)

def validate_records(output):
    import random
    r=definition();c=L.compile_rule(r);d=output;assert not d.exists();d.mkdir()
    plan={'frozen_at':now(),'rule':L.ruleset_to_dict(r,include_metadata=True),'fingerprint':L.compute_fingerprint(r),'seeds':[202610230000+i for i in range(8)],'policy':'uniform over complete Corelegalactions; actualrule64/repeat4; all8kept, no replacements/refill','question':'Do the bound singleton board/hand/currenttype invariant and fullhistory terminalsemantics survive actual initial-to-terminal records with observedpromotion/drop/capture events?','scope':'Eight NEW semanticvalidationtrajectories, not policyfitness or broadinversequality. No Player/solver. Actual literalhistories never synthesizedcountercounts.','cap_seconds':60}
    write_json(d/'plan.json',plan);start=now();tick=time.perf_counter();rows=[]
    for seed in plan['seeds']:
        ss=L.GameSession(c);rng=random.Random(seed);events={'drops':0,'promotions':0,'captures':0};path=[]
        while not ss.state.terminal_status.is_terminal:
            if time.perf_counter()-tick>=60 or session.stopped():raise RuntimeError('validationrecordcap/stop')
            assert closed(ss.state.position)
            aa=ss.legal_actions();action=aa[rng.randrange(len(aa))];before=ss.state.position;raw=action_to_dict(action)
            ss.submit(action);after=ss.state.position
            path.append({'action':raw,'state_sha256':L.state_sha(ss.state)})
            # Save actual completed prefix BEFORE any scientific assertion.
            write_json(d/('seed-'+str(seed)+'.json'),{'seed':seed,'full_record':L.record_value(ss.to_record()),'full_state':L.record_value(ss.state),'path':path,'events_so_far':events})
            assert closed(after) and ss.result.winner is None
            events['drops']+=int(raw['kind'] in ('drop','semantic_drop'))
            events['promotions']+=int(raw.get('promotion_target_id') is not None)
            events['captures']+=int(sum(x is not None for x in after.board)<sum(x is not None for x in before.board))
        item={'seed':seed,'full_record':L.record_value(ss.to_record()),'full_state':L.record_value(ss.state),'path':path,'events':events,'terminal':L.record_value(ss.result)}
        write_json(d/('seed-'+str(seed)+'.json'),item);rows.append(item)
    out={'status':'PASS','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'rows':rows,'events':{k:sum(x['events'][k] for x in rows) for k in ('drops','promotions','captures')},'total_plies':sum(len(x['path']) for x in rows),'new_validation_trajectories':len(rows),'new_Player_calls':0,'new_solver_calls':0,'source_sha256':L.sha(Path(__file__))};write_json(d/'results.json',out);return out

def qualify_local_packet(packet, rule_file, output):
    """Distinct public legal_actions/apply_action reader, not producer reuse."""
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.transition import apply_action
    from generic_chess.core.terminal import terminal_result
    result=L.load(packet);r=L.ruleset_from_dict(L.load(rule_file));c=L.compile_rule(r)
    assert result['status']=='CLOSED' and L.sha(rule_file)==result['rule_sha256']
    start=now();tick=time.perf_counter();n=edges=0;chain=hashlib.sha256()
    for row in result['rows']:
        if session.stopped() or time.perf_counter()-tick>=900:raise RuntimeError('900s independentreader budget orscopedstop')
        pos=position(c,row['spec']);key=repetition_identity_key(pos,c);hist=(HistoryRecord(key,-1,'',False),)
        term=terminal_result(GameState(pos,0,((key,1),),None,hist),c)
        assert L.record_value(term)==row['terminal'] and term.winner is None
        state=GameState(pos,0,((key,1),),term,hist);aa=legal_actions(state,c)
        assert [action_to_dict(a) for a in aa]==row['actions']
        for action in aa:
            child=apply_action(state,action,c)
            assert closed(child.position) and child.terminal_status.winner is None
            chain.update(json.dumps({'source_spec':row['spec'],'action':action_to_dict(action),'child':L.record_value(child)},sort_keys=True,separators=(',',':')).encode())
            edges+=1
        n+=1
        if n%1024==0:
            write_json(output.with_suffix('.progress.json'),{'started_at':start,'at':now(),'rows':n,'edges':edges,'seconds':time.perf_counter()-tick});print(n,edges,flush=True)
    assert n==result['counts']['admitted'] and edges==result['counts']['actions']
    out={'status':'PASS','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'rows':n,'literal_applied_actions':edges,'source_packet_sha256':L.sha(packet),'source_rule_sha256':L.sha(rule_file),'actual_child_digest':chain.hexdigest(),'route':'publiclegal_actions plus publicapply_action; distinct fromproducerlegal_successors, sharedCore not independent engine/oracle','source_sha256':L.sha(Path(__file__))};write_json(output,out);print(out);return out

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--records',action='store_true');p.add_argument('--qualify',type=Path);a=p.parse_args();r=qualify_local_packet(a.qualify,a.qualify.parent/'rule.json',a.output) if a.qualify else validate_records(a.output) if a.records else run(a.output);print({k:v for k,v in (r or {}).items() if k!='rows'})
