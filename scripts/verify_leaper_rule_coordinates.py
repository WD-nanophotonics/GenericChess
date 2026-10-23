"""Reproduce typed rule-coordinate evidence through scoped geometry and Core.

No AlphaBeta rerun, graph solver or independent-engine claim. All original
scientific JSON is byte-hash checked, repeated initial setups are reconstructed
losslessly, and actual API checks are counted separately from integer checks.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json,time
from collections import Counter
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_rule_coordinates import (
    PAIRS,template,cells,integer_actions,integer_terminal,physical_action,
    qualify_pairs,corner_catalog,branch_law,property_bounds,cost_summary,
    history_conversion_check,digest,now,new_orbit_check,rule_conditioning_alias,
    two_ply_coordinates,exact_forward2_witness,action_alignment,audit_mate_pv,qualify_offpv_oneply,active_offset_catalog,coordinates,
)
from scripts.verify_leaper_scope_e0 import recover_original_json
from generic_chess.rules.schema import RuleInitialSetupOption
from generic_chess.core.movegen import legal_actions
from generic_chess.core.transition import apply_action
from tools.local_agent.common import write_json
from tools.local_agent.slack_transport import save_plugin_original


def verify(bundle,output,reuse_pair_phase=None):
    if output.exists():raise ValueError('fresh output required')
    if not output.resolve().is_relative_to(Path.cwd().resolve()/'.local_agent'):raise ValueError('qualification outputs must be ignored local artifacts')
    output.mkdir(parents=True);start=now();tick=time.perf_counter();manifest=L.load(bundle.parent/'manifest.json');raw=bundle.read_bytes()
    assert hashlib.sha256(raw).hexdigest()==manifest['compressed_sha256'];body=gzip.decompress(raw)
    assert hashlib.sha256(body).hexdigest()==manifest['decoded_sha256'];p=json.loads(body)
    assert p['schema']=='genericchess.rule_coordinates.evidence.v1';docs={key:json.loads(text) for key,text in p['documents_utf8'].items()};restored={}
    source_capsules_verified=verify_runtime_sources(bundle.parent,p['producer_source_sha256'])
    for key,v in docs.items():
        assert digest(v)==p['logical_json_sha256'][key]
        original=p['documents_utf8'][key].encode('utf-8');assert hashlib.sha256(original).hexdigest()==p['original_json_sha256'][key]
        restored[key]=output/(key+'.json');save_plugin_original(restored[key],original)
    compiled={};rule_raw={}
    for factor in p['factorized_rules']:
        mu=docs[factor['common_mu_reference']];n=mu['board_size'];support=mu['support'];m=next(z['mask'] for z in docs['scale/results']['summaries'] if z['fingerprint']==factor['fingerprint'])
        r=replace(L.ruleset_from_dict(factor['base_rule']),initial_setup_options=tuple(RuleInitialSetupOption('s-'+'-'.join(map(str,s)),cells(s,n)) for s in support[1:]))
        expanded=L.ruleset_to_dict(r,include_metadata=True);assert digest(expanded)==factor['logical_sha256'] and L.compute_fingerprint(r)==factor['fingerprint']
        # Exact-template check prevents a mask tag from licensing labels on a
        # different scoring/clock/promotion/drop/auxiliary/history contract.
        expected=replace(template(m,n,support[0]),initial_setup_options=r.initial_setup_options)
        assert L.ruleset_to_dict(expected,include_metadata=True)==expanded
        restored[factor['key']]=recover_original_json(expanded,factor['original_file_sha256'],output/(factor['key']+'.json'))
        compiled[n,m]=L.compile_rule(r);rule_raw[n,m]=expanded
    if reuse_pair_phase is None:
        pair=qualify_pairs(output/'pairs',output/'pair-public-Core.json')
    else:
        # A failed later presentation check does not invalidate a completed
        # Core phase. Reuse ONLY with every exact phase input byte unchanged.
        pair=L.load(reuse_pair_phase)
        assert pair['status']=='PASS'
        for a,b in PAIRS:
            for name in (f'rows-{a}-{b}',f'pair-{a}-{b}-frozen',f'rule-{a}-{b}-{a}',f'rule-{a}-{b}-{b}'):
                assert L.sha(reuse_pair_phase.parent/'pairs'/(name+'.json'))==p['original_json_sha256']['pairs/'+name]
        write_json(output/'pair-public-Core.json',pair)

    assert pair['totals']==docs['pairs/qualification-v2']['totals']
    corner=corner_catalog(output/'corner-public-Core.json');assert L.record_value(corner['minimal'])==docs['pairs/corner-catalog']['minimal']
    counts=Counter();history_coordinates=[]
    for summary in docs['scale/results']['summaries']:
        n,m=summary['n'],summary['mask'];features=docs[f'scale/features-{n}-{m}']['rows'];c=compiled[n,m];N=len(features)
        selected={i*(N-1)//15 for i in range(16)};physical={};weighted=F(0);mate_edges=0;edges=0
        for index,row in enumerate(features):
            spec=row['placement'];key=None if index==0 else 's-'+'-'.join(map(str,spec));ss=L.GameSession(c,key)
            assert L.state_sha(ss.state)==row['state_sha256'];counts['full_initial_records_Core_checked']+=1
            model=dict(integer_actions(spec,m,0,n));terms={a:integer_terminal(child,m,1,n) for a,child in model.items()};hist=Counter(t['status'] for t in terms.values())
            assert len(model)==row['branch'] and hist['checkmate']==row['mate_children'] and hist['stalemate']==row['stalemate_children']
            assert sum(a[0]=='A' for a in model)==row['ordinary_moves'] and sum(a[0]=='K' for a in model)==row['king_moves']
            counts['integer_child_terminals_checked']+=len(model);edges+=len(model);mate_edges+=hist['checkmate'];weighted+=F(hist['checkmate'],len(model))/N
            for act,child in model.items():
                term=terms[act]['status'];assert physical.setdefault(child,term)==term
            if index in selected:
                aa={physical_action(L.record_value(a),n):a for a in legal_actions(ss.state,c)};assert set(aa)==set(model);counts['sampled_public_Core_frontiers']+=1
                for act,ac in aa.items():
                    ch=apply_action(ss.state,ac,c);assert L.record_value(ch.terminal_status)==terms[act];counts['sampled_public_Core_applied_edges']+=1
        pos=Counter(physical.values());expected=next(x for x in docs['scale/analysis']['state_history_coordinates'] if x['n']==n and x['mask']==m)
        assert len(physical)==expected['oneply_unique_physical_positions'] and edges==expected['oneply_full_history_count']
        assert expected['literal_mate_event_rates']=={'uniform_initial_then_uniform_action':str(weighted),'uniform_all_edges_or_fullhistories1':str(F(mate_edges,edges)),'uniform_unique_physical_children':str(F(pos['checkmate'],len(physical)))}
        history_coordinates.append({'n':n,'mask':m,'integer_reproduced_edges':edges,'physical_children':len(physical)})
        print({'n':n,'mask':m,'initial_records_checked':N,'sample_frontiers':len(selected)},flush=True)
    witnesses=docs['scale/literal-witnesses'];positive=fork=0
    for row in witnesses['rows']:
        c=compiled[row['n'],row['mask']];ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(row['source_full_record'])))
        assert L.state_sha(ss.state)==row['source_state_sha256'] and ss.state.position.ruleset_fingerprint==row['fingerprint']
        terms=[]
        for proof in row['proofs']:
            ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(proof['complete_record'])))
            assert L.state_sha(ss.state)==proof['child_state_sha256'] and L.record_value(ss.state.terminal_status)==proof['terminal'];terms.append(ss.state.terminal_status.winner)
            counts['complete_literal_child_records_replayed']+=1
        assert 0 in terms;positive+=1;fork+=int(None in terms);assert row['literal_fork_positive']==(None in terms)
    assert positive==488 and fork==328 and counts['complete_literal_child_records_replayed']==816
    law=branch_law(output/'scale',output/'branch-law-recomputed.json');assert law['rows']==docs['scale/branch-law']['rows']
    bounds=property_bounds(output/'scale',output/'property-bounds-recomputed.json');assert bounds['counts']==docs['scale/property-bounds']['counts']
    costs=cost_summary(output/'cost',output/'cost-public-Core.json');assert costs['qualification']==docs['cost/analysis']['qualification']
    conv=history_conversion_check(restored['pairs/stalemate-mutation'],output/'history-conversion-recomputed.json');assert conv['refusal']==docs['pairs/history-conversion']['refusal']
    added=verify_added_public(docs,output,output)
    result={'status':'PASS','bundle_sha256':L.sha(bundle),'decoded_sha256':manifest['decoded_sha256'],'added_facts':added,'runtime_source_capsules_verified':source_capsules_verified,'started_at':start,'ended_at':now(),'seconds':time.perf_counter()-tick,'counts':dict(counts),'pair_Core_edges':pair['totals']['integer_and_public_Core_edges'],'corner_controls':len(corner['rows']),'literal_positive_roots':positive,'literal_fork_positive_roots':fork,'cost_PVs':costs['qualification'],'restored_byte_exact_scientific_JSON':len(restored),'source_sha256':L.sha(Path(__file__)),'pair_phase_reused_after_exact_input_check':reuse_pair_phase is not None,
            'scope':'Distinct publicCoreAPI/sourcebinding, independent scoped integer calculations, allfullinitialrecords andallliteralpositiveforkwitnesses checked. Only384scaleCorefrontiers sampled, not all521388publicCorechildren rerun; those allproducerreturns separatelyhashretainedprivately. SharedCore, not independentengine/allhistoryoracle/WDLregion/strength/heldoutcalibration. No newPlayer queries.'}
    write_json(output/'qualification.json',result);print(result,flush=True);return result



def verify_added_public(docs,base,output):
    """Only newly added facts; old phases may be separately byte-bound/reused."""
    if 'pairs/new-orbit' not in docs:return {'new_facts':0}
    extended=new_orbit_check(output/'new-orbit-checked.json')
    assert L.record_value(extended['rows'])==docs['pairs/new-orbit']['rows']
    alias=rule_conditioning_alias(base/'pairs',output/'alias-checked.json')
    for key in ('physical_placement','shared_rule_blind_features','full_initial_records','full_initial_states','value_claims'):
        assert L.record_value(alias[key])==docs['pairs/rule-conditioning-alias'][key]
    f2=two_ply_coordinates(base/'scale',output/'forward2-checked.json')
    assert L.record_value(f2['rows'])==docs['scale/forward2']['rows'] and f2['counts']==docs['scale/forward2']['counts']
    exact=exact_forward2_witness(base/'scale',output/'forward2-checked.json',output/'forward2-exact-checked.json')
    assert L.record_value(exact['rows'])==docs['pairs/forward2-exact-witness']['rows']
    alignment=action_alignment(base/'pairs',output/'alignment-checked.json')
    assert alignment['totals']==docs['pairs/action-alignment-strict']['totals']
    # Validate the actual published examples, irrespective of set iteration
    # order when that illustrative (nonblind) subset was first retained.
    checks={tuple(x['masks']):x for x in docs['pairs/action-alignment-strict']['actual_Core_rematch_checks']}
    for row in docs['pairs/action-alignment-strict']['examples']:
        a,b=row['masks'];c=L.compile_rule(L.ruleset_from_dict(L.load(base/'pairs'/f'rule-{a}-{b}-{b}.json')))
        ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(row['target_initial_record'])))
        choices=[ac for ac in ss.legal_actions() if physical_action(L.record_value(ac),4)==tuple(row['physical_action'])]
        assert len(choices)==1 and L.record_value(choices[0])==row['target_IR_action']
        ss.submit(choices[0]);assert L.state_sha(ss.state)==checks[tuple(row['masks'])]['actual_target_state_sha256']
    audit=audit_mate_pv(base/'cost',output/'mate-pv-audit-checked.json')
    for key in ('trace','off_PV_defense_histories','verified_cooperative_complete_record'):
        assert L.record_value(audit[key])==docs['cost/mate7-defense-handoff'][key]
    narrow=qualify_offpv_oneply(base/'cost'/'mate7-defense-handoff.json',output/'mate-pv-oneply-checked.json')
    assert L.record_value(narrow['rows'])==docs['cost/mate7-defense-oneply']['rows']
    active_checks=0
    if 'pairs/active-offset-catalog' in docs:
        active=active_offset_catalog(output/'active-offset-checked.json')
        assert L.record_value(active['rows'])==docs['pairs/active-offset-catalog']['rows']
        for n in (3,4,5):assert L.record_value(coordinates(n))==docs['pairs/coordinates-corrected']['by_size'][str(n)]
        active_checks=active['minimal_pairs']
    return {'new_facts':9+(3 if active_checks else 0),'directional_active_offset_Core_checks':active_checks,'forward2_sample_Core':f2['counts'],'samephysical_IR_rematches':len(checks),'offPV_literal_child_returns':narrow['Core_child_returns'],'offPV_closed':narrow['literal_oneply_closed_branches'],'offPV_UNKNOWN':narrow['remaining_UNKNOWN_branches'],'new_Player_queries':0}



def verify_runtime_sources(directory,expected):
    raw=(directory/'executed-sources.json.gz').read_bytes()
    manifest=L.load(directory/'executed-sources-manifest.json')
    assert hashlib.sha256(raw).hexdigest()==manifest['compressed_sha256']
    body=gzip.decompress(raw);assert hashlib.sha256(body).hexdigest()==manifest['decoded_sha256']
    source=json.loads(body)
    assert set(source['sources'])==set(expected)
    for name,record in source['sources'].items():
        assert hashlib.sha256(record['utf8'].encode('utf-8')).hexdigest()==record['sha256']==expected[name]
    return len(expected)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--reuse-pair-phase',type=Path);a=p.parse_args();verify(a.bundle,a.output,a.reuse_pair_phase)
