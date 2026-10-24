"""Data-only qualification of frozen actual-default complete-history queries."""
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,gzip
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from tools.local_agent.common import write_json

def raw(p):
    p=Path(p)
    if not p.exists():p=Path(str(p)+'.gz')
    b=p.read_bytes()
    return gzip.decompress(b)if p.suffix=='.gz'else b

def load(p):return json.loads(raw(p))

def qualify(d,inputs=None):
    plan=load(d/'plan.json'); src=Path(inputs or plan['inputs'])
    assert hashlib.sha256(raw(src)).hexdigest()==plan['inputs_sha256']
    data=load(src); cases=data['cases']; rr=[json.loads(x)for x in raw(d/'queries.jsonl').decode('utf-8').splitlines()if x.strip()]
    receipt=load(d/'receipt.json')
    assert receipt['status']=='CLOSED' and receipt['queries']==receipt['planned']==len(cases)==64
    assert plan['slots']==[c['key']for c in cases]==[r['key']for r in rr],'missing/duplicate/reordered slots'
    summary=[]; PVsteps=0
    for case,row in zip(cases,rr):
        c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]))
        sess=replay(c,case['record'])
        assert L.state_sha(sess.state)==case['state_sha256']==row['state_sha256']
        assert row['actor']==case['actor']==sess.state.position.side_to_move
        labels=case['labelled_actions']; available={json.dumps(x['action'],sort_keys=True):x['truth']['value']for x in labels}
        assert len(available)==len(labels)
        assert set(available)=={json.dumps(L.record_value(a),sort_keys=True)for a in sess.legal_actions()}
        assert (max if case['actor']==0 else min)(available.values())==case['root_global_WDL']
        assert case['root_own_WDL']==case['root_global_WDL']*(1 if case['actor']==0 else -1)
        def truth(raw):return available[json.dumps(raw,sort_keys=True)]
        def check(a,v,p):
            assert v==truth(a) and p==(v==case['root_global_WDL'])
            assert v*(1 if case['actor']==0 else -1)<=case['root_own_WDL']
        dec=row['decision'];check(dec['action'],row['chosen_global_WDL'],row['preserves_root_value'])
        assert row['root_global_WDL']==case['root_global_WDL']
        its=row['iterations'];assert [x['depth']for x in its]==list(range(1,dec['completed_depth']+1))
        for it in its:check(it['action'],it['chosen_global_WDL'],it['preserves_root_value'])
        for a,b in zip(its,its[1:]):assert all(a[k]<=b[k]for k in ('nodes','qnodes','elapsed'))
        if dec['result_source']=='main_iteration':
            assert its and all(dec[k]==its[-1][v]for k,v in [('score','score'),('action','action')])
        assert dec['nodes']>= (its[-1]['nodes']if its else 0) and dec['qnodes']>= (its[-1]['qnodes']if its else 0)
        for action in dec['principal_variation']:
            a=L.match_action(sess,action);sess.submit(a);PVsteps+=1
        assert L.record_value(sess.result)==row['PV_final_result']
        work=dec['nodes']+dec['qnodes']
        correct_depths=[i['preserves_root_value']for i in its]
        sensitive=len(set(available.values()))>1
        suffix=next((its[k]['depth']for k in range(len(its))if all(correct_depths[k:])),None)
        fresh=replay(c,case['record'])
        lexical=truth(L.record_value(sorted(fresh.legal_actions(),key=str)[0]))
        density=sum(v==case['root_global_WDL']for v in available.values())/len(available)
        summary.append(dict(choice_sensitive=sensitive,lexical_preserves=lexical==case['root_global_WDL'],uniform_preserve_probability=density,any_wrong_iteration=not all(correct_depths),observed_correct_suffix_depth=suffix,key=row['key'],actor=row['actor'],ply=case['absolute_ply'],root=row['root_global_WDL'],chosen=row['chosen_global_WDL'],correct=row['preserves_root_value'],first_correct_depth=next((i['depth']for i in its if i['preserves_root_value']),None),last_depth=dec['completed_depth'],iteration_correct=[i['preserves_root_value']for i in its],query_seconds=row['query_seconds'],main=dec['nodes'],q=dec['qnodes'],q_fraction=dec['qnodes']/work if work else None,reason=dec['termination_reason'],source=dec['result_source'],tt_hits=dec['tt_hits'],tt_cutoffs=dec['tt_cutoffs'],evaluation_seconds=dec['evaluation_seconds'],ordering_seconds=dec['ordering_seconds'],legal_generation_seconds=dec['legal_generation_seconds'],native_calls=dec['native_legality_calls'],native_fallbacks=dec['native_legality_fallbacks']))
    return dict(status='PASS',queries=len(rr),PV_steps=PVsteps,scope='Actual default45 quality on one exposed RuleSet/twoTRAIN paths,64histories/44physical positions; not IID/holdout.',input_preparation_scope=data['scope'],correct=sum(r['correct']for r in summary),choice_sensitive=dict(total=sum(r['choice_sensitive']for r in summary),correct=sum(r['choice_sensitive']and r['correct']for r in summary)),lexical_correct=sum(r['lexical_preserves']for r in summary),uniform_expected_correct=sum(r['uniform_preserve_probability']for r in summary),wrong=[r['key']for r in summary if not r['correct']],by_actor={str(a):dict(total=sum(r['actor']==a for r in summary),correct=sum(r['actor']==a and r['correct']for r in summary))for a in (0,1)},seconds=sum(r['query_seconds']for r in summary),reasons=dict(Counter(r['reason']for r in summary)),summary=summary,limitations='Shared Core semantic replay and fixed published WDL labels, not a new graph solve or independent rules engine. One exposed rule/two TRAIN paths, not IID/holdout. Work fractions are not time fractions. PV may omit q suffix.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--inputs',type=Path);a=p.parse_args();r=qualify(a.directory,a.inputs);write_json(a.output,r);print(json.dumps({k:v for k,v in r.items()if k!='summary'}))
