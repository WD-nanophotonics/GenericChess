import json
from results.dev_aux.task2136.test_legal_fallback import observed,player
from results.dev_aux.task2136.legal_fallback import LegalFallbackPhasePlayer
from results.dev_aux.task2139.receipt import decision_receipt
from pathlib import Path

def test_cancelled_and_budget_fallback_receipts_are_json_and_full_replay_bound():
 c,s=observed();p=json.loads(Path('results/dev_aux/task2139/plan.json').read_text(encoding='utf-8'))
 for cancel in (None,lambda:True):
  d=player(LegalFallbackPhasePlayer,c).choose(s,max_nodes=64,seconds=.75,cancel=cancel)
  r=decision_receipt(s,d,physical_id=0,logical_slot=0,ply=17,candidate=0,limits=p)
  assert json.loads(json.dumps(r))==r
  assert r['root_record']['actions'] and r['ruleset_fingerprint']==c.ruleset_fingerprint
  assert (r['choice'] is None)==(cancel is not None)
  assert r['requested_limits']['H']==96
