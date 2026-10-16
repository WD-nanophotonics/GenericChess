"""Frozen five-condition TRAIN selection, no validation outcome reads."""
from pathlib import Path
from collections import defaultdict,Counter
import json,hashlib
from results.dev_aux.task2153.stop_evidence import EvidenceStopReader
OUT=Path('results/dev_aux/task2357')
def run():
 EvidenceStopReader(Path.cwd())();a=json.loads(Path('results/dev_aux/task2359/result.json').read_text());assert a['status'].startswith('PASS');games=json.loads(Path('results/dev_aux/task2358/matrix-games.json').read_text());by=defaultdict(list)
 for g in games:by[g['ratio']].append(g)
 grid=[.5,1.,1.5,2.,3.];complete=len(games)==160 and all(len(by[p])==32 and all(g['reward']is not None for g in by[p])for p in grid);scores={str(p):sum(g['reward']for g in by[p])/32 if complete else None for p in grid};selected=None
 if complete:
  best=max(scores.values());selected=1. if best<=scores['1.0']else min(p for p in grid if scores[str(p)]==best)
 result=dict(status='TRAIN_SELECTION_COMPLETE'if complete else'NO_SELECTION_INCOMPLETE_TRAIN',candidate_grid=grid,scores=scores,selected_price=selected,strict_improvement_accepted=selected is not None and selected!=1.,matrix_games=len(games),outcomes={str(p):dict(Counter(g['outcome']for g in by[p]))for p in grid},reserved_input_sha=hashlib.sha256(Path('results/dev_aux/task2341/inputs.json').read_bytes()).hexdigest(),scope='New82actual-WL TRAIN160matrix with65explicitreusedterminals+95newslots. Old2340 stayspartial, noU/missingasdraw, strictgain/tieprefersbaseline1thenlowerprice. Fiveprior79material-orderconditions underlimitedinventory; notuniqueintrinsic/globalvalue orwalllimitedpolicy-classproof. No DEV/reserveperformanceread/defaultchange.')
 with(OUT/'selection.json').open('x')as f:json.dump(result,f,indent=2)
 if selected is not None and selected!=1.:
  future=dict(status='RESERVED_NOT_EXECUTED',baseline=1.,candidate=selected,inputs='results/dev_aux/task2341/inputs.json',inputs_sha=result['reserved_input_sha'],foes=[1.5,4.],roles=[0,1],planned_games=128,forecast_seconds=2300,cap_seconds=3300,selection_sha=hashlib.sha256((OUT/'selection.json').read_bytes()).hexdigest(),scope='FixedTRAINwinnerfuturevalidation, no newfit/DEVpricechoice; condition onexposedreference/initialfamilyorbits only.')
  with(OUT/'reserved-validation.json').open('x')as f:json.dump(future,f,indent=2)
 print(json.dumps(result))
if __name__=='__main__':run()
