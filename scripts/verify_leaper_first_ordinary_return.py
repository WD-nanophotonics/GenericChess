"""Read-only qualification of actual early consumer returns; never runs a search."""
from pathlib import Path
import argparse,hashlib,json,statistics
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.verify_leaper_forced_continuation import raw,load,rows,key

STRONG={'root_immediate_win','root_declaration','terminal'}

def stage_contract(row):
    its=row['iterations'];dec=row['decision'];arm=row['arm']
    assert arm in {'default','refined'} and len(its)<=2
    expected=[(1,0),(2,4)] if arm=='default' else [(1,0),(1,4)]
    assert [(i['depth'],i['ordinary_qdepth'])for i in its]==expected[:len(its)]
    assert all(i['elapsed']>=0 for i in its)
    assert all(a['elapsed']<=b['elapsed']for a,b in zip(its,its[1:]))
    assert not its or row['seconds']>=its[-1]['elapsed']
    if dec['result_source']=='main_iteration':
        assert its and dec['action']==its[-1]['action'] and dec['score']==its[-1]['score']
        assert dec['completed_depth']==its[-1]['depth']
    return dec['result_source']in STRONG or len(its)==2

def assess(directory):
    d=Path(directory);p=load(d/'plan.json');receipt=load(d/'receipt.json');data=load(d/'inputs.json');rr=rows(d/'queries.jsonl')
    assert receipt['status']=='CLOSED'and receipt['queries']==receipt['attempted']==len(rr)==128
    assert hashlib.sha256(raw(d/'inputs.json')).hexdigest()==p['inputs_sha256']
    assert receipt['source_sha256']==p['source_sha256']and receipt['policy_sha256']==p['policy_sha256']
    cases={c['key']:c for c in data['cases']};assert set(p['keys'])==set(cases)and len(cases)==64
    expected=[(k,a)for i,k in enumerate(p['keys'])for a in (['default','refined']if i%2==0 else['refined','default'])]
    assert [(r['key'],r['arm'])for r in rr]==expected
    quals={(r['key'],r['arm']):r for r in rows(d/'qualification.jsonl')};assert len(quals)==128
    values={};pvsteps=0
    for r in rr:
        case=cases[r['key']];assert r['state_sha256']==case['state_sha256']
        c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]));s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256']
        labels={key(x['action']):x['truth']['value']for x in case['labelled_actions']}
        assert set(labels)=={key(L.record_value(a))for a in s.legal_actions()}
        assert (max if case['actor']==0 else min)(labels.values())==case['root_global_WDL']
        assert r['returned_source']==r['decision']['result_source']
        if r['cancel_observed_seconds']is not None:
            assert 0<=r['cancel_observed_seconds']<=r['seconds'] and r['cancel_to_return_seconds']>=0
            assert abs(r['seconds']-r['cancel_observed_seconds']-r['cancel_to_return_seconds'])<1e-9
        else:assert r['cancel_to_return_seconds']is None
        val=labels[key(r['decision']['action'])];q=quals[(r['key'],r['arm'])];goal=stage_contract(r)
        assert q['chosen_global_WDL']==val and q['correct']==(val==case['root_global_WDL'])and q['ordinary_goal_complete']==goal
        for a in r['decision']['principal_variation']:s.submit(L.match_action(s,a));pvsteps+=1
        values[(r['key'],r['arm'])]=dict(correct=q['correct'],value=val,goal_complete=goal,seconds=r['seconds'],events=r['decision']['nodes']+r['decision']['qnodes'],termination=r['decision']['termination_reason'],result_source=r['decision']['result_source'],cancel_observed_seconds=r.get('cancel_observed_seconds'),cancel_to_return_seconds=r.get('cancel_to_return_seconds'),depth=r['decision']['completed_depth'])
    pairs=[]
    for k in p['keys']:
        b=values[(k,'default')];n=values[(k,'refined')];br=next(r for r in rr if r['key']==k and r['arm']=='default');nr=next(r for r in rr if r['key']==k and r['arm']=='refined')
        assert br['tuning']==nr['tuning']and br['evaluation_profile']==nr['evaluation_profile']
        assert bool(br['iterations'])==bool(nr['iterations'])
        if br['iterations']:assert all(br['iterations'][0][f]==nr['iterations'][0][f]for f in ['action','score','nodes','qnodes'])
        choice_sensitive=len({x['truth']['value']for x in cases[k]['labelled_actions']})>1
        pairs.append(dict(key=k,choice_sensitive=choice_sensitive,default=b,refined=n,repair=not b['correct']and n['correct'],regression=b['correct']and not n['correct'],latency_ratio=n['seconds']/b['seconds']))
    return dict(cases=64,queries=128,pv_steps=pvsteps,choice_sensitive_cases=sum(x['choice_sensitive']for x in pairs),choice_sensitive_correct={a:sum(x['choice_sensitive']and x[a]['correct']for x in pairs)for a in ['default','refined']},default_correct=sum(x['default']['correct']for x in pairs),refined_correct=sum(x['refined']['correct']for x in pairs),goal_unknown={a:[x['key']for x in pairs if not x[a]['goal_complete']]for a in ['default','refined']},repairs=[x['key']for x in pairs if x['repair']],regressions=[x['key']for x in pairs if x['regression']],median_paired_latency_ratio=statistics.median(x['latency_ratio']for x in pairs),seconds=sum(r['seconds']for r in rr),pairs=pairs,limitations='Exposed64histories/two TRAIN trajectories/oneRuleSet. Different completed depth and work at a matched consumer goal; not strength, fixed-depth or equal-cost superiority. Alternating order limits but does not remove shared-machine timing uncertainty.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();print(json.dumps(assess(a.directory),indent=2))
