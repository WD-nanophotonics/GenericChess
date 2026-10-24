"""Data-only full-history qualification for local controls and prospective mu."""
from pathlib import Path
from collections import Counter
import argparse,json,hashlib,time
from scripts import leaper_design as L
from scripts.leaper_two_type_packet import read_packet
from scripts.leaper_two_type_qualify import qualify_game
from scripts.semantic_probe_cost import unit_evaluator
from generic_chess.ai.evaluation.config import EvaluationConfig
from generic_chess.ai.evaluation.evaluator import Evaluator
from generic_chess.core.attacks import anchor_square,pseudo_attacks
from tools.local_agent.common import write_json

LEGACY_SLOT_POLICY_SOURCES={
    '02f8f8e4f009cc29dfe5978f4b87f3fe7592815ea46783f60f0da06b678d83cf':frozenset({'UNIT'}),
    'df7b67719cd01267d3e39a6c1f53d571b8dc1c012fc6ae2b2f891f5fe7201822':frozenset({'UNIT','STATIC_FIXED','DYNAMIC_FIXED','FULL_FIXED'}),
}

def validate_controller_labels(row,reg):
    actual=reg['controller'];assert row['controller']==actual and row['slot']['root']==reg['root']
    assert actual in {'UNIT','DEFAULT','STATIC_FIXED','DYNAMIC_FIXED','FULL_FIXED'}
    for q in row['queries']:
        assert q['actor'] in (0,1) and q['controller']==(actual if q['actor']==0 else 'UNIT')
    if row['slot']['policy']==actual:return None
    assert row['slot']['policy']=='DEFAULT' and actual in LEGACY_SLOT_POLICY_SOURCES.get(reg['source_sha256'],()),'unrecognized controller-label mismatch'
    return dict(recorded_slot_policy='DEFAULT',actual_controller=actual,executed_source_sha256=reg['source_sha256'],scope='Pinned historical constant-label defect only; actual registration/row/perquery/source match required, originals unchanged.')

def qualify_documents(docs,local_only=False):
    j=lambda name:json.loads(docs[name]);sha=lambda name:hashlib.sha256(docs[name].encode('utf-8')).hexdigest()
    world=j('contact/inputs.json');oldreg=j('contact/unit-registration.json')
    assert sha('contact/inputs.json')==oldreg['input_sha256']
    assert sha('source/baseline_forward.py')==oldreg['source_sha256']
    local=[];counts=Counter();legacy_labels=[]
    c=L.compile_rule(L.ruleset_from_dict(world['rule']));unit_eval=unit_evaluator(c);dp=L.AlphaBetaPlayer(c,use_disk_cache=False).evaluation_profile
    unit=qualify_game(world,j('contact/unit-reference.json'),oldreg);local.append(dict(controller='UNIT',**unit));counts.update(unit['counts'])
    for name,source in [('DEFAULT','driver-natural'),('UNIT-firstB','intervention'),('DEFAULT-firstA','intervention'),('STATIC_FIXED','driver'),('DYNAMIC_FIXED','driver'),('FULL_FIXED','driver')]:
        reg=j('contact/'+name+'-registration.json');row=j('contact/'+name+'.json')
        assert reg['input_sha256']==sha('contact/inputs.json') and reg['source_sha256']==sha('source/'+source+'.py')
        assert row['controller']==reg['controller'] and row.get('generated_default_profile',row.get('profile'))==reg['profile']==L.record_value(dp)
        if name in ('STATIC_FIXED','DYNAMIC_FIXED','FULL_FIXED'):
            assert reg['actual_leaf_profile']==L.record_value(unit_eval._profile if name=='DYNAMIC_FIXED' else dp)
            assert reg['actual_leaf_config']==L.record_value(unit_eval._config if name=='STATIC_FIXED' else EvaluationConfig())
        label_note=validate_controller_labels(row,reg)
        if label_note:legacy_labels.append(dict(section='contact',case=name,**label_note))
        q=qualify_game(world,row,reg);local.append(dict(controller=name,**q));counts.update(q['counts'])
    decomp=j('analysis/selected-leaf-decomposition.json');verified_leaves=0
    label_files={'UNIT':'unit-reference','UNIT-firstB':'UNIT-firstB','DEFAULT-firstA':'DEFAULT-firstA','DEFAULT':'DEFAULT','STATIC_FIXED':'STATIC_FIXED','DYNAMIC_FIXED':'DYNAMIC_FIXED','FULL_FIXED':'FULL_FIXED'}
    for group in decomp['rows']:
        row=j('contact/'+label_files[group['controller']]+'.json');s=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(row['initial_record'])));actual=[]
        for i,q in enumerate(row['queries']):
            pv=L.GameSession.replay(c,s.to_record())
            for a in q['decision']['principal_variation']:pv.submit(L.match_action(pv,a))
            if not pv.state.terminal_status.is_terminal:
                st=pv.state;ct=Counter((x.owner,x.current_type_id)for x in st.position.board if x);a=ct[0,'A']-ct[1,'A'];b=ct[0,'B']-ct[1,'B'];full=Evaluator(c,dp,EvaluationConfig());maps=full._attack_maps(st);mob=len(maps[0])-len(maps[1]);esc=full._anchor_escape(st.position,0,maps[1])-full._anchor_escape(st.position,1,maps[0]);check=int(anchor_square(st.position,1,c)in maps[0])-int(anchor_square(st.position,0,c)in maps[1]);material=1000*(a+b);static=891*a+1109*b;delta=2*mob+5*esc+50*check
                expected=dict(query=i,absolute_ply=st.ply_count,state_sha256=L.state_sha(st),deltaA=a,deltaB=b,unit=material,static_default=static,dynamic_unit=material+delta,full_default=static+delta,mobility_difference=mob,escape_difference=esc,check_difference=check)
                actual.append(expected);verified_leaves+=1
            s.submit(L.match_action(s,q.get('executed_action',q['action'])))
        assert actual==group['leaves'] and len(actual)==group['nonterminal_PV_leaves']
    if local_only:
        return dict(status='PASS',local=local,legacy_slot_policy_mislabels=legacy_labels,verified_selected_PV_leaves=verified_leaves,counts=dict(counts),new_Player_queries=0,source_capsule_executions=0)
    cold_plan=j('analysis/common-depth-plan.json');cold=j('analysis/common-depth-returns.json');cold_analysis=j('analysis/common-depth-analysis.json');cold_pv=0
    assert cold_plan['input_sha256']==sha('contact/inputs.json') and cold['status']=='CLOSED' and cold['missing']==0 and len(cold['rows'])==24
    assert cold_analysis['source_sha256']==sha('source/common_depth.py')
    source_names={'ac-default-game.json':'DEFAULT','ac-default-firstA-game.json':'DEFAULT-firstA'}
    roles=[]
    for h in cold_plan['histories']:
        source=j('contact/'+source_names[h['source']]+'.json');ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(source['initial_record'])))
        for q in source['queries'][:h['prefix']]:ss.submit(L.match_action(ss,q.get('executed_action',q['action'])))
        assert L.record_value(ss.to_record())==h['record'] and L.state_sha(ss.state)==h['state_sha256'];roles.append(ss.state.position.side_to_move)
    assert len({(r['history'],r['requested_depth'],r['controller'])for r in cold['rows']})==24
    for row in cold['rows']:
        d=row['decision'];ss=L.GameSession.replay(c,L.deserialize_game_record(json.dumps(cold_plan['histories'][row['history']]['record'])))
        assert row['requested_depth']in cold_plan['depths'] and row['controller']in cold_plan['controllers'] and d['completed_depth']==row['requested_depth']
        assert d['qnodes']==0 and d['nodes']<=cold_plan['nodes'];L.match_action(ss,d['action'])
        for a in d['principal_variation']:ss.submit(L.match_action(ss,a));cold_pv+=1
    minimal=j('next/inputs.json');prep=j('next/preparation.json');front=j('next/frontier.json');freg=j('next/frontier-registration.json')
    assert prep['input_sha256']==freg['input_sha256']==sha('next/inputs.json') and prep['source_sha256']==sha('source/minimal_prepare.py')
    assert freg['source_sha256']==sha('source/minimal_frontier.py') and front['status']=='CLOSED' and not front['missing']
    mc=L.compile_rule(L.ruleset_from_dict(minimal['rule']));assert L.record_value(L.AlphaBetaPlayer(mc,use_disk_cache=False).evaluation_profile)==minimal['profile']
    from scripts.leaper_two_type_forward import profiles
    ev={str(b):profiles(mc,b)[0]for b in (500,1000,2000)};next_edges=0
    def material_values(ss):
        if ss.state.terminal_status.is_terminal:
            value=0 if ss.result.winner is None else (1 if ss.result.winner==0 else -1)*(1000000000-ss.state.ply_count)
            return {k:value for k in ev}
        return {k:e.evaluate(ss.state)*(1 if ss.state.position.side_to_move==0 else -1)for k,e in ev.items()}
    assert len(minimal['roots'])==len(front['rows'])==8
    for root,row in zip(minimal['roots'],front['rows']):
        ss=L.GameSession.replay(mc,L.deserialize_game_record(json.dumps(root['record'])));assert row['initial_record']==root['record'] and L.record_value(ss.state)==root['state'] and ss.state.ply_count==0
        ct=Counter((x.owner,x.current_type_id)for x in ss.state.position.board if x);assert dict(ct)=={(0,'K'):1,(0,'A'):1,(1,'K'):1,(1,'B'):1}
        assert unit_evaluator(mc).evaluate(ss.state)==0 and root['initial_material_coefficients']=={'A':1,'B':-1}
        assert {json.dumps(L.record_value(a),sort_keys=True)for a in ss.legal_actions()}=={json.dumps(a['action'],sort_keys=True)for a in row['arms']}
        for arm in row['arms']:
            child=L.GameSession.replay(mc,ss.to_record());child.submit(L.match_action(child,arm['action']));next_edges+=1
            assert L.record_value(child.to_record())==arm['record'] and material_values(child)==arm['D1']
            legal=[]if child.state.terminal_status.is_terminal else child.legal_actions();assert {json.dumps(L.record_value(a),sort_keys=True)for a in legal}=={json.dumps(a['action'],sort_keys=True)for a in arm['replies']}
            for reply in arm['replies']:
                leaf=L.GameSession.replay(mc,child.to_record());leaf.submit(L.match_action(leaf,reply['action']));next_edges+=1
                assert L.record_value(leaf.to_record())==reply['record'] and material_values(leaf)==reply['values']
            assert arm['D2']=={k:min(x['values'][k]for x in arm['replies'])if arm['replies']else value for k,value in arm['D1'].items()}
        for depth in ('D1','D2'):
            expected={k:dict(value=max(a[depth][k]for a in row['arms']),actions=[a['action']for a in row['arms']if a[depth][k]==max(b[depth][k]for b in row['arms'])])for k in ev}
            assert expected==row['best'][depth] and len({json.dumps(v['actions'],sort_keys=True)for v in expected.values()})==1
    assert next_edges==front['edges'] and prep['Player_queries']==front['Player_queries']==0 and prep['training_updates']==front['learner_updates']==0
    fresh=j('fresh/inputs.json');reg=j('fresh/registration.json');results=j('fresh/results.json')
    assert results['status']=='CLOSED' and sha('fresh/inputs.json')==reg['input_sha256']
    assert sha('source/fresh_mu.py')==reg['source_sha256'] and sha('source/driver.py')==reg['driver_sha256']
    assert len(fresh['roots'])==12 and len(reg['slots'])==24 and len(results['slots'])==24
    fc=L.compile_rule(L.ruleset_from_dict(fresh['rule']));assert L.record_value(L.AlphaBetaPlayer(fc,use_disk_cache=False).evaluation_profile)==reg['profile']==fresh['profile']
    for root in fresh['roots']:
        ss=L.GameSession.replay(fc,L.deserialize_game_record(json.dumps(root['record'])));assert L.record_value(ss.state)==root['state'] and L.state_sha(ss.state)==root['state_sha256']
        assert not ss.state.terminal_status.is_terminal and len(ss.legal_actions())==root['legal_count']
        assert not any(anchor_square(ss.state.position,side,fc)in pseudo_attacks(ss.state.position,1-side,fc)for side in (0,1))
    summaries=[]
    for i,(slot,actual)in enumerate(zip(reg['slots'],results['slots'])):
        assert all(actual[k]==v for k,v in slot.items())
        if actual['status']!='finished':continue
        row=j(f'fresh/game-{i:03d}.json');case=j(f'fresh/case-{i:03d}.json')
        assert case['root']==slot['root'] and case['controller']==slot['controller']==row['controller']
        label_note=validate_controller_labels(row,case)
        if label_note:legacy_labels.append(dict(section='fresh',index=i,**label_note))
        assert case['source_sha256']==reg['driver_sha256'] and case['parent_registration_sha256']==sha('fresh/registration.json')
        assert case['profile']==reg['profile'] and case['nodes']==reg['nodes'] and 0<case['cap_seconds']<=reg['per_game_cap']
        q=qualify_game(fresh,row,case);assert actual['value']==q['value'] and actual['censor']==row['censor'];counts.update(q['counts']);summaries.append(dict(index=i,root=slot['root'],controller=slot['controller'],**q))
    missing=[i for i,x in enumerate(results['slots'])if x['status']!='finished' or x['value']is None];assert results['missing']==missing
    pairs=[]
    for root in range(12):
        by={r['controller']:r for r in summaries if r['root']==root};d=by.get('DEFAULT',{}).get('value');u=by.get('UNIT',{}).get('value');lo=(d if d is not None else -1)-(u if u is not None else 1);hi=(d if d is not None else 1)-(u if u is not None else -1)
        pairs.append(dict(root=root,DEFAULT=d,UNIT=u,difference=None if d is None or u is None else d-u,lower=lo,upper=hi))
    return dict(status='PASS',local=local,legacy_slot_policy_mislabels=legacy_labels,verified_selected_PV_leaves=verified_leaves,cold_queries=24,cold_PV_plies=cold_pv,cold_history_roles=roles,next_input_roots=8,next_frontier_edges=next_edges,next_Player_queries=0,fresh=dict(rows=summaries,missing=missing,paired=pairs,mean_difference_bounds=[sum(x['lower']for x in pairs)/12,sum(x['upper']for x in pairs)/12]),counts=dict(counts),new_Player_queries=0,source_capsule_executions=0,scope='Data-only exact bytes and complete history/PV replay through shared Core. Finite12mu paired payoff bounds, not iid population inference or independently rerun search. row.profile is generated DEFAULT metadata, actual UNIT leaf/order follows explicit executed constructor.')

def qualify(packet,manifest,output):
    tick=time.perf_counter();out=qualify_documents(read_packet(packet,manifest));out['seconds']=time.perf_counter()-tick;write_json(output,out);print('PACKET_PASS',out['counts'],out['fresh']['mean_difference_bounds'],out['seconds'],flush=True);return out
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--packet',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();qualify(a.packet,a.manifest,a.output)
