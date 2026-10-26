"""Data-only full-session/PV and independent TD arithmetic reader.

No experimental search or training episodes are run. Exact frozen receipt
gradients, eligibility sums and actual terminal targets are checked separately
from any claim of full-tree optimality or terminal improvement.
"""
from collections import Counter
from pathlib import Path
from math import tanh,isclose
import argparse,json,time
import random
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import restore,write
from scripts.verify_leaper_frozen_learning import replay_query
from generic_chess.learning.incremental import FixedScaleSessionEnv,Model,MATE
from generic_chess.core.actions import action_to_dict


def td_sum(before,receipts,outcome,eta=.05,lam=.95,scale=10.):
    predictions=[]
    for r in receipts:
        if r['pv_terminal']:
            if (r.get('pv_phi') is not None or isinstance(r['value'],bool)
                    or r['value'] not in (-MATE,0.,MATE)):
                raise ValueError('terminal arithmetic requires literal MATE*WDL and no features')
            predictions.append(r['value']/MATE)
        else:
            predictions.append(tanh(r['value']/scale))
    elig=[0.]*len(before);delta=[0.]*len(before);terms=0;loss=0.;terminal_credit=0.
    for i,r in enumerate(receipts):
        target=predictions[i+1]if i+1<len(receipts)else outcome
        if target is None:break
        p=predictions[i];g=[0.]*len(before)if r['pv_terminal']else[x*(1-p*p)/scale for x in r['pv_phi']];g[0]=0.
        error=target-p;elig=[lam*a+b for a,b in zip(elig,g)];delta=[a+error*b for a,b in zip(delta,elig)];terms+=1;loss+=error*error/2
        if i+1==len(receipts):terminal_credit=sum(abs(error*e)for e in elig)
    after=[a+eta*b for a,b in zip(before,delta)];after[0]=1.
    return after,dict(samples=terms,loss=loss/max(1,terms),changed=any(delta),terminal_credit_l1=terminal_credit,observed_searches=len(receipts),censored=outcome is None)


def verify_game(world,row):
    c=L.compile_rule(L.ruleset_from_dict(world['rule']));slot=row['slot'];s=restore(c,world['roots'][slot['root']]['record']);counts=Counter();receipts=[]
    for q in row['queries']:
        if q['state_sha256']!=L.state_sha(s.state)or q['actor']!=s.state.position.side_to_move:raise ValueError('actual full-history query binding differs')
        r=q['receipt'];weights=row['before']if q['actor']==slot['role']else[1,1,0,0]
        counts['queries']+=1;counts['nodes']+=r['nodes']
        if not r['complete']:
            if r['action']is not None:raise ValueError('incomplete action advanced')
            continue
        if r['action']['kind']!='ACTION':raise ValueError('scope excludes declarations')
        action=L.match_action(s,r['action']['action'])
        counts['PV_plies']+=replay_query(s,weights,r,action_to_dict(action))
        if q['actor']==slot['role']:
            receipts.append(r);counts['own_queries']+=1
            if not r['pv_terminal']:
                counts['own_nonterminal_PV']+=1
                counts['own_active_B_PV']+=int(Model(weights).gradient(r['pv_phi'])[1]!=0)
        s.submit(action)
    if L.record_value(s.to_record())!=row['final_record']or L.record_value(s.result)!=row['terminal']:raise ValueError('final actual record differs')
    outcome=FixedScaleSessionEnv(s,unit_type='A').terminal()
    if row['result']['outcome']!=outcome:raise ValueError('UNKNOWN/actual terminal target differs')
    utility=None if outcome is None else outcome*(1 if slot['role']==0 else-1)
    if row['utility']!=utility:raise ValueError('utility perspective differs')
    if slot['phase']=='train':
        after,stats=td_sum(row['before'],receipts,outcome)
        if any(not isclose(a,b,abs_tol=1e-14,rel_tol=1e-13)for a,b in zip(after,row['after'])):raise ValueError('independent eligibility update differs')
        for key,value in stats.items():
            actual=row['result']['update'][key]
            if isinstance(value,float):
                if not isclose(actual,value,abs_tol=1e-14,rel_tol=1e-12):raise ValueError('TD statistic differs:'+key)
            elif actual!=value:raise ValueError('TD statistic differs:'+key)
    elif row['before']!=row['after']or row['result']['update']is not None:raise ValueError('frozen model changed during evaluation')
    return dict(counts)


def verify(pilot,initialization,output):
    began=time.perf_counter();totals=Counter();groups=[]
    for kind,directory in(('unit',pilot),('initialization',initialization)):
        cfg=json.loads((directory/'plan.json').read_bytes());rows=[];pairs={}
        for f in sorted(directory.glob('game-*.json')):
            row=json.loads(f.read_bytes());slot=row['slot'];world=cfg['worlds'][slot['group']]if kind=='unit'else cfg['world']
            counts=verify_game(world,row);totals.update(counts);rows.append(dict(slot=slot,counts=counts,before=row['before'],after=row['after'],utility=row['utility'],update=row['result']['update']))
            if slot['phase']=='eval':
                key=(slot.get('group',slot.get('initial')),slot['root'],slot['role']);pairs.setdefault(key,{})[slot['arm']]=row
        comparisons=[]
        for key,arms in pairs.items():
            baseline=arms['Unit'if kind=='unit'else'Initial'];td=arms['TD']
            comparisons.append(dict(key=key,difference=None if baseline['utility']is None or td['utility']is None else td['utility']-baseline['utility'],identical_record=baseline['final_record']==td['final_record']))
        groups.append(dict(kind=kind,games=len(rows),rows=rows,paired=comparisons))
    result=dict(verified=True,groups=groups,counts=dict(totals),seconds=time.perf_counter()-began,
        scope='Literal Core full histories/PVs and independent TD eligibility arithmetic, no new Player or training. Same engine semantics, not independently implemented rules; paired finite exposed starts, not an iid/heldout strength estimate.')
    write(output,result);return result


def verify_uniform_game(world,row):
    """Replay the actual RNG stream and committed record, including cap tails.

    A selected Uniform action or completed query can precede the episode's
    final cancellation poll. Such a last event is an observation, not a move
    or TD observation, unless the final public record actually contains it.
    """
    slot=row['slot'];c=L.compile_rule(L.ruleset_from_dict(world['rule']));s=restore(c,world['roots'][slot['root']]['record']);rng=random.Random(slot['seed']);counts=Counter();receipts=[]
    final=restore(c,row['final_record']);actions=final.to_record().actions
    for index,event in enumerate(row['events']):
        if event['state_sha256']!=L.state_sha(s.state)or event['actor']!=s.state.position.side_to_move:raise ValueError('Uniform event state binding differs')
        candidate=event['kind']=='candidate';choice=None
        if candidate:
            if event['actor']!=slot['role']:raise ValueError('opponent search fabricated')
            r=event['receipt'];counts['queries']+=1;counts['nodes']+=r['nodes']
            if r['complete']:
                choice=L.match_action(s,r['action']['action']);counts['PV_plies']+=replay_query(s,row['before'],r,action_to_dict(choice))
        else:
            if event['kind']!='Uniform'or event['actor']==slot['role']:raise ValueError('Uniform role differs')
            legal=sorted(FixedScaleSessionEnv(s,unit_type='A').actions(),key=lambda a:json.dumps(L.record_value(a),sort_keys=True));expected=legal[rng.randrange(len(legal))]
            if L.record_value(expected)!=event['choice']:raise ValueError('actual legal Uniform RNG stream differs')
            choice=expected.action;counts['Uniform_selections']+=1
        committed=s.state.ply_count<len(actions)
        if not committed:
            if index!=len(row['events'])-1 or row['result']['outcome']is not None:raise ValueError('uncommitted event is not an UNKNOWN tail')
            counts['uncommitted_tail_events']+=1;continue
        if choice is None or choice!=actions[s.state.ply_count]:raise ValueError('event does not match actual committed action')
        if candidate:
            receipts.append(event['receipt']);r=event['receipt'];counts['own_queries']+=1
            if not r['pv_terminal']:counts['own_active_B_PV']+=int(Model(row['before']).gradient(r['pv_phi'])[1]!=0)
        s.submit(choice);counts['committed_plies']+=1
    if s.to_record()!=final.to_record()or L.record_value(s.result)!=row['terminal']:raise ValueError('Uniform final record differs')
    outcome=FixedScaleSessionEnv(s,unit_type='A').terminal()
    if row['result']['outcome']!=outcome or row['result']['plies']!=counts['committed_plies']:raise ValueError('Uniform target/plies differ')
    if row['result']['queries']!=counts['queries']or row['result']['nodes']!=counts['nodes']:raise ValueError('Uniform actual search work differs')
    utility=None if outcome is None else outcome*(1 if slot['role']==0 else-1)
    if row['utility']!=utility:raise ValueError('Uniform payoff perspective differs')
    if slot['phase']=='train':
        after,stats=td_sum(row['before'],receipts,outcome)
        if any(not isclose(a,b,abs_tol=1e-14,rel_tol=1e-12)for a,b in zip(after,row['after'])):raise ValueError('Uniform independent update differs')
        for key,value in stats.items():
            actual=row['result']['update'][key]
            if isinstance(value,float):
                if not isclose(actual,value,abs_tol=1e-14,rel_tol=1e-12):raise ValueError('Uniform TD statistic differs')
            elif actual!=value:raise ValueError('Uniform TD statistic differs')
    elif row['before']!=row['after']or row['result']['update']is not None:raise ValueError('Uniform evaluation updated its model')
    return dict(counts)


def verify_uniform(directory,output):
    began=time.perf_counter();cfg=json.loads((directory/'plan.json').read_bytes());result=json.loads((directory/'result.json').read_bytes());totals=Counter();rows=[];models={g:[1,1,0,0]for g in cfg['worlds']};pairs={}
    for entry in result['rows']:
        slot=entry['slot'];row=json.loads((directory/f"game-{slot['id']:03d}.json").read_bytes());g=slot['group']
        expected=models[g]if slot['phase']=='train'or slot['arm']=='TD'else[1,1,0,0]
        if row['before']!=expected:raise ValueError('Uniform episode/frozen model sequence differs')
        counts=verify_uniform_game(cfg['worlds'][g],row);totals.update(counts)
        if slot['phase']=='train':models[g]=row['after']
        else:pairs.setdefault((g,slot['root'],slot['role'],slot['rep']),{})[slot['arm']]=row
        rows.append(dict(slot=slot,counts=counts,utility=row['utility'],before=row['before'],after=row['after'],update=row['result']['update']))
    comparisons=[]
    for key,arms in pairs.items():
        if set(arms)!={'Unit','TD'}:continue
        u,t=arms['Unit'],arms['TD'];comparisons.append(dict(key=key,difference=None if u['utility']is None or t['utility']is None else t['utility']-u['utility'],identical_record=u['final_record']==t['final_record']))
    if models!=result['models']:raise ValueError('Uniform final model differs')
    out=dict(verified=True,rows=rows,counts=dict(totals),paired=comparisons,models=models,seconds=time.perf_counter()-began,
        scope='Actual legal RNG/records/PVs and independent episode TD arithmetic only; no new games or Player calls, no iid-rule or holdout claim.')
    write(output,out);return out


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--pilot',type=Path,required=True);ap.add_argument('--initialization',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();r=verify(a.pilot,a.initialization,a.output);print(r['counts'],r['seconds'])
