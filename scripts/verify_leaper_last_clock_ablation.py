"""Qualify the exposed one-ply clock policy ablation without rerunning search."""
from pathlib import Path
import argparse,json,hashlib,gzip
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from generic_chess.ai.alphabeta.tuning import SearchTuning

def raw(p):
    if p.suffix=='.gz':return gzip.decompress(p.read_bytes())
    return p.read_bytes()if p.exists()else gzip.decompress(p.with_name(p.name+'.gz').read_bytes())
def load(p):return json.loads(raw(p))
def qualify(d,inputs):
    p=load(d/'plan.json');rr=load(d/'receipt.json');data=json.loads(raw(inputs));rows=[json.loads(x)for x in raw(d/'queries.jsonl').splitlines()]
    assert hashlib.sha256(raw(inputs)).hexdigest()==p['inputs_sha256']
    assert rr['status']=='CLOSED' and rr['attempted']==rr['queries']==len(rows)==6 and [x['slot']for x in rows]==p['slots']
    assert rr['source_sha256']==p['source_sha256']and rr['policy_sha256']==p['policy_sha256']
    expected=[dict(key=k,shield=a)for k,order in [('next-role-p7',(False,True)),('next-role-p49',(True,False)),('next-role-p53',(False,True))]for a in order];assert p['slots']==expected
    pair={};pvc=0
    for r in rows:
        case=next(c for c in data['cases']if c['key']==r['slot']['key']);c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]))
        s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256']==r['state_sha256'];assert s.state.position.side_to_move==case['actor']
        labels=case['labelled_actions'];legal=[L.record_value(a)for a in s.legal_actions()];assert sorted(json.dumps(x,sort_keys=True)for x in legal)==sorted(json.dumps(x['action'],sort_keys=True)for x in labels)
        def value(a):return next(x['truth']['value']for x in labels if x['action']==a)
        its=r['iterations'];assert [x['depth']for x in its]==list(range(1,len(its)+1));assert r['actual_tuning']==L.record_value(SearchTuning())
        for it in its:assert it['action']in legal
        dec=r['decision'];assert dec['action']in legal and dec['runtime_depth_balanced']is True
        if dec['result_source']=='main_iteration':assert its and dec['completed_depth']==its[-1]['depth']and dec['score']==its[-1]['score']and dec['action']==its[-1]['action']
        elif dec['result_source']not in {'completed_root_win','root_scan_fallback','legal_fallback','root_immediate_win'}:raise AssertionError('unexpected source')
        for a in dec['principal_variation']:
            action=next(x for x in s.legal_actions()if L.record_value(x)==a);s.submit(action);pvc+=1
        pair.setdefault(case['key'],{})[r['slot']['shield']]=dict(raw=r,root_global_WDL=case['root_global_WDL'],chosen_global_WDL=value(dec['action']),preserves_root_value=value(dec['action'])==case['root_global_WDL'],iteration_values=[dict(depth=x['depth'],chosen_global_WDL=value(x['action']),correct=value(x['action'])==case['root_global_WDL'])for x in its])
    out=[]
    for key,arms in pair.items():
        assert set(arms)=={False,True};a,b=arms[False],arms[True];ra,rb=a.pop('raw'),b.pop('raw');common=list(zip(ra['iterations'],rb['iterations']))
        if key=='next-role-p7':
            assert not rb['policy_counts'],'unreachable last clock must not activate'
            assert common and all(all(x[f]==y[f]for f in ('depth','nodes','qnodes','score','action'))for x,y in common),'negative control must retain exact common-prefix behavior'
        out.append(dict(key=key,baseline=a,shield=b,final_depth=[ra['decision']['completed_depth'],rb['decision']['completed_depth']],final_score=[ra['decision']['score'],rb['decision']['score']],seconds=[ra['seconds'],rb['seconds']],termination=[ra['decision']['termination_reason'],rb['decision']['termination_reason']],policy_counts=rb['policy_counts'],common=[dict(depth=x['depth'],scores=[x['score'],y['score']],actions_equal=x['action']==y['action'],work=[x['nodes']+x['qnodes'],y['nodes']+y['qnodes']])for x,y in common]))
    return dict(status='DATA_QUALIFIED_NOT_DEFAULT_ACTIVATED',queries=6,pv_legal_steps=pvc,pairs=out,scope='3 exposed full histories,1rule. Fixed published AUX labels and shared Core, not an independent solve/holdout. New policy can change finite-depth values and abort; these are results, not qualification failures. Query budgets unchanged.')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',required=True,type=Path);a.add_argument('--inputs',required=True,type=Path);x=a.parse_args();print(json.dumps(qualify(x.directory,x.inputs),ensure_ascii=False))
