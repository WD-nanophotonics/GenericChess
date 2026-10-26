"""Read saved single-span observations without new Player calls."""
from pathlib import Path
import json,statistics,argparse
from collections import defaultdict
from scripts.leaper_cost_profile_trial import signature
from scripts.verify_leaper_cost_profile import saved_returns
from scripts.research_record import write_record
def analyze(folder):
 rows=saved_returns(folder);groups=defaultdict(dict)
 for r in rows:
  assert r['arm'] not in groups[r['case_id']],'duplicate arm'
  groups[r['case_id']][r['arm']]=r
 result=[]
 for case,arms in sorted(groups.items()):
  if set(arms)!={'before','push_span','after'}:continue
  b,o,a=[arms[k] for k in ('before','push_span','after')]
  m=o['observed_push']
  assert m['calls']-m['exceptions']==o['decision']['runtime_pushes'],'successful push count mismatch'
  assert m['active']==0 and m['nested_calls']==0
  assert 0<=m['seconds']<=o['choose_seconds']
  complete=all(r['decision']['completed_depth']==8 for r in (b,o,a))
  parity=signature(b['decision'])==signature(o['decision'])==signature(a['decision'])
  result.append({'case_id':case,'complete':complete,'exact_nontiming_parity':parity,'before_seconds':b['choose_seconds'],'observer_seconds':o['choose_seconds'],'after_seconds':a['choose_seconds'],'observer_vs_bracket_ratio':o['choose_seconds']/statistics.mean((b['choose_seconds'],a['choose_seconds'])),'after_before_ratio':a['choose_seconds']/b['choose_seconds'],'observed_push_seconds':m['seconds'],'observed_push_fraction_of_instrumented_choose':m['seconds']/o['choose_seconds'],'push_attempts':m['calls'],'push_exceptions':m['exceptions'],'successful_pushes':o['decision']['runtime_pushes']})
 good=[r for r in result if r['complete'] and r['exact_nontiming_parity']]
 return {'raw_returns':len(rows),'captured_trios':len(result),'eligible_trios':len(good),'incomplete_trios':sum(not r['complete'] for r in result),'complete_parity_failures':sum(r['complete'] and not r['exact_nontiming_parity'] for r in result),'median_observer_vs_bracket_ratio':statistics.median(r['observer_vs_bracket_ratio'] for r in good) if good else None,'median_bracket_drift':statistics.median(r['after_before_ratio'] for r in good) if good else None,'eligible_observed_push_fraction':sum(r['observed_push_seconds'] for r in good)/sum(r['observer_seconds'] for r in good) if good else None,'rows':result,'limits':'Observed inclusive wrapper/push wall within instrumented choose; not unbiased uninstrumented share, Native internals, a removable fraction, speedup or strength. Truncated trios remain excluded without refill.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--folder',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=analyze(a.folder);write_record(a.output,r);print(json.dumps({k:v for k,v in r.items() if k!='rows'}))
