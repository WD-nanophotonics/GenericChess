"""Replay saved perturbations, negative first-action control and new5x5 targets."""
import argparse,gzip,json,math,sys
from collections import Counter
from copy import copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.verify_leaper_prior_td import *

def verify(pilot,budget,extra):
    count=Counter()
    def target(s,r,weights):
        assert r['complete']; leaf=copy(s)
        if r['action'] is None:
            v=FixedScaleSessionEnv(s,unit_type='A').terminal()
            assert v is not None and r['pv_terminal'] and r['value']==MATE*v
        else:
            assert r['pv'] and r['pv'][0]==r['action']
            for a in r['pv']:leaf.submit(match(leaf,a));count['target_PV_edges']+=1
            env=FixedScaleSessionEnv(leaf,unit_type='A'); v=env.terminal()
            if v is None:
                assert not r['pv_terminal'] and list(env.features())==r['pv_phi'] and len(r['pv'])==r['completed_depth']
                assert math.isclose(Model(weights).raw(env.features()),r['value'],rel_tol=1e-12,abs_tol=1e-10)
            else:assert r['pv_terminal'] and r['value']==MATE*v
        count['targets']+=1
    worlds=pilot['inputs']['worlds'];cs={int(k):compile_rule(ruleset_from_dict(w['rule'])) for k,w in worlds.items()}
    old={g['slot']:g for g in pilot['games']}; new={g['slot']:g for g in budget['games']}
    roots={(r['world'],r['index']):r for r in pilot['inputs']['roots'] if r['phase']=='eval'}
    d=extra['directional'];assert len(d['queries'])==16
    for row in d['queries']:
        case=d['plan']['cases'][row['case']]; baseline=old[case['slot']]['queries'][case['query_index']]
        assert baseline['id']==case['id'] and baseline['receipt']==case['baseline'] and baseline['weights']==case['weights']
        s=replay(cs[case['world']],case['root_record']);assert state_sha(s.state)==case['id']
        w=list(case['weights']);w[row['dimension']]+=row['sign']*d['plan']['epsilon'];assert w==row['weights']
        r=row['receipt'];target(s,r,w);assert r['completed_depth']==4 and not r['pv_terminal']
        slope=(r['value']-case['baseline']['value'])/(row['sign']*d['plan']['epsilon'])
        assert slope==row['slope'] and row['matches']==(abs(slope-case['baseline']['pv_phi'][row['dimension']])<1e-7)
    assert d['summary']['mismatched']==0 and d['summary']['nodes']==sum(r['receipt']['nodes'] for r in d['queries'])
    n=extra['negative'];g=n['game'];s=replay(cs[12],roots[12,0]['record'])
    forced=new[260]['queries'][0]['receipt']['action'];s.submit(match(s,forced))
    assert state_sha(s.state)==g['root'] and g['before']==old[30]['before']
    for q in g['queries']:
        assert q['id']==state_sha(s.state) and q['actor']==s.state.position.side_to_move
        if q['kind']=='candidate':r=q['receipt'];target(s,r,q['weights']);a=r['action']
        else:
            r=q['decision'];leaf=copy(s)
            for a in r['principal_variation']:leaf.submit(match(leaf,a));count['reference_PV_edges']+=1
            a=r['action']
        assert a is not None;s.submit(match(s,a));count['actual_control_moves']+=1
    assert record_value(s.to_record())==g['final_record'] and FixedScaleSessionEnv(s,unit_type='A').terminal()==0
    assert g['utility']==[0,0] and old[30]['utility']==[1,1]
    for row in n['crossscores']:
        s=replay(cs[12],roots[12,0]['record']);s.submit(match(s,row['first_action']))
        assert row['first_action']==(old[30] if row['first_action_name']=='Mobility' else new[260])['queries'][0]['receipt']['action']
        assert row['weights']==(old[30] if row['model']=='Mobility' else new[260])['before']
        target(s,row['receipt'],row['weights']);assert row['receipt']['value']==0 and row['receipt']['completed_depth']==3
    assert old[30]['queries'][0]['receipt']['value']==new[260]['queries'][0]['receipt']['value']==0
    z=extra['next_probe'];assert len(z['worlds'])==len(z['queries'])==96
    counts=Counter();cs={}
    for w,q in zip(z['worlds'],z['queries']):
        fp=w['fingerprint']
        if fp not in cs:cs[fp]=compile_rule(ruleset_from_dict(w['rule']))
        s=replay(cs[fp],w['initial_record']);assert state_sha(s.state)==q['id'] and w['world']==q['world']
        names=FixedScaleSessionEnv(s,unit_type='A').names;v=w['price_profiles']['MOBILITY']['board_value_by_type'];weights=[0. if k=='hand' else v[t]/v['A'] for k,t in names]
        assert weights==q['weights'];target(s,q['receipt'],weights);r=q['receipt']
        counts['queries']+=1;counts['nodes']+=r['nodes'];counts['complete']+=r['complete'];counts['nonterminal_targets']+=not r['pv_terminal'];counts['terminal_returns']+=r['pv_terminal'];counts['nonzero_trainable_PV_features']+=r['pv_phi'] is not None and any(r['pv_phi'][1:3]);counts['D'+str(r['completed_depth'])]+=1
    assert counts==z['summary']['paid']
    return dict(status='PASS',counts=count,next_targets=counts,scope='Shared Core histories/literal targets only;no independent WDL,new query or training.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);a=p.parse_args();read=lambda n:json.loads(gzip.decompress((a.directory/(n+'.json.gz')).read_bytes()))
    print(json.dumps(verify(read('pilot'),read('budget'),read('extras')),ensure_ascii=True))
