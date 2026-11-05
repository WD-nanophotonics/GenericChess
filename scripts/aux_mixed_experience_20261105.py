"""One matched TRAIN-law control using unchanged TDLeaf/q0/Core.

Shared warmup is physical data once; Single/Mixed are copied model branches.
Root law, all slots, early terminals and caps freeze before the first Player.
"""
from __future__ import annotations
import argparse,gzip,hashlib,json,random,subprocess,time
from dataclasses import asdict
from pathlib import Path
from scripts import leaper_design as L
from scripts.leaper_prior_td_pilot import restore
from scripts.leaper_microgames import role_stop_requested
from scripts.aux_material_episode_20261105 import write,load
from generic_chess.learning.incremental import Model,TDLeafEpisode,FixedScaleSessionEnv,play_episode,BudgetEnd
SOURCE='d07794e6af9bc25ca59251d89fe86017bb099bac'
INPUT='docs/research/data/leaper_capture_admission_20261105/inputs.json.gz'
def code_sha():return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
def copied(model):return Model(model.weights,fixed=model.fixed,scale=model.scale)
def consumed_indices(events,episode):
    # on_query precedes a final guard and observe. A complete returned query
    # may therefore NOT be consumed after cancellation. Actual learner count
    # selects the chronological consumed prefix, never all callback receipts.
    if episode.update is None:return []
    n=episode.update['observed_searches']
    eligible=[i for i,e in enumerate(events) if e['kind']=='candidate' and e['receipt']['complete']]
    assert 0<=n<=len(eligible) and len(eligible)-n<=1
    return eligible[:n]
def freeze(out):
    out.mkdir(exist_ok=False)
    raw=subprocess.check_output(['git','show',SOURCE+':'+INPUT]);data=json.loads(gzip.decompress(raw));worlds={}
    for f in (0,1,2):
        worlds[str(f)]={str(l):next(r for r in data['rows'] if r['family']==f and r['layout']==l) for l in (0,1)}
        assert worlds[str(f)]['0']['RuleSet']['piece_types']==worlds[str(f)]['1']['RuleSet']['piece_types']
    roots={};slots=[];definitions=[]
    def slot(phase,stage,arm,f,role,layout,seed,rid):
        if rid not in roots:
            roots[rid]=None;definitions.append(dict(id=rid,family=f,layout=layout,seed=seed))
        slots.append(dict(id=len(slots),phase=phase,stage=stage,arm=arm,family=f,role=role,root=rid))
    for f in (0,1,2):
        for role in (0,1):slot('train','common','Common',f,role,0,202611050000+f*100+role,'common-f'+str(f)+'-r'+str(role))
    for f in (0,1,2):
        arms=('Single','Mixed') if f%2==0 else ('Mixed','Single')
        for arm in arms:
            for role in (0,1):slot('train','fork',arm,f,role,int(arm=='Mixed'),202611052000+f*100+role,'fork-'+arm+'-f'+str(f)+'-r'+str(role))
    for f in (0,1,2):
        for l in (0,1):
            rid='eval-f'+str(f)+'-l'+str(l);seed=202611059000+f*100+l
            slot('eval','frozen','Unit',f,0,l,seed,rid)
            for role in (0,1):
                arms=('Single','Mixed') if (f+l+role)%2==0 else ('Mixed','Single')
                for arm in arms:slot('eval','frozen',arm,f,role,l,seed,rid)
    # Definitions/slots are complete BEFORE Core outcomes are observed.
    compiled={}
    for d in definitions:
        key=str(d['family']),str(d['layout']);w=worlds[key[0]][key[1]]
        if key not in compiled:compiled[key]=L.compile_rule(L.ruleset_from_dict(w['RuleSet']))
        env=FixedScaleSessionEnv(restore(compiled[key],w['record']),unit_type='A',feature_mode='count_pairs')
        rng=random.Random(d['seed']);events=[]
        for _ in range(8):
            if env.terminal() is not None:break
            actions=sorted(env.actions(),key=lambda a:json.dumps(L.record_value(a),sort_keys=True))
            a=actions[rng.randrange(len(actions))];events.append(dict(actor=env.player(),choice=L.record_value(a)));env.push(a)
        roots[d['id']]=dict(**d,source_id=w['id'],record=L.record_value(env.session.to_record()),prefix_events=events,
            actual_prefix=len(events),terminal=env.terminal(),names=env.names,root_phi=env.features())
        assert env.names[17]==('pair','board','C','board','C')
    cfg=dict(source=SOURCE,input_path=INPUT,input_sha256=hashlib.sha256(raw).hexdigest(),producer_sha256=code_sha(),
        worlds=worlds,roots=roots,slots=slots,initial=[1.,1.,1.,0.,0.,0.]+[0.]*21,scale=10.,eta=.05,lam=.95,
        depth=2,query_nodes=2048,game_nodes=65536,game_seconds=30.,total_seconds=600.,total_queries=3584,total_nodes=2400000,horizon=64,
        question='Does a matched mixed-layout TRAIN law expose C/C and improve actual frozen play versus a Single-layout law at equal episode views/service?',
        selection='Families0/1/2 fixed source order; allTRAIN/EVALlegalUniform8prefixes fixed beforePlayer, distinct declared seed streams. Layout includes placement AND quantity; no oracle/prefix filtering or holdoutclaim.',
        models='Common2C1episodes/family once, copy complete fixed/scale/weights into Single/Mixed. Each branch2moreepisodes, Singlelayout0/Mixedlayout1. Fourepisodeviewsperarm,18physicalTRAINmaximum, not24.',
        evaluation='Bothlayouts/bothseats,24candidate+6Unitbaseline=30physicalmax,12pairedseatframes,not12independentbaselines. FrozenlearnerNone. No checkpoint/seed/family/model selection or refill.',
        reuse='Only exactsamefrozenweights/fixed/scale/samecontext/role/seed may reuse an earlier actualterminal allD2record; Unit/Unit record may serve bothseatviews. No censored record reuse, no newgame/query claim.',
        budgets='Whole600s includes sharedcompile and output;game30s includesrestore/returnpacking. Queryslack3584 above48x64max3072. Actualconsumed learner rows inferred from observed_searches prefix, not callback count. Unexpectederror stopsrest;localUNKNOWN retainedwithoutretry.',
        cost='Priorrepresentation51.336+linearprelude11.776min+currentintakecarried. Forecast40min from13:31:34includingengineering/tests/analysis/delivery;55isNOTavailablebalance,cumulative120checkpointtakesprecedence;reserveclosing. No phase/UUID reset, newworker/search/default or PRIMARYtask.')
    write(out/'plan.json',cfg);print(json.dumps(dict(slots=len(slots),roots=len(roots),terminal_prefixes=sum(r['terminal'] is not None for r in roots.values())),indent=2))
def run(out):
    cfg=load(out/'plan.json');assert cfg['producer_sha256']==code_sha()
    with (out/'execution.json').open('x',encoding='utf-8') as f:json.dump({'started_utc':time.time(),'source':cfg['source']},f)
    began=time.perf_counter();cpu=time.process_time();totals={'queries':0,'nodes':0};rows=[];fatal=None
    compiled={(f,l):L.compile_rule(L.ruleset_from_dict(w['RuleSet'])) for f,ls in cfg['worlds'].items() for l,w in ls.items()}
    unit=Model(cfg['initial'],scale=cfg['scale']);models={'Common:'+f:copied(unit) for f in cfg['worlds']};forked=False;frozen=False;cache={};terminal_cache={}
    def snapshot():return {k:dict(weights=list(m.weights),fixed=m.fixed,scale=m.scale) for k,m in models.items()}
    def guard():
        if role_stop_requested():raise BudgetEnd('USER_STOP')
        if time.perf_counter()-began>=cfg['total_seconds']:raise BudgetEnd('STUDY_TIME_UNKNOWN')
        if totals['queries']>=cfg['total_queries']:raise BudgetEnd('STUDY_QUERY_UNKNOWN')
        if totals['nodes']>=cfg['total_nodes']:raise BudgetEnd('STUDY_NODES_UNKNOWN')
    with (out/'games.jsonl').open('x',encoding='utf-8',buffering=1) as stream:
        for slot in cfg['slots']:
            row=dict(slot=slot);f=str(slot['family']);arm=slot['arm'];phase=slot['phase'];root=cfg['roots'][slot['root']]
            if slot['stage']=='fork' and not forked:
                write(out/'warmup_models.json',snapshot())
                for family in cfg['worlds']:
                    for branch in ('Single','Mixed'):models[branch+':'+family]=copied(models['Common:'+family])
                forked=True
            if phase=='eval' and not frozen:write(out/'frozen_models.json',snapshot());frozen=True
            model=unit if arm=='Unit' else models[arm+':'+f]
            if fatal:row.update(status='NOT_STARTED',reason=fatal)
            else:
                try:guard()
                except BudgetEnd as e:fatal=str(e);row.update(status='NOT_STARTED',reason=fatal)
                else:
                    key=(slot['root'],slot['role'],tuple(model.weights),model.fixed,model.scale)
                    source=terminal_cache.get(slot['root']) if phase=='eval' else None
                    terminal_reuse=source is not None
                    if phase=='eval' and (terminal_reuse or key in cache):
                        source=source if terminal_reuse else cache[key];actual=source['result']['outcome']
                        row.update(status='REUSED_TERMINAL_CONTEXT' if terminal_reuse else 'REUSED_SAME_FROZEN_POLICY',source_slot=source['slot']['id'],before=list(model.weights),after=list(model.weights),outcome=actual,
                            utility=actual*(1 if slot['role']==0 else -1),physical_game=False,service_executed=False,queries=0,nodes=0)
                    else:
                        eb=time.perf_counter();ec=time.process_time();events=[];before=list(model.weights)
                        env=FixedScaleSessionEnv(restore(compiled[f,str(root['layout'])],root['record']),unit_type='A',feature_mode='count_pairs')
                        def query(ply,actor,r):
                            totals['queries']+=1;totals['nodes']+=r.nodes
                            events.append(dict(ply=env.session.state.ply_count,local_ply=ply,actor=actor,kind='candidate' if actor==slot['role'] else 'Unit',receipt=L.record_value(asdict(r))))
                        try:
                            ep=play_episode(env,model,opponent=copied(unit),learner=TDLeafEpisode(eta=cfg['eta'],lam=cfg['lam']) if phase=='train' else None,
                                learner_color=slot['role'],horizon=max(1,cfg['horizon']-root['actual_prefix']),depth=cfg['depth'],query_nodes=cfg['query_nodes'],
                                max_nodes=min(cfg['game_nodes'],cfg['total_nodes']-totals['nodes']),seconds=cfg['game_seconds']-(time.perf_counter()-eb),
                                seed=root['seed']+root['actual_prefix'],cancel=guard,on_query=query,search_backend='mainline')
                            actual=env.terminal();assert ep.outcome==actual
                            if phase=='eval':assert model.weights==before and ep.update is None
                            row.update(status='RETURNED',result=asdict(ep),utility=None if actual is None else actual*(1 if slot['role']==0 else -1),consumed_query_event_indices=consumed_indices(events,ep),physical_game=ep.plies>0,service_executed=True,initial_terminal=root['terminal'] is not None)
                            if arm in ('Common','Single'):assert model.weights[17]==0.  # C/C unexposed on no-create one-C roots.
                        except Exception as e:
                            fatal=type(e).__name__+':'+str(e);row.update(status='ERROR',error=fatal,physical_game=env.session.state.ply_count>root['actual_prefix'],service_executed=True,initial_terminal=root['terminal'] is not None)
                        row.update(before=before,after=list(model.weights),events=events,initial_record=root['record'],final_record=L.record_value(env.session.to_record()),terminal=L.record_value(env.session.result),wall_seconds=time.perf_counter()-eb,cpu_seconds=time.process_time()-ec)
                        if phase=='eval' and row['status']=='RETURNED' and row['result']['outcome'] is not None and all(e['receipt']['complete'] and e['receipt']['completed_depth']==cfg['depth'] for e in events):
                            cache[key]=row
                            if root['terminal'] is not None:terminal_cache[slot['root']]=row
                            if arm=='Unit':cache[slot['root'],1,tuple(model.weights),model.fixed,model.scale]=row
            rows.append(row);stream.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n')
            print(json.dumps(dict(slot=slot['id'],phase=phase,arm=arm,family=f,status=row['status'],utility=row.get('utility'),ending=row.get('result',{}).get('ending')),separators=(',',':')),flush=True)
    if not frozen:write(out/'frozen_models.json',snapshot())
    summary=dict(source=cfg['source'],physical_games=sum(r.get('physical_game',False) for r in rows),executed_episodes=sum(r.get('service_executed',False) for r in rows),terminal_root_services=sum(r.get('service_executed',False) and r.get('initial_terminal',False) for r in rows),reused_views=sum(r['status'].startswith('REUSED_') for r in rows),
        planned_slots=len(rows),totals=totals,whole_wall_seconds=time.perf_counter()-began,whole_cpu_seconds=time.process_time()-cpu,fatal=fatal,final_models=snapshot())
    write(out/'summary.json',summary);print(json.dumps(summary,separators=(',',':')))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('freeze','run'));p.add_argument('output',type=Path);a=p.parse_args();freeze(a.output) if a.mode=='freeze' else run(a.output)
