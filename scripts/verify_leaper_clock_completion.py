"""Bind completion-policy queries to exact histories, goals and published labels."""
from pathlib import Path
import argparse,json,hashlib,gzip
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.evaluation.config import MATE_THRESHOLD

def raw(p):
    if p.suffix=='.gz':return gzip.decompress(p.read_bytes())
    return p.read_bytes()if p.exists()else gzip.decompress(p.with_name(p.name+'.gz').read_bytes())
def load(p):return json.loads(raw(p))
def qualify(d,inputs):
    plan=load(d/'plan.json');receipt=load(d/'receipt.json');data=load(inputs);rows=[json.loads(x)for x in raw(d/'queries.jsonl').splitlines()]
    assert hashlib.sha256(raw(inputs)).hexdigest()==plan['inputs_sha256']
    assert receipt['status']=='CLOSED'and receipt['queries']==receipt['attempted']==len(rows)==len(plan['slots'])and[x['slot']for x in rows]==plan['slots']
    assert receipt['source_sha256']==plan['source_sha256']and receipt['policy_sha256']==plan['policy_sha256']
    proof=len(rows)==2;assert len(rows)in(2,32)
    if proof:assert plan['slots']==[dict(key='next-role-p53',completion=x)for x in(True,False)]
    else:
        selected=[x for x in data['cases']if x['remaining']<=16];assert len(selected)==16
        expected=[dict(key=c['key'],completion=x)for i,c in enumerate(selected)for x in((False,True)if i%2==0 else(True,False))];assert plan['slots']==expected
    out=[];pvc=0;arms={}
    for r in rows:
        case=next(x for x in data['cases']if x['key']==r['slot']['key']);c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]))
        s=replay(c,case['record']);assert L.state_sha(s.state)==r['state_sha256']==case['state_sha256']and s.state.position.side_to_move==case['actor']
        labels=case['labelled_actions'];legal=[L.record_value(a)for a in s.legal_actions()];assert sorted(json.dumps(a,sort_keys=True)for a in legal)==sorted(json.dumps(x['action'],sort_keys=True)for x in labels)
        def truth(action):return next(x['truth']['value']for x in labels if x['action']==action)
        assert r['actual_tuning']==L.record_value(SearchTuning(stop_after_root_win=proof))
        its=r['iterations'];assert [x['depth']for x in its]==list(range(1,len(its)+1));timeline=[]
        for x in its:
            assert x['action']in legal;v=truth(x['action']);timeline.append(dict(depth=x['depth'],elapsed=x['elapsed'],score=x['score'],correct=v==case['root_global_WDL'],chosen_global_WDL=v,nodes=x['nodes'],qnodes=x['qnodes']))
        dec=r['decision'];assert dec['action']in legal and dec['runtime_depth_balanced']is True
        assert dec['result_source']in{'main_iteration','completed_root_win','root_immediate_win','root_scan_fallback','legal_fallback'}
        if dec['result_source']=='main_iteration':assert its and dec['completed_depth']==its[-1]['depth']and dec['score']==its[-1]['score']and dec['action']==its[-1]['action']
        for a in dec['principal_variation']:
            s.submit(next(x for x in s.legal_actions()if L.record_value(x)==a));pvc+=1
        v=truth(dec['action']);rr=dict(key=case['key'],actor=case['actor'],completion=r['slot']['completion'],remaining=case['remaining'],root_global_WDL=case['root_global_WDL'],chosen_global_WDL=v,correct=v==case['root_global_WDL'],first_correct=next((x for x in timeline if x['correct']),None),reported_mate_band_win=dec['score']>=MATE_THRESHOLD,iterations=timeline,seconds=r['seconds'],cpu_seconds=r['cpu_seconds'],work=dec['nodes']+dec['qnodes'],completed_depth=dec['completed_depth'],score=dec['score'],source=dec['result_source'],termination=dec['termination_reason'],policy_counts=r['policy_counts'])
        out.append(rr);arms.setdefault(case['key'],{})[r['slot']['completion']]=rr
    pairs=[]
    for key,a in arms.items():
        assert set(a)=={False,True};old,new=a[False],a[True]
        pairs.append(dict(key=key,root_global_WDL=old['root_global_WDL'],baseline_correct=old['correct'],completion_correct=new['correct'],baseline_chosen=old['chosen_global_WDL'],completion_chosen=new['chosen_global_WDL'],seconds=[old['seconds'],new['seconds']],depths=[old['completed_depth'],new['completed_depth']],work=[old['work'],new['work']],changed=old['chosen_global_WDL']!=new['chosen_global_WDL']))
    return dict(status='DATA_QUALIFIED',goal='reported_any_win_feasibility'if proof else'equal20s_move_quality',queries=len(rows),pv_legal_steps=pvc,results=out,pairs=pairs,baseline_correct=sum(x['baseline_correct']for x in pairs),completion_correct=sum(x['completion_correct']for x in pairs),regressions=[x['key']for x in pairs if x['baseline_correct']and not x['completion_correct']],repairs=[x['key']for x in pairs if not x['baseline_correct']and x['completion_correct']],scope='Exposed one-rule/full-history tests, fixed published AUX labels/shared Core, not independent solving or heldout strength. Distinct goals; no common-depth parity requirement for the intentionally changed q policy.')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',required=True,type=Path);a.add_argument('--inputs',required=True,type=Path);x=a.parse_args();print(json.dumps(qualify(x.directory,x.inputs),ensure_ascii=False))
