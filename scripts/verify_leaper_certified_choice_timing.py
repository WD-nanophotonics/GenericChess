"""Data-only acceptance of certificate-tier completed-iteration observations."""
from pathlib import Path
import json,hashlib
from scripts import leaper_design as L
from scripts.leaper_delayed_capture_witness import replay
from generic_chess.ai.alphabeta.tuning import SearchTuning
from generic_chess.ai.limits import SearchLimits
from tools.local_agent.common import write_json

def rows(p):return [json.loads(x)for x in p.read_text().splitlines()]
def classification(case,action):
 labels=[a for a in case['action_labels']if a['action']==action]
 assert len(labels)<=1
 if not labels:return dict(known=False,own_WDL=None,goal_met=None,tier=case['label_tier'])
 value=labels[0]['own_WDL'];return dict(known=True,own_WDL=value,goal_met=value>=0 if case['goal']=='certified_nonloss'else value==case['root_own_WDL'],tier=case['label_tier'])
def assess(d):
 plan=L.load(d/'plan.json');data=L.load(d/'inputs.json');assert hashlib.sha256((d/'inputs.json').read_bytes()).hexdigest()==plan['inputs_sha256'];cases={x['key']:x for x in data['cases']};result=[];pvsteps=0;expected=L.record_value(SearchTuning(use_pvs=True,use_ordered_qsearch=False,use_ordered_qsearch_in_check=False))
 for phase in('qualification','measurement'):
  rr=rows(d/(phase+'-queries.jsonl'));receipt=L.load(d/(phase+'-receipt.json'));assert receipt['status']=='CLOSED'and receipt['queries']==len(rr)==len(plan[phase]);assert [r['slot']for r in rr]==plan[phase]
  for r in rr:
   case=cases[r['slot']['case']];c=L.compile_rule(L.ruleset_from_dict(case['rule']));root=replay(c,case['record']);assert L.record_value(root.to_record())==r['before_record']==case['record'];assert root.state.position.side_to_move==case['root_actor'];assert r['tuning']==expected and r['use_ordering'];limits=SearchLimits(max_depth=plan['qualification_depth']if phase=='qualification'else 8,max_nodes=200000,max_time_seconds=15 if phase=='qualification'else 30);assert r['limits']==L.record_value(limits);dec=r['decision'];assert dec['runtime_pushes']==dec['runtime_pops'];assert r['final_label']==classification(case,dec['action'])
   for group in r['provider_delta'].values():assert all(x>=0 for x in group.values())
   a,b=r['provider_delta']['availability'],r['provider_delta']['check'];assert a.get('declines',0)==0 and a.get('imports',0)+a.get('reused_imports',0)==a.get('queries',0)and b.get('imports',0)==b.get('queries',0)
   L.match_action(root,dec['action']);s=replay(c,case['record'])
   for raw in dec['principal_variation']:s.submit(L.match_action(s,raw));pvsteps+=1
   events=r['iterations'];assert bool(events)or not r['slot']['observed']or dec['result_source']!='main_iteration';lasttime=0.;lastwork=0
   for i,e in enumerate(events,1):
    assert e['depth']==i and e['source']=='completed_main_iteration';assert lasttime<=e['seconds']<=r['seconds']+.001 and lastwork<=e['nodes']+e['qnodes'];lasttime=e['seconds'];lastwork=e['nodes']+e['qnodes'];assert e['label']==classification(case,e['action']);L.match_action(root,e['action']);s=replay(c,case['record'])
    for raw in e['pv']:s.submit(L.match_action(s,raw));pvsteps+=1
   if r['slot']['observed']and dec['result_source']=='main_iteration':assert events[-1]['depth']==dec['completed_depth']and events[-1]['action']==dec['action']and events[-1]['score']==dec['score']
   if phase=='measurement':
    goals=[e for e in events if e['label']['goal_met']is True];first=goals[0]if goals else None;later=[e for e in events if first and e['depth']>first['depth']]
    result.append(dict(case=case['key'],tier=case['label_tier'],goal=case['goal'],seconds=r['seconds'],final_source=dec['result_source'],final_depth=dec['completed_depth'],final_label=r['final_label'],first_supported_completed_choice_seconds=first['seconds']if first else None,first_supported_depth=first['depth']if first else None,later_known_goal_failure_depths=[e['depth']for e in later if e['label']['goal_met']is False],later_unknown_depths=[e['depth']for e in later if e['label']['goal_met']is None],final_only_goal_time_upper_bound=r['seconds']if not first and r['final_label']['goal_met']is True else None,trajectory=[dict(depth=e['depth'],seconds=e['seconds'],score=e['score'],label=e['label'],action=e['action'])for e in events]))
  if phase=='qualification':
   for a,b in zip(rr[::2],rr[1::2]):
    fields=L.load(d/'qualification-assessment.json')['fields'];assert all(a['decision'][f]==b['decision'][f]for f in fields)and a['provider_delta']==b['provider_delta'];assert a['decision']['completed_depth']==b['decision']['completed_depth']==plan['qualification_depth']
 return dict(passed=True,records_read=sum(len(plan[x])for x in('qualification','measurement')),new_player_queries=len(plan['measurement'])if'qualification_reuse'in plan else sum(len(plan[x])for x in('qualification','measurement')),reused_qualification_records=len(plan['qualification'])if'qualification_reuse'in plan else 0,pv_steps=pvsteps,cases=result,scope='Input-declared named-action certificate or attributed original-graph WDL tier; source graph is never upgraded to independent proof. Not complete four-root action labels/holdout. Unknown alternatives neither right nor wrong. First timestamp is first RECORDED completed-iteration goal-supported choice in its declared label tier, includes setup/observer perturbation, not earliest internal correct candidate or monotonic convergence. Root immediate/fallback final-only time is upper bound, not synthetic iteration0. No new search/solver calls.')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();r=assess(a.directory);write_json(a.directory/'assessment.json',r);print({k:v for k,v in r.items()if k!='cases'});print([{k:v for k,v in x.items()if k!='trajectory'}for x in r['cases']])
