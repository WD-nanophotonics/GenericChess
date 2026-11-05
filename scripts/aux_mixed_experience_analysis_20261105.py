"""Saved-only matched-law analysis, no new Player or rollout calls."""
from __future__ import annotations
import argparse,collections,json,math,random,time
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_prior_td_pilot import restore
from scripts.aux_material_first_action_20261105 import match
from scripts.aux_count_pair_analysis_20261105 import physical_features
from scripts.aux_material_episode_analysis_20261105 import td_details,raw,write
from generic_chess.learning.incremental import FixedScaleSessionEnv,MATE

def analyze(out):
    began=time.perf_counter();cfg=json.loads((out/'plan.json').read_bytes())
    rows=[json.loads(x) for x in (out/'games.jsonl').read_text().splitlines()]
    assert len(rows)==len(cfg['slots'])==48
    compiled={(f,l):L.compile_rule(L.ruleset_from_dict(w['RuleSet'])) for f,ls in cfg['worlds'].items() for l,w in ls.items()}
    # Recreate the declared RANDOM initializer, retaining both early terminals.
    for root in cfg['roots'].values():
        f,l=str(root['family']),str(root['layout']);w=cfg['worlds'][f][l]
        env=FixedScaleSessionEnv(restore(compiled[f,l],w['record']),unit_type='A',feature_mode='count_pairs');rng=random.Random(root['seed'])
        for e in root['prefix_events']:
            assert env.terminal() is None and env.player()==e['actor']
            choices=sorted(env.actions(),key=lambda a:json.dumps(L.record_value(a),sort_keys=True));a=choices[rng.randrange(len(choices))]
            assert L.record_value(a)==e['choice'];env.push(a)
        assert L.record_value(env.session.to_record())==root['record'] and env.terminal()==root['terminal']
        assert len(root['prefix_events'])==root['actual_prefix']<=8
    expected={'Common:'+f:list(cfg['initial']) for f in cfg['worlds']};forked=False;diagnostics=[];facts=[];queries=nodes=edges=0
    for row,slot in zip(rows,cfg['slots']):
        assert row['slot']==slot
        f=str(slot['family']);root=cfg['roots'][slot['root']];phase=slot['phase'];arm=slot['arm']
        if slot['stage']=='fork' and not forked:
            for family in cfg['worlds']:
                for branch in ('Single','Mixed'):expected[branch+':'+family]=expected['Common:'+family].copy()
            warm=json.loads((out/'warmup_models.json').read_bytes())
            for family in cfg['worlds']:assert warm['Common:'+family]==dict(weights=expected['Common:'+family],fixed=0,scale=cfg['scale'])
            forked=True
        if row['status'].startswith('REUSED_'):
            source=rows[row['source_slot']];assert source['status']=='RETURNED' and source['slot']['root']==slot['root']
            actual=source['result']['outcome'];assert actual is not None
            if row['status']=='REUSED_TERMINAL_CONTEXT':assert root['terminal']==actual and source['result']['plies']==0
            else:
                assert source['before']==row['before'] and (source['slot']['role']==slot['role'] or source['slot']['arm']=='Unit')
                assert all(e['receipt']['complete'] and e['receipt']['completed_depth']==cfg['depth'] for e in source['events'])
            assert row['before']==row['after']==expected[arm+':'+f]
            assert not row['physical_game'] and not row['service_executed'] and row['queries']==row['nodes']==0
            assert row['outcome']==actual and row['utility']==actual*(1 if slot['role']==0 else -1)
            continue
        assert row['status']=='RETURNED'
        want=cfg['initial'] if arm=='Unit' else expected[arm+':'+f];assert row['before']==want
        env=FixedScaleSessionEnv(restore(compiled[f,str(root['layout'])],root['record']),unit_type='A',feature_mode='count_pairs')
        eligible=[];localnodes=0
        for i,e in enumerate(row['events']):
            assert env.terminal() is None and e['actor']==env.player() and e['ply']==env.session.state.ply_count
            assert e['local_ply']==i and e['kind']==('candidate' if e['actor']==slot['role'] else 'Unit')
            assert env.features()==physical_features(env.session.state.position,env.base_names)
            r=e['receipt'];assert r['complete'] and r['completed_depth']==2
            leaf=FixedScaleSessionEnv(env.session,unit_type='A',feature_mode='count_pairs')
            assert r['pv_choices'][0]==r['action']
            for a in r['pv_choices']:leaf.push(match(leaf,a));edges+=1
            if r['pv_terminal']:assert leaf.terminal() is not None and r['pv_phi'] is None and r['value']==MATE*leaf.terminal()
            else:
                assert list(leaf.features())==r['pv_phi'] and leaf.features()==physical_features(leaf.session.state.position,leaf.base_names)
                w=row['before'] if e['actor']==slot['role'] else cfg['initial']
                assert math.isclose(raw(w,r['pv_phi']),r['value'],abs_tol=1e-12)
            if e['kind']=='candidate' and r['complete']:eligible.append(i)
            env.push(match(env,r['action']));queries+=1;nodes+=r['nodes'];localnodes+=r['nodes']
        actual=env.terminal();assert actual==row['result']['outcome']
        assert L.record_value(env.session.to_record())==row['final_record'] and L.record_value(env.session.result)==row['terminal']
        assert row['utility']==actual*(1 if slot['role']==0 else -1)
        assert len(row['events'])==row['result']['plies'] and localnodes==row['result']['nodes']
        assert row['physical_game']==(row['result']['plies']>0) and row['initial_terminal']==(root['terminal'] is not None)
        env.replay()
        if phase=='train':
            n=row['result']['update']['observed_searches'];assert row['consumed_query_event_indices']==eligible[:n]
            selected=dict(row,events=[row['events'][i] for i in row['consumed_query_event_indices']])
            detail=td_details(selected,cfg);cc=17
            terms=[dict(ply=t['ply'],phiCC=None if t['phi'] is None else t['phi'][cc],gradientCC=t['gradient'][cc],eligibilityCC=t['eligibility'][cc],error=t['error'],deltaCC=t['delta'][cc],target_kind=t['target_kind']) for t in detail['terms']]
            diagnostics.append(dict(slot=slot,consumed_queries=n,callback_candidate_complete=len(eligible),CC_nonzero_gradients=sum(t['gradientCC']!=0 for t in terms),
                CC_before=row['before'][cc],CC_after=row['after'][cc],CC_net_delta=row['after'][cc]-row['before'][cc],CC_terms=terms,
                utility=row['utility'],initial_terminal=row['initial_terminal'],queries=len(row['events']),nodes=localnodes,wall_seconds=row['wall_seconds'],cpu_seconds=row['cpu_seconds']))
            if arm in ('Common','Single'):assert all(t['phiCC'] in (0,None) for t in terms) and row['after'][cc]==0.
            expected[arm+':'+f]=row['after']
        else:assert row['consumed_query_event_indices']==[] and row['result']['update'] is None and row['before']==row['after']
        facts.append(dict(slot=slot,utility=row['utility'],terminal=row['terminal']['status'],added_plies=row['result']['plies'],candidate_queries=sum(e['actor']==slot['role'] for e in row['events']),
            physical_game=row['physical_game'],initial_terminal=row['initial_terminal']))
    frozen=json.loads((out/'frozen_models.json').read_bytes())
    for key,w in expected.items():assert frozen[key]==dict(weights=w,fixed=0,scale=cfg['scale'])
    def realized(row):
        if row['status'].startswith('REUSED_'):return rows[row['source_slot']]
        return row
    pairviews=[]
    for f in (0,1,2):
        for l in (0,1):
            rid='eval-f'+str(f)+'-l'+str(l)
            group=[r for r in rows if r['slot']['phase']=='eval' and r['slot']['root']==rid]
            base=next(r for r in group if r['slot']['arm']=='Unit')
            for role in (0,1):
                s=next(r for r in group if r['slot']['arm']=='Single' and r['slot']['role']==role)
                m=next(r for r in group if r['slot']['arm']=='Mixed' and r['slot']['role']==role)
                sr,mr=realized(s),realized(m);a=sr['final_record']['actions'];b=mr['final_record']['actions']
                first=next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y),min(len(a),len(b)))
                pairviews.append(dict(family=f,layout=l,role=role,Single_utility=s['utility'],Mixed_utility=m['utility'],
                    Unit_utility=base['result']['outcome']*(1 if role==0 else -1),difference=m['utility']-s['utility'],same_record=a==b,first_difference_absolute_ply=first,
                    initial_terminal=cfg['roots'][rid]['terminal'] is not None,candidate_decisions_Single=sum(e['actor']==role for e in sr['events']),candidate_decisions_Mixed=sum(e['actor']==role for e in mr['events'])))
    for f in (0,1,2):assert frozen['Single:'+str(f)]['weights'][17]==0.
    groups={}
    for arm in ('Common','Single','Mixed'):
        ds=[d for d in diagnostics if d['slot']['arm']==arm]
        groups[arm]=dict(episode_services=len(ds),consumed_queries=sum(d['consumed_queries'] for d in ds),nonzero_CC_gradient_rows=sum(d['CC_nonzero_gradients'] for d in ds),
            queries=sum(d['queries'] for d in ds),nodes=sum(d['nodes'] for d in ds),wall_seconds=sum(d['wall_seconds'] for d in ds),
            note='Commonphysicaldatais shared by bothlogicalmodels;do not countit twice in total physicalcost.')
    roots=list(cfg['roots'].values());overlaps=[]
    for a in roots:
        if not a['id'].startswith('eval'):continue
        for b in roots:
            if not b['id'].startswith('eval') and a['record']==b['record']:overlaps.append([a['id'],b['id']])
    result=dict(source=cfg['source'],zero_new_analysis_calls=True,episode_services=len(facts),played_continuations=sum(x['physical_game'] for x in facts),
        terminal_root_services=sum(x['initial_terminal'] for x in facts),reused_views=sum(r['status'].startswith('REUSED_') for r in rows),planned_slots=len(rows),
        root_sampler_paths=len(roots),root_sampler_actions=sum(r['actual_prefix'] for r in roots),queries=queries,nodes=nodes,pv_edges=edges,
        training_diagnostics=diagnostics,physical_training_cost=groups,episode_facts=facts,paired_eval_views=pairviews,exact_eval_train_root_overlaps=overlaps,
        summary=dict(paired_frames=len(pairviews),Mixed_minus_Single_WDL_sum=sum(p['difference'] for p in pairviews),
            Mixed_minus_Single_WDL_mean=sum(p['difference'] for p in pairviews)/len(pairviews),Mixed_minus_Single_gamepoint_mean=sum(p['difference'] for p in pairviews)/(2*len(pairviews)),
            changed_eval_records=sum(not p['same_record'] for p in pairviews),early_terminal_frames=sum(p['initial_terminal'] for p in pairviews),
            Single_CC=[frozen['Single:'+str(f)]['weights'][17] for f in (0,1,2)],Mixed_CC=[frozen['Mixed:'+str(f)]['weights'][17] for f in (0,1,2)]),
        analysis_wall_seconds=time.perf_counter()-began,
        caveats='Finite exposed experience-law contrast:placements AND quantities differ. Equalepisodeviews do not mean equalinfo/resourceuse. Sharedwarmup/reusedterminalviews/pairedseats notindependent samples;nonzeroCCupdate notintrinsicprice or pureCCcausalutility. No oraclelabel selection, extraepisode/tuning/refill or policystrengthclaim.')
    write(out/'analysis.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('training_diagnostics','episode_facts','paired_eval_views')},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);analyze(p.parse_args().output)
