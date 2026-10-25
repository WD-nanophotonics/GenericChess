"""Use the fixed published 19-witness bundle as exposed quality diagnostics.

No solver, learner, price intervention or source-capsule execution. Original
graph labels are attributed; one selected LOSS/DRAW certificate is checked apart.
"""
from pathlib import Path
from contextlib import nullcontext
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse, hashlib, json, time, traceback
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.pure_leaper_search_study import append
from scripts.leaper_lmr_feasibility import LateQuietReduction
from tools.local_agent.common import write_json
from tools.local_agent.session import stopped
from generic_chess.core.actions import action_to_dict, action_from_dict
from generic_chess.ai.alphabeta.player import AlphaBetaPlayer
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits

def stamp(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run(d):
    plan=L.load(d/'plan.json');data=L.load(d/'inputs.json')
    parent=L.load(Path(plan['parent_receipt']))
    assert parent['status']=='CLOSED', 'complete earlier frozen batch first; no replacement/continuation'
    origin=datetime.fromisoformat(plan['logical_origin'])
    assert (datetime.now(timezone.utc)-origin).total_seconds()<plan['latest_start_seconds'], 'whole-chain budget gate; do not reset'
    assert not (d/'queries.jsonl').exists() and not (d/'receipt.json').exists()
    assert sha(d/'inputs.json')==plan['inputs_sha256']
    for p,h in plan['sources'].items(): assert sha(p)==h
    tick=time.perf_counter();start=stamp();count=0;status='FAILED'
    cases={c['id']:c for c in data['cases']}
    class Cancel:
        last=0.;flag=False
        def is_cancelled(self):
            t=time.perf_counter()
            if t-self.last>=.25:
                self.last=t;self.flag=stopped() or t-tick>=plan['batch_seconds']
            return self.flag
    cancel=Cancel()
    try:
        for slot in plan['slots']:
            if cancel.is_cancelled():status='STOPPED_UNKNOWN';break
            case=cases[slot['id']];c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['record']['ruleset_fingerprint']]))
            s=replay(c,case['record']);assert L.state_sha(s.state)==case['id']
            legal=set(s.legal_actions());labelled={action_from_dict(b['action']):b['WDL'] for b in case['branches']}
            assert legal==set(labelled) and max(labelled.values())==case['WDL']
            limits=SearchLimits(max_nodes=slot['nodes'],max_time_seconds=slot['seconds'])
            player=AlphaBetaPlayer(c,use_disk_cache=False,tuning=SearchTuning(use_pvs=True))
            policy=LateQuietReduction() if slot['enabled'] else None
            begin=stamp();qt=time.perf_counter();cp=time.process_time()
            with policy if policy else nullcontext():decision=player.choose_action(s,limits,cancel_token=cancel)
            end=stamp();row=dict(slot=slot,started_at=begin,ended_at=end,seconds=time.perf_counter()-qt,
                cpu_seconds=time.process_time()-cp,decision=L.record_value(decision),action_record=action_to_dict(decision.action) if decision.action is not None else None,
                profile=L.record_value(player.evaluation_profile),tuning=L.record_value(SearchTuning(use_pvs=True)),
                policy_counts=dict(policy.counts) if policy else {},root_record=case['record'],state_sha256=L.state_sha(s.state),
                source_graph_root_WDL=case['WDL'],source_graph_chosen_WDL=labelled.get(decision.action),
                label_scope='Original published fullhistory graph labels, not independent rerun or holdout. Selective scores not proofs.')
            append(d/'queries.jsonl',row);count+=1
            assert L.record_value(s.to_record())==case['record']
            pv=replay(c,case['record'])
            for a in decision.principal_variation:
                choices=[x for x in pv.legal_actions() if L.record_value(x)==L.record_value(a)];assert len(choices)==1;pv.submit(choices[0])
            assert decision.action in legal
            print('LMR-QUALITY',count,slot['budget'],slot['enabled'],case['id'][:8],row['source_graph_chosen_WDL'],round(row['seconds'],3),flush=True)
        else:status='CLOSED'
    except BaseException:
        write_json(d/'failure.json',dict(at=stamp(),queries=count,traceback=traceback.format_exc()));raise
    finally:write_json(d/'receipt.json',dict(status=status,started_at=start,ended_at=stamp(),seconds=time.perf_counter()-tick,queries=count,plan_sha256=sha(d/'plan.json')))

def assess(d):
    d=Path(d);plan=L.load(d/'plan.json');data=L.load(d/'inputs.json');receipt=L.load(d/'receipt.json')
    rows=[json.loads(x)for x in (d/'queries.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(rows)==receipt['queries']
    if receipt['status']=='CLOSED':assert len(rows)==len(plan['slots'])
    cases={c['id']:c for c in data['cases']};groups=defaultdict(dict);counts=defaultdict(Counter);pvsteps=0
    for r in rows:
        case=cases[r['slot']['id']];c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['record']['ruleset_fingerprint']]))
        s=replay(c,r['root_record']);assert L.state_sha(s.state)==case['id']==r['state_sha256']
        labels={action_from_dict(b['action']):b['WDL']for b in case['branches']};a=action_from_dict(r['action_record'])
        assert set(labels)==set(s.legal_actions()) and labels[a]==r['source_graph_chosen_WDL']
        assert r['root_record']==case['record'] and r['source_graph_root_WDL']==max(labels.values())
        for raw in r['decision']['principal_variation']:
            legal=[a for a in s.legal_actions()if L.record_value(a)==raw];assert len(legal)==1;s.submit(legal[0]);pvsteps+=1
        key=(r['slot']['id'],r['slot']['budget']);assert r['slot']['enabled']not in groups[key];groups[key][r['slot']['enabled']]=r
    pairs=[]
    for (id,budget),arms in groups.items():
        if set(arms)!={False,True}:continue
        a,b=arms[False],arms[True];assert a['profile']==b['profile'] and a['tuning']==b['tuning']
        c=counts[budget];c['pairs']+=1
        for name,r in [('baseline',a),('candidate',b)]:
            c[name+'_correct']+=int(r['source_graph_chosen_WDL']==r['source_graph_root_WDL'])
            c[name+'_seconds']+=r['seconds'];c[name+'_events']+=r['decision']['nodes']+r['decision']['qnodes']
            c[name+'_time_censors']+=int(r['decision']['termination_reason']=='time_limit')
        c['repairs']+=int(b['source_graph_chosen_WDL']>a['source_graph_chosen_WDL'])
        c['regressions']+=int(b['source_graph_chosen_WDL']<a['source_graph_chosen_WDL'])
        pairs.append(dict(id=id,budget=budget,baseline=a['source_graph_chosen_WDL'],candidate=b['source_graph_chosen_WDL'],root=a['source_graph_root_WDL'],same_action=a['action_record']==b['action_record']))
    return dict(status=receipt['status'],queries=len(rows),pv_steps=pvsteps,by_budget=dict(counts),pairs=pairs,
        scope='19fixed published selected witnesses/9rules/exposed and correlated; actualdefaultdynamic bothPVS, noAUXprices. Sourcegraphlabels retained; only namedbadproof/safeclosure independentlyqualified elsewhere. No Elo/classsuccess/default activation or originalpriceclaim.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['run','assess']);p.add_argument('--directory',type=Path,required=True);a=p.parse_args()
    if a.phase=='run':run(a.directory)
    else:
        r=assess(a.directory);write_json(a.directory/'assessment.json',r);print({k:r[k]for k in ('status','queries','pv_steps','by_budget')})
