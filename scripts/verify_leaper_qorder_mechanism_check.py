"""Data-only matching of the frozen existing-q-order mechanism contrast."""
from pathlib import Path
import argparse,json
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.verify_leaper_default_history_panel import raw,load
from tools.local_agent.common import write_json

def qualify(d,inputs=None):
    import hashlib
    p=load(d/'plan.json');inp=Path(inputs or p['inputs']);assert hashlib.sha256(raw(inp)).hexdigest()==p['inputs_sha256']
    data=load(inp); rr=[json.loads(x)for x in raw(d/'queries.jsonl').decode().splitlines()if x.strip()];receipt=load(d/'receipt.json')
    assert len(p['slots'])in(2,4)
    assert receipt['status']=='CLOSED' and receipt['queries']==receipt['planned']==len(p['slots'])
    assert [r['slot']for r in rr]==p['slots']
    pv_steps=0
    for r in rr:
        case=next(c for c in data['cases']if c['key']==r['slot']['key'])
        c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]))
        sess=replay(c,case['record']);assert L.state_sha(sess.state)==case['state_sha256']
        def label(a):return next(t['truth']['value']for t in case['labelled_actions']if t['action']==a)
        dec=r['decision'];assert label(dec['action'])==r['chosen_global_WDL'];assert r['root_global_WDL']==case['root_global_WDL']
        assert r['tuning']['use_ordered_qsearch']==r['slot']['ordered']
        assert r['TT']['probes']==dec['tt_probes'] and r['TT']['hits']==dec['tt_hits']
        assert sum(r['TT_depth_delta'].values())==r['TT'].get('hits',0)
        assert sum(v for k,v in r['TT_depth_delta'].items()if int(k)>=0)==r['TT'].get('depth_eligible',0)
        assert sum(r['TT'].get('eligible_'+k,0)for k in ['EXACT','LOWER','UPPER'])==r['TT'].get('depth_eligible',0)
        its=r['iterations'];assert [i['depth']for i in its]==list(range(1,dec['completed_depth']+1))
        for i in its:assert label(i['action'])==i['chosen_global_WDL']
        if dec['result_source']=='main_iteration':assert its and dec['score']==its[-1]['score'] and dec['action']==its[-1]['action']
        for a in dec['principal_variation']:sess.submit(L.match_action(sess,a));pv_steps+=1
        assert L.record_value(sess.result)==r['PV_final_result']
    pairs=[]
    for key in dict.fromkeys(s['key']for s in p['slots']):
        a=next(r for r in rr if r['slot']==dict(key=key,ordered=False));b=next(r for r in rr if r['slot']==dict(key=key,ordered=True))
        aa={i['depth']:i for i in a['iterations']};bb={i['depth']:i for i in b['iterations']};shared=sorted(aa.keys()&bb.keys())
        comparisons=[]
        for depth in shared:
            x=aa[depth];y=bb[depth];wx=x['nodes']+x['qnodes'];wy=y['nodes']+y['qnodes']
            comparisons.append(dict(depth=depth,same_score=x['score']==y['score'],same_action=x['action']==y['action'],WDL_lexical=x['chosen_global_WDL'],WDL_ordered=y['chosen_global_WDL'],work_lexical=wx,work_ordered=wy,work_ratio=wy/wx if wx else None,seconds_lexical=x['elapsed'],seconds_ordered=y['elapsed']))
        pairs.append(dict(key=key,requested_depth=p['limits']['max_depth'],completed_lexical=a['decision']['completed_depth'],completed_ordered=b['decision']['completed_depth'],requested_depth_quality='COMPLETE'if min(a['decision']['completed_depth'],b['decision']['completed_depth'])>=p['limits']['max_depth']else'UNKNOWN',common_depths=comparisons,all_common_scores_equal=bool(comparisons)and all(x['same_score']for x in comparisons),final_WDL_lexical=a['chosen_global_WDL'],final_WDL_ordered=b['chosen_global_WDL'],TT_lexical=a['TT'],TT_ordered=b['TT']))
    return dict(status='PASS',queries=len(rr),PV_steps=pv_steps,pairs=pairs,limitations='Registered metadata roots or separately registered targeted development failure; timing has one observation per arm, common-depth curves descriptive and requested missing depth UNKNOWN. TT instrumentation is common to both arms and adds overhead; no production-default change or all-rule strength claim.')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--directory',type=Path,required=True);ap.add_argument('--inputs',type=Path);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();r=qualify(a.directory,a.inputs);write_json(a.output,r);print(json.dumps(r))
