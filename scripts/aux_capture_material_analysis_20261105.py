"""Describe actual new capture-rich learner episodes; no new search/training."""
from __future__ import annotations
import argparse, collections, json, math, time
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_prior_td_pilot import restore
from scripts.aux_material_first_action_20261105 import match
from scripts.aux_material_episode_analysis_20261105 import td_details,raw,write
from generic_chess.learning.incremental import FixedScaleSessionEnv,MATE

def analyze(out):
    began=time.perf_counter();cfg=json.loads((out/'plan.json').read_bytes())
    rows=[json.loads(x) for x in (out/'games.jsonl').read_text().splitlines()]
    assert len(rows)==len(cfg['slots'])==15 and cfg['opponent_policy']=='Unit'
    compiled={(f,p):L.compile_rule(L.ruleset_from_dict(w['RuleSet'])) for f,world in cfg['worlds'].items() for p,w in world.items()}
    facts=[];training=[];query_context={};allnodes=allqueries=edges=0
    for row,slot in zip(rows,cfg['slots']):
        assert row['slot']==slot and row['status']=='RETURNED'
        f=str(slot['family']);phase=slot['phase'];world=cfg['worlds'][f][phase]
        assert row['initial_record']==world['record']
        env=FixedScaleSessionEnv(restore(compiled[f,phase],world['record']),unit_type='A')
        roots=[];captures=[];nonterminal=free=0
        for i,e in enumerate(row['events']):
            assert i==e['ply'] and env.player()==e['actor'] and env.terminal() is None
            assert e['kind']==('candidate' if e['actor']==slot['role'] else 'Unit')
            r=e['receipt'];assert r['complete'] and r['completed_depth']==2
            leaf=FixedScaleSessionEnv(env.session,unit_type='A')
            assert r['pv_choices'] and r['pv_choices'][0]==r['action']
            for a in r['pv_choices']:leaf.push(match(leaf,a));edges+=1
            if r['pv_terminal']:
                assert leaf.terminal() is not None and r['pv_phi'] is None and r['value']==MATE*leaf.terminal()
            else:
                assert leaf.terminal() is None and list(leaf.features())==r['pv_phi']
                w=row['before'] if e['actor']==slot['role'] else cfg['initial']
                assert math.isclose(raw(w,r['pv_phi']),r['value'],abs_tol=1e-12)
                nonterminal+=1;free+=any(r['pv_phi'][1:3])
            roots.append(dict(ply=i,actor=e['actor'],root_phi=env.features(),leaf_phi=r['pv_phi'],leaf_terminal=leaf.terminal(),value=r['value'],choice=r['action']))
            choice=match(env,r['action'])
            board=env.session.state.position.board;prior=sum(x is not None for x in board)
            env.push(choice);now=sum(x is not None for x in env.session.state.position.board)
            if now<prior:captures.append(dict(ply=i,actor=e['actor'],removed=prior-now,root_phi=roots[-1]['root_phi'],after_phi=env.features(),choice=r['action']))
            allnodes+=r['nodes'];allqueries+=1
        assert L.record_value(env.session.to_record())==row['final_record']
        assert L.record_value(env.session.result)==row['terminal']
        assert env.terminal()==row['result']['outcome'] and row['utility']==env.terminal()*(1 if slot['role']==0 else -1)
        assert len(row['events'])==row['result']['plies']
        env.replay()
        if phase=='train':
            detail=td_details(row,cfg)
            by={}
            for term in detail['terms']:
                v=by.setdefault(term['target_kind'],[0.]*6)
                for j,x in enumerate(term['delta']):v[j]+=x
            detail['deltas_by_target']=by;training.append(detail)
        else:assert row['result']['update'] is None and row['after']==row['before']
        query_context[slot['id']]=roots
        facts.append(dict(slot=slot,terminal=row['terminal'],utility=row['utility'],plies=len(row['events']),captures=captures,nonterminal_query_rows=nonterminal,free_feature_query_rows=free))
    pairs=[]
    for f in (0,1,2):
        group=[r for r in rows if r['slot']['phase']=='eval' and r['slot']['family']==f]
        unit=next(r for r in group if r['slot']['arm']=='Unit')
        for r in group:
            if r['slot']['arm']!='TD':continue
            a=unit['final_record']['actions'];b=r['final_record']['actions']
            k=next((i for i,(x,y) in enumerate(zip(a,b)) if x!=y),min(len(a),len(b)))
            first=None
            if k<min(len(a),len(b)):
                qa=query_context[unit['slot']['id']][k];qb=query_context[r['slot']['id']][k]
                assert qa['actor']==qb['actor']==r['slot']['role'] and qa['root_phi']==qb['root_phi']
                first=dict(Unit=qa,TD=qb)
                if qa['leaf_phi'] is not None and qb['leaf_phi'] is not None:
                    first['saved_leaf_cross_values']={name:[raw(w,q['leaf_phi']) for q in (qa,qb)] for name,w in (('Unit',cfg['initial']),('TD',r['before']))}
            u=unit['result']['outcome']*(1 if r['slot']['role']==0 else -1)
            pairs.append(dict(family=f,role=r['slot']['role'],baseline_game=unit['slot']['id'],TD_game=r['slot']['id'],baseline_utility=u,TD_utility=r['utility'],difference=r['utility']-u,identical_record=a==b,common_prefix_plies=k,first_divergence=first))
    result=dict(source=cfg['source'],zero_new_calls=True,physical_games=len(rows),queries=allqueries,nodes=allnodes,pv_edges=edges,
        facts=facts,training=training,pairviews=pairs,
        summary=dict(train_utility=dict(collections.Counter(str(r['utility']) for r in rows if r['slot']['phase']=='train')),
            eval_TD_utility=dict(collections.Counter(str(p['TD_utility']) for p in pairs)),
            pair_differences=dict(collections.Counter(str(p['difference']) for p in pairs)),
            changed_eval_records=sum(not p['identical_record'] for p in pairs),terminal_kinds=dict(collections.Counter(r['terminal']['status'] for r in rows))),
        analysis_wall_seconds=time.perf_counter()-began,
        caveats='ThreephysicalUnitbaselines reused for sixseatviews; no sixindependentbaselinegames. Posthocdevelopment/quantitytransfer only. Freefeatures and actionchanges notWDLquality. SavedPVleafcrossvalues notallactionQ; alloldcaps/sourcecohortsclosed.')
    write(out/'analysis.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('facts','training','pairviews')},indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);analyze(p.parse_args().output)
