"""Data-only validation of admitted hard-clock depth cap versus paid controls."""
from pathlib import Path
import argparse,gzip,json,hashlib
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay

def raw(p):
    if p.suffix=='.gz':return gzip.decompress(p.read_bytes())
    return p.read_bytes()if p.exists()else gzip.decompress(p.with_name(p.name+'.gz').read_bytes())
def load(p):return json.loads(raw(p))
def qualify(d,reference,inputs):
    plan=load(d/'plan.json');receipt=load(d/'receipt.json');data=load(inputs)
    assert hashlib.sha256(raw(inputs)).hexdigest()==plan['inputs_sha256']
    rows=[json.loads(x)for x in raw(d/'queries.jsonl').splitlines()];old=[json.loads(x)for x in raw(reference/'queries.jsonl').splitlines()if not json.loads(x)['slot']['completion']]
    expected=[x['key']for x in data['cases']if x['remaining']<=10];assert len(expected)==10 and plan['slots']==expected==[x['key']for x in rows]
    assert receipt['status']=='CLOSED' and receipt['queries']==receipt['attempted']==len(rows)==10 and receipt['source_hashes']==plan['source_hashes']
    out=[];pvc=0
    for r in rows:
        case=next(x for x in data['cases']if x['key']==r['key']);ref=next(x for x in old if x['slot']['key']==r['key']);c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]));s=replay(c,case['record'])
        assert L.state_sha(s.state)==case['state_sha256']==r['state_sha256'];assert r['actual_opt_in']is True and r['actual_clock_depth_cap']==case['remaining']==r['remaining']
        its=r['iterations'];assert [x['depth']for x in its]==list(range(1,len(its)+1));assert its
        common=list(zip(its,ref['iterations']));assert len(common)==min(len(its),len(ref['iterations']))
        assert all(all(x[f]==y[f]for f in('depth','nodes','qnodes','score','action'))for x,y in common),'same search through shared depths must be unchanged'
        dec=r['decision'];assert dec['result_source']=='main_iteration' and dec['score']==its[-1]['score']and dec['action']==its[-1]['action']and dec['completed_depth']==its[-1]['depth']<=r['remaining']
        assert dec['runtime_depth_balanced']is True
        val=next(x['truth']['value']for x in case['labelled_actions']if x['action']==dec['action']);refval=next(x['truth']['value']for x in case['labelled_actions']if x['action']==ref['decision']['action'])
        assert val==refval==case['root_global_WDL']
        for rawaction in dec['principal_variation']:
            s.submit(next(x for x in s.legal_actions()if L.record_value(x)==rawaction));pvc+=1
        out.append(dict(key=r['key'],actor=case['actor'],remaining=r['remaining'],new_completed_depth=dec['completed_depth'],old_completed_depth=ref['decision']['completed_depth'],full_clock_completed=dec['completed_depth']>=r['remaining'],shared_prefix_exact=True,old_seconds=ref['seconds'],new_seconds=r['seconds'],old_work=ref['decision']['nodes']+ref['decision']['qnodes'],new_work=dec['nodes']+dec['qnodes'],correct=True,old_score=ref['decision']['score'],new_score=dec['score']))
    completed=[x for x in out if x['full_clock_completed']]
    return dict(status='EXACT_PREFIX_AND_ROOT_VALUE_QUALIFIED',queries=10,pv_legal_steps=pvc,cases=out,complete_clock_cases=len(completed),budget_limited=[x['key']for x in out if not x['full_clock_completed']],completed_total_old_seconds=sum(x['old_seconds']for x in completed),completed_total_new_seconds=sum(x['new_seconds']for x in completed),completed_total_old_work=sum(x['old_work']for x in completed),completed_total_new_work=sum(x['new_work']for x in completed),scope='Reuse10paid default controls;10new candidate calls. Eight short-clock DRAW roots,2budget-limited controls,one exposed rule. Defaultfalse backend option; requested cap is not completion. No class-wide strength claim.')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',required=True,type=Path);a.add_argument('--reference',required=True,type=Path);a.add_argument('--inputs',required=True,type=Path);x=a.parse_args();print(json.dumps(qualify(x.directory,x.reference,x.inputs),ensure_ascii=False))
