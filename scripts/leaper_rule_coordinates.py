"""Finite pure-Leaper rule coordinates and paired fresh-initial one-ply features.

No game-graph solver: geometry, compiler admission and literal Core children are
separate observations. Full-history truth stays with the established AUX lane.
"""
from __future__ import annotations
import argparse,itertools,time
from collections import Counter
from dataclasses import replace
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_e0_panel import rule as singleton_rule
from scripts.leaper_parity_scope import adjacent,xy,escapes,orthogonally_independent,digest,now
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.schema import RuleInitialSetupOption
from tools.local_agent.common import write_json
from tools.local_agent import session

PAIRS=((4,6),(1,5),(1,17))


def motion_graph(mask,n):
    moves=L.offsets(mask);rows=[]
    for a in range(n*n):
        x,y=xy(a,n)
        rows.append(tuple(sorted(n*(y+dy)+x+dx for dx,dy in moves
                                 if 0<=x+dx<n and 0<=y+dy<n)))
    unseen=set(range(n*n));components=[]
    while unseen:
        front=[min(unseen)];seen=set(front)
        while front:
            for z in set(rows[front.pop()])-seen:seen.add(z);front.append(z)
        components.append(sorted(seen));unseen-=seen
    distances=[]
    for source in range(n*n):
        d={source:0};front=[source]
        while front:
            v=front.pop(0)
            for z in rows[v]:
                if z not in d:d[z]=d[v]+1;front.append(z)
        distances.extend(d.values())
    return {'mask':mask,'board_size':n,'offsets':[list(x) for x in moves],
            'adjacency':rows,'component_sizes':sorted(map(len,components)),
            'components':components,'directed_edges':sum(map(len,rows)),
            'mean_degree':sum(map(len,rows))/(n*n),'degree_histogram':dict(sorted(Counter(map(len,rows)).items())),
            'maximum_finite_distance':max(distances),'ordered_unreachable_pairs':(n*n)**2-len(distances),
            'single_parity':len({(x+y)%2 for x,y in moves})==1,
            'orthogonal_offset_independence':orthogonally_independent(moves)}


def coordinates(n):
    graphs=[motion_graph(m,n) for m in range(1,32)];by={g['mask']:g for g in graphs}
    edges=[]
    for a in range(1,32):
        for bit in range(5):
            b=a^(1<<bit)
            if b<=a:continue
            ga,gb=by[a],by[b]
            edges.append({'masks':[a,b],'changed_orbit_bit':bit,'changed_orbit':list(L.ORBITS[bit]),
                          'edge_symmetric_difference':gb['directed_edges']-ga['directed_edges'],
                          'component_counts':[len(ga['components']),len(gb['components'])],
                          'same_component_partition':ga['components']==gb['components'],
                          'parity_boundary':ga['single_parity']!=gb['single_parity'],
                          'no_mate_sufficient_condition':[ga['orthogonal_offset_independence'],gb['orthogonal_offset_independence']]})
    squares=n*n;nonadj=sum(not adjacent(xy(k,n),xy(v,n)) for k,v in itertools.permutations(range(squares),2))
    return {'board_size':n,'graphs':graphs,'singlebit_edges':edges,
            'physical_configuration_bounds':{'labelled_K0_A0_K1_side':2*squares*(squares-1)*(squares-2),
              'plus_captured_A_bareKings_side':2*squares*(squares-1),
              'nonadjacent_K0_K1_pairs':nonadj,'nonadjacent_three_piece_with_side':2*nonadj*(squares-2),
              'scope':'Static placements, not reachable states or histories. No auxiliary/hand/promotion in this exact experiment; full generated domain unchanged.'},
            'history_bound':{'max_ply':64,'repetition_limit':4,'coarse_max_branch':8+max(len(L.offsets(m)) for m in range(1,32)),
                            'coarse_max_action_sequences_through_H64':str(sum((8+max(len(L.offsets(m)) for m in range(1,32)))**d for d in range(65))),
                            'reason':'At most8King+24ordinary leaps on attacking turn; defender8. This loose tree bound is not a measured reachable-history count, complexity, runtime or independent samples.'}}


def cells(spec,n):
    k,a,v=spec;b=[None]*(n*n)
    for index,owner,tid in ((k,0,'K'),(a,0,'A'),(v,1,'K')):b[index]=L.Piece(owner,tid,tid)
    return tuple(tuple(b[n*y:n*y+n]) for y in range(n))


def template(mask,n,spec):
    r=singleton_rule(mask,0)
    return replace(r,board_size=n,initial_position=cells(spec,n),initial_setup_options=(),
                   drop_allowed={'A':((False,)*(n*n),)*2})


def common_candidates(a,b,n):
    # Both Kings must be safe in a fresh compiler initial setup. This differs
    # from a static placement with a checked side to move or from a played prefix.
    large=set(L.offsets(a))|set(L.offsets(b))
    return [s for s in itertools.permutations(range(n*n),3)
            if not adjacent(xy(s[0],n),xy(s[2],n))
            and (xy(s[2],n)[0]-xy(s[1],n)[0],xy(s[2],n)[1]-xy(s[1],n)[1]) not in large]


def paired_run(output,cap=900):
    if output.exists():raise ValueError('new immutable output directory required')
    output.mkdir(parents=True);start=now();tick=time.perf_counter();n=4
    plan={'started_at':start,'question':'Does a fixed onebit change separate empty motion connectivity from same-mu literal immediate scoring opportunities?',
          'pairs':PAIRS,'selection':'Preregistered exposed mechanism pairs, not blind or label-selected holdout.',
          'mu':'For EACHpair: uniform over common fresh initial physical placements admitted by BOTH exact complete rules; same mover0/maxply64/repeat4, no fabricated cross-rule record replay.',
          'cap_seconds':cap,'expected_seconds':180,'source_sha256':L.sha(Path(__file__)),
          'stop':'all3pairs complete or first mismatch/stop/cap; missing rows UNKNOWN, no extension/refill.',
          'labels':'Only literal oneply Core scoring children; absent witness UNKNOWN for eventual cooperation except scoped no-mate theorem, no minimax/fork/allhistory solver or Player.'}
    write_json(output/'plan.json',plan)
    coord={str(z):coordinates(z) for z in (3,4,5)};write_json(output/'coordinates.json',coord)
    totals={'roots':0,'Core_children':0,'GameSession_records':0};pairs=[];failure=None
    try:
      for a,b in PAIRS:
        if session.stopped() or time.perf_counter()-tick>=cap:raise TimeoutError('cap or scoped stop')
        candidates=common_candidates(a,b,n);approved=[];refused=[];compiled=[]
        # Compiler still owns admission: geometry only proposes common candidates.
        # A fixed safe nonterminal template compiles; per-state Core checks then
        # classify admission, and the complete option collection is compiled below.
        for mask in (a,b):
            c=None
            for spec in candidates:
                try:c=L.compile_rule(template(mask,n,spec));break
                except ValueError:continue
            if c is None:raise ValueError('no compiler-admitted anchor')
            compiled.append(c)
        for spec in candidates:
            statuses=[]
            for c in compiled:
                p=replace(c.initial_position,board=tuple(z for row in cells(spec,n) for z in row));e=semantic_engine_for(c)
                statuses.append({'safe':not e.in_check(p,0) and not e.in_check(p,1),'has_action':e.has_legal_action(p)})
            if all(z['safe'] and z['has_action'] for z in statuses):approved.append(spec)
            else:refused.append({'placement':spec,'admission_checks':statuses})
        fixed={'masks':[a,b],'board_size':n,'candidate_count':len(candidates),'common_support':approved,
               'common_support_sha256':digest(approved),'admission_refused':refused,
               'same_physical_mu_not_same_rule_fingerprint':True,'side_to_move':0,'remaining_plies':64,'repetition_limit':4,
               'forecast_before_features':{'both_no_mate':a==4 or b==17,'at_least_one_positive_larger':b==5,
                                          'event':'existence of atmostoneply scoring path on wholecommonfresh support; not probability ofeventualcooperation/strategicWDL'}}
        write_json(output/f'pair-{a}-{b}-frozen.json',fixed)
        rr=[];cs=[]
        for mask in (a,b):
            r=replace(template(mask,n,approved[0]),initial_setup_options=tuple(RuleInitialSetupOption('s-'+'-'.join(map(str,s)),cells(s,n)) for s in approved[1:]))
            rr.append(r);write_json(output/f'rule-{a}-{b}-{mask}.json',L.ruleset_to_dict(r,include_metadata=True));cs.append(L.compile_rule(r))
        rows=[];pair_start=time.perf_counter()
        for index,spec in enumerate(approved):
            if session.stopped() or time.perf_counter()-tick>=cap:raise TimeoutError('cap or scoped stop')
            key=None if index==0 else 's-'+'-'.join(map(str,spec));views=[]
            for mask,c,r in zip((a,b),cs,rr,strict=True):
                ss=L.GameSession(c,key);children=L.legal_successors(ss.state,c)
                view={'mask':mask,'fingerprint':L.compute_fingerprint(r),'record':L.record_value(ss.to_record()),
                      'state_sha256':L.state_sha(ss.state),'full_state':L.record_value(ss.state),
                      'children':[{'action':L.record_value(ac),'state_sha256':L.state_sha(ch),'terminal':L.record_value(ch.terminal_status)} for ac,ch in children]}
                write_json(output/'latest-return.json',view)  # preserve before assertions
                views.append(view);totals['roots']+=1;totals['Core_children']+=len(children);totals['GameSession_records']+=1
                assert not ss.state.terminal_status.is_terminal
            row={'placement':spec,'initial_setup_key':key,'views':views,
                 'oneply_scoring':[any(z['terminal']['winner'] is not None for z in v['children']) for v in views],
                 'eventual_cooperation':['FALSE_SCOPED_THEOREM' if orthogonally_independent(L.offsets(m)) else 'UNKNOWN' for m in (a,b)]}
            rows.append(row)
            if index==127:
                actual=time.perf_counter()-pair_start
                write_json(output/f'cost-first128-{a}-{b}.json',{'actual_pairs':128,'seconds':actual,'entire_pair_estimate_seconds':actual*len(approved)/128,'cap_unchanged':cap,'is_guaranteed_upper_bound':False})
            if (index+1)%256==0:
                write_json(output/f'rows-{a}-{b}.json',{'status':'RUNNING','rows':rows});print({'pair':[a,b],'completed':index+1,'total':len(approved),'seconds':time.perf_counter()-tick},flush=True)
        summary={'masks':[a,b],'same_mu_count':len(rows),'oneply_scoring_counts':[sum(r['oneply_scoring'][i] for r in rows) for i in (0,1)],
                 'joint_oneply_counts':dict(Counter(str(r['oneply_scoring']) for r in rows)),'seconds':time.perf_counter()-pair_start,
                 'common_support_sha256':fixed['common_support_sha256'],'rule_fingerprints':[L.compute_fingerprint(r) for r in rr]}
        pairs.append(summary);write_json(output/f'rows-{a}-{b}.json',{'status':'CLOSED','summary':summary,'rows':rows});print(summary,flush=True)
    except Exception as exc:
        failure={'error':repr(exc),'at':now()};write_json(output/'failure.json',failure)
        raise
    finally:
        result={'status':'CLOSED' if failure is None and len(pairs)==len(PAIRS) else 'INCOMPLETE','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'pairs':pairs,'counts':totals,'failure':failure,'Player_calls':0,'solver_calls':0,'source_sha256':L.sha(Path(__file__))}
        write_json(output/'results.json',result);print(result,flush=True)
    return result





def minimal_mating_masks():
    """Minimal orbit conflicts under inclusion, restricted to the five orbits."""
    return [m for m in range(1,32) if not orthogonally_independent(L.offsets(m))
            and all(orthogonally_independent(L.offsets(m^(1<<bit)))
                    for bit in range(5) if m&(1<<bit) and m!=(1<<bit))]


def corner_catalog(output):
    """Five finite local certificates plus a monotone corner embedding proof.

    These are synthetic checked positions. They are NOT admitted initial records,
    reachable-state counts, whole-history cooperative rates or minimax labels.
    """
    from generic_chess.core.identity import repetition_identity_key
    from generic_chess.core.position import HistoryRecord
    start=now();tick=time.perf_counter();small=[];qualified=[]
    for mask in minimal_mating_masks():
        examples=[s for s in itertools.permutations(range(9),3) if s[2]==0
                  and not adjacent(xy(s[0],3),xy(s[2],3))
                  and (-xy(s[1],3)[0],-xy(s[1],3)[1]) in L.offsets(mask)
                  and not escapes(xy(s[0],3),xy(s[1],3),xy(s[2],3),set(L.offsets(mask)),3)]
        if not examples:raise ValueError('no3x3cornercertificate')
        spec=examples[0];small.append({'minimal_mask':mask,'placement3':spec,
                                      'coordinates':[xy(z,3) for z in spec]})
    for mask in range(1,32):
        if orthogonally_independent(L.offsets(mask)):continue
        primitive=next(x for x in small if mask&x['minimal_mask']==x['minimal_mask'])
        for n in (3,4,5):
            # Bare-Kings admission supplies the same movement/terminal semantics.
            # Declared A is absent at this valid source, then inserted ONLY into
            # the synthetic local Position. Reachability from this source is
            # explicitly false: it is not an alternate legal initial setup.
            raw=template(mask,n,(0,1,n*n-1))
            board=[list(row) for row in raw.initial_position]
            board[0][1]=None
            raw=replace(raw,initial_position=tuple(map(tuple,board)))
            c=L.compile_rule(raw)
            spec=tuple(n*y+x for x,y in primitive['coordinates'])
            pos=replace(c.initial_position,board=tuple(z for row in cells(spec,n) for z in row),side_to_move=1)
            e=semantic_engine_for(c);key=repetition_identity_key(pos,c);hist=(HistoryRecord(key,-1,'',False),)
            observed={'mask':mask,'board_size':n,'source_minimal_mask':primitive['minimal_mask'],
                      'placement':spec,'position':L.record_value(pos),'fingerprint':pos.ruleset_fingerprint,
                      'check':e.in_check(pos,1),'legal_actions':L.record_value(tuple(e.legal_actions(pos))),
                      'terminal':L.record_value(e.terminal_result(pos,0,((key,1),),hist)),
                      'synthetic_history_not_reachable':True}
            qualified.append(observed);write_json(output,{'status':'RUNNING','rows':qualified,'minimal':small})
            assert observed['check'] and not observed['legal_actions'] and observed['terminal']=={'status':'checkmate','winner':0}
    r={'status':'PASS','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'minimal':small,'rows':qualified,
       'scope':'Exact5orbit mask vocabulary, square boardn>=3, K+A0 vsK1, ordinary fixedleaps, King8neighbors, remove/noextraeffect. All31 masks classified for STATIC mate capacity, not any particular initialmu/history or winning region.',
       'proof':'If offsets are orthogonally independent, each available orthogonal victim neighbor is not attacked by A while victim is checked; choose neighbor perpendicular to a coordinate on which Kings are separated by>=2, preserving separation. Capture A removes its attack. Conversely each nonindependentmask includes one of five minimal masks, each has retained3x3cornercheckmate. Added Aoffsets only remove bareKing escapes; embed same corner/threepieces on anyn>=3 without adding cornerKingneighbors.',
       'theorem_negative_masks':[m for m in range(1,32) if orthogonally_independent(L.offsets(m))],
       'synthetic_only':True,'independent_game_engine':False,'Player_calls':0,'solver_calls':0}
    write_json(output,r);return r


def physical_action(raw,n):
    return (raw['actor_type_id'],raw['from_square']['rank']*n+raw['from_square']['file'],
            raw['to_square']['rank']*n+raw['to_square']['file'],raw['promotion_target_id'])


def integer_actions(spec,mask,side,n):
    """Separate scoped integer model for K0+A0 vs K1, no history/extra rules."""
    k,a,v=spec;out=[]
    for tid,source,moves in ((('K',k,L.offsets(3)),('A',a,L.offsets(mask))) if side==0 else (('K',v,L.offsets(3)),)):
        if source is None:continue
        x,y=xy(source,n)
        for dx,dy in moves:
            xx,yy=x+dx,y+dy
            if not(0<=xx<n and 0<=yy<n):continue
            dest=n*yy+xx
            if side==0:
                if dest in (k,a,v):continue
                after=(dest,a,v) if tid=='K' else (k,dest,v)
                if adjacent(xy(after[0],n),xy(v,n)):continue
            else:
                if dest in (k,v):continue
                aa=None if dest==a else a
                after=(k,aa,dest)
                if adjacent(xy(k,n),(xx,yy)):continue
                if aa is not None and (xx-xy(aa,n)[0],yy-xy(aa,n)[1]) in L.offsets(mask):continue
            out.append(((tid,source,dest,None),after))
    return sorted(out)


def integer_terminal(spec,mask,side,n):
    if integer_actions(spec,mask,side,n):return {'status':'ongoing','winner':None}
    k,a,v=spec
    checked=(adjacent(xy(k,n),xy(v,n)) or (side==1 and a is not None
             and (xy(v,n)[0]-xy(a,n)[0],xy(v,n)[1]-xy(a,n)[1]) in L.offsets(mask)))
    return {'status':'checkmate' if checked else 'stalemate','winner':1-side if checked else None}


def qualify_pairs(directory,output):
    """Full retained integer frontier control plus distinct public Core replay."""
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.transition import apply_action
    if output.exists() or output.with_suffix('.returns.jsonl').exists():raise ValueError('fresh qualification output required')
    start=now();tick=time.perf_counter();summaries=[];total=Counter();examples=[]
    for a,b in PAIRS:
        data=L.load(directory/f'rows-{a}-{b}.json');frozen=L.load(directory/f'pair-{a}-{b}-frozen.json');n=4
        rules=[L.ruleset_from_dict(L.load(directory/f'rule-{a}-{b}-{m}.json')) for m in (a,b)]
        cs=list(map(L.compile_rule,rules));count=Counter();branch=[Counter(),Counter()];term=[Counter(),Counter()];action_changes=Counter()
        assert digest([r['placement'] for r in data['rows']])==frozen['common_support_sha256']
        for row in data['rows']:
            childmaps=[];physical=row['placement']
            for i,(mask,c,rr,v) in enumerate(zip((a,b),cs,rules,row['views'],strict=True)):
                ss=L.GameSession.replay(c,L.deserialize_game_record(__import__('json').dumps(v['record'])))
                assert L.record_value(ss.state)==v['full_state'] and L.state_sha(ss.state)==v['state_sha256']
                assert c.initial_position.ruleset_fingerprint==v['fingerprint']==L.compute_fingerprint(rr)
                expected=dict(integer_actions(physical,mask,0,n))
                retained={physical_action(z['action'],n):z for z in v['children']}
                assert len(retained)==len(v['children']) and set(expected)==set(retained)
                actual={physical_action(L.record_value(z),n):z for z in legal_actions(ss.state,c)}
                assert set(actual)==set(expected)
                branch[i][len(actual)]+=1
                for key,childspec in expected.items():
                    child=apply_action(ss.state,actual[key],c);z=retained[key]
                    observed={'pair':[a,b],'placement':physical,'mask':mask,'physical_action':key,'child_state_sha256':L.state_sha(child),'terminal':L.record_value(child.terminal_status)}
                    with output.with_suffix('.returns.jsonl').open('a',encoding='utf-8') as log:
                        log.write(__import__('json').dumps(observed,sort_keys=True)+'\n')
                    assert observed['child_state_sha256']==z['state_sha256'] and observed['terminal']==z['terminal']==integer_terminal(childspec,mask,1,n)
                    count['integer_and_public_Core_edges']+=1;term[i][z['terminal']['status']]+=1
                childmaps.append(retained);count['complete_initial_records']+=1
            low,high=childmaps
            assert set(low)<=set(high)  # scoped own-turn action monotonicity ONLY
            common=set(low)&set(high);added=set(high)-set(low)
            count['shared_physical_actions']+=len(common);count['added_physical_actions']+=len(added)
            oldwins={k for k in low if low[k]['terminal']['winner'] is not None};newwins={k for k in high if high[k]['terminal']['winner'] is not None}
            assert oldwins<=newwins
            for key in newwins:
                action_changes['new_mate_from_shared_action' if key in common else 'new_mate_from_added_action']+=1
                if len(examples)<4 and a==1 and b==5:
                    examples.append({'placement':physical,'physical_action':key,'class':'shared_action_changed_threat' if key in common else 'added_action','records':[v['record'] for v in row['views']],'fingerprints':[v['fingerprint'] for v in row['views']]})
            for key in common:
                if low[key]['terminal']!=high[key]['terminal']:
                    action_changes[low[key]['terminal']['status']+'->'+high[key]['terminal']['status']]+=1
            count['common_roots']+=1
        summary={'masks':[a,b],'counts':dict(count),'root_branch_histograms':[dict(x) for x in branch],'oneply_terminal_histograms':[dict(x) for x in term],'mechanism_counts':dict(action_changes)}
        summaries.append(summary);total.update(count);write_json(output,{'status':'RUNNING','pairs':summaries,'examples':examples})
        print(summary,flush=True)
    result={'status':'PASS','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'pairs':summaries,'totals':dict(total),'examples':examples,
            'scope':'Two routes: independent scoped integer frontier/terminal model plus public Core legal_actions/apply_action on every retained complete initial record. Shared compiler/Core engine; not an independent game engine or all-history oracle. Physical action mapping only; fingerprints/history keys remain rule-specific.','new_Player_calls':0,'solver_calls':0}
    write_json(output,result);return result


def mutation_stalemate_witness(output):
    """One fixed three-ply all-defenses local certificate; no graph solver.

    The candidate was found by a deterministic scoped integer search, hence is
    a discovered mechanism example, not a frozen held-out predictive success.
    """
    start=now();tick=time.perf_counter();spec=(0,5,3);rows=[]
    for mask in (3,7):
        r=template(mask,4,spec);c=L.compile_rule(r);ss=L.GameSession(c);root=L.record_value(ss.to_record());rootstate=L.record_value(ss.state)
        act=next(ac for ac in ss.legal_actions() if physical_action(L.record_value(ac),4)==('K',0,1,None))
        ss.submit(act);afterfirst=L.record_value(ss.state);replies=[L.record_value(z) for z in ss.legal_actions()]
        observed={'mask':mask,'rule':L.ruleset_to_dict(r,include_metadata=True),'root_record':root,'root_state':rootstate,
                  'after_shared_first_record':L.record_value(ss.to_record()),'after_shared_first_state':afterfirst,'replies':replies}
        rows.append(observed);write_json(output,{'status':'RUNNING','rows':rows})
        if mask==3:
            assert len(replies)==1 and physical_action(replies[0],4)==('K',3,7,None)
            ss.submit(ss.legal_actions()[0]);ss.submit(next(ac for ac in ss.legal_actions() if physical_action(L.record_value(ac),4)==('A',5,6,None)))
            observed['forced_threeply_record']=L.record_value(ss.to_record());observed['final_state']=L.record_value(ss.state)
            write_json(output,{'status':'RUNNING','rows':rows})
            assert ss.state.terminal_status.status.value=='checkmate' and ss.result.winner==0
        else:
            assert not replies and ss.state.terminal_status.status.value=='stalemate' and ss.result.winner is None
    result={'status':'PASS','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'rows':rows,
            'scope':'Rule3 to7 adds only orbit(2,0), allothersemantics/initialboard/clock64/repeat4 identical. Fixedlegal shared firstKingmove has WIN for0 at3 via one forceddefenderreply+literal mate, but DRAW at7 via immediate stalemate. LowerrootWIN; higherrootWDL UNKNOWN, so NOT a rootWDL monotonicity counterexample.','reason':'Additional attacks remove the last defender escape without checking its current square. Under stalemateDRAW, action-level value need not improve when attacking movement grows.','independent_AUX_review':'PENDING','new_Player_calls':0,'solver_calls':0}
    write_json(output,result);return result


def scale_profiles(output,plan_path):
    """Fixed twelve-rule mechanism casebook, literal one-ply only.

    Raw returns stay private before interpretation. Compact per-root features
    and full factorized scientific inputs make the finite claims reproducible.
    """
    import json
    if output.exists():raise ValueError('fresh output directory required')
    output.mkdir(parents=True);plan=L.load(plan_path);start=now();tick=time.perf_counter();cap=plan['producer_cap_seconds'];palette=plan['palette']
    write_json(output/'plan.json',{**plan,'execution_started_at':start,'source_sha256':L.sha(Path(__file__))})
    counts=Counter();summaries=[];failure=None;completed=[];coordinate_times=Counter()
    try:
      for n in (4,5):
        candidates=common_candidates(31,31,n)
        support=[s for s in candidates if all(integer_actions(s,m,0,n) for m in range(1,32))]
        assert len(support)==plan['counts'][str(n)]['global_common_admitted']
        write_json(output/f'common-mu-{n}.json',{'board_size':n,'support':support,'uniform_denominator':len(support),'support_sha256':digest(support),
                    'definition':'Complete fresh setups safe and nonstalemated for ALL31masks, independently of actual oneply labels; not eachrule ownmu.',
                    'side':0,'max_ply':64,'repeat':4})
        for mask in palette:
            if session.stopped() or time.perf_counter()-tick>=cap:raise TimeoutError('fixed producer cap or scoped stop')
            prep_tick=time.perf_counter()
            r=replace(template(mask,n,support[0]),initial_setup_options=tuple(RuleInitialSetupOption('s-'+'-'.join(map(str,s)),cells(s,n)) for s in support[1:]))
            raw=L.ruleset_to_dict(r,include_metadata=True);fp=L.compute_fingerprint(r)
            write_json(output/f'actual-rule-{n}-{mask}.json',raw)
            c=L.compile_rule(r);assert c.initial_position.ruleset_fingerprint==fp
            preparation_seconds=time.perf_counter()-prep_tick
            features=[];per=Counter();core_seconds=0.;integer_seconds=0.;run_tick=time.perf_counter()
            rawpath=output/f'Core-returns-{n}-{mask}.jsonl'
            with rawpath.open('x',encoding='utf-8') as log:
              for index,spec in enumerate(support):
                if session.stopped() or time.perf_counter()-tick>=cap:raise TimeoutError('fixed producer cap or scoped stop')
                key=None if index==0 else 's-'+'-'.join(map(str,spec))
                query_tick=time.perf_counter();ss=L.GameSession(c,key);children=L.legal_successors(ss.state,c);core_seconds+=time.perf_counter()-query_tick
                observed={'n':n,'mask':mask,'support_index':index,'placement':spec,'fingerprint':fp,'full_initial_record':L.record_value(ss.to_record()),'initial_state_sha256':L.state_sha(ss.state),
                           'children':[{'action':L.record_value(ac),'terminal':L.record_value(ch.terminal_status),'state_sha256':L.state_sha(ch)} for ac,ch in children]}
                log.write(json.dumps(observed,separators=(',',':'))+'\n');log.flush()
                # Distinct integer geometry does not use Core children to produce
                # its own proposed frontier or terminal classification.
                integer_tick=time.perf_counter();expected=integer_actions(spec,mask,0,n)
                expected_terms={ac:integer_terminal(child,mask,1,n) for ac,child in expected}
                integer_seconds+=time.perf_counter()-integer_tick
                actual={physical_action(z['action'],n):z['terminal'] for z in observed['children']}
                assert len(actual)==len(children) and actual==expected_terms
                terminal_counts=Counter(z['status'] for z in actual.values());mate=terminal_counts['checkmate'];stale=terminal_counts['stalemate']
                f={'support_index':index,'placement':spec,'state_sha256':observed['initial_state_sha256'],'branch':len(children),'ordinary_moves':sum(ac[0]=='A' for ac in actual),'king_moves':sum(ac[0]=='K' for ac in actual),'mate_children':mate,'stalemate_children':stale,'literal_oneply_scoring':mate>0}
                features.append(f);per['roots']+=1;per['Core_children']+=len(children);per['roots_with_immediate_mate']+=int(mate>0);per['mate_children']+=mate;per['stalemate_children']+=stale
                counts['roots']+=1;counts['Core_children']+=len(children)
                if index==127:
                    actual_seconds=time.perf_counter()-run_tick
                    forecast=(actual_seconds/128)*(len(support)-128)*(len(palette)-palette.index(mask))
                    write_json(output/f'first128-cost-{n}-{mask}.json',{'actual_roots':128,'actual_seconds_including_capture_and_integer_validation':actual_seconds,'current_size_remaining_estimate_seconds':forecast,'producer_cap_seconds_unchanged':cap,'sampled_not_guaranteed_bound':True})
                if (index+1)%1024==0:print({'n':n,'mask':mask,'roots':index+1,'total':len(support),'whole_seconds':time.perf_counter()-tick},flush=True)
            summary={'n':n,'mask':mask,'fingerprint':fp,'support_sha256':digest(support),'counts':dict(per),'branch_histogram':dict(Counter(x['branch'] for x in features)),
                     'root_event_rate':str(__import__('fractions').Fraction(per['roots_with_immediate_mate'],len(features))),
                     'mean_branch':str(__import__('fractions').Fraction(per['Core_children'],len(features))),
                     'preparation_seconds':preparation_seconds,'whole_rule_query_record_validate_seconds':time.perf_counter()-run_tick,'inner_Core_seconds':core_seconds,'inner_integer_seconds':integer_seconds,
                     'source_raw_sha256':L.sha(rawpath),'raw_bytes':rawpath.stat().st_size}
            write_json(output/f'features-{n}-{mask}.json',{'status':'CLOSED','summary':summary,'rows':features})
            summaries.append(summary);completed.append([n,mask]);print(summary,flush=True)
    except Exception as exc:
        failure={'error':repr(exc),'observed_at':now(),'completed':completed};write_json(output/'failure.json',failure)
        raise
    finally:
        result={'status':'CLOSED' if failure is None and len(completed)==24 else 'INCOMPLETE','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'summaries':summaries,'counts':dict(counts),'failure':failure,'Player_calls':0,'solver_calls':0,'source_sha256':L.sha(Path(__file__)),'labels':'Only literaloneply events at exactlyregistered freshmu. No absent-witness=>deadzone claim; no allhistory/minimax/fork truth.'}
        write_json(output/'results.json',result);print({k:v for k,v in result.items() if k!='summaries'},flush=True)
    return result


def analyze_scale(directory,output):
    import json
    from fractions import Fraction as F
    start=now();tick=time.perf_counter();report=L.load(directory/'results.json');assert report['status']=='CLOSED'
    support4=L.load(directory/'common-mu-4.json')['support'];embedded={tuple(5*(z//4)+z%4 for z in s) for s in support4};summaries=[];mu_comparisons=[]
    for summary in report['summaries']:
        n,m=summary['n'],summary['mask'];features=L.load(directory/f'features-{n}-{m}.json')['rows'];byindex={r['support_index']:r for r in features}
        physical={};histories=set();weighted_mate=F(0);all_edges=0;mate_edges=0
        path=directory/f'Core-returns-{n}-{m}.jsonl';assert L.sha(path)==summary['source_raw_sha256']
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                r=json.loads(line);assert r['fingerprint']==summary['fingerprint'];row=byindex[r['support_index']];k,a,v=r['placement'];assert row['placement']==r['placement']
                for ch in r['children']:
                    tid,source,dest,_=physical_action(ch['action'],n);after=(dest,a,v) if tid=='K' else (k,dest,v)
                    term=ch['terminal']['status'];previous=physical.setdefault(after,term);assert previous==term
                    assert ch['state_sha256'] not in histories;histories.add(ch['state_sha256'])
                    all_edges+=1;mate_edges+=int(term=='checkmate')
                weighted_mate+=F(row['mate_children'],row['branch'])/len(features)
        assert all_edges==len(histories)==summary['counts']['Core_children']
        hist=Counter(physical.values());summaries.append({'n':n,'mask':m,'initial_mu_count':len(features),'oneply_full_history_count':len(histories),'oneply_unique_physical_positions':len(physical),
            'oneply_history_to_position_ratio':str(F(len(histories),len(physical))),
            'literal_mate_event_rates':{'uniform_initial_then_uniform_action':str(weighted_mate),'uniform_all_edges_or_fullhistories1':str(F(mate_edges,all_edges)),'uniform_unique_physical_children':str(F(hist['checkmate'],len(physical)))},
            'physical_terminal_counts':dict(hist),'clock':{'ply':1,'remaining':63,'repeat_limit':4},'label_transfer':'SamephysicalchildterminalconsistentHERE, not arbitraryhistoryWDL equivalence; differentrootprefixes retained in allfullstatehashes.'})
        if n==5:
            selected=[r for r in features if tuple(r['placement']) in embedded];assert len(selected)==len(support4)
            old=L.load(directory/f'features-4-{m}.json')['rows'];oldmap={tuple(5*(z//4)+z%4 for z in r['placement']):r for r in old}
            flips=Counter((oldmap[tuple(r['placement'])]['literal_oneply_scoring'],r['literal_oneply_scoring']) for r in selected)
            mu_comparisons.append({'mask':m,'same_coordinate_embedding_support':len(selected),'4x4_original_mu_mate_roots':sum(r['literal_oneply_scoring'] for r in old),'5x5_embedded_mu_mate_roots':sum(r['literal_oneply_scoring'] for r in selected),'5x5_own_global_common_mu_count':len(features),'5x5_own_global_common_mu_mate_roots':sum(r['literal_oneply_scoring'] for r in features),'joint_root_event_counts':{str(k):v for k,v in flips.items()},'reason':'Changingboardaddsphysicaldestinations while preservingoldcoordinateplacements; own5x5mu additionally changesweight/support. Neither is a onebit-only contrast.'})
    r={'status':'PASS','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'root_counts':report['counts'],'state_history_coordinates':summaries,'board_embedding_and_mu':mu_comparisons,
       'scope':'Literaldepth1properties underexplicitfinite mu, not independent-rule calibration, policyoccupancy, wholegraphreachability, minimaxtruth or solverdifficulty. Fullhistorycounts are actuallyobserved from freshroots, not projectedtimesupperbound.',
       'raw_queries_reused':True,'new_Core_queries':0,'new_Player_queries':0}
    write_json(output,r);return r


def branch_law(directory,output):
    """Pointwise orbit-additive LEGAL COUNT under fixed safe singleton setups.

    This is not linear piece value, payoff, quantity conservation or a generic
    semantic compiler shortcut. Admission must be common and side0 safe.
    """
    from fractions import Fraction as F
    start=now();tick=time.perf_counter();rows=[]
    for n in (4,5):
        singles={m:L.load(directory/f'features-{n}-{m}.json')['rows'] for m in (1,2,4,8,16)}
        king=[r['king_moves'] for r in singles[1]];N=len(king)
        for bit in singles:assert [r['king_moves'] for r in singles[bit]]==king
        coefficients={str(bit):str(F(sum(r['ordinary_moves'] for r in rr),N)) for bit,rr in singles.items()}
        candidates=[];max_error=0
        for mask in L.load(directory/'plan.json')['palette']:
            actual=L.load(directory/f'features-{n}-{mask}.json')['rows']
            predicted=[king[i]+sum(singles[1<<b][i]['ordinary_moves'] for b in range(5) if mask&(1<<b)) for i in range(N)]
            errors=[a['branch']-p for a,p in zip(actual,predicted,strict=True)];max_error=max(max_error,max(map(abs,errors)))
            candidates.append({'mask':mask,'root_rows':N,'max_absolute_branch_error':max(map(abs,errors)),'mean_branch':str(F(sum(predicted),N))})
        assert max_error==0
        rows.append({'n':n,'common_mu_count':N,'king_intercept_mean':str(F(sum(king),N)),'orbit_coefficients_mean':coefficients,'casebook_validation':candidates,'no_New_Core_or_Player_calls':True,
                     'law':'b(s,mask)=b_K(s)+sum_i bit_i(mask)*b_A_orbit_i(s); all nontarget occupied squares excluded, opponent only fixedKing, ownKing remains safe. Ordinary orbits have disjoint destinations; King legal set independent of ordinary offset vocabulary at admitted root.'})
    result={'status':'PASS','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'rows':rows,'scope':'Exactpointwise branchcount identity for this pureKAK, freshsafe commonphysicalmu. Read after labels as explanatoryalgebra, not blindfit. Does not forecast deeperpositions/searchcost/WDL or material prices; no default activation.'}
    write_json(output,result);return result


def cost_summary(directory,output):
    import json,statistics
    from fractions import Fraction as F
    from generic_chess.session.session import GameSession
    start=now();tick=time.perf_counter();inputdata=L.load(directory/'inputs.json');metadata=L.load(directory/'metadata.json')['rows'];meta={r['seed']:r for r in metadata};worlds={r['seed']:r for r in inputdata['worlds']};allrows=[];bybudget=[];qualification=Counter()
    for budget in (512,2048,8192):
        p=L.load(directory/f'N{budget}.json');assert not p['failures']
        assert p['protocol']['nodes']==budget and p['protocol']['evaluation_backend']=='unit' and p['protocol']['qdepth']==0
        group=[]
        for row in p['rows']:
            w=worlds[row['seed']];r=L.ruleset_from_dict(w['rule']);c=L.compile_rule(r);ss=GameSession.replay(c,L.deserialize_game_record(json.dumps(w['roots'][0]['record'])))
            assert L.state_sha(ss.state)==meta[row['seed']]['full_state_sha256'] and L.compute_fingerprint(r)==meta[row['seed']]['fingerprint']
            d=row['decision'];assert d['runtime_depth_balanced'] and d['nodes']<=budget
            root_actions={physical_action(L.record_value(a),r.board_size):a for a in ss.legal_actions()}
            selected=physical_action(d['action'],r.board_size);assert selected in root_actions
            assert not d['principal_variation'] or physical_action(d['principal_variation'][0],r.board_size)==selected
            for action in d['principal_variation']:
                assert not ss.result.status.value in ('checkmate','stalemate','max_ply','repetition')
                ss.submit(L.match_action(ss,action));qualification['PV_plies']+=1
            qualification['queries']+=1
            rr={**meta[row['seed']],'budget':budget,'variant':row['variant'],'root_branch':len(root_actions),'nodes':d['nodes'],'completed_depth':d['completed_depth'],'selective_depth':d['selective_depth'],'qnodes':d['qnodes'],'seconds':row['query_seconds'],'termination_reason':d['termination_reason'],'score':d['score'],'physical_action':selected,'provider_available':row['provider_available'],'native_calls':d['native_legality_calls'],'native_fallbacks':d['native_legality_fallbacks'],'result_source':d['result_source']}
            group.append(rr);allrows.append(rr)
        summary={'budget':budget,'planned':p['protocol']['planned_queries'],'observed':len(group),'missing':p['missing_slots'],'batch_wall_seconds':p['wall_seconds'],'termination_counts':dict(Counter(r['termination_reason'] for r in group)),'by_backend':{v:{'queries':sum(r['variant']==v for r in group),'sum_query_seconds':sum(r['seconds'] for r in group if r['variant']==v),'depth_histogram':dict(Counter(r['completed_depth'] for r in group if r['variant']==v)),'provider_unavailable':sum(not r['provider_available'] for r in group if r['variant']==v),'native_fallbacks':sum(r['native_fallbacks'] for r in group if r['variant']==v)} for v in ('core','all')}}
        bybudget.append(summary)
    paired=[];examples=[]
    for budget in (512,2048,8192):
        rows=[r for r in allrows if r['budget']==budget];a={r['seed']:r for r in rows if r['variant']=='core'};b={r['seed']:r for r in rows if r['variant']=='all'}
        for seed in sorted(set(a)&set(b)):
            x,y=a[seed],b[seed];same_work=(x['nodes']==y['nodes'] and x['completed_depth']==y['completed_depth']);same_score_action=(x['score']==y['score'] and x['physical_action']==y['physical_action'])
            paired.append({'budget':budget,'seed':seed,'same_nodes_and_depth':same_work,'same_score_and_physical_action':same_score_action,'time_ratio_core_over_native':x['seconds']/y['seconds'],'time_censor':x['termination_reason']=='time_limit' or y['termination_reason']=='time_limit'})
        for x in rows:
            for y in rows:
                if x['variant']!=y['variant'] or x['seed']>=y['seed'] or x['n']!=y['n'] or x['fixture']!=y['fixture'] or x['fixture']=='discovered-stalemate-mechanism':continue
                if x['root_branch']>y['root_branch'] and x['completed_depth']>y['completed_depth'] and not any(r['termination_reason']=='time_limit' for r in (x,y)):
                    if len(examples)<6:examples.append({'larger_branch_deeper_completed':x,'smaller_branch_shallower_completed':y})
    result={'status':'PASS','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'by_budget':bybudget,'qualification':dict(qualification),'rows':allrows,'backend_pairs':paired,'nonmonotone_branch_depth_examples':examples,
            'scope':'Finite coldPlayer/coldTT unit-leaf cost/completion observations at sharedphysicalstarts. ActualCore/Nativeavailability/fallbacks and timecensor separate. PVlegality is not all-defense proof; score/depth differences not WDL/strength/learning utility. No attempt to fit a costpredictor or refill frozen slots.'}
    write_json(output,result);return result


def property_bounds(directory,output):
    """Typed partial truth coordinates; NOT fitted probabilities or blind labels."""
    from fractions import Fraction as F
    start=now();tick=time.perf_counter();case=L.load(directory/'results.json');rows=[];total=Counter()
    for f in case['summaries']:
        n,m=f['n'],f['mask'];rr=L.load(directory/f'features-{n}-{m}.json')['rows'];N=len(rr);negative=orthogonally_independent(L.offsets(m));c=Counter()
        for r in rr:
            positive=r['mate_children']>0
            assert not(negative and positive)
            fork_positive=r['mate_children']>0 and r['stalemate_children']>0
            fork_negative=negative or r['branch']==1 or r['mate_children']==r['branch'] or r['stalemate_children']==r['branch']
            assert not(fork_positive and fork_negative)
            c['coop_literal_positive']+=int(positive);c['coop_theorem_negative']+=int(negative)
            c['fork_literal_positive']+=int(fork_positive);c['fork_negative']+=int(fork_negative)
        c['coop_UNKNOWN']=N-c['coop_literal_positive']-c['coop_theorem_negative'];c['fork_UNKNOWN']=N-c['fork_literal_positive']-c['fork_negative'];c['roots']=N;total.update(c)
        rows.append({'n':n,'mask':m,'fingerprint':f['fingerprint'],'mu_support_sha256':f['support_sha256'],'denominator':N,
          'static_mate_capacity':not negative,'static_capacity_certificate':'orthogonal-independent noMate' if negative else 'contains one of five cornercertificate primitives',
          'partial_claim_counts':dict(c),'coop_rate_bounds':[str(F(c['coop_literal_positive'],N)),str(F(N-c['coop_theorem_negative'],N))],
          'fork_rate_bounds':[str(F(c['fork_literal_positive'],N)),str(F(N-c['fork_negative'],N))],
          'scope':'Proposed theorem-bound negatives need independentAUXreview, literalpositives from actualregistered1plyCore returns. AllotherrowsUNKNOWN; samefullhistory/clockmu, notstaticallplacements or policyoutcomes. No predicted probabilities assigned.'})
    result={'status':'PASS','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'rows':rows,'counts':dict(total),'independent_AUX_truth':'NOT_IMPORTED/PENDING','new_Core_queries':0,'new_Player_queries':0}
    write_json(output,result);return result


def capacity_interaction_certificate(output):
    """Four exact mask vectors rule out any affine threshold on orbit bits."""
    from fractions import Fraction
    masks=(3,12,6,9);vectors={str(m):[(m>>i)&1 for i in range(5)] for m in masks}
    assert [a+b for a,b in zip(vectors['3'],vectors['12'])]==[a+b for a,b in zip(vectors['6'],vectors['9'])]
    labels={str(m):not orthogonally_independent(L.offsets(m)) for m in masks};assert labels=={'3':True,'12':True,'6':False,'9':False}
    coords=coordinates(4);edges=coords['singlebit_edges']
    no_mate=[m for m in range(1,32) if orthogonally_independent(L.offsets(m))]
    maximal=[m for m in no_mate if not any(m!=z and m&z==m for z in no_mate)]
    result={'status':'PASS','at':now(),'minimal_positive_masks':minimal_mating_masks(),'maximal_no_mate_masks':maximal,
            'boolean_formula':'M=(x0 AND x1) OR (x0 AND x2) OR (x1 AND x3) OR (x2 AND x3) OR (x3 AND x4)',
            'equivalent_negative':'nonempty mask is submask of9 OR17 OR22',
            'affine_threshold_impossibility':{'vectors':vectors,'capacity_labels':labels,'identity':'v3+v12=v6+v9. Any affine score has score3+score12=score6+score9. Two positive scores>=t cannot coexist with two negative scores<t. Strict-positive convention similarly impossible.','scope':'Staticmatecapacity oncomplete31maskcatalog inexactsingleton rules/n>=3; not generic price impossibility, not rule-rate/policy/WDL calibration.'},
            'singlebit_boundary_counts':{'all_edges':len(edges),'parity_boundary':sum(e['parity_boundary'] for e in edges),'capacity_boundary':sum(e['no_mate_sufficient_condition'][0]!=e['no_mate_sufficient_condition'][1] for e in edges),'parity_false_positive_edges':[e['masks'] for e in edges if e['parity_boundary'] and e['no_mate_sufficient_condition'][0]==e['no_mate_sufficient_condition'][1]],'parity_false_negative_edges':[e['masks'] for e in edges if not e['parity_boundary'] and e['no_mate_sufficient_condition'][0]!=e['no_mate_sufficient_condition'][1]]},
            'interpretation':'Rootlegalbranch is orbit-additive underfixedmu, staticcapacity requires interactions, actionvalue canregress via stalemate, and measuredsearchcost depends onmore than either coordinate. DifferentFcoordinates have differentmathematicalstructure; no scalar quality or price table fitted.'}
    write_json(output,result);return result


def history_conversion_check(witness_path,output):
    """Re-execute physical actions under each rule, never rename old hashes."""
    import json
    start=now();data=L.load(witness_path);source=data['rows'][0];target=data['rows'][1]
    low=L.compile_rule(L.ruleset_from_dict(source['rule']));high=L.compile_rule(L.ruleset_from_dict(target['rule']))
    old=L.GameSession.replay(low,L.deserialize_game_record(json.dumps(source['forced_threeply_record'])))
    expected=[physical_action(L.record_value(action),4) for action in old.to_record().actions]
    converted=L.GameSession(high);trace=[];refusal=None
    for index,physical in enumerate(expected):
        if converted.state.terminal_status.is_terminal:
            refusal={'at_source_ply':index+1,'reason':'target already terminal after convertedprefix','terminal':L.record_value(converted.result)};break
        choices=[z for z in converted.legal_actions() if physical_action(L.record_value(z),4)==physical]
        if len(choices)!=1:
            refusal={'at_source_ply':index+1,'reason':'not uniquely legal under target rule','matches':len(choices)};break
        converted.submit(choices[0]);trace.append({'source_ply':index+1,'target_record':L.record_value(converted.to_record()),'target_state_sha256':L.state_sha(converted.state)})
    assert len(trace)==1 and refusal['at_source_ply']==2 and refusal['terminal']['status']=='stalemate'
    assert converted.state.position.board==L.GameSession.replay(low,L.deserialize_game_record(json.dumps(source['after_shared_first_record']))).state.position.board
    result={'status':'PASS','started_at':start,'ended_at':now(),'trace':trace,'refusal':refusal,'source_full_record':source['forced_threeply_record'],
            'target_valid_prefix_record':L.record_value(converted.to_record()),'scope':'Physicalprefix1islegalunderboth; full3plyhistoryisNOT jointlyadmissible. Rulefingerprints/repetitionkeys/actionpatternIDs recalculated byCore; rawGameRecordcannotbeconverted byrenaming onlyfingerprint. Postprefix boardmatches but terminalvalues differ.'}
    write_json(output,result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('pairs','corners','qualify','scale','analyze','branch-law','properties','mutation'),default='pairs')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--input',type=Path)
    parser.add_argument('--plan',type=Path)
    args=parser.parse_args()
    if args.mode=='pairs':paired_run(args.output)
    elif args.mode=='corners':corner_catalog(args.output)
    elif args.mode=='mutation':mutation_stalemate_witness(args.output)
    else:
        if args.mode=='scale':
            if args.plan is None:parser.error('scale requires --plan')
            scale_profiles(args.output,args.plan)
        else:
            if args.input is None:parser.error('selected mode requires --input')
            {'qualify':qualify_pairs,'analyze':analyze_scale,'branch-law':branch_law,'properties':property_bounds}[args.mode](args.input,args.output)



def new_orbit_check(output):
    """Prospective single-primitive extrapolation; does not change ORBITS."""
    from generic_chess.core.movement import LeapAtom
    from generic_chess.core.identity import repetition_identity_key
    from generic_chess.core.position import HistoryRecord
    start=now();tick=time.perf_counter();old=tuple(L.offsets(4));new=((-3,0),(0,-3),(0,3),(3,0));vocab={'orth2':old,'orth3':new,'orth2_plus_orth3':tuple(sorted(set(old)|set(new)))}
    rows=[]
    for name,moves in vocab.items():
        if session.stopped() or time.perf_counter()-tick>=60:raise TimeoutError('bounded primitive check')
        r=template(4,4,(2,4,0));r=replace(r,piece_types=(r.piece_types[0],replace(r.piece_types[1],movement_atoms=tuple(LeapAtom(z) for z in moves))))
        c=L.compile_rule(r);ss=L.GameSession(c);record=L.record_value(ss.to_record());physical=('A',4,12,None)
        matches=[z for z in ss.legal_actions() if physical_action(L.record_value(z),4)==physical]
        row={'vocabulary':'originalfiveD4orbits+one(3,0)diagnostic','rule_name':name,'offsets':moves,'orthogonal_independence':orthogonally_independent(moves),
             'full_rule':L.ruleset_to_dict(r,include_metadata=True),'fingerprint':L.compute_fingerprint(r),'initial_record':record,'initial_state_sha256':L.state_sha(ss.state),'shared_physical_action':physical,'action_admitted':bool(matches)}
        rows.append(row);write_json(output,{'status':'RUNNING','rows':rows})
        if matches:
            assert len(matches)==1;ss.submit(matches[0]);row['after_action_record']=L.record_value(ss.to_record());row['after_action_state']=L.record_value(ss.state)
        # Same local target also checks the single3-leap control, for which the
        # proposed2-leap action is actually absent. Never forge that prefix.
        pos=replace(c.initial_position,board=tuple(z for line in cells((2,12,0),4) for z in line),side_to_move=1)
        e=semantic_engine_for(c);key=repetition_identity_key(pos,c);hist=(HistoryRecord(key,-1,'',False),)
        row['synthetic_target']={'position':L.record_value(pos),'check':e.in_check(pos,1),'legal_actions':L.record_value(e.legal_actions(pos)),'terminal':L.record_value(e.terminal_result(pos,0,((key,1),),hist)),'is_not_claimed_reachable_from_control':not bool(matches)}
        write_json(output,{'status':'RUNNING','rows':rows})
    a,b,c=rows
    assert a['orthogonal_independence'] and b['orthogonal_independence'] and not c['orthogonal_independence']
    assert a['action_admitted'] and not b['action_admitted'] and c['action_admitted']
    assert a['synthetic_target']['terminal']=={'status':'stalemate','winner':None}
    assert b['synthetic_target']['terminal']=={'status':'ongoing','winner':None}
    assert c['synthetic_target']['terminal']=={'status':'checkmate','winner':0}
    result={'status':'PASS','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'rows':rows,
            'scope':'Prospectivelyderived singleD4orbit(3,0) mechanismcheck; same4x4legalfreshstart/H64/repeat4, actualorth2actiongoesDRAW->WIN afteronly addingorth3. Ordinaryindividualoffset independenceprooftransfers, original5minimalmask catalogue notdeclared validfornewvocabulary. No blindcalibration or all63rules classification, no defaultgenerator changes.','Player_calls':0,'solver_calls':0}
    write_json(output,result);return result


def rule_conditioning_alias(directory,output):
    """Exact cross-rule value alias under an explicitly rule-blind encoding.

    This concerns a single shared function with no rule-dependent parameters.
    Separate per-rule networks or rule-conditioned features are not ruled out.
    """
    import json
    start=now();data=L.load(directory/'rows-1-5.json');row=next(r for r in data['rows'] if r['oneply_scoring']==[False,True]);rules=[L.ruleset_from_dict(L.load(directory/f'rule-1-5-{m}.json')) for m in (1,5)];states=[];records=[];encoded=[]
    for m,r,v in zip((1,5),rules,row['views'],strict=True):
        c=L.compile_rule(r);ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(v['record'])))
        assert L.record_value(ss.state)==v['full_state'] and not ss.state.terminal_status.is_terminal
        pos=ss.state.position;physical={'board':L.record_value(pos.board),'hands':L.record_value(pos.hands),'auxiliary':L.record_value(pos.aux_state),'side':pos.side_to_move,'ply':ss.state.ply_count,'remaining_plies':r.max_ply-ss.state.ply_count,'repetition_limit':r.repetition_limit,'repetition_multiplicities':sorted(n for _,n in ss.state.repetition_counts),'physical_past_actions':[],'terminal_status':L.record_value(ss.state.terminal_status)}
        encoded.append(physical);records.append(v['record']);states.append(L.record_value(ss.state))
    assert encoded[0]==encoded[1]
    canonical=singleton_rule(1,0);normalized=replace(rules[0],initial_position=canonical.initial_position,initial_setup_options=())
    assert L.ruleset_to_dict(normalized,include_metadata=True)==L.ruleset_to_dict(canonical,include_metadata=True) and orthogonally_independent(L.offsets(1))
    c=L.compile_rule(rules[1]);ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(records[1])));positive=next(z for z in row['views'][1]['children'] if z['terminal']['winner']==0);ss.submit(L.match_action(ss,positive['action']))
    assert ss.result.winner==0 and ss.state.ply_count==1
    result={'status':'PASS','started_at':start,'ended_at':now(),'physical_placement':row['placement'],'rule_references':['rule-1-5-1','rule-1-5-5'],'full_initial_records':records,'full_initial_states':states,'shared_rule_blind_features':encoded[0],
            'differing_rule_information':['movementoffsetdefinitions','ruleset_fingerprint and derivedpositionkeys'],
            'value_claims':[{'mask':1,'WDL_for_side0':0,'basis':'ExactsingletonnoMateproof allotherendingsdraw finite64clock; independentreviewpending'},{'mask':5,'WDL_for_side0':1,'basis':'ActualoneplyCorecheckmate, completepositivewitness','winning_record':L.record_value(ss.to_record()),'terminal':L.record_value(ss.result)}],
            'impossibility':'BothrootsareONGOING with samephysicalboard/typeIDs/side/emptyphysicalhistory/clock. AnysharedfunctionofONLYthesefeatures assignsonevalue toboth, so cannotrepresentboth exactWDL0and1. Atleastoneabsoluteerror>=1/2; equalweighttwo-rootminimumMSE=1/4. Thisis anencoder-specific deterministic approximation bound, not a statisticalpopulation or priceclaim.',
            'scope':'NoNNUEtraining or modelactivation. Rule-conditionedfeatures, rule-specificweights/adaptation, typeencodingfrommovementor explicitruleinput canavoidthiscollision. Terminaloverridealone doesnotresolveitbecausebothrootsongoing. No claimthatfullCorestatescollide: fingerprints/historykeysaredifferent.'}
    write_json(output,result);return result


def two_ply_coordinates(directory,output):
    """Forward tree width to ply2, not minimax search or a game-graph solver."""
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.transition import apply_action
    start=now();tick=time.perf_counter();n=4;plan=L.load(directory/'plan.json');rows=[];counts=Counter()
    frozen={'at':start,'question':'Does exact orbit-additive root branching remain sufficient for the next forward tree layer under the same legal mu?','scope':'Only full forward depth2 on4x4casebook; no WDL/minimax/futuregoal solver, no labels fitted. ALL12existingmechanismmasks andALL596sameglobalmu; fixed8Corevalidationindices/rule.','expected_seconds':20,'cap_seconds':180,'source_sha256':L.sha(Path(__file__))}
    write_json(output.with_suffix('.plan.json'),frozen)
    for mask in plan['palette']:
        features=L.load(directory/f'features-4-{mask}.json')['rows'];c=L.compile_rule(L.ruleset_from_dict(L.load(directory/f'actual-rule-4-{mask}.json')));sample={i*(len(features)-1)//7 for i in range(8)};case=[]
        for i,r in enumerate(features):
            if session.stopped() or time.perf_counter()-tick>=180:raise TimeoutError('fixed forward2cap')
            spec=tuple(r['placement']);first=integer_actions(spec,mask,0,n);width=0;stop1=0;second_terms=Counter()
            for a,ch in first:
                term=integer_terminal(ch,mask,1,n)
                if term['status']!='ongoing':stop1+=1;continue
                second=integer_actions(ch,mask,1,n);width+=len(second)
                for _,cc in second:second_terms[integer_terminal(cc,mask,0,n)['status']]+=1
            assert len(first)==r['branch'];case.append({'support_index':i,'placement':spec,'root_branch':len(first),'ply1_terminal_leaves':stop1,'ply2_nonpruned_histories':width,'ply2_terminal_histogram':dict(second_terms)})
            counts['integer_root_profiles']+=1;counts['integer_second_edges']+=width
            if i in sample:
                ss=L.GameSession(c,None if i==0 else 's-'+'-'.join(map(str,spec)));actual1={physical_action(L.record_value(a),n):a for a in legal_actions(ss.state,c)};assert set(actual1)=={a for a,_ in first}
                for a,ch in first:
                    child=apply_action(ss.state,actual1[a],c);counts['Core_first_edges']+=1
                    if child.terminal_status.is_terminal:continue
                    actual2={physical_action(L.record_value(z),n):z for z in legal_actions(child,c)};expected2=dict(integer_actions(ch,mask,1,n));assert set(actual2)==set(expected2)
                    for b,z in actual2.items():
                        cc=apply_action(child,z,c);observed={'mask':mask,'support_index':i,'first':a,'second':b,'state_sha256':L.state_sha(cc),'terminal':L.record_value(cc.terminal_status)}
                        with output.with_suffix('.returns.jsonl').open('a',encoding='utf-8') as log:log.write(__import__('json').dumps(observed)+'\n')
                        assert observed['terminal']==integer_terminal(expected2[b],mask,0,n);counts['Core_second_edges']+=1
                counts['Core_root_profiles']+=1
        rows.append({'mask':mask,'rows':case,'mean_root_branch':str(__import__('fractions').Fraction(sum(x['root_branch'] for x in case),len(case))),'mean_ply2_width':str(__import__('fractions').Fraction(sum(x['ply2_nonpruned_histories'] for x in case),len(case)))})
        write_json(output,{'status':'RUNNING','rows':rows,'counts':dict(counts)})
    by={r['mask']:r['rows'] for r in rows};examples=[]
    for a in sorted(by):
        for b in sorted(by):
            if a==b or a&b!=a or (a^b).bit_count()!=1:continue
            for x,y in zip(by[a],by[b],strict=True):
                if y['root_branch']>=x['root_branch'] and y['ply2_nonpruned_histories']<x['ply2_nonpruned_histories']:
                    if len(examples)<8:examples.append({'masks':[a,b],'physical_placement':x['placement'],'root_branches':[x['root_branch'],y['root_branch']],'ply2_widths':[x['ply2_nonpruned_histories'],y['ply2_nonpruned_histories']],'firstply_terminal_counts':[x['ply1_terminal_leaves'],y['ply1_terminal_leaves']]})
    result={'status':'PASS','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'rows':rows,'counts':dict(counts),'nonmonotone_forward_width_examples':examples,'scope':'Exactscopedinteger forward2profiles,96fullrootfrontiers sampledthroughpublicCore. Actualhistoryprefixes notuniformphysicalstates; no gamegraph/minimax/WDL labels orPlayer. Rootbranch neednotorder next-layer width.'}
    write_json(output,result);return result


def exact_forward2_witness(directory,forward_path,output):
    from generic_chess.core.movegen import legal_actions
    from generic_chess.core.transition import apply_action
    start=now();candidate=L.load(forward_path)['nonmonotone_forward_width_examples'][0];a,b=candidate['masks'];spec=candidate['physical_placement'];rows=[]
    for mask in (a,b):
        c=L.compile_rule(L.ruleset_from_dict(L.load(directory/f'actual-rule-4-{mask}.json')));ss=L.GameSession(c,'s-'+'-'.join(map(str,spec)));front=[]
        for action in legal_actions(ss.state,c):
            first=apply_action(ss.state,action,c);second=[]
            for response in legal_actions(first,c):
                final=apply_action(first,response,c);second.append({'action':L.record_value(response),'state_sha256':L.state_sha(final),'terminal':L.record_value(final.terminal_status)})
            front.append({'action':L.record_value(action),'physical_action':physical_action(L.record_value(action),4),'state_sha256':L.state_sha(first),'terminal':L.record_value(first.terminal_status),'responses':second})
        row={'mask':mask,'rule_reference':f'scale/actual-rule-4-{mask}','fingerprint':ss.state.position.ruleset_fingerprint,'full_initial_record':L.record_value(ss.to_record()),'initial_state_sha256':L.state_sha(ss.state),'root_branch':len(front),'ply2_history_count':sum(len(x['responses']) for x in front),'frontier':front};rows.append(row);write_json(output,{'status':'RUNNING','rows':rows})
    assert [r['root_branch'] for r in rows]==candidate['root_branches'] and [r['ply2_history_count'] for r in rows]==candidate['ply2_widths']
    assert all(x['terminal']['status']=='ongoing' for r in rows for x in r['frontier'])
    lower={tuple(x['physical_action']):x for x in rows[0]['frontier']};higher={tuple(x['physical_action']):x for x in rows[1]['frontier']}
    shared=sorted(set(lower)&set(higher));added=sorted(set(higher)-set(lower));decomposition={'shared_physical_actions':[{'physical_action':key,'response_counts':[len(lower[key]['responses']),len(higher[key]['responses'])]} for key in shared],'added_physical_actions':[{'physical_action':key,'response_count':len(higher[key]['responses'])} for key in added]}
    result={'status':'PASS','started_at':start,'ended_at':now(),'candidate_selection':'Firstdeterministicintegercasebookcounterexample, not heldoutpredictivesuccess','physical_placement':spec,'rows':rows,'decomposition':decomposition,'scope':'CompleteactualpublicCoredepth2frontiers6to7rootactionsbut24to22secondhistories, zero firstplyterminals. Addedattacksreduceopponentmoves evenwithout absorption. No WDL/minimax/allhistorysolver orstrengthclaim.'}
    write_json(output,result);return result


def audit_mate_pv(directory,output):
    """Audit retained mate7 PV defenses, WITHOUT searching missing branches."""
    import json
    start=now();p=L.load(directory/'N8192.json');metadata=L.load(directory/'metadata.json')['rows'];target=next(x for x in metadata if x['mask']==7 and x['fixture']=='discovered-stalemate-mechanism');row=next(x for x in p['rows'] if x['seed']==target['seed'] and x['variant']=='all');world=next(x for x in L.load(directory/'inputs.json')['worlds'] if x['seed']==target['seed']);r=L.ruleset_from_dict(world['rule']);c=L.compile_rule(r);ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(world['roots'][0]['record'])));off=[];trace=[]
    assert L.state_sha(ss.state)==target['full_state_sha256'];pv=row['decision']['principal_variation']
    for ply,raw in enumerate(pv):
        chosen=L.match_action(ss,raw);legal=ss.legal_actions();trace.append({'ply':ply,'side':ss.state.position.side_to_move,'source_record':L.record_value(ss.to_record()),'source_state_sha256':L.state_sha(ss.state),'legal_count':len(legal),'chosen_action':raw})
        if ss.state.position.side_to_move==1:
            for action in legal:
                if action==chosen:continue
                branch=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(L.record_value(ss.to_record()))));branch.submit(action)
                ordinary=[x for x in branch.state.position.board if x is not None and x.current_type_id!='K'];literal=branch.state.terminal_status.is_terminal
                bound=[0,0] if literal and branch.result.winner is None or not ordinary else [0,1]
                off.append({'diverges_after_ply':ply,'action':L.record_value(action),'full_record':L.record_value(branch.to_record()),'full_state':L.record_value(branch.state),'state_sha256':L.state_sha(branch.state),'remaining_plies':r.max_ply-branch.state.ply_count,'terminal':L.record_value(branch.result),'ordinary_count':len(ordinary),'WDL_for0_bound':bound,'basis':'literal draw or bareKingsscope' if bound==[0,0] else 'onlydefenderKing cannotmate; forceWIN unverified'})
        ss.submit(chosen)
    assert ss.result.winner==0
    contradicted=any(x['WDL_for0_bound']==[0,0] for x in off)
    result={'status':'PASS','started_at':start,'ended_at':now(),'full_rule':world['rule'],'full_initial_record':world['roots'][0]['record'],'initial_state_sha256':target['full_state_sha256'],'fingerprint':target['fingerprint'],'retained_decision':row['decision'],'source_cost_file_sha256':L.sha(directory/'N8192.json'),'verified_cooperative_complete_record':L.record_value(ss.to_record()),'trace':trace,'off_PV_defense_histories':off,'off_PV_count':len(off),'literal_or_bareKing_draw_refutation':contradicted,
            'root_cooperative_reachability':True,'root_forced_WDL_for0':'UNKNOWN_[0,1]' if off else 'WIN_verified_unique_defense_line','Native_mate_score_is_not_independent_proof':True,
            'next_question':'Can independentreviewcertify the retained mate7 strategy on these exact offPVfullhistories (orfind aDRAWdefense), establishing whether rootvalue staysWIN although samefirstKingaction goesWINtoDRAW? Prefer thisconcreteP1action/strategycomparison over broadUNKNOWNreduction. No requestto launchnewworker/longgraph orAUXstatewrite.',
            'scope':'Only actualretainedPV andoneplyoffPVdefense capture; no newPlayer/minimax/historysolver. AlternativeWhiteactionsnotsearched; UNKNOWNbounds are notcostforecasts. OnlyK1defender andfixedscoringtemplate supplynonlossbound, not arbitraryrules.'}
    write_json(output,result);return result


def action_alignment(directory,output):
    """Measure encoding changes separately from physical action changes."""
    start=now();rows=[];examples=[];totals=Counter()
    for a,b in PAIRS:
        low=L.ruleset_from_dict(L.load(directory/f'rule-{a}-{b}-{a}.json'));high=L.ruleset_from_dict(L.load(directory/f'rule-{a}-{b}-{b}.json'))
        # Only the A move vocabulary differs, including all initial setups and
        # history/scoring settings in this exact comparison.
        normalized=normalize_only_A_moves(low,high)
        assert L.ruleset_to_dict(normalized,include_metadata=True)==L.ruleset_to_dict(low,include_metadata=True)
        assert (a^b).bit_count()==1 and a&b==a
        counts=Counter();case=L.load(directory/f'rows-{a}-{b}.json')
        for r in case['rows']:
            lo={physical_action(z['action'],4):z for z in r['views'][0]['children']};hi={physical_action(z['action'],4):z for z in r['views'][1]['children']}
            for physical in set(lo)&set(hi):
                left,right=lo[physical]['action'],hi[physical]['action'];counts['shared_physical_actions']+=1
                same=left==right;counts['raw_action_equal' if same else 'same_physical_but_IR_identifier_changed']+=1
                if not same and not any(x['masks']==[a,b] for x in examples):
                    examples.append({'masks':[a,b],'placement':r['placement'],'physical_action':physical,'source_IR_action':left,'target_IR_action':right,'target_initial_record':r['views'][1]['record'],'source_initial_record':r['views'][0]['record']})
        rows.append({'masks':[a,b],'counts':dict(counts),'added_orbit':L.ORBITS[(a^b).bit_length()-1],'all_other_rule_fields_identical':True});totals.update(counts)
    validations=[]
    for r in examples:
        a,b=r['masks'];c=L.compile_rule(L.ruleset_from_dict(L.load(directory/f'rule-{a}-{b}-{b}.json')));ss=L.GameSession.replay(c,L.deserialize_game_record(__import__('json').dumps(r['target_initial_record'])))
        failed=False
        try:L.match_action(ss,r['source_IR_action'])
        except ValueError:failed=True
        assert failed
        matched=[x for x in ss.legal_actions() if physical_action(L.record_value(x),4)==tuple(r['physical_action'])]
        assert len(matched)==1 and L.record_value(matched[0])==r['target_IR_action'];ss.submit(matched[0])
        validations.append({'masks':r['masks'],'old_IR_action_rejected':True,'unique_target_physical_rematch_executed':True,'actual_target_record':L.record_value(ss.to_record()),'actual_target_state_sha256':L.state_sha(ss.state)})
    result={'status':'PASS','started_at':start,'ended_at':now(),'pairs':rows,'totals':dict(totals),'examples':examples,'actual_Core_rematch_checks':validations,
            'scope':'TheseplainLeap rules have no competingsemantic effects/promotion, so each physicalactiontuple uniquelymatches. ArbitraryDSL canhavemultiple same-squareactions; rejectambiguity, doNOTapplythisprojectiongenerically. IRIDs changing is not strategy/valuechange. Physicalhistorymustbereplayedwith targetfingerprint/keys, not rawcopied.'}
    write_json(output,result);return result


def normalize_only_A_moves(low,high):
    # Keep every King/A property and every other field from HIGH. Replacing
    # the whole piece_types tuple would conceal a changed royal or effect.
    source=next(t for t in low.piece_types if t.type_id=='A')
    return replace(high,piece_types=tuple(replace(t,movement_atoms=source.movement_atoms) if t.type_id=='A' else t for t in high.piece_types))



def qualify_offpv_oneply(source,output):
    """Only inspect literal one-ply replies, never solve an unknown subtree."""
    import json
    start=now();old=L.load(source);c=L.compile_rule(L.ruleset_from_dict(old['full_rule']));rows=[];edges=0
    for r in old['off_PV_defense_histories']:
        ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(r['full_record'])));assert L.record_value(ss.state)==r['full_state']
        children=L.legal_successors(ss.state,c);observed={'source_state_sha256':r['state_sha256'],'source_full_record':r['full_record'],'ply':ss.state.ply_count,'required_remaining_mate_plies_for_original7bound':7-ss.state.ply_count,
              'actual_children':[{'action':L.record_value(a),'terminal':L.record_value(ch.terminal_status),'state_sha256':L.state_sha(ch)} for a,ch in children]}
        rows.append(observed);write_json(output,{'status':'RUNNING','rows':rows})
        positive=next((a for a,ch in children if ch.terminal_status.winner==0),None);edges+=len(children)
        if positive is not None:
            ss.submit(positive);observed['literal_mate_record']=L.record_value(ss.to_record());observed['literal_mate_state_sha256']=L.state_sha(ss.state);observed['verified_WDL_for0']=1
        else:observed['verified_WDL_for0']='UNKNOWN_[0,1]'
    all_closed=all(r['verified_WDL_for0']==1 for r in rows)
    result={'status':'PASS','started_at':start,'ended_at':now(),'source_handoff_sha256':L.sha(source),'rows':rows,'Core_child_returns':edges,'literal_oneply_closed_branches':sum(r['verified_WDL_for0']==1 for r in rows),'remaining_UNKNOWN_branches':sum(r['verified_WDL_for0']!=1 for r in rows),
            'composed_retained_strategy_mate7_verified':all_closed,'root_WDL_for0':'WIN_bounded_strategy_certificate' if all_closed else 'UNKNOWN_[0,1]',
            'scope':'Onlyliteralnewoneplyreturns onthethreeactualoffPVhistories. IfallWIN, fixedWhitePVchoices+theseoneplyreplies coveralldefenderchoices andcomposemate<=7; otherwise remainingboundedmate5/3/1queries go toindependentreview. Afailedshortmatecertificate isNOTaDRAWorrootWDLrefutation. No newPlayer/historygraph/minimaxsolver.'}
    write_json(output,result);return result



def active_attack_offsets(offsets,n):
    if isinstance(n,bool) or not isinstance(n,int) or n<3:raise ValueError('square n>=3 required')
    if any(len(z)!=2 or any(isinstance(v,bool) or not isinstance(v,int) for v in z) or tuple(z)==(0,0) for z in offsets):raise ValueError('nonzerointeger offsetpairs required')
    return {tuple(z) for z in offsets if abs(z[0])<n and abs(z[1])<n}


def constructive_corner(offsets,n):
    active=active_attack_offsets(offsets,n)
    pairs=[(p,q) for p in sorted(active) for q in sorted(active) if p<q and abs(p[0]-q[0])+abs(p[1]-q[1])==1]
    if not pairs:return None
    p,q=pairs[0];axis=0 if p[0]!=q[0] else 1;perp=1-axis;chosen=max((p,q),key=lambda v:abs(v[axis]));other=q if chosen==p else p;p=chosen;victim=[n-1 if v>0 else 0 for v in p]
    attacker=[victim[i]-p[i] for i in range(2)];king=list(victim);king[perp]+= -2 if victim[perp]==n-1 else 2
    assert all(0<=z<n for point in (victim,attacker,king) for z in point)
    assert len({tuple(king),tuple(attacker),tuple(victim)})==3 and not adjacent(king,victim)
    assert not escapes(tuple(king),tuple(attacker),tuple(victim),active,n)
    return {'king0':king,'ordinary0':attacker,'king1':victim,'active_attack_pair':[list(p),list(other)]}


def active_offset_catalog(output):
    from generic_chess.core.movement import LeapAtom
    from generic_chess.core.identity import repetition_identity_key
    from generic_chess.core.position import HistoryRecord
    start=now();tick=time.perf_counter();n=4;alloff={(x,y) for x in range(-3,4) for y in range(-3,4) if (x,y)!=(0,0)};pairs=[(p,q) for p in sorted(alloff) for q in sorted(alloff) if p<q and abs(p[0]-q[0])+abs(p[1]-q[1])==1];assert len(pairs)==80
    rows=[]
    for pair in pairs:
        if session.stopped() or time.perf_counter()-tick>=60:raise TimeoutError('fixed active-offset check cap')
        witness=constructive_corner(pair,n);r=template(1,n,(0,1,n*n-1));board=[list(line) for line in r.initial_position];board[0][1]=None
        r=replace(r,initial_position=tuple(map(tuple,board)),piece_types=(r.piece_types[0],replace(r.piece_types[1],movement_atoms=tuple(LeapAtom(z) for z in pair))))
        c=L.compile_rule(r);spec=tuple(n*p[1]+p[0] for p in (witness['king0'],witness['ordinary0'],witness['king1']));pos=replace(c.initial_position,board=tuple(z for line in cells(spec,n) for z in line),side_to_move=1);key=repetition_identity_key(pos,c);e=semantic_engine_for(c);hist=(HistoryRecord(key,-1,'',False),)
        observed={'offset_pair':pair,'constructive_witness':witness,'full_rule':L.ruleset_to_dict(r,include_metadata=True),'synthetic_position':L.record_value(pos),'check':e.in_check(pos,1),'legal_actions':L.record_value(e.legal_actions(pos)),'terminal':L.record_value(e.terminal_result(pos,0,((key,1),),hist))}
        rows.append(observed);write_json(output,{'status':'RUNNING','rows':rows})
        assert observed['check'] and not observed['legal_actions'] and observed['terminal']=={'status':'checkmate','winner':0}
    clipped3=active_attack_offsets(set(L.offsets(4))|{(-3,0),(0,-3),(0,3),(3,0)},3)
    assert orthogonally_independent(clipped3) and constructive_corner(clipped3,3) is None
    result={'status':'PASS','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'rows':rows,'minimal_pairs':len(pairs),
            'criterion':'StaticMate(O,n) iff there existp,q in O_active with ManhattanDistance(p,q)=1, whereO_active={d inO:abs(dx),abs(dy)<=n-1}, zeroexcluded.',
            'proof_negative':'IfcheckedvictimVand offsetsetindependent, its orthogonalneighbor cannotbeattackedbyA. Kingsnonadjacent=>onecoordinate separation>=2; choose anavailableorthogonalstepperpendiculartothatcoordinate, preservingKingseparation. IfitcapturesA itsattacks disappear. ThuscheckedKingalwayshaslegal escape.',
            'proof_positive':'Pickorthadjacentattackpair; letp havegreaterabsolutevalueinchangedaxis(nonzero). ChooseVcornerwhoseaxis signs matchp, A=V-p. PlaceK0twoinward onperpendicularaxis. The inwardchanged-axisneighborisattackedbyotheroffset; remainingorthogonalneighboranddiagonalarecoveredbyK0. A !=K0 becausechanged-axis coordinate differs. A cannot be theunprotectedchanged-axisneighbor: thatwouldrequirezerootheroffset. Hence no captureescape. Allpiecesfitgivenactivebounds andn>=3. Addedattacks cannotrestore bareKingescapes.','inactive_control':{'n':3,'declared_offsets':sorted(set(L.offsets(4))|{(-3,0),(0,-3),(0,3),(3,0)}),'active_offsets':sorted(clipped3),'static_capacity':False,'compare4x4_positive_reference':'new-orbitorth2_plus_orth3'},
            'scope':'Mathematicalstaticconfigurationcriterion foronefixedordinaryLeapentityandtwoKing8royals, square n>=3. Asymmetricoffsets allowed. No claimforrays, conditionalcapture/moveasymmetry, extraentities, drops/promotionreachability/aux/effect/scoringvariants orparticularinitialhistory.80Coreminimalcontrols are sourceassistedvalidation, notindependentproof/all2^48enumeration.','Player_calls':0,'solver_calls':0}
    write_json(output,result);return result


def qualify_cost_screen(directory,output):
    """Replay retained cost returns; no Player calls or latent difficulty labels."""
    import json,math,statistics
    from collections import defaultdict
    start=now();tick=time.perf_counter();plan=L.load(directory/'plan.json');execution=L.load(directory/'execution.json')
    if execution['status'] not in ('CLOSED','FAILED'):raise ValueError('only inspect a closed producer report')
    assert L.sha(directory/'inputs.json')==plan['input_sha256'] and L.sha(directory/'metadata.json')==plan['metadata_sha256']
    worlds={w['seed']:w for w in L.load(directory/'inputs.json')['worlds']};metadata={r['seed']:r for r in L.load(directory/'metadata.json')['rows']}
    assert len(worlds)==len(metadata)==plan['worlds']
    counts=Counter();rows=[];compiled={};batch=[]
    for budget in plan['budgets']:
        path=directory/f'N{budget}.json'
        if not path.exists():
            batch.append({'budget':budget,'unattempted':True,'missing':len(worlds)});continue
        data=L.load(path);protocol=data['protocol'];limits=protocol['query_limits']
        assert protocol['source_sha256']==plan['runner_source_sha256'] and protocol['input_sha256']==plan['input_sha256']
        assert protocol['evaluation_backend']=='unit' and protocol['variants']==['all']
        assert limits['max_depth']==64 and limits['max_nodes']==budget and limits['max_time_seconds']==3 and limits['quiescence_max_depth']==0
        assert protocol['planned_queries']==len(worlds) and len(data['rows'])+len(data['missing_slots'])==len(worlds)
        assert not data['failures']
        retained={w['seed']:w for w in data['worlds']};seen=set()
        for row in data['rows']:
            seed=row['seed'];assert seed not in seen;seen.add(seed);w=worlds[seed];meta=metadata[seed]
            assert row['prefix']==row['rep']==0 and row['variant']=='all'
            r=L.ruleset_from_dict(w['rule']);assert L.ruleset_to_dict(r,include_metadata=True)==L.ruleset_to_dict(template(meta['mask'],meta['n'],meta['placement']),include_metadata=True)
            assert L.compute_fingerprint(r)==L.compute_fingerprint(L.ruleset_from_dict(retained[seed]['rule']))
            assert retained[seed]['roots'][0]['record']==w['roots'][0]['record']
            c=compiled.setdefault(seed,L.compile_rule(r));ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(w['roots'][0]['record'])))
            assert L.state_sha(ss.state)==meta['initial_state_sha256']
            d=row['decision'];assert d['nodes']>=0 and d['qnodes']>=0 and row['query_seconds']>0
            chosen=L.match_action(ss,d['action']);counts['legal_decisions']+=1
            if d['termination_reason']=='root_immediate_win':
                check=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(w['roots'][0]['record'])));check.submit(chosen)
                assert check.state.terminal_status.winner==0;counts['literal_root_immediate_wins']+=1
            for a in d['principal_variation']:
                ss.submit(L.match_action(ss,a));counts['Core_PV_plies']+=1
            counts['provider_available']+=int(row['provider_available']);counts['native_legality_fallbacks']+=d['native_legality_fallbacks']
            counts['time_limit_returns']+=int(d['termination_reason']=='time_limit');counts['budget_limit_returns']+=int(d['termination_reason']=='node_limit')
            total=d['nodes']+d['qnodes'];rows.append(dict(meta,budget=budget,nodes=d['nodes'],qnodes=d['qnodes'],total_work=total,query_seconds=row['query_seconds'],setup_seconds=row['player_setup_seconds'],completed_depth=d['completed_depth'],reason=d['termination_reason'],work_per_query_second=total/row['query_seconds']))
        batch.append({'budget':budget,'observed':len(seen),'missing':len(data['missing_slots']),'wall_seconds':data['wall_seconds'],'reason_histogram':dict(Counter(r['decision']['termination_reason'] for r in data['rows']))})
    def ranks(values):
        ordered=sorted(set(values));rank={};pos=1
        for x in ordered:
            n=values.count(x);rank[x]=pos+(n-1)/2;pos+=n
        return [rank[x] for x in values]
    def rho(x,y):
        x=ranks(x);y=ranks(y);mx=statistics.mean(x);my=statistics.mean(y);den=math.sqrt(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))
        return None if den==0 else sum((a-mx)*(b-my) for a,b in zip(x,y,strict=True))/den
    groups=defaultdict(list)
    for r in rows:groups[r['n'],r['budget']].append(r)
    associations=[]
    features=('graph_components','graph_mean_degree','root_branch','forward2_width','static_capacity')
    targets=('total_work','completed_depth','query_seconds','work_per_query_second')
    for (n,budget),rs in sorted(groups.items()):
        rule_rows=[]
        for m in sorted({r['mask'] for r in rs}):
            sel=[r for r in rs if r['mask']==m]
            rule_rows.append({f:statistics.mean(r[f] for r in sel) for f in features+targets}|{'mask':m,'observed_roots':len(sel)})
        for target in targets:
            associations.append({'n':n,'budget':budget,'target':target,'root_count':len(rs),'rule_count':len(rule_rows),'all_planned_roots_observed':len(rs)==plan['roots_per_board_mask']*len(plan['masks']),
               'root_Spearman':{f:rho([r[f] for r in rs],[r[target] for r in rs]) for f in features},
               'rule_mean_Spearman':{f:rho([r[f] for r in rule_rows],[r[target] for r in rule_rows]) for f in features}})
    result={'status':'PASS','started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'counts':dict(counts),'batches':batch,'rows':rows,'associations':associations,
      'scope':'Finite actually paid work and observed iterations under given cooperative clocks; time-limit returns are censored for requested-depth completion, not uncensored work-needed labels. Correlated roots/shared board distribution,24cost-new masks and new6x6domain. Spearman exploratory screen not fittedquality/WDL/causal claim. All actualPVs Core-replayed, not independentengine. No newPlayer calls.'}
    write_json(output,result);return result



def forward2_orbit_polynomial(spec,n):
    """Exact scoped fresh K+A-v-K width: quadratic, nonpositive pair terms.

    Each outer A action needs one orbit bit. Each bare-K defense is forbidden
    by at most one disjoint attack orbit. Thus x_i*(1-x_j), with x_i^2=x_i.
    This is not a general DSL/history/search-work polynomial.
    """
    orbit={d:i for i in range(5) for d in L.offsets(1<<i)}
    coefficients=Counter()
    for action,child in integer_actions(tuple(spec),31,0,n):
        k,a,v=child;tid,source,target,_=action
        if tid=='K':outer=()
        else:
            dx=xy(target,n)[0]-xy(source,n)[0];dy=xy(target,n)[1]-xy(source,n)[1];outer=(orbit[dx,dy],)
        vx,vy=xy(v,n);kx,ky=xy(k,n);ax,ay=xy(a,n)
        for dx,dy in L.offsets(3):
            x,y=vx+dx,vy+dy
            if not(0<=x<n and 0<=y<n) or adjacent((x,y),(kx,ky)):continue
            coefficients[outer]+=1
            if (x,y)==(ax,ay):continue # capture removes A's attacks
            j=orbit.get((x-ax,y-ay))
            if j is not None:coefficients[tuple(sorted(set(outer+(j,))))]-=1
    return {','.join(map(str,k)):v for k,v in sorted(coefficients.items()) if v}



def multi_actor_forward2_polynomial(king0, ordinary, king1, n):
    """Exact two-action path polynomial for identical plain A actors vs bare K.

    All actors share the five disjoint offset bits; mover0, fresh H64/repeat4,
    no other declarations/effects/drops/promotion. Common-safe/ongoing root is
    required. Quantity k gives degree <=min(k+1,5), not singleton submodularity.
    An A move supplies x_i and each remaining attacker forbids one orbit bit.
    """
    ordinary=tuple(sorted(ordinary));points=(king0,)+ordinary+(king1,)
    if isinstance(n,bool) or not isinstance(n,int) or n<3 or not ordinary:
        raise ValueError('square n>=3 and at least one ordinary actor required')
    if len(set(points))!=len(points) or any(type(z) is not int or not 0<=z<n*n for z in points):
        raise ValueError('distinct on-board physical actors required')
    orbit={d:i for i in range(5) for d in L.offsets(1<<i)}
    def displacement(a,b):
        ax,ay=xy(a,n);bx,by=xy(b,n);return bx-ax,by-ay
    if adjacent(xy(king0,n),xy(king1,n)) or any(displacement(a,king1) in orbit for a in ordinary):
        raise ValueError('root must be safe under every mask')
    outer=[];available_bits=set();kx,ky=xy(king0,n)
    for dx,dy in L.offsets(3):
        x,y=kx+dx,ky+dy;target=n*y+x
        if 0<=x<n and 0<=y<n and target not in ordinary and not adjacent((x,y),xy(king1,n)):
            outer.append(((),target,ordinary))
    king_can_move=bool(outer)
    for index,source in enumerate(ordinary):
        ax,ay=xy(source,n)
        for (dx,dy),bit in orbit.items():
            x,y=ax+dx,ay+dy;target=n*y+x
            if not(0<=x<n and 0<=y<n) or target in points:continue
            child=list(ordinary);child[index]=target
            outer.append(((bit,),king0,tuple(child)));available_bits.add(bit)
    if not king_can_move and len(available_bits)!=5:
        raise ValueError('root is not ongoing for every nonempty mask')
    coefficients=Counter();vx,vy=xy(king1,n)
    for gate,k,actors in outer:
        for dx,dy in L.offsets(3):
            x,y=vx+dx,vy+dy;target=n*y+x
            if not(0<=x<n and 0<=y<n) or adjacent((x,y),xy(k,n)):continue
            # Capturing one A removes just that actor's attack contribution.
            forbidden={orbit[d] for a in actors if a!=target and (d:=displacement(a,target)) in orbit}
            terms=Counter({gate:1})
            for bit in sorted(forbidden):
                updated=Counter(terms)
                for monomial,value in terms.items():updated[tuple(sorted(set(monomial+(bit,))))]-=value
                terms=updated
            coefficients.update(terms)
    return {','.join(map(str,k)):v for k,v in sorted(coefficients.items()) if v}


def minimum_static_ordinary_count(mask,n):
    """Minimum IDENTICAL A actors in a mating CONFIGURATION, never reachability.

    Square n>=3, King8 vs bare King, the five fixed disjoint plain-Leap orbits,
    unrestricted static placements. No inventory/initial-admission or WDL claim.
    None means no number of these A actors can form mate on that board.
    """
    if type(mask) is not int or not 1<=mask<=31 or type(n) is not int or n<3:
        raise ValueError('five-bit nonempty mask and square n>=3 required')
    if constructive_corner(L.offsets(mask),n) is not None:return 1
    # On3x3 diag2 attacks only the opposite corner. Every edge-centre has
    # zero incoming A attacks. If a corner King is checked, one orthogonal
    # edge-centre escape lies outside the nonadjacent friendly King's cover.
    if n==3 and mask==16:return None
    return 2


def static_quantity_witness(mask,n):
    """Construct a minimum-count static mate witness under the scope above."""
    count=minimum_static_ordinary_count(mask,n)
    if count is None:return None
    if count==1:
        w=constructive_corner(L.offsets(mask),n)
        return {'king0':w['king0'],'ordinary':[w['ordinary0']],'king1':w['king1']}
    # Each singleton orbit has this two-actor corner construction; any added
    # ordinary attacks cannot restore a bare King's escape. No zero offset.
    bits=[i for i in range(5) if mask&(1<<i)]
    bit=next((i for i in bits if i!=4),4)
    constructions={0:((2,0),((1,0),(0,2))),1:((2,0),((1,1),(1,2))),
                   2:((2,0),((0,2),(2,1))),3:((2,0),((1,2),(2,2))),
                   4:((0,2),((2,2),(3,2)))}
    king,actors=constructions[bit]
    assert all(0<=x<n and 0<=y<n for x,y in (king,)+actors)
    return {'king0':list(king),'ordinary':[list(z) for z in actors],'king1':[0,0]}

def evaluate_orbit_polynomial(coefficients,mask):
    return sum(value for term,value in coefficients.items() if all(mask&(1<<int(i)) for i in term.split(',') if i))


if __name__=='__main__':main()
