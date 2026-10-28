"""Independent raw-return and full-Core replay; no new search or game."""
from __future__ import annotations
import argparse,hashlib,json
from collections import Counter,defaultdict
from pathlib import Path
from generic_chess.rules.schema import ruleset_from_dict,compute_fingerprint
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record
from scripts.research_record import record_value,write_record
from scripts.verify_leaper_pvs_quality_pilot import load,action,full_digest,original_return


def service(q):
    target=1.5
    assert q['requested_service_seconds']==target
    assert 0<q['limits']['max_time_seconds']<=target
    assert q['limits']['max_time_seconds']+q['construction_packing_seconds']<=target+1e-9
    assert q['timing_eligible']==(q['service_wall_seconds']<=target*1.1)
    expected={'use_root_tactical','use_ordered_qsearch_in_check'}
    if q['on']:expected.add('use_one_check_extension')
    assert {k for k,v in q['actual_tuning'].items() if k.startswith('use_') and v is True}==expected
    assert not q['actual_tuning']['require_full_pv'] and not q['actual_tuning']['stop_after_root_win']
    d=q['decision']
    assert d['pvs_null_window_searches']==d['pvs_researches']==0
    assert d['main_extension_max_path']<=int(q['on'])
    if not q['on']:assert d['main_check_extensions']==0 and d['main_search_max_ply']==0
    assert d['runtime_depth_balanced'] and d['native_legality_fallbacks']==d['native_legality_operational_failures']==0
    assert q['provider_present'] and q['provider_delta']['availability'].get('declines',0)==0
    assert q['limits']['max_depth']==64 and q['limits']['max_nodes']==500000
    assert q['limits']['quiescence_max_depth']==4 and q['limits']['quiescence_hard_max_depth']==8
    if d['result_source']=='main_iteration':
        assert d['completed_depth']>=1
        assert d['result_ordinary_qdepth']==(0 if d['completed_depth']==1 else 4)

def submission(raw,embedded,actual_after_hash):
    # choose() persists raw BEFORE submit; only its returned object receives
    # the independently replayable post-submit annotation. Never mutate raw.
    assert 'record_after_sha256' not in raw
    assert all(embedded[k]==v for k,v in raw.items())
    assert embedded['record_after_sha256']==actual_after_hash
    assert embedded['root_unchanged'] is True and embedded['pv_legal'] is True


def endpoints(games,planned=30):
    assert len(games)==planned
    scores=[];families=defaultdict(list);outcomes=Counter();missing=0
    for g in games:
        valid=g['status']=='TERMINAL' and g['timing_eligible']
        if valid:
            winner=g['Core_terminal']['winner']
            p=.5 if winner is None else float(winner==g['on_seat'])
            outcomes['DRAW' if winner is None else ('ON_WIN' if p else 'OFF_WIN')]+=1
            scores.append(p);families[g['family']].append(p)
        else:missing+=1;families[g['family']].append(None)
    bounds={}
    for f,xs in families.items():
        good=[x for x in xs if x is not None];n=len(xs)
        bounds[str(f)]=dict(planned_games=n,observed=len(good),points=sum(good),lower=sum(good)/n,upper=(sum(good)+n-len(good))/n)
    positive=sum(x['lower']>.5 for x in bounds.values())
    return dict(planned_games=planned,eligible_terminals=planned-missing,missing=missing,outcomes=dict(outcomes),ON_points=sum(scores),raw_completion_bounds=[sum(scores)/planned,(sum(scores)+missing)/planned],equal_family_completion_bounds=[sum(x['lower'] for x in bounds.values())/8,sum(x['upper'] for x in bounds.values())/8],families=bounds,positive_families=positive,exploratory_gate_passed=missing==0 and positive>=5 and sum(scores)>=.55*planned,interpretation='Conditional DEVELOPMENT result only. Frozen raw-game gate; equal-family bounds descriptive, not replacement acceptance. No independent population CI, default activation or all-class strength claim.')


def verify(prepared,folder,output):
    roots={r['id']:r for r in load(prepared/'inputs.json')['rows']}
    frozen=load(folder/'frozen.json');plan=frozen['plan']
    inp=prepared/'inputs.json';raw=inp.read_bytes() if inp.exists() else __import__('gzip').decompress(Path(str(inp)+'.gz').read_bytes())
    assert hashlib.sha256(raw).hexdigest()==plan['input_sha256']==frozen['input_sha256'] and len(roots)==15
    for name,text in frozen['sources'].items():assert hashlib.sha256(text.encode()).hexdigest()==plan['sources'][name]
    binary=load(folder/'loaded-binary.json');assert len(binary['sha256'])==64 and binary['bytes']>0
    profiles={};seen=set();PV=transitions=0;statistics={False:Counter(),True:Counter()}
    def inspect(qid,root,s,embedded=None):
        nonlocal PV
        assert qid not in seen;seen.add(qid);q=original_return(folder,qid)
        if embedded is not None:assert all(embedded[k]==v for k,v in q.items())
        assert q['query_id']==qid and q['record_before_sha256']==full_digest(s.to_record()) and q['seat']==s.state.position.side_to_move and q['ply_before']==s.state.ply_count
        service(q);profile=q['evaluation_profile'];assert profile['ruleset_fingerprint']==root['fingerprint']
        if root['id'] in profiles:assert profiles[root['id']]==profile
        else:profiles[root['id']]=profile
        d=q['decision'];chosen=action(d['action'],s);assert chosen in s.legal_actions()
        pv=GameSession.replay(compiled[root['id']],s.to_record())
        if d['principal_variation']:assert d['principal_variation'][0]==d['action']
        for a in d['principal_variation']:pv.submit(action(a,pv));PV+=1
        if d['result_source']=='root_immediate_win':
            from generic_chess.ai.evaluation.config import MATE_SCORE
            child=GameSession.replay(compiled[root['id']],s.to_record());child.submit(chosen)
            assert child.state.terminal_status.is_terminal and child.state.terminal_status.winner==s.state.position.side_to_move
            assert d['completed_depth']==0 and d['score']==MATE_SCORE-1
        return q,chosen
    compiled={}
    for r in roots.values():
        rules=ruleset_from_dict(r['RuleSet']);assert compute_fingerprint(rules)==r['fingerprint'];compiled[r['id']]=compile_legacy_ruleset_for_semantic_execution(rules)
    qual=load(folder/'qualification.json');assert len(qual)==30
    for i,x in enumerate(qual):
        assert x['case_id']==plan['root_ids'][i//2]
        if x['status']=='NOT_RUN':continue
        assert x['status']=='RETURNED' and x['accepted_goal']=='legal_same_service_return'
        r=roots[x['case_id']];s=GameSession.replay(compiled[r['id']],deserialize_game_record(json.dumps(r['record'])))
        q,a=inspect(x['query_id'],r,s);assert q['decision']==x['decision'] and q['on']==x['on'] and q['timing_eligible']
    games=load(folder/'games.json');assert len(games)==30
    for i,g in enumerate(games):
        r=roots[g['case_id']];assert g['case_id']==plan['root_ids'][i//2] and r['record']==g['initial_record'] and r['fingerprint']==g['fingerprint'] and r['family']==g['family']
        assert {games[i-i%2]['on_seat'],games[i-i%2+1]['on_seat']}=={0,1}
        s=GameSession.replay(compiled[r['id']],deserialize_game_record(json.dumps(r['record'])))
        for old in g['queries']:
            q,a=inspect(old['query_id'],r,s,old);assert q['on']==(q['seat']==g['on_seat'])
            before=s.to_record();s.submit(a);transitions+=1;submission(q,old,full_digest(s.to_record()))
            d=q['decision'];statistics[q['on']].update(calls=1,wall=q['service_wall_seconds'],cpu=q['cpu_seconds'],nodes=d['nodes'],qnodes=d['qnodes'],extensions=d['main_check_extensions'],overtime=not q['timing_eligible'],fallback=d['result_source']=='root_fallback')
        if g['status'] in ('TERMINAL','UNFINISHED'):
            assert record_value(s.to_record())==g['final_record'] and record_value(s.state.terminal_status)==g['Core_terminal'] and record_value(s.result)==g['Session_result']
            assert s.state.terminal_status.is_terminal==(g['status']=='TERMINAL')
            assert g['timing_eligible']==all(q['timing_eligible'] for q in g['queries'])
        write_record(output.with_suffix('.progress.json'),dict(games=i+1,transitions=transitions,PV_plies=PV))
    actual={p.stem for p in (folder/'returns').glob('*.json')} if (folder/'returns').exists() else set(load(folder/'returns.json'))
    assert actual==seen,'orphan or missing raw return'
    result=dict(status='PASS',endpoint=endpoints(games),raw_returns=len(seen),Core_transitions=transitions,literal_PV_plies=PV,identical_profiles_checked=len(profiles),by_policy={str(k):dict(v) for k,v in statistics.items()},new_Player=0,new_game=0,new_solver=0,loaded_binary_receipt=binary,limitations='Core saved-action/PV/raw replay, not independent search reproduction; conditional development only.')
    write_record(output,result);print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--prepared',type=Path,required=True);p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();verify(a.prepared,a.folder,a.output)
