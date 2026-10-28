"""Bounded AUX interpretation/counterfactuals for the new static-mask packet.

No new Player/search, game campaign, fitted price, WDL solver or timing run.
"""
from __future__ import annotations
import argparse,copy,gzip,json
from collections import Counter
from dataclasses import replace
from pathlib import Path
from scripts.verify_aux_static_mask_packet import archive,save,SOURCE,encode,bound_inputs
from scripts.research_record import record_value

def dormant_type(source,output):
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution,compile_ruleset
    from generic_chess.ai.evaluation.config import EvaluationConfig
    from generic_chess.ai.evaluation.profile import build_ruleset_profile,_initially_reachable_type_ids
    from generic_chess.ai.evaluation.evaluator import Evaluator
    from generic_chess.core.search_runtime import _plain_leaper_hash_patterns
    from generic_chess.session.session import GameSession
    from generic_chess.session.serialization import deserialize_game_record
    from scripts.leaper_mask_evaluator import PureLeaperMaskEvaluator
    archive(source);row=bound_inputs(output)[1];rule=copy.deepcopy(row['RuleSet']);n=rule['board_size'];unused='UNUSED'
    assert unused not in {t['type_id'] for t in rule['piece_types']}
    rule['piece_types'].append(dict(type_id=unused,name=unused,movement_atoms=[dict(kind='leap',offset=[97,99])],is_anchor=False,is_promotable=False,promotion_target_ids=[]));rule['drop_allowed'][unused]=[[False]*(n*n)]*2
    ca=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(row['RuleSet']));cb=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(rule));assert _plain_leaper_hash_patterns(cb)is not None
    cfg=EvaluationConfig();pa=build_ruleset_profile(ca,cfg);pb=build_ruleset_profile(cb,cfg);ea=Evaluator(ca,pa,cfg);eb=Evaluator(cb,pb,cfg);fa=PureLeaperMaskEvaluator(ca,ea);fb=PureLeaperMaskEvaluator(cb,eb)
    la=build_ruleset_profile(compile_ruleset(ruleset_from_dict(row['RuleSet'])),cfg);lb=build_ruleset_profile(compile_ruleset(ruleset_from_dict(rule)),cfg)
    oldids=set(ca.types_by_id)
    assert all(pa.piece_profiles[t].raw_capability_score==pb.piece_profiles[t].raw_capability_score for t in oldids)
    assert all(la.board_value_by_type[t]==lb.board_value_by_type[t] for t in oldids)
    assert all(ca.empty_mobility[t]==cb.empty_mobility[t] for t in oldids)
    assert all(not any(any(owner) for owner in cb.drop_allowed[t]) for t in cb.drop_allowed)
    assert all(p is None or p.base_type_id!=unused and p.current_type_id!=unused for p in cb.initial_position.board)
    assert all(h.count(unused)==0 for h in cb.initial_position.hands)
    assert all(e.kind in ('move','remove') for p in cb.ir.patterns if cb.ir.geometry[p.geometry_ids[0]].kind!='drop' for e in p.effects)
    def active(c,exclude_unused=False):
        ps=[p for p in c.ir.patterns if c.ir.geometry[p.geometry_ids[0]].kind!='drop' and (not exclude_unused or unused not in p.type_ids)]
        assert len({p.name for p in ps})==len(ps)
        return {p.name:p for p in ps}
    ap,bp=active(ca),active(cb,True);assert set(ap)==set(bp)
    pattern_map={}
    for name,p in ap.items():
        x,y=record_value(p),record_value(bp[name]);x.pop('pattern_id');y.pop('pattern_id');assert x==y
        pattern_map[p.pattern_id]=bp[name].pattern_id
    assert all(record_value(ca.ir.geometry[g])==record_value(cb.ir.geometry[g]) for p in ap.values() for g in p.geometry_ids)
    def mapped(action):return replace(action,pattern_id=pattern_map[action.pattern_id])
    ra=deserialize_game_record(json.dumps(row['record']));rb=replace(ra,ruleset_fingerprint=cb.ruleset_fingerprint,actions=tuple(map(mapped,ra.actions)))
    sa=GameSession.replay(ca,ra);sb=GameSession.replay(cb,rb)
    def behavioral(s):
        p=s.state.position
        return (p.board,p.hands,p.side_to_move,p.aux_state,s.state.ply_count,s.state.terminal_status,tuple(sorted(v for _,v in s.state.repetition_counts)))
    assert behavioral(sa)==behavioral(sb)
    aa=sa.legal_actions();ab=sb.legal_actions();assert Counter(encode(record_value(mapped(x))) for x in aa)==Counter(encode(record_value(x)) for x in ab)
    witness=None;checked=0
    for a in aa:
        b=mapped(a);xa=GameSession.replay(ca,sa.to_record());xb=GameSession.replay(cb,sb.to_record());xa.submit(a);xb.submit(b);assert behavioral(xa)==behavioral(xb);checked+=1
        va,vb=ea.evaluate(xa.state),eb.evaluate(xb.state);assert fa.evaluate(xa.state)==va and fb.evaluate(xb.state)==vb
        if va!=vb and not xa.state.terminal_status.is_terminal:
            witness=dict(action=record_value(a),mapped_action=record_value(b),original_value=va,augmented_value=vb,original_material_seat0=sum((1 if p.owner==0 else -1)*pa.board_value_by_type[p.current_type_id] for p in xa.state.position.board if p is not None),augmented_material_seat0=sum((1 if p.owner==0 else -1)*pb.board_value_by_type[p.current_type_id] for p in xb.state.position.board if p is not None),actual_terminal=record_value(xa.state.terminal_status),original_record=record_value(xa.to_record()),augmented_record=record_value(xb.to_record()));break
    assert witness is not None
    raw={t:pa.piece_profiles[t].raw_capability_score for t in oldids};rawb={t:pb.piece_profiles[t].raw_capability_score for t in cb.types_by_id}
    def median(values):
        s=sorted(values);return s[len(s)//2] if len(s)%2 else (s[len(s)//2-1]+s[len(s)//2])/2
    result=dict(source=SOURCE,source_case=row['id'],original_fingerprint=ca.ruleset_fingerprint,augmented_fingerprint=cb.ruleset_fingerprint,appended_type=unused,all_existing_active_IR_patterns_equal_modulo_pattern_id=True,pattern_id_mapping=pattern_map,renamed_active_patterns=sum(k!=v for k,v in pattern_map.items()),all_existing_geometry_equal=True,eligible_mask_both=True,root_legal_actions=len(aa),literal_children_checked_before_first_witness=checked,root_legal_actions_with_renamed_pattern=sum(x.pattern_id!=mapped(x).pattern_id for x in aa),original_raw_capabilities=raw,augmented_raw_capabilities=rawb,original_raw_median=median([raw[t] for t in oldids if not ca.types_by_id[t].is_anchor]),augmented_raw_median=median([rawb[t] for t in cb.types_by_id if not cb.types_by_id[t].is_anchor]),original_board_values=dict(pa.board_value_by_type),augmented_board_values=dict(pb.board_value_by_type),legacy_original_board_values=dict(la.board_value_by_type),legacy_augmented_board_values=dict(lb.board_value_by_type),original_hand_values=dict(pa.hand_value_by_base_type),augmented_hand_values=dict(pb.hand_value_by_base_type),witness=witness,unreachability='Initial UNUSED inventory0; disabled drops; no promotions/creation/transform/aux/trigger/declaration; active effects only preserve moving type or remove enemy. By induction UNUSED stays absent. Old active patterns modulo explicit pattern-ID bijection/geometry, initial board/hands, all clock/repetition/terminal settings identical. Fingerprint is relabelled, never reused as an equal TT identity. Full history must be transported under this relation, not dropped.',interpretation='Actual finite reference-profile representation dependency. Mask still equals reference on each distinct RuleSet; this is not a mask optimization regression, proof of player-choice loss, WDL, strength, or permission to change historical profiles/defaults. Semantic-all-types is deliberately conservative for arbitrary effects; this narrow plain subset permits stronger reachability reasoning. Raw old geometry scores unchanged; median scaling and integer rounding change material-vs-fixed-dynamic balance.',augmented_RuleSet=rule)
    save(output/'dormant-type-counterexample.json',result);return {k:v for k,v in result.items() if k not in ('augmented_RuleSet','witness')}

def history_transport(output):
    """One specified reversible Core cycle; no Player, tree search or WDL oracle."""
    from generic_chess.rules.schema import ruleset_from_dict
    from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
    from generic_chess.session.session import GameSession
    from generic_chess.core.identity import repetition_identity_key,search_state_identity
    r=json.loads((output/'dormant-type-counterexample.json').read_bytes());rule=r['augmented_RuleSet'];old=copy.deepcopy(rule);old['piece_types']=[t for t in old['piece_types'] if t['type_id']!='UNUSED'];old['drop_allowed'].pop('UNUSED')
    ca=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(old));cb=compile_legacy_ruleset_for_semantic_execution(ruleset_from_dict(rule));sa,sb=GameSession(ca),GameSession(cb);initial_a,initial_b=sa.state,sb.state
    cycle=[((2,1),(4,1)),((4,5),(2,5)),((4,1),(2,1)),((2,5),(4,5))]
    assert ca.repetition_limit==cb.repetition_limit==4
    mapping={};trace=[];entry_counts=[]
    def check():
        a,b=sa.state,sb.state;ka=repetition_identity_key(a.position,ca);kb=repetition_identity_key(b.position,cb)
        assert mapping.setdefault(ka,kb)==kb and len(set(mapping.values()))==len(mapping)
        assert {mapping[k]:v for k,v in a.repetition_counts}==dict(b.repetition_counts)
        assert a.position.board==b.position.board and a.position.hands==b.position.hands and a.position.side_to_move==b.position.side_to_move and a.ply_count==b.ply_count and a.terminal_status==b.terminal_status
        assert all(p is None or p.current_type_id!='UNUSED' for p in a.position.board+b.position.board)
        if a.ply_count%4==0:entry_counts.append(dict(ply=a.ply_count,current_count=dict(a.repetition_counts)[ka],status=record_value(a.terminal_status)))
        trace.append(dict(ply=a.ply_count,source_key=ka,target_key=kb,source_counts=record_value(a.repetition_counts),target_counts=record_value(b.repetition_counts),source_history=record_value(a.history),target_history=record_value(b.history)))
    check()
    for start,end in cycle*(ca.repetition_limit-1):
        x=next(x for x in sa.legal_actions() if x.actor_type_id=='C' and (x.from_square.file,x.from_square.rank)==start and (x.to_square.file,x.to_square.rank)==end)
        y=replace(x,pattern_id=r['pattern_id_mapping'][x.pattern_id]);assert y in sb.legal_actions();sa.submit(x);sb.submit(y);check()
        if sa.state.ply_count==4:
            assert sa.state.position.board==initial_a.position.board and sb.state.position.board==initial_b.position.board
            assert search_state_identity(sa.state,ca)!=search_state_identity(initial_a,ca)
    assert sa.state.terminal_status.is_terminal and sa.state.terminal_status.winner is None
    result=dict(source=SOURCE,kind='Paired finite full-Core repetition contract trace, not engine gameplay or minimax label',literal_plies_per_rule=4*(ca.repetition_limit-1),distinct_mapped_repetition_keys=len(mapping),repeat_entries=entry_counts,full_count_maps_preserved_under_bijection=True,board_return_does_not_equal_search_state=True,source_record=record_value(sa.to_record()),target_record=record_value(sb.to_record()),trace=trace,limits='No TT bank/key reuse across fingerprints. Numeric profile equivalence was not assumed. This one concrete repetition path plus structural induction supports the declared transport only, not arbitrary trigger/perpetual/aux semantic rules.')
    save(output/'history-transport.json',result);return {k:v for k,v in result.items() if k not in ('trace','source_record','target_record')}

def timing_scope(source,output):
    from fractions import Fraction
    members,_=archive(source);get=lambda n:json.loads(members[n]);results={}
    for prefix,cold,offset in [('mask-evaluator',False,3),('cold-lifecycle',True,0)]:
        rows=get(prefix+'/queries.json')[offset:];groups=get(prefix+'/groups.json');arms={False:[],True:[]}
        for r in rows:arms[r['on'] if cold else r['mode']=='ON'].append(r)
        def totals(rs):
            return dict(wall=sum(x['wall_seconds'] for x in rs),cpu=sum(x['cpu_seconds'] for x in rs),evaluation_timed_wall=sum((x['decision'] if cold else x['stats'])['evaluation_seconds'] for x in rs),constructor_timed_wall=sum(x.get('constructor_seconds',0) for x in rs),work_nodes=sum((x['decision'] if cold else x['stats'])['nodes']+(x['decision'] if cold else x['stats'])['qnodes'] for x in rs),zero_cpu_calls=sum(x['cpu_seconds']==0 for x in rs))
        off,on=totals(arms[False]),totals(arms[True]);assert off['work_nodes']==on['work_nodes'];n0,n1=len(arms[False]),len(arms[True]);assert n0==n1==24
        epsilon=Fraction(1,64);c0=sum(Fraction(x['cpu_seconds']) for x in arms[False]);c1=sum(Fraction(x['cpu_seconds']) for x in arms[True]);lower=max(0,c1-n1*epsilon)/(c0+n0*epsilon);upper=(c1+n1*epsilon)/(c0-n0*epsilon)
        details=[]
        for i,g in enumerate(groups):
            r=rows[4*i:4*i+4];stats=r[0]['decision'] if cold else r[0]['stats']
            details.append(dict(id=g['id'],family=g['family'],reason=stats['termination_reason'],retained_depth=stats['completed_depth'],work_nodes=stats['nodes']+stats['qnodes'],wall_ratio=g['wall_ON']/g['wall_OFF'],cpu_ratio=g['cpu_ON']/g['cpu_OFF'] if g['cpu_OFF'] else None,weight_in_pooled_wall=g['wall_OFF']/off['wall']))
        delta_total=off['wall']-on['wall'];delta_eval=off['evaluation_timed_wall']-on['evaluation_timed_wall'];delta_setup=off['constructor_timed_wall']-on['constructor_timed_wall'];residual=delta_total-delta_eval-delta_setup
        result=dict(OFF=off,ON=on,pooled_wall_ratio=on['wall']/off['wall'],equal_root_mean_wall_ratio=sum(x['wall_ratio'] for x in details)/len(details),groups=details,recorded_wall_difference=delta_total,recorded_evaluation_timer_difference=delta_eval,recorded_constructor_timer_difference=delta_setup,residual_difference_by_bookkeeping=residual,baseline_evaluation_timer_fraction=off['evaluation_timed_wall']/off['wall'],all_recorded_CPU_multiples_of_1over64=all(Fraction(x['cpu_seconds'])*64==int(Fraction(x['cpu_seconds'])*64) for x in rows),conditional_CPU_error_model={'assumption':'Each recorded CPU interval differs from its target by at most epsilon seconds. This bound is hypothetical, not established by API units or observed quantization. No sampling or clock calibration inference.','epsilon':str(epsilon),'ratio_bounds':[str(lower),str(upper)],'ratio_bound_values':[float(lower),float(upper)],'epsilon_supremum_for_ratio_below_1':str((c0-c1)/(n0+n1)),'epsilon_supremum_for_ratio_below_frozen_095':str((Fraction(95,100)*c0-c1)/(n1+Fraction(95,100)*n0))},scope='Separate fixed measurements. Pooled ratio weights by recorded OFF service. Equal-root mean is a different descriptive statistic, not replacement gate. Timer differences/residual do not identify causal exclusive savings or prove unchanged hardware conditions. CPU-model bounds are conditional algebra, not CIs, measured error bars or repairs of the failed group-resolution gate.')
        results[prefix]=result
    save(output/'timing-scope.json',results);return {k:{f:v[f] for f in ('pooled_wall_ratio','equal_root_mean_wall_ratio','recorded_wall_difference','recorded_evaluation_timer_difference','residual_difference_by_bookkeeping','baseline_evaluation_timer_fraction','conditional_CPU_error_model')} for k,v in results.items()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--phase',choices=['dormant','timing','history'],default='dormant');a=p.parse_args();print(json.dumps(history_transport(a.output) if a.phase=='history' else (dormant_type if a.phase=='dormant' else timing_scope)(a.source,a.output),indent=2))
if __name__=='__main__':main()
