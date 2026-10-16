from collections import Counter
import json
from pathlib import Path
from results.dev_aux.task2030.campaign import scheduled_slots

def test_full_fixed_counterbalanced_schedule():
 p=json.loads(Path('results/dev_aux/task2030/run-plan.json').read_text(encoding='utf-8'));slots=list(scheduled_slots(p,[],None,lambda:False))
 assert len(slots)==64 and len({(g['family'],g['candidate_side'],g['R'],g['N'])for g in slots})==64
 assert all(g['opponent_R']==720 and g['opponent_nodes']==4096 for g in slots)
 orders=[[g['profile_index']for g in slots if g['family']==f][::2]for f in range(8)]
 for index in range(4):assert Counter(row[index]for row in orders)=={0:2,1:2,2:2,3:2}
 for profile in range(4):assert Counter([g['candidate_side']for g in slots if g['profile_index']==profile][::2])=={0:4,1:4}
 assert p['seconds_cap']==600 and p['expected_seconds']<600 and p['H']==96
