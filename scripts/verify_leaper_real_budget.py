"""Read-only paired actual-return qualification at code-defined UI budgets."""
from pathlib import Path
from collections import defaultdict
import argparse,json,statistics,hashlib
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from scripts.verify_leaper_forced_continuation import raw,load,rows,key

def paired(records):
    grouped=defaultdict(dict)
    for r in records:
        k=(r['budget'],r['key']);assert r['arm']not in grouped[k];grouped[k][r['arm']]=r
    out={}
    for budget in ['fixed1.5','balanced50k','deep200k']:
        complete=[(k,a)for k,a in grouped.items()if k[0]==budget and set(a)=={'default','refined'}];missing=[k[1]for k,a in grouped.items()if k[0]==budget and set(a)!={'default','refined'}]
        pairs=[dict(key=k[1],default=a['default'],refined=a['refined'],repair=not a['default']['correct']and a['refined']['correct'],regression=a['default']['correct']and not a['refined']['correct'],latency_ratio=a['refined']['seconds']/a['default']['seconds'],caller_ratio=a['refined']['caller_seconds']/a['default']['caller_seconds'])for k,a in complete]
        out[budget]=dict(pairs=len(pairs),unpaired_UNKNOWN=missing,default_correct=sum(p['default']['correct']for p in pairs),refined_correct=sum(p['refined']['correct']for p in pairs),choice_sensitive=sum(p['default']['choice_sensitive']for p in pairs),sensitive_correct={a:sum(p[a]['correct']and p[a]['choice_sensitive']for p in pairs)for a in ['default','refined']},repairs=[p['key']for p in pairs if p['repair']],regressions=[p['key']for p in pairs if p['regression']],node_target_censored={a:[p['key']for p in pairs if p[a]['node_target_censored']]for a in ['default','refined']},seconds={a:sum(p[a]['seconds']for p in pairs)for a in ['default','refined']},caller_seconds={a:sum(p[a]['caller_seconds']for p in pairs)for a in ['default','refined']},median_paired_latency_ratio=statistics.median(p['latency_ratio']for p in pairs)if pairs else None,pair_rows=pairs)
    return out

def assess(directory):
    d=Path(directory);plan=load(d/'plan.json');receipt=load(d/'receipt.json');data=load(d/'inputs.json');rr=rows(d/'queries.jsonl');qq=rows(d/'qualification.jsonl')
    assert receipt['source_sha256']==plan['source_sha256']and hashlib.sha256(raw(d/'inputs.json')).hexdigest()==plan['inputs_sha256']
    assert receipt['queries']==len(rr)and receipt['attempted']>=len(rr)and [r['slot']for r in rr]==plan['slots'][:len(rr)]
    if receipt['status']=='CLOSED':assert len(rr)==len(plan['slots'])==288
    qmap={key(x['slot']):x for x in qq};assert len(qmap)==len(qq);cases={c['key']:c for c in data['cases']};out=[];steps=0;pair_profiles={}
    for r in rr:
        slot=r['slot'];case=cases[slot['key']];assert r['state_sha256']==case['state_sha256'];c=L.compile_rule(L.ruleset_from_dict(data['rules'][case['rule_sha256']]));s=replay(c,case['record']);assert L.state_sha(s.state)==case['state_sha256']
        labels={key(x['action']):x['truth']['value']for x in case['labelled_actions']};assert set(labels)=={key(L.record_value(a))for a in s.legal_actions()};assert(max if case['actor']==0 else min)(labels.values())==case['root_global_WDL']
        dec=r['decision'];value=labels[key(dec['action'])];q=qmap[key(slot)];assert q['chosen_global_WDL']==value and q['correct']==(value==case['root_global_WDL'])
        for a in dec['principal_variation']:s.submit(L.match_action(s,a));steps+=1
        profile=(r['tuning'],r['evaluation_profile']);pk=(slot['budget'],slot['key']);assert pk not in pair_profiles or profile==pair_profiles[pk];pair_profiles[pk]=profile
        if slot['arm']=='default':assert not r['policy_counts']
        else:assert r['policy_counts'].get('q_semantic_tt_clears',0)<=1
        censored=slot['budget']!='fixed1.5'and dec['termination_reason']=='time_limit';assert censored==q['node_target_censored'];n=plan['budgets'][slot['budget']]['ui_allocated_limits']['max_nodes'];events=dec['nodes']+dec['qnodes']
        out.append(dict(**slot,correct=q['correct'],value=value,choice_sensitive=len(set(labels.values()))>1,seconds=r['seconds'],caller_seconds=r['caller_seconds'],setup_seconds=r['setup_seconds'],decision_seconds=dec['elapsed_seconds'],events=events,node_budget_overshoot=None if n is None else max(0,events-n),node_target_censored=censored,completed_depth=dec['completed_depth'],score=dec['score'],termination=dec['termination_reason'],source=dec['result_source'],ordinary_qdepth=dec['result_ordinary_qdepth']))
    return dict(status=receipt['status'],queries=len(rr),expected=len(plan['slots']),missing_slots_UNKNOWN=len(plan['slots'])-len(rr),pv_steps=steps,by_budget=paired(out),limitations='One exposedRuleSet/64correlatedfullhistories,deep16everyfourth. Same allocated time or node budget within each pair, not equal completed depth. Node45s safetycensor distinct from desirednode budget. Actual total return includes research AST setup while PlayerDecision timer excludes its context-entry overhead; elapsed time is cooperative, not a hard end-to-end deadline. FreshTT/profiles and alternating order do not remove shared-machine timing uncertainty. No independent solver/holdout or strength claim.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);a=p.parse_args();print(json.dumps(assess(a.directory),indent=2))
