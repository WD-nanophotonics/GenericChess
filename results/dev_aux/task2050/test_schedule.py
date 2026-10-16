import json
from pathlib import Path
from collections import Counter
from results.dev_aux.task2050.campaign import scheduled_slots
def test_fixed_opponent_and_candidate_only_balanced_schedule():
 p=json.loads(Path('results/dev_aux/task2050/run-plan.json').read_text(encoding='utf-8'));slots=list(scheduled_slots(p,[],None,lambda:False))
 assert len(slots)==32 and len({(s['family'],s['candidate_side'],s['candidate_filter']) for s in slots})==32
 assert all(s['B']==s['opponent_B']==s['N']==720 and s['opponent_R']==1260 and s['candidate_cached'] for s in slots)
 assert p['opponent_filter']is False and p['seconds_cap']==750 and p['expected_seconds']<750
 assert Counter([s['candidate_filter']for s in slots][::4])=={False:4,True:4}
 assert Counter([s['candidate_side']for s in slots][::4])=={0:4,1:4}
