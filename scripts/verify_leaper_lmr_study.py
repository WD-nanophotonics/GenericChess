"""Data-only Core replay of frozen LMR returns, not an independent WDL solver."""
from pathlib import Path
from collections import Counter, defaultdict
import argparse
import hashlib
import json
from statistics import median
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from tools.local_agent.common import write_json
from generic_chess.ai.evaluation.config import MATE_THRESHOLD


def lines(path):
    if not path.exists(): return []
    raw=path.read_bytes(); rows=raw.splitlines()
    if raw and not raw.endswith(b'\n'): rows=rows[:-1]
    return [json.loads(x) for x in rows]


def action(s, raw):
    found=[a for a in s.legal_actions() if L.record_value(a)==raw]
    assert len(found)==1, 'illegal or ambiguous recorded action'
    return found[0]


def outcome(s, color):
    r=s.result
    if r.winner is not None: return 'candidate_win' if r.winner==color else 'candidate_loss'
    if r.status.value in ('stalemate','repetition','max_ply','action_class_draw','no_progress_draw'):
        return 'rule_draw'
    return 'unresolved'


def assess(d, partial=False):
    d=Path(d); plan=L.load(d/'plan.json'); data=L.load(d/'inputs.json')
    assert hashlib.sha256((d/'inputs.json').read_bytes()).hexdigest()==plan['inputs_sha256']
    capsule=L.load(d/'source-capsule.json')
    for f in capsule['files']:
        assert hashlib.sha256(f['source'].encode()).hexdigest()==f['sha256']==plan['source_sha256'][f['path']]
    receipt=L.load(d/'receipt.json') if (d/'receipt.json').exists() else None
    if not partial: assert receipt is not None, 'live batch is not a final acceptance'
    rows=lines(d/'queries.jsonl'); games=lines(d/'games.jsonl')
    assert [r['id'] for r in rows]==list(range(len(rows)))
    if receipt is not None: assert receipt['queries']==len(rows) and receipt['games']==len(games)
    cases={c['key']:c for c in data['cases']}; compiled={}
    profiles={}; bygame=defaultdict(list); totals=defaultdict(Counter); pv_steps=0
    for r in rows:
        key=r['case']
        if key not in compiled:
            rr=data['reference']['rules'] if key=='published-horizontal-root137' else cases[key]['rule']
            compiled[key]=L.compile_rule(L.ruleset_from_dict(rr))
        c=compiled[key]; s=replay(c,r['before_record']); before=L.record_value(s.to_record())
        assert before==r['before_record'] and r['decision']['runtime_pushes']==r['decision']['runtime_pops']
        actual_profile=json.dumps(r['profile'],sort_keys=True)
        if key in profiles: assert profiles[key]==actual_profile
        profiles[key]=actual_profile
        assert r['tuning']['use_pvs'] is True and r['tuning']['stop_after_root_win'] is False
        assert r['limits']['quiescence_max_depth']==4 and r['limits']['quiescence_hard_max_depth']==8
        if r['decision']['action'] is not None: action(s,r['decision']['action'])
        for a in r['decision']['principal_variation']:
            s.submit(action(s,a));pv_steps+=1
        if r['label'] not in ('pilot',) and not r['label'].startswith('reference'):
            assert r['limits']['max_time_seconds']==plan['game_seconds'] and r['limits']['max_nodes'] is None
            bygame[r['label']].append(r)
        t=totals['candidate' if r['enabled'] else 'baseline']
        t['queries']+=1;t['seconds']+=r['seconds'];t['cpu_seconds']+=r['cpu_seconds']
        t['nodes']+=r['decision']['nodes'];t['qnodes']+=r['decision']['qnodes']
        t['selective_mate_band_returns_NOT_certificates']+=int(r['enabled'] and abs(r['decision']['score'])>=MATE_THRESHOLD)
        for k,v in r['policy_counts'].items():t[k]+=v
    results=Counter();eligible=Counter();perrule=defaultdict(Counter);game_query_count=0
    for g in games:
        key=g['case']; s=replay(compiled[key],g['initial_record']); qs=bygame[g['game']]
        assert g['initial_record']==cases[key]['record']
        assert len(qs)==len(g['events'])
        for r,event in zip(qs,g['events']):
            assert L.record_value(s.to_record())==r['before_record'], 'history or actual action join mismatch'
            assert r['enabled']==(s.state.position.side_to_move==g['candidate_color'])==event['candidate']
            assert r['decision']['choice_kind']!='DECLARATION', 'declared none in frozen pure-Leaper scope'
            s.submit(action(s,r['decision']['action']));game_query_count+=1
        assert L.record_value(s.to_record())==g['final_record']
        assert L.record_value(s.result)==g['final_result']
        assert outcome(s,g['candidate_color'])==g['outcome']['result']
        results[g['outcome']['result']]+=1
        if g['eligible']:eligible[g['outcome']['result']]+=1
        perrule[cases[key]['semantic_fingerprint']][g['outcome']['result']]+=1
    if receipt and receipt['status']=='CLOSED':
        assert len(games)==2*len(plan['game_cases'])
        assert len({(g['case'],g['candidate_color']) for g in games})==len(games)
    return dict(status=receipt['status'] if receipt else 'RUNNING_COMPLETED_GAME_PREFIX_ONLY',
        queries=len(rows),games=len(games),game_query_count=game_query_count,pv_steps=pv_steps,
        outcomes=dict(results),eligible_outcomes=dict(eligible),per_rule=dict(perrule),totals=dict(totals),
        receipt=receipt,remaining_games=2*len(plan['game_cases'])-len(games),
        limits='Exposed6rule/12root small paired games; no Elo/independent holdout/classsuccess. Selective nominal-depth/mate/TTEXACT are not full-width proofs. Accepted-reduced-fail-low counter includes excluded child probes searched without reduction; actual reduced_calls separate. Concurrency/time perturbation retained.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);p.add_argument('--partial',action='store_true');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=assess(a.directory,a.partial);write_json(a.output,r)
    print({k:r[k] for k in ('status','queries','games','pv_steps','outcomes','eligible_outcomes')})
