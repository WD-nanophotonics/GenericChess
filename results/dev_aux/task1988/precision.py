"""Posthoc precision diagnostic between two pre-locked profitable prices."""
from pathlib import Path
from collections import Counter
import json
from results.dev_aux.task1988.audit import interval
OUT=Path('results/dev_aux/task1988')
def run():
 rows=[json.loads(x) for x in Path('results/dev_aux/task1987/games.jsonl').read_text().splitlines()]
 c={(g['family'],g['candidate_side'],g['R'],g['opponent_R']):g for g in rows}
 ds=[sum(c[f,s,1260,o]['finite_event_score']-c[f,s,2160,o]['finite_event_score'] for s in (0,1) for o in (360,720,1440,2880))/8 for f in range(32)]
 transitions=Counter((c[f,s,2160,o]['outcome'],c[f,s,1260,o]['outcome']) for f in range(32) for s in (0,1) for o in (360,720,1440,2880))
 result=dict(status='POSTHOC_PRECISION_DESCRIPTION_NOT_NEW_PRIMARY_TEST',prices=[1.75,3.0],mean=sum(ds)/32,bootstrap32family_interval=interval(ds,20261016661994),family_deltas=ds,outcome_transitions={a+'->'+b:n for (a,b),n in transitions.items()},scope='Bothprices frozen fromTRAINbefore freshinputs. This usesSAMEalreadyreported32DEVfamilies; notextra confirmation/training runs/preciseprice recovery. Reportallcases andbothCI limits; no candidate picked from this description.')
 with (OUT/'precision-diagnostic.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items() if k!='family_deltas'}))
if __name__=='__main__':run()
