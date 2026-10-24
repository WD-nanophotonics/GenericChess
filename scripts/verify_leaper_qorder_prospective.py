"""Data-only qualification of prospectively frozen q-order pairs."""
from pathlib import Path
import argparse,hashlib,json,gzip
from collections import Counter
from scripts import leaper_design as L
from generic_chess.ai.evaluation.config import MATE_THRESHOLD
from scripts.leaper_delayed_capture_witness import replay

def raw(p):
    if p.suffix=='.gz':return gzip.decompress(p.read_bytes())
    if p.exists():return p.read_bytes()
    return gzip.decompress(p.with_name(p.name+'.gz').read_bytes())
def load(p):return json.loads(raw(p))
def validate_registration(plan,inp):
    cases=inp['cases'];assert len(cases)==16 and len(inp['rules'])==8
    assert len({x['key']for x in cases})==len(cases)
    expected=[]
    for i,c in enumerate(cases):
        for ordered in ((False,True)if i%2==0 else(True,False)):expected.append(dict(key=c['key'],ordered=ordered))
    assert plan['slots']==expected
    for rh,r in inp['rules'].items():assert hashlib.sha256(json.dumps(r,sort_keys=True,separators=(',',':')).encode()).hexdigest()==rh

def qualify(d):
    plan=load(d/'plan.json');inp=load(d/'inputs.json');receipt=load(d/'receipt.json');validate_registration(plan,inp)
    assert hashlib.sha256(raw(d/'inputs.json')).hexdigest()==plan['inputs_sha256']
    rows=[json.loads(x)for x in raw(d/'queries.jsonl').splitlines()]
    assert receipt['status']=='CLOSED' and receipt['queries']==receipt['attempted']==len(plan['slots'])==len(rows)
    assert [r['slot'] for r in rows]==plan['slots']
    assert receipt['source_sha256']==plan['source_sha256']
    cases={x['key']:x for x in inp['cases']};compiled={};pairrows={};pvc=0
    for index,r in enumerate(rows):
        assert r['index']==index
        case=cases[r['slot']['key']];rh=case['rule_sha256'];c=compiled.get(rh)
        if c is None:c=compiled[rh]=L.compile_rule(L.ruleset_from_dict(inp['rules'][rh]))
        s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256']==r['state_sha256']
        assert r['actor']==case['actor']==s.state.position.side_to_move and r['rule_sha256']==rh
        legal=[L.record_value(x)for x in s.legal_actions()];assert legal==case['legal_frontier']
        dec=r['decision'];assert dec['action'] in legal;assert dec['runtime_depth_balanced'] is True
        assert dec['result_source'] in {'main_iteration','completed_root_win','root_immediate_win','root_scan_fallback','legal_fallback'}
        its=r['iterations'];assert [it['depth'] for it in its]==list(range(1,len(its)+1))
        for it in its:
            assert it['action'] in legal and it['elapsed']<=r['seconds']+.05 and it['nodes']>=0 and it['qnodes']>=0
        assert all(a['elapsed']<=b['elapsed'] and a['nodes']<=b['nodes'] and a['qnodes']<=b['qnodes'] for a,b in zip(its,its[1:]))
        if dec['result_source']=='main_iteration':
            assert its and dec['completed_depth']==its[-1]['depth'] and dec['score']==its[-1]['score'] and dec['action']==its[-1]['action']
        if dec['result_source']in {'root_immediate_win','root_scan_fallback','legal_fallback'}:assert not its and dec['completed_depth']==0
        if dec['result_source']=='completed_root_win':assert dec['score']>=MATE_THRESHOLD and dec['completed_depth']==len(its)
        for a in dec['principal_variation']:
            action=next(x for x in s.legal_actions()if L.record_value(x)==a);s.submit(action);pvc+=1
        if dec['result_source']=='root_immediate_win':assert len(dec['principal_variation'])==1 and s.state.terminal_status.is_terminal and s.state.terminal_status.winner==case['actor']
        pairrows.setdefault(case['key'],{})[r['slot']['ordered']]=r
    pairs=[]
    for key,arms in pairrows.items():
        assert set(arms)=={False,True};a,b=arms[False],arms[True]
        assert a['evaluation_profile']==b['evaluation_profile']
        common=[]
        for ia,ib in zip(a['iterations'],b['iterations']):
            assert ia['depth']==ib['depth']
            wa=ia['nodes']+ia['qnodes'];wb=ib['nodes']+ib['qnodes']
            common.append(dict(depth=ia['depth'],score_equal=ia['score']==ib['score'],scores=[ia['score'],ib['score']],action_equal=ia['action']==ib['action'],work=[wa,wb],work_ratio=wb/wa if wa else None,seconds=[ia['elapsed'],ib['elapsed']],time_ratio=ib['elapsed']/ia['elapsed'] if ia['elapsed'] else None))
        pairs.append(dict(key=key,actor=cases[key]['actor'],masks=cases[key]['masks'],common_depths=common,common_value_parity=all(x['score_equal']for x in common)if common else None,highest_common=common[-1]if common else None,final_depths=[a['decision']['completed_depth'],b['decision']['completed_depth']],final_scores=[a['decision']['score'],b['decision']['score']],final_actions_equal=a['decision']['action']==b['decision']['action'],result_sources=[a['decision']['result_source'],b['decision']['result_source']],termination=[a['decision']['termination_reason'],b['decision']['termination_reason']],WDL_quality='IMMEDIATE_CORE_WIN_VERIFIED'if a['decision']['result_source']==b['decision']['result_source']=='root_immediate_win'else'UNKNOWN'))
    return dict(status='DATA_QUALIFIED',queries=len(rows),rules=len(compiled),histories=len(cases),pv_legal_steps=pvc,actual_seconds=sum(x['seconds']for x in rows),cpu_seconds=sum(x['cpu_seconds']for x in rows),pairs=pairs,parity_mismatches=[p['key']for p in pairs if p['common_value_parity']is False],no_common=[p['key']for p in pairs if p['common_value_parity']is None],native_legality_calls=sum(x['decision']['native_legality_calls']for x in rows),native_legality_failures=sum(x['decision']['native_legality_operational_failures']for x in rows),termination_counts=dict(Counter(x['decision']['termination_reason']for x in rows)),scope='Qualification is data binding, not successful optimization or WDL truth. All mismatches/negative costs retained.')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--directory',required=True,type=Path);x=a.parse_args();print(json.dumps(qualify(x.directory),ensure_ascii=False))
