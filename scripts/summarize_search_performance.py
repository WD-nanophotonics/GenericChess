"""Read saved benchmark decisions; no Player execution, no source-capsule execution."""
from pathlib import Path
from collections import defaultdict
from statistics import median
import json,argparse,hashlib,gzip
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.search_performance_study import digest
from generic_chess.ai.benchmark.runner import _adjudicate
from generic_chess.rules.compiler import compile_ruleset
from tools.local_agent.common import write_json

def rows_exist(p):return p.exists() or p.with_suffix(p.suffix+'.gz').exists()
def rows(p):
    if not p.exists():p=p.with_suffix(p.suffix+'.gz')
    raw=gzip.decompress(p.read_bytes()) if p.suffix=='.gz' else p.read_bytes()
    return [json.loads(l)for l in raw.decode('utf-8').splitlines()if l.strip()]
def summarize(d):
    cases=json.loads((d/'inputs.json').read_text())['cases']
    if(d/'transfer-inputs.json').exists():cases+=json.loads((d/'transfer-inputs.json').read_text())['cases']
    lookup={x['key']:x for x in cases};compiled={}
    for x in cases:
        assert x['input_sha256']==digest([x['rule'],x['record']])
        c=(compile_ruleset if x.get('execution_api')=='compile_ruleset' else L.compile_rule)(L.ruleset_from_dict(x['rule']));s=replay(c,x['record']);assert(s.state.position.side_to_move,s.state.ply_count)==(x['side'],x['ply']);compiled[x['key']]=c
    calls=0;pv_actions=0;known_checks=0
    def check(case,dec):
        nonlocal calls,pv_actions,known_checks
        c=compiled[case['key']];s=replay(c,case['record']);calls+=1
        if dec.get('action')is not None:L.match_action(s,dec['action'])
        for a in dec['principal_variation']:
            s.submit(L.match_action(s,a));pv_actions+=1
        threshold=3 if case['key']=='solved3_0'else 2
        if case['key'].startswith('solved3')and dec['completed_depth']>=threshold:
            assert abs(dec['score'])>=900000000 and(1 if dec['score']>0 else -1)==case['expected_WDL'];known_checks+=1
    measured=[]
    for name in ['baseline','candidate','snapshot-ab','transfer']:
        if not rows_exist(d/(name+'.jsonl')):continue
        rr=rows(d/(name+'.jsonl'))
        for r in rr:
            assert 'failure'not in r, 'retain failed query, do not qualify as success'
            case=lookup[r['case']]
            if 'input_sha256'in r:assert r['input_sha256']==case['input_sha256']
            check(case,r['decision'])
            if 'prime'in r:check(case,r['prime'])
        if name in ['snapshot-ab','transfer']:
            grouped=defaultdict(dict)
            for r in rr:grouped[(r['case'],r.get('qdepth',4),r['mode'],r['rep'])][r['arm']]=r
            for k,arms in grouped.items():
                assert set(arms)=={'old','new'},'incomplete pair'
                a,b=arms['old'],arms['new'];da,db=a['decision'],b['decision'];assert a['limits']==b['limits']
                deterministic=k[2]!='wall'and da['termination_reason']!='time_limit'and db['termination_reason']!='time_limit'
                if deterministic:
                    assert tuple(da[x]for x in ['score','completed_depth','nodes','qnodes','principal_variation','tt_probes','tt_hits','tt_cutoffs','beta_cutoffs','runtime_pushes','runtime_pops','result_source','termination_reason'])==tuple(db[x]for x in ['score','completed_depth','nodes','qnodes','principal_variation','tt_probes','tt_hits','tt_cutoffs','beta_cutoffs','runtime_pushes','runtime_pops','result_source','termination_reason'])
                measured.append(dict(case=k[0],qdepth=k[1],mode=k[2],rep=k[3],old_seconds=a['wall_seconds'],new_seconds=b['wall_seconds'],old_depth=da['completed_depth'],new_depth=db['completed_depth'],old_work=da['nodes']+da['qnodes'],new_work=db['nodes']+db['qnodes'],old_qshare=da['qnodes']/max(1,da['nodes']+da['qnodes']),exact_work_and_value_parity=deterministic))
    agg=defaultdict(list)
    for r in measured:agg[(r['case'],r['qdepth'],r['mode'])].append(r)
    table=[]
    for k,rr in sorted(agg.items()):
        old=median(r['old_seconds']for r in rr);new=median(r['new_seconds']for r in rr)
        table.append(dict(case=k[0],qdepth=k[1],mode=k[2],repeats=len(rr),old_seconds_median=old,new_seconds_median=new,speed_ratio_old_over_new=old/new,seconds_reduction_fraction=1-new/old,old_depths=[r['old_depth']for r in rr],new_depths=[r['new_depth']for r in rr],old_work_median=median(r['old_work']for r in rr),new_work_median=median(r['new_work']for r in rr),qshare=median(r['old_qshare']for r in rr),all_nonwall_deterministic_equal=all(r['exact_work_and_value_parity']for r in rr)))
    for filename in ('profiles.json', 'q4-hotspots.json'):
        if (d / filename).exists():
            for row in json.loads((d / filename).read_text())['rows']:
                check(lookup[row['case']], row['decision'])
    availability_table = []
    availability_pairs = 0
    availability_queries = 0
    if rows_exist(d / 'availability.jsonl'):
        av_groups = defaultdict(dict)
        for row in rows(d / 'availability.jsonl'):
            case = lookup[row['case']]
            assert row['input_sha256'] == case['input_sha256']
            check(case, row['decision'])
            if row['availability_enabled']:
                assert row['availability_delta'].get('queries', 0) > 0
                availability_queries += row['availability_delta']['queries']
            else:
                assert row['availability_delta'] == {}
            av_groups[(row['case'], row['mode'], row['rep'])][row['availability_enabled']] = row
        av_aggregate = defaultdict(list)
        for key, arms in av_groups.items():
            assert set(arms) == {False, True}
            a, b = arms[False], arms[True]
            assert a['limits'] == b['limits']
            x, y = a['decision'], b['decision']
            comparable = key[1] == 'nodes' and all(v['termination_reason'] != 'time_limit' for v in (x, y))
            if comparable:
                fields = ('score', 'completed_depth', 'nodes', 'qnodes', 'principal_variation', 'tt_hits', 'tt_cutoffs', 'runtime_pushes', 'runtime_pops')
                assert tuple(x[f] for f in fields) == tuple(y[f] for f in fields)
            av_aggregate[key[:2]].append((a, b, comparable))
            availability_pairs += 1
        for key, pairs in sorted(av_aggregate.items()):
            old = median(a['wall_seconds'] for a, b, comparable in pairs)
            new = median(b['wall_seconds'] for a, b, comparable in pairs)
            availability_table.append(dict(case=key[0], mode=key[1], repeats=len(pairs), core_seconds_median=old, native_seconds_median=new, seconds_reduction_fraction=1-new/old, core_depths=[a['decision']['completed_depth'] for a,b,c in pairs], native_depths=[b['decision']['completed_depth'] for a,b,c in pairs], all_fixed_work_equal=all(c for a,b,c in pairs)))
    games=[]
    if rows_exist(d/'games.jsonl'):
        for r in rows(d/'games.jsonl'):
            case=next(x for x in cases if x['input_sha256']==r['input_sha256']);z=replay(compiled[case['key']],r['final_record']);o=r['outcome']
            if o['result']!='failed':assert o['result']==_adjudicate(z,o['candidate_color'])
            assert z.state.ply_count == o['plies']
            for turn in rows(d / (r['game'] + '-turns.jsonl')):
                check({**case, 'record':turn['before_record']}, turn['decision'])
            games.append(dict(game=r['game'],result=o['result'],plies=o['plies'],eligible=r['eligible'],final_status=z.result.status.value,rule_max_ply=r['rule_max_ply'],caller_cap=r['caller_cap']))
    return dict(status='PASS',record_cases=len(cases),validated_saved_decisions=calls,legal_PV_actions=pv_actions,known_WDL_score_checks=known_checks,comparison_pairs=len(measured),table=table,availability_pairs=availability_pairs,actual_native_availability_queries=availability_queries,availability_table=availability_table,games=games,limitations=['Repeated timings are not independent opening samples or strength evidence.','ColdTT resets preserve same-player Native action-conversion cache; ABBA balances order, not fully cold process setup.','Q0 and Q4 are separate trees. Partial completed-depth6 requests are not depth6 minimax claims.','Actual time cap is cooperative. NPS/depth do not prove human strength.','Same-Core replay plus independent exact-map controls is not an independent full game engine.'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();q=summarize(a.directory);write_json(a.output,q);print(json.dumps({k:v for k,v in q.items()if k not in ['table','availability_table','games']}));print('games',q['games'])
