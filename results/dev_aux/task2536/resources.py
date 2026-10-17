from pathlib import Path
from collections import Counter
import json
T=Path('results/dev_aux/task2534');E=Path('results/dev_aux/task2535');O=Path('results/dev_aux/task2536')
def run():
 train=json.loads((T/'result.json').read_text());ev=json.loads((E/'result.json').read_text());query=Counter();failed=[];endings=Counter();episodes=Counter()
 for line in(T/'queries.jsonl').open():
  q=json.loads(line);query['queries']+=1;query['nodes']+=q['nodes'];query['commits']+=q['complete']
  if not q['complete']:failed.append({k:q[k]for k in('generator_seed','method','seed','game','ply','nodes','effective_node_limit','effective_wall_limit','reason')})
 for line in(T/'episodes.jsonl').open():
  e=json.loads(line);endings[e['ending']]+=1;episodes[e['method']]+=1
 assert query['nodes']==train['nodes']and query['queries']==train['counters']['queries']
 vq=Counter()
 for line in(E/'queries.jsonl').open():
  q=json.loads(line);vq['queries']+=1;vq['nodes']+=q['nodes'];vq['failed']+=not q['complete']
 assert vq['nodes']==ev['nodes']and vq['queries']==ev['queries']
 r=dict(status='PASS_ACTUAL_WORK_AND_ALL_UNKNOWN_ENDINGS',train=dict(query),evaluation=dict(vq),producer_nodes=train['nodes']+ev['nodes'],producer_seconds=train['seconds']+ev['seconds'],training_endings=dict(endings),training_episodes_by_method=dict(episodes),training_failed_queries=failed,expected_validation=ev['expected'],returned_validation=ev['actual'],missing_validation=ev['missing'],scope='Producerwallincludesownsearch/records/stops/replay/logging. NotCPU/wholeengineering/test/audit/transport/tokencost; TRAINperquery/perarmwallsecondsnotjournaled; no per-armwallspeedclaim. Failedlastsmallnodepool distinctfromordinary4096queryfaults; no outcomeimputation/retry/capreset. Actualconcurrentloadnotcontrolledtimingcomparison.')
 (O/'resources.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
if __name__=='__main__':run()
