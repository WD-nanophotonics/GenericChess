"""Source-bound descriptive inference for the new finite admitted packet.

No new Core/search/solver/labels. Completion envelopes use only score range;
unknown cells remain unknown. They are not confidence intervals or forecasts.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from fractions import Fraction
from pathlib import Path
from scripts.verify_aux_admitted_extension_packet import load,raw_return,verify_archives,SOURCE

def fraction(x):
    q=Fraction(x);return {'rational':str(q),'value':float(q)}

def completion_envelope(known_points, observed_games, target_games):
    assert isinstance(known_points,Fraction) and 0<=known_points<=observed_games<=target_games and target_games>0
    missing=target_games-observed_games
    return {'known_points':fraction(known_points),'observed_games':observed_games,'target_games':target_games,'unknown_games':missing,'lower':fraction(known_points/target_games),'upper':fraction((known_points+missing)/target_games)}

def experienced_regret_lower_bounds(games):
    """Reuse the telescoping identity on a DIFFERENT, newly published packet.

    Utility is finite full-game seat0 WDL in {-1,0,1}. No action label is
    estimated and there is no claim of independent information beyond outcomes.
    """
    rows=[]
    for i in range(0,len(games),2):
        pair=games[i:i+2];assert len(pair)==2
        assert pair[0]['initial_record']==pair[1]['initial_record'] and pair[0]['fingerprint']==pair[1]['fingerprint']
        a,b=sorted(pair,key=lambda g:g['on_seat']);assert [a['on_seat'],b['on_seat']]==[0,1]
        def utility(g):
            w=g['Core_terminal']['winner'];return 0 if w is None else 1 if w==0 else -1
        delta=utility(a)-utility(b)
        on_min=max(0,-delta);off_min=max(0,delta)
        rows.append({'case_id':a['case_id'],'family':a['family'],'on0_game':a['game_id'],'on1_game':b['game_id'],'seat0_utility_on0':utility(a),'seat0_utility_on1':utility(b),'OFF_minus_ON_experienced_WDL_regret':delta,'ON_regret_lower':on_min,'OFF_regret_lower':off_min,'ON_strict_decision_count_lower':(on_min+1)//2,'OFF_strict_decision_count_lower':(off_min+1)//2})
    return {'pairs':rows,'OFF_minus_ON_total':sum(x['OFF_minus_ON_experienced_WDL_regret'] for x in rows),'ON_regret_lower':sum(x['ON_regret_lower'] for x in rows),'OFF_regret_lower':sum(x['OFF_regret_lower'] for x in rows),'ON_strict_decision_count_lower':sum(x['ON_strict_decision_count_lower'] for x in rows),'OFF_strict_decision_count_lower':sum(x['OFF_strict_decision_count_lower'] for x in rows),'proof':'For each game z=V(root)-R0+R1, with nonnegative actor losses relative to full-game minimax. Swapped-controller starts cancel the same V(root), giving delta=R_OFF-R_ON. Each strict action loss is1 or2 WDL units. Apply nonnegativity per pair, then sum disjoint games. This reexpresses these SAME observed outcomes; no statistical replication, action localization or product-defect claim.','limits':'Minimax is for the literal finiteH96/repetition4 rules, not H6/H128/infinite play or external-regret benchmark. No optimal action, exact starting value or individual mistaken choice is identified.'}

def analyze(source, replay, output):
    packet=load(replay/'packet.json');admission=load(replay/'admission.json')
    assert packet['status']=='PASS' and packet['source']==admission['source']==SOURCE
    games=load(source/'comparison-run/games.json');quals=load(source/'comparison-run/qualification.json');returns=load(source/'comparison-run/returns.json');frozen=load(source/'comparison-run/frozen.json')
    # These are inspected producer clauses, not an independently observed historical process.
    producer=frozen['sources']['scripts/leaper_admitted_extension_quality.py']
    player=frozen['sources']['generic_chess/ai/alphabeta/player.py']
    search=frozen['sources']['generic_chess/ai/alphabeta/search.py']
    assert 'q=choose(c,s,{},s.state.position.side_to_move,on,1.5,' in producer
    assert 'self._tt = TranspositionTable(' in player
    assert 'if depth <= 0:' in search and 'depth + extension_delta - 1' in search
    roots={x['case_id']:x for x in admission['rows']};ons=[]
    for q in quals:
        if not q['on']:continue
        raw=raw_return(q['query_id'],returns);d=raw['decision'];root=roots[q['case_id']]
        assert root['eligible'] and root['status']=='AUDITED' and not root['reasons']
        # All admission roots are non-check and have no initial immediate win.
        impossible=(d['result_source']=='main_iteration' and d['completed_depth']==1)
        ons.append({'case_id':q['case_id'],'qid':q['query_id'],'completed_depth':d['completed_depth'],'result_qdepth':d['result_ordinary_qdepth'],'total_extension_attempts':d['main_check_extensions'],'reason':d['termination_reason'],'cold_ttable_from_bound_producer':True,'retained_iteration_cannot_expand_main_extension':impossible,'count_attribution':'Only later abandoned iterations can contribute these extension counts' if impossible and d['main_check_extensions'] else 'No retained-iteration count snapshot; do not attribute cumulative count to retained result'})
    positive=[x for x in ons if x['total_extension_attempts']>0]
    excluded=[x for x in positive if x['retained_iteration_cannot_expand_main_extension']]
    possible=[x for x in positive if not x['retained_iteration_cannot_expand_main_extension']]
    # Unknown cell envelope: every root represents two swapped games, each in [0,1].
    pairs=packet['endpoint']['pairs']; points={x['case_id']:Fraction(str(x['points'])) for x in pairs}
    rows=admission['rows']; eligible=[x for x in rows if x['eligible']];valid=[x for x in rows if x['status']=='AUDITED']
    assert set(points)==set(admission['selected']) and len(points)==15 and sum(points.values())==13
    def bounds(subset):
        ids={x['case_id'] for x in subset};known=[v for k,v in points.items() if k in ids]
        return completion_envelope(sum(known,Fraction()),2*len(known),2*len(subset))
    family_bounds={str(f):bounds([x for x in eligible if x['family']==f]) for f in range(8)}
    equal_lower=sum(Fraction(x['lower']['rational']) for x in family_bounds.values())/8
    equal_upper=sum(Fraction(x['upper']['rational']) for x in family_bounds.values())/8
    density={str(d):bounds([x for x in eligible if x['density']==d]) for d in (5,9)}
    result={'source':SOURCE,'extension_count_scope':{'qualification_ON_returns':15,'positive_cumulative_count_roots':len(positive),'positive_but_retained_D1_cannot_extend':len(excluded),'their_count_sum':sum(x['total_extension_attempts'] for x in excluded),'remaining_positive_roots_with_retained_count_UNKNOWN':len(possible),'retained_causal_benefit_identified':False,'rows':ons,'qualification':'Conditional on the bound producer cold-start/return-source contract. No historical event trace or independent replay of Player. D1 proof: non-check root delta0, each main child enters at depth0; extension check is after depth<=0 exit. Q has no main extension. Cumulative counters can therefore arise in abandoned D2+ attempts. Warm game calls cannot use this cold argument without TT provenance.'},'finite_coverage_envelopes':{'eligible_roots':bounds(eligible),'all_compiler_valid_roots':bounds(valid),'families':family_bounds,'equal_family_eligible':{'lower':fraction(equal_lower),'upper':fraction(equal_upper)},'density_eligible':density,'invalid_roots':25,'invalid_anchor_and_game_scores':'UNDEFINED, never zero or draw','assumptions':'Each unobserved pair is allowed two hypothetical terminal scores in[0,1], without additional cross-root constraints. Bounds are sharp only for this numerical range model, not a realizability proof for the fixed engine or its future runtime. No missing score is imputed. Deterministic first-two sampling gives no random-sampling or population confidence claim.','interpretation':'These wide completion envelopes delimit possible extensions of the finite table; they do not recommend filling the pool or overturn the frozen FAILED selected-panel gate.'},'known_selected_result':packet['endpoint'],'experienced_regret_bounds':experienced_regret_lower_bounds(games)}
    allqueries=[q for g in games for q in g['queries']]
    nominal=[{'qid':q['query_id'],'ply':q['ply_before'],'remaining_clock':96-q['ply_before'],'completed_depth':q['decision']['completed_depth'],'pv_length':len(q['decision']['principal_variation']),'on':q['on']} for q in allqueries if q['decision']['completed_depth']>96-q['ply_before']]
    allraw=[raw_return(qid,returns) for qid in returns]
    result['clock_and_service_scope']={'nominal_depth_exceeds_rule_clock':len(nominal),'rows':nominal,'D64_calls':sum(q['decision']['completed_depth']==64 for q in allqueries),'recorded_service_above_requested_1_5':sum(q['service_wall_seconds']>1.5 for q in allraw),'total_including_qualification':len(allraw),'max_recorded_service_seconds':max(q['service_wall_seconds'] for q in allraw),'all_service_within_frozen_1_65':all(q['service_wall_seconds']<=1.65 for q in allraw),'scope':'Nominal completed depth is not physical path length; real CoreH96 may terminate earlier. No rule-clock cap was enabled in the frozen constructor. OFF main_search_max_ply0 is a disabled counter, not zero search. Cooperatively requested1.5s is accepted under the frozen1.65s ceiling; these are producer timing records, not independent hardware observations.'}
    output.mkdir(parents=True,exist_ok=True);(output/'exposure-and-coverage.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def feature_exposure(source,output):
    """Read maintained material channels at ALREADY SAVED qualification actions/PVs.

    No new alternative, label, solver, Player, training or fitted price is added.
    Main PV endpoints are not assumed to be actual Q leaves or TD targets.
    """
    from generic_chess.learning.incremental import compile_channels,_material_features
    from generic_chess.learning.features import material_features
    verify_archives(source)
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record
    from scripts.verify_published_boolean_returns import diagnostic_action
    from scripts.research_record import record_value
    roots={r['id']:r for r in load(source/'comparison-prepared/inputs.json')['rows']}
    returns=load(source/'comparison-run/returns.json');quals=load(source/'comparison-run/qualification.json')
    cases=[];pv_steps=0
    for rid,root in roots.items():
        c=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(root['RuleSet']))
        names=compile_channels(c,unit_type='A');session=GameSession.replay(c,deserialize_game_record(json.dumps(root['record'])))
        assert c.ruleset_fingerprint==root['fingerprint']
        rootphi=_material_features(session.state.position,c,names);assert not any(rootphi)
        assert list(rootphi)==material_features(session.state.position,('A','B','C'),perspective=0).array()
        arms={}
        for slot in (q for q in quals if q['case_id']==rid):
            raw=raw_return(slot['query_id'],returns);d=raw['decision'];first=d['action']
            child=GameSession.replay(c,session.to_record());child.submit(diagnostic_action(first,root['fingerprint']))
            childphi=_material_features(child.state.position,c,names)
            assert list(childphi)==material_features(child.state.position,('A','B','C'),perspective=0).array()
            pv=GameSession.replay(c,session.to_record())
            for a in d['principal_variation']:pv.submit(diagnostic_action(a,root['fingerprint']));pv_steps+=1
            phi=_material_features(pv.state.position,c,names)
            assert list(phi)==material_features(pv.state.position,('A','B','C'),perspective=0).array()
            assert all(v==0 for v,(kind,_) in zip(phi,names) if kind=='hand')
            leaf_actor=pv.state.position.side_to_move
            actor_phi=[v*(1 if leaf_actor==0 else -1) for v in phi]
            assert actor_phi==material_features(pv.state.position,('A','B','C'),perspective=leaf_actor).array()
            arms[str(raw['on'])]={'qid':raw['query_id'],'action':first,'selected_child_phi':list(childphi),'literal_main_PV_phi':list(phi),'main_PV_player':leaf_actor,'literal_main_PV_actor_phi':actor_phi,'main_PV_terminal':pv.state.terminal_status.is_terminal,'main_PV_length':len(d['principal_variation']),'completed_depth':d['completed_depth'],'result_qphase':d['result_ordinary_qdepth'],'raw_default_score':d['score']}
        assert set(arms)=={'False','True'}
        off,on=arms['False'],arms['True']
        cases.append({'case_id':rid,'family':root['family'],'fingerprint':root['fingerprint'],'channels':list(map(list,names)),'root_phi':list(rootphi),'arms':arms,'different_selected_action':off['action']!=on['action'],'different_selected_child_material':off['selected_child_phi']!=on['selected_child_phi'],'different_main_PV_material':off['literal_main_PV_phi']!=on['literal_main_PV_phi'],'different_default_score':off['raw_default_score']!=on['raw_default_score']})
    result={'source':SOURCE,'cases':cases,'roots':len(cases),'saved_qualification_returns':30,'saved_main_PV_steps':pv_steps,'root_zero_vectors':sum(not any(x['root_phi']) for x in cases),'action_difference_pairs':sum(x['different_selected_action'] for x in cases),'action_differences_with_equal_child_material':sum(x['different_selected_action'] and not x['different_selected_child_material'] for x in cases),'main_PV_material_difference_pairs':sum(x['different_main_PV_material'] for x in cases),'nonzero_ongoing_main_PV_endpoints':sum(any(a['literal_main_PV_phi']) and not a['main_PV_terminal'] for x in cases for a in x['arms'].values()),'scope':'Diagnostic material-feature support only. No actual learner call/gradient/fit, new labels or WDL inference. Different families have different A/B/C movements; type names are not pooled parameter identity. Default-v5 Q4 search scores cannot be paired with these exported MAIN-PV material features as exact TDLeaf targets. Current maintained learner deliberately uses fresh configuredQ0/fullPV/numeric match. Zero root vector does not imply no deeper learning signal; unreachable hand features do not imply true hand price zero.'}
    result['declared_fixed_unit']='board:A index0, declared before extraction; no alternative-unit scan'
    result['nonzero_trainable_feature_main_PV_returns']=sum(any(a['literal_main_PV_phi'][1:]) for row in cases for a in row['arms'].values())
    result['trainable_feature_rows']=[{'case_id':row['case_id'],'on':arm=='True','qid':a['qid'],'phi':a['literal_main_PV_phi']} for row in cases for arm,a in row['arms'].items() if any(a['literal_main_PV_phi'][1:])]
    result['same_main_PV_material_but_different_default_score_pairs']=[row['case_id'] for row in cases if row['different_default_score'] and not row['different_main_PV_material']]
    result['zero_ongoing_material_nonzero_raw_score_returns']=[{'case_id':row['case_id'],'on':arm=='True','qid':a['qid'],'raw_score':a['raw_default_score']} for row in cases for arm,a in row['arms'].items() if not a['main_PV_terminal'] and not any(a['literal_main_PV_phi']) and a['raw_default_score']!=0]
    result['independent_existing_feature_interface_checks']=75
    result['explicit_leaf_actor_perspective_checks']=30
    result['nonzero_endpoints_with_actor1']=sum(a['main_PV_player']==1 and any(a['literal_main_PV_phi']) for row in cases for a in row['arms'].values())
    result['gradient_scope']='Only2of30vectors have any nonzero freecoordinate, both B in the samefamily6/density9RuleSet. This is input support, not observed nonzero gradients/updates; tanh scaling, target error and receipt admissibility were not measured. C andhandchannelsare unexposed at these exportedendpoints,notzero-valued pieces or zero-valued stock.'
    output.mkdir(parents=True,exist_ok=True);(output/'feature-exposure.json').write_bytes((json.dumps(result,indent=2)+'\n').encode('utf8'));return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--replay',type=Path);p.add_argument('--phase',choices=['derived','features'],default='derived');p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=feature_exposure(a.source,a.output) if a.phase=='features' else analyze(a.source,a.replay,a.output)
    if a.phase=='features':
        print(json.dumps({k:v for k,v in r.items() if k!='cases'},indent=2));return
    summary={'extension':{k:v for k,v in r['extension_count_scope'].items() if k!='rows'},'coverage':r['finite_coverage_envelopes'],'regret':{k:v for k,v in r['experienced_regret_bounds'].items() if k!='pairs'},'clock':{k:v for k,v in r['clock_and_service_scope'].items() if k!='rows'}};print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
