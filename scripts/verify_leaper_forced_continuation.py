"""Core-replayed quality join of fixed singleton-continuation experiments."""
from pathlib import Path
import argparse,json,gzip,hashlib
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay

def raw(p):
    p=Path(p)
    if not p.exists():p=Path(str(p)+'.gz')
    b=p.read_bytes();return gzip.decompress(b)if p.suffix=='.gz'else b

def load(p):return json.loads(raw(p))
def rows(p):return [json.loads(x)for x in raw(p).decode('utf-8').splitlines()if x]
def key(a):return json.dumps(a,sort_keys=True,separators=(',',':'))

def assess(directories,control,*,allow_failed_prefix=False):
    control=Path(control);reference={r['key']:r for r in rows(control/'queries.jsonl')};out=[];seen=set();steps=0;attempted=0;calls=0
    for directory in directories:
        d=Path(directory);p=load(d/'plan.json');data=load(d/'inputs.json');receipt=load(d/'receipt.json');rr=rows(d/'queries.jsonl')
        assert hashlib.sha256(raw(d/'inputs.json')).hexdigest()==p['inputs_sha256']
        assert receipt['source_sha256']==p['source_sha256']and receipt['policy_sha256']==p['policy_sha256']
        assert receipt['queries']==len(rr) and receipt['attempted']>=len(rr)
        if receipt['status']!='CLOSED':
            assert allow_failed_prefix and [r['key']for r in rr]==p['keys'][:len(rr)]
        else:assert [r['key']for r in rr]==p['keys']
        attempted+=receipt['attempted'];calls+=len(rr)
        cases={x['key']:x for x in data['cases']}
        for row in rr:
            k=row['key'];assert k not in seen;seen.add(k);case=cases[k];baseline=reference[k]
            assert row['state_sha256']==case['state_sha256']==baseline['state_sha256']
            assert row['tuning']==baseline['tuning']and row['evaluation_profile']==baseline['evaluation_profile']
            c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]));s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256']
            labels={key(x['action']):x['truth']['value']for x in case['labelled_actions']}
            assert set(labels)=={key(L.record_value(a))for a in s.legal_actions()}
            truth=lambda a:labels[key(a)]
            dec=row['decision'];new=truth(dec['action']);old=truth(baseline['decision']['action']);root=case['root_global_WDL']
            assert (max if case['actor']==0 else min)(labels.values())==root
            its=row['iterations']
            depths=[i['depth']for i in its]
            if p['policy']=='first_q_refinement':
                expected=list(range(1,dec['completed_depth']+1))
                if len(its)>1:expected.insert(1,1)
                assert depths==expected
                if its:
                    assert its[0]['ordinary_qdepth']==0
                    assert all(i['ordinary_qdepth']==4 for i in its[1:])
                    assert baseline['iterations'] and all(its[0][f]==baseline['iterations'][0][f]for f in ['action','score','nodes','qnodes'])
                assert row['policy_counts'].get('q_semantic_tt_clears',0)<=1
            else:assert depths==list(range(1,dec['completed_depth']+1))
            if dec['result_source']=='main_iteration':assert its and dec['score']==its[-1]['score']and dec['action']==its[-1]['action']
            for a in dec['principal_variation']:s.submit(L.match_action(s,a));steps+=1
            correct=[truth(i['action'])==root for i in its]
            first=next((i['elapsed']for i in its if truth(i['action'])==root),None)
            baseline_first=next((i['elapsed']for i in baseline['iterations']if truth(i['action'])==root),None)
            out.append(dict(control_first_correct_seconds=baseline_first,first_correct_stage=next((dict(depth=i['depth'],ordinary_qdepth=i.get('ordinary_qdepth'))for i in its if truth(i['action'])==root),None),key=k,actor=case['actor'],root_global_WDL=root,control_value=old,candidate_value=new,control_correct=old==root,candidate_correct=new==root,repair=old!=root and new==root,regression=old==root and new!=root,first_correct_seconds=first,iteration_correct=correct,completed_depth=dec['completed_depth'],score=dec['score'],termination=dec['termination_reason'],seconds=row['seconds'],policy_counts=row['policy_counts'],main=dec['nodes'],q=dec['qnodes'],PV_result=L.record_value(s.result)))
    return dict(cases=len(out),attempted=attempted,returns=calls,PV_steps=steps,control_correct=sum(r['control_correct']for r in out),candidate_correct=sum(r['candidate_correct']for r in out),repairs=[r['key']for r in out if r['repair']],regressions=[r['key']for r in out if r['regression']],seconds=sum(r['seconds']for r in out),rows=out,limits='Exposed oneRuleSet, same45s historical controls, freshTT per policy. Different load/opt-in-capfalse source-version overhead limits wall causality. Branch-depth policy cannot claim same-depth parity.')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('directories',nargs='+',type=Path);a.add_argument('--control',type=Path,required=True);a.add_argument('--allow-failed-prefix',action='store_true');p=a.parse_args();print(json.dumps(assess(p.directories,p.control,allow_failed_prefix=p.allow_failed_prefix),indent=2))
