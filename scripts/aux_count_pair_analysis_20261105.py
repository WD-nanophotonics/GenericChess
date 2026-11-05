"""Actual count-conditioned pilot: physical semantics, TD and fixed baselines.

No new Player/game/training calls. Pair features are independently counted by
explicit pairs of actor/stock tokens, not the production count-product formula.
"""
from __future__ import annotations
import argparse,collections,itertools,json,math,time
from fractions import Fraction
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_prior_td_pilot import restore
from scripts.aux_material_first_action_20261105 import match
from scripts.aux_material_episode_analysis_20261105 import td_details,raw,write
from generic_chess.learning.incremental import FixedScaleSessionEnv,MATE

def physical_features(position,base_names):
    tokens=[[],[]];lookup={name:i for i,name in enumerate(base_names)}
    for piece in position.board:
        if piece is not None and ('board',piece.current_type_id) in lookup:
            tokens[piece.owner].append(lookup['board',piece.current_type_id])
    for owner,hand in enumerate(position.hands):
        for base,n in hand.counts:
            if ('hand',base) in lookup:tokens[owner].extend([lookup['hand',base]]*n)
    singles=collections.Counter();pairs=collections.Counter()
    for owner,items in enumerate(tokens):
        sign=1 if owner==0 else -1
        for i in items:singles[i]+=sign
        for a,b in itertools.combinations(items,2):pairs[tuple(sorted((a,b)))]+=sign
    return tuple(singles[i] for i in range(len(base_names)))+tuple(pairs[i,j] for i in range(len(base_names)) for j in range(i,len(base_names)))

def span_add(basis,values,insert=False):
    row=list(map(Fraction,values))
    for pivot,b in sorted(basis.items()):
        if row[pivot]:
            v=row[pivot];row=[a-v*c for a,c in zip(row,b)]
    pivot=next((i for i,x in enumerate(row) if x),None)
    if pivot is None:return True
    if insert:
        v=row[pivot];basis[pivot]=tuple(x/v for x in row)
    return False

def analyze(out):
    began=time.perf_counter();cfg=json.loads((out/'plan.json').read_bytes())
    rows=[json.loads(x) for x in (out/'games.jsonl').read_text().splitlines()]
    base_dir=Path(cfg['baseline_artifacts']);base=[json.loads(x) for x in (base_dir/'games.jsonl').read_text().splitlines()]
    assert len(rows)==len(cfg['slots'])==12 and cfg['feature_mode']=='count_pairs'
    compiled={(f,p):L.compile_rule(L.ruleset_from_dict(w['RuleSet'])) for f,world in cfg['worlds'].items() for p,w in world.items()}
    train=[];facts=[];workload=[];pairs=[];queries=nodes=edges=0
    train_phi={f:[] for f in cfg['worlds']};eval_phi={f:[] for f in cfg['worlds']}
    names=None
    for row,slot in zip(rows,cfg['slots']):
        assert row['slot']==slot and row['status']=='RETURNED'
        f=str(slot['family']);phase=slot['phase'];world=cfg['worlds'][f][phase]
        env=FixedScaleSessionEnv(restore(compiled[f,phase],world['record']),unit_type='A',feature_mode='count_pairs')
        assert len(env.names)==27 and row['initial_record']==world['record'];names=env.names
        freepairrows=0;localnodes=0
        for i,e in enumerate(row['events']):
            assert i==e['ply'] and e['actor']==env.player() and env.terminal() is None
            assert e['kind']==('candidate' if e['actor']==slot['role'] else 'Unit')
            assert env.features()==physical_features(env.session.state.position,env.base_names)
            r=e['receipt'];assert r['complete'] and r['completed_depth']==2
            leaf=FixedScaleSessionEnv(env.session,unit_type='A',feature_mode='count_pairs')
            assert r['pv_choices'][0]==r['action']
            for step in r['pv_choices']:leaf.push(match(leaf,step));edges+=1
            if r['pv_terminal']:
                assert leaf.terminal() is not None and r['value']==MATE*leaf.terminal() and r['pv_phi'] is None
            else:
                phi=leaf.features();assert phi==physical_features(leaf.session.state.position,leaf.base_names)
                assert list(phi)==r['pv_phi'] and leaf.terminal() is None
                w=row['before'] if e['actor']==slot['role'] else cfg['initial']
                assert math.isclose(raw(w,phi),r['value'],abs_tol=1e-12)
                if e['actor']==slot['role']:
                    (train_phi if phase=='train' else eval_phi)[f].append(phi)
                    freepairrows+=any(phi[6:])
            env.push(match(env,r['action']));queries+=1;nodes+=r['nodes'];localnodes+=r['nodes']
        assert L.record_value(env.session.to_record())==row['final_record']
        assert L.record_value(env.session.result)==row['terminal']
        assert env.terminal()==row['result']['outcome'] and row['utility']==env.terminal()*(1 if slot['role']==0 else -1)
        assert len(row['events'])==row['result']['plies'] and localnodes==row['result']['nodes']
        env.replay();assert env.features()==env.search_view().features() if env.terminal() is None else True
        if phase=='train':
            detail=td_details(row,cfg)
            detail['pair_gradient_rows']=sum(any(t['gradient'][6:]) for t in detail['terms'])
            detail['pair_delta_l1']=sum(abs(x-y) for x,y in zip(row['before'][6:],row['after'][6:]))
            train.append(detail)
            if slot['role']==0:
                original=next(b for b in base if b['slot']['phase']=='train' and b['slot']['family']==slot['family'] and b['slot']['role']==0)
                equal_record=row['final_record']==original['final_record']
                equal_queries=len(row['events'])==len(original['events'])
                equal_receipts=equal_queries and all((a['receipt']['action'],a['receipt']['pv_choices'],a['receipt']['value'],a['receipt']['nodes'],a['receipt']['completed_depth'])==(b['receipt']['action'],b['receipt']['pv_choices'],b['receipt']['value'],b['receipt']['nodes'],b['receipt']['completed_depth']) for a,b in zip(row['events'],original['events']))
                assert equal_record and equal_receipts and row['before']==cfg['initial']
                workload.append(dict(family=slot['family'],same_full_record=equal_record,same_action_value_PV_depth_nodes=equal_receipts,
                    queries=len(row['events']),nodes=localnodes,linear_wall=original['wall_seconds'],pair_wall=row['wall_seconds'],
                    linear_cpu=original['cpu_seconds'],pair_cpu=row['cpu_seconds'],wall_ratio=row['wall_seconds']/original['wall_seconds']))
        else:
            assert row['result']['update'] is None and row['after']==row['before']
            original=next(b for b in base if b['slot']['phase']=='eval' and b['slot']['family']==slot['family'] and b['slot']['arm']=='TD' and b['slot']['role']==slot['role'])
            unit=next(b for b in base if b['slot']['phase']=='eval' and b['slot']['family']==slot['family'] and b['slot']['arm']=='Unit')
            a=original['final_record']['actions'];b=row['final_record']['actions']
            first=next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y),min(len(a),len(b)))
            pairs.append(dict(family=slot['family'],role=slot['role'],PairTD_utility=row['utility'],LinearTD_utility=original['utility'],Unit_utility=unit['result']['outcome']*(1 if slot['role']==0 else -1),
                Pair_vs_Linear=row['utility']-original['utility'],same_linear_record=a==b,common_linear_prefix=first,
                same_unit_record=row['final_record']==unit['final_record']))
        facts.append(dict(slot=slot,terminal=row['terminal'],utility=row['utility'],plies=len(row['events']),candidate_pair_feature_rows=freepairrows))
    exposure=[]
    for f in cfg['worlds']:
        basis={}
        for phi in train_phi[f]:span_add(basis,phi[1:],insert=True)
        unseen=[names[j] for j in range(1,len(names)) if all(p[j]==0 for p in train_phi[f]) and any(p[j]!=0 for p in eval_phi[f])]
        exposure.append(dict(family=int(f),training_nonterminal_candidate_rows=len(train_phi[f]),evaluation_nonterminal_candidate_rows=len(eval_phi[f]),
            exact_free_feature_rank=len(basis),evaluation_rows_outside_training_free_span=sum(not span_add(basis,p[1:]) for p in eval_phi[f]),
            train_zero_eval_nonzero_channels=unseen))
    result=dict(source=cfg['source'],new_physical_games=len(rows),queries=queries,nodes=nodes,pv_edges=edges,zero_analysis_calls=True,
        feature_names=names,training=train,facts=facts,paired_views=pairs,first_episode_workload_controls=workload,exposure=exposure,
        summary=dict(train_utility=dict(collections.Counter(str(r['utility']) for r in rows if r['slot']['phase']=='train')),
            eval_utility=dict(collections.Counter(str(r['utility']) for r in rows if r['slot']['phase']=='eval')),
            changed_eval_records_vs_linear=sum(not p['same_linear_record'] for p in pairs),pair_delta_utility=sum(p['Pair_vs_Linear'] for p in pairs),
            terminal_kinds=dict(collections.Counter(r['terminal']['status'] for r in rows))),
        analysis_wall_seconds=time.perf_counter()-began,
        caveats='Exposed single representation control; exact baselines reused, no new strength denominator. Feature rank/exposure describes retained targets, not strategic identifiability or an admission gate. Three timing observations under ordinary concurrent use do not establish stable performance. All old caps/studies remain closed; no tuning.')
    # One concrete identifiability limit, tied to this consumer/input contract.
    # No extra fitted model or Player call: perturb ONLY a coefficient whose
    # gradient is structurally zero for every possible TRAIN trajectory.
    cc=tuple(names).index(('pair','board','C','board','C'))
    support=[]
    for f,worlds in cfg['worlds'].items():
        rule=worlds['train']['RuleSet']
        count=[sum(p is not None and p['owner']==owner and p['current_type_id']=='C'
                   for line in rule['initial_position'] for p in line) for owner in (0,1)]
        assert count==[1,1] and rule['capture_disposition']=='remove_from_game'
        assert not rule.get('semantic_actions') and not rule.get('transition_triggers')
        assert not rule.get('promotion_allowed') and not rule.get('promotion_forced')
        assert all(not t['is_promotable'] and not t['promotion_target_ids']
                   and all(a['kind']=='leap' for a in t['movement_atoms']) for t in rule['piece_types'])
        assert not any(v for masks in rule['drop_allowed'].values() for mask in masks for v in mask)
        assert all(phi[cc]==0 for phi in train_phi[f])
        support.append(dict(family=int(f),TRAIN_initial_C_by_owner=count,
            invariant='No creation/drop/promotion; C count per owner cannot increase. Therefore same-owner C/C pair feature and its TD gradient are zero on EVERY legal TRAIN continuation, not just saved PVs.'))
    witness=None
    for row in rows:
        if row['slot']['phase']!='eval':continue
        for event in row['events']:
            r=event['receipt']
            if event['actor']==row['slot']['role'] and not r['pv_terminal'] and r['pv_phi'][cc]:
                w=list(row['before']);alternative=w.copy();alternative[cc]+=1.
                prefix=dict(row['initial_record'],actions=row['final_record']['actions'][:event['ply']])
                witness=dict(family=row['slot']['family'],game=row['slot']['id'],ply=event['ply'],
                    root_record=prefix,literal_PV=r['pv_choices'],leaf_phi=r['pv_phi'],channel=names[cc],
                    learned_coefficient=w[cc],analytic_perturbation=1.,unchanged_all_TRAIN_predictions=True,
                    original_leaf_raw=raw(w,r['pv_phi']),alternative_leaf_raw=raw(alternative,r['pv_phi']),
                    interpretation='Analytic coefficient witness ONLY, never trained/played/selected. Both respect fixed linear A1 and all retained TRAIN predictions; EVAL leaf value differs. No numeric WDL/action label follows.')
                break
        if witness:break
    assert witness is not None
    result['structural_quantity_support']=support
    result['unidentified_coefficient_witness']=witness
    result['next_decision']='Additional epochs or a stronger teacher on the SAME one-C TRAIN quantity cannot expose C/C. A separately prospective mixed-quantity experience law could; do not assume zero C/C synergy or launch a refilled/tuned cohort.'
    write(out/'analysis.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('feature_names','training','facts','paired_views','unidentified_coefficient_witness')},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);analyze(p.parse_args().output)
