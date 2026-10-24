"""Data-only qualification of pure-Leaper search; never runs Players/capsules."""
from pathlib import Path
from collections import defaultdict,Counter
from statistics import median
import argparse,json,gzip
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.search_performance_study import digest
from generic_chess.ai.benchmark.runner import _adjudicate
from tools.local_agent.common import write_json


def rows(p):
    if not p.exists():p=p.with_suffix(p.suffix+'.gz')
    if not p.exists():return []
    b=gzip.decompress(p.read_bytes())if p.suffix=='.gz'else p.read_bytes()
    return [json.loads(l)for l in b.decode().splitlines()if l.strip()]


def qualify(d):
    cases=L.load(d/'inputs.json')['cases'];index={x['key']:x for x in cases};compiled={}
    for case in cases:
        assert case['input_sha256']==digest([case['rule'],case['record']])
        rr=L.ruleset_from_dict(case['rule']);assert all(type(m).__name__=='LeapAtom'for t in rr.piece_types for m in t.movement_atoms)
        c=L.compile_rule(rr);s=replay(c,case['record']);assert s.state.ply_count==case['actual_ply'];assert s.state.position.ruleset_fingerprint==case['semantic_fingerprint'];compiled[case['key']]=c
    counts=Counter();queries=0;query_counts=Counter()
    def check(case,dec):
        s=replay(compiled[case['key']],case['record']);counts['decisions']+=1
        if dec['action'] is not None:L.match_action(s,dec['action'])
        for a in dec['principal_variation']:s.submit(L.match_action(s,a));counts['PV_actions']+=1
    table=[];wall_differences=[]
    for phase in ('pilot','bench'):
        rr=rows(d/(phase+'.jsonl'));groups=defaultdict(dict);agg=defaultdict(list)
        for r in rr:
            case=index[r['case']];assert r['input_sha256']==case['input_sha256'];check(case,r['decision'])
            if r['availability_enabled']:
                assert r['availability_delta'].get('queries',0)>0;queries+=r['availability_delta']['queries'];query_counts[phase]+=r['availability_delta']['queries']
            else:assert r['availability_delta']=={}
            groups[(r['case'],r['mode'],r['rep'])][r['availability_enabled']]=r
        for (key,mode,rep),arms in groups.items():
            if set(arms)!={False,True}:counts['incomplete_pairs']+=1;continue
            a,b=arms[False],arms[True];assert a['limits']==b['limits'];x,y=a['decision'],b['decision'];comparable=mode=='nodes' and all(z['termination_reason']!='time_limit'for z in (x,y))
            if comparable:
                fs=('action','score','completed_depth','nodes','qnodes','principal_variation','tt_probes','tt_hits','tt_cutoffs','beta_cutoffs','runtime_pushes','runtime_pops','result_source','termination_reason')
                assert all(x[f]==y[f]for f in fs),'fixed work/score/action mismatch'
                counts['fixed_work_pairs']+=1
            agg[(key,mode)].append((a,b,comparable));counts[phase+'_pairs']+=1
            if phase=='bench' and mode=='wall':wall_differences.append(dict(case=key,rep=rep,same_action=x['action']==y['action'],old_depth=x['completed_depth'],new_depth=y['completed_depth'],old_work=x['nodes']+x['qnodes'],new_work=y['nodes']+y['qnodes'],old_action=x['action'],new_action=y['action'],old_source=x['result_source'],new_source=y['result_source']))
        for (key,mode),ps in agg.items():
            old=median(a['wall_seconds']for a,b,c in ps);new=median(b['wall_seconds']for a,b,c in ps)
            table.append(dict(phase=phase,case=key,mode=mode,pairs=len(ps),core_median_seconds=old,native_median_seconds=new,seconds_reduction_fraction=1-new/old,all_fixed_work=all(c for a,b,c in ps)))
    games=[]
    for r in rows(d/'games.jsonl'):
        s=replay(compiled[r['case']],r['final_record']);assert r['outcome']['result']==_adjudicate(s,r['candidate_color']);assert s.state.ply_count==r['outcome']['plies']
        for turn in rows(d/(r['game']+'-turns.jsonl')):
            check({**index[r['case']],'record':turn['before_record']},turn['decision'])
            n=turn['availability_delta'].get('queries',0);queries+=n;query_counts['games']+=n
        games.append(dict(game=r['game'],result=r['outcome']['result'],eligible=r['eligible'],plies=r['outcome']['plies'],terminal=s.result.status.value))
    refs=[]
    for r in rows(d/'reference.jsonl'):
        check({**index[r['case']],'record':r['after_forced_action_record']},r['decision']);refs.append(dict(case=r['case'],arm=r['arm'],requested_depth=r['requested_depth'],completed=r['completed'],root_score=r['root_score'],depth=r['decision']['completed_depth']))
    pvs_groups=defaultdict(dict);pvs_table=[]
    for r in rows(d/'pvs.jsonl'):
        check(index[r['case']],r['decision'])
        assert r['availability_enabled'] is True and r['availability_metrics'].get('queries',0)>0
        n=r['availability_metrics']['queries'];queries+=n;query_counts['pvs']+=n
        if r['pvs_enabled']:assert r['decision']['pvs_null_window_searches']>0
        else:assert r['decision']['pvs_null_window_searches']==0
        pvs_groups[r['case'],r['rep']][r['pvs_enabled']]=r
    for (key,rep),arms in pvs_groups.items():
        if set(arms)!={False,True}:counts['incomplete_pvs_pairs']+=1;continue
        a,b=arms[False],arms[True];assert a['limits']==b['limits'];complete=a['complete'] and b['complete']
        if complete:assert a['decision']['score']==b['decision']['score']
        na=a['decision']['nodes']+a['decision']['qnodes'];nb=b['decision']['nodes']+b['decision']['qnodes']
        pvs_table.append(dict(case=key,rep=rep,requested_depth=a['requested_depth'],both_completed=complete,old_depth=a['decision']['completed_depth'],new_depth=b['decision']['completed_depth'],old_work=na,new_work=nb,old_seconds=a['wall_seconds'],new_seconds=b['wall_seconds'],work_ratio=na/max(1,nb),time_ratio=a['wall_seconds']/b['wall_seconds'],null_windows=b['decision']['pvs_null_window_searches'],researches=b['decision']['pvs_researches'],same_action=a['decision']['action']==b['decision']['action']))
    return dict(status='PASS',rules=6,full_roots=len(cases),counts=dict(counts),actual_native_availability_queries=queries,native_queries_by_phase=dict(query_counts),table=table,wall_decisions=wall_differences,same_wall_same_action=sum(r['same_action']for r in wall_differences),same_wall_pairs=len(wall_differences),games=games,references=refs,pvs_pairs=pvs_table,limitations=['Six exogenous rules/two correlated roots each, not IID or whole pureLeaper class.','FreshPlayer resets Native actioncache andTT per benchmarkquery; games preserveTT acrossmoves.','5sec wall comparisons are measured online and may be noisy; extra depth alone not strength.','Reference only paired proposed actions/same evaluator, not full regret or independenttruth.','Incomplete reference/callertruncated/failed games retain UNKNOWN.'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();q=qualify(a.directory);write_json(a.output,q);print(json.dumps({k:v for k,v in q.items()if k not in ['table','wall_decisions','games','references','pvs_pairs']}))
