"""Larger-board fixed-price feasibility, allcases retained, no selector."""
from pathlib import Path
from collections import Counter
import json,hashlib,itertools
from results.dev_aux.task2028.physical_audit import audit,read,lines
from results.dev_aux.task1998.audit import ci
ROOT=Path('results/dev_aux/task2027');OUT=Path('results/dev_aux/task2028')
def run():
 p=read(ROOT/'run-plan.json');physical=audit(ROOT);rows=lines(ROOT/'games.jsonl')
 assert all(hashlib.sha256(Path(k).read_bytes()).hexdigest()==v for k,v in p['source_sha'].items())
 assert len(p['slots'])==32 and {(g['family'],g['candidate_side'],g['B'])for g in p['slots']}==set(itertools.product(range(8),(0,1),(720,1440)))
 result=dict(status='PASS_6X6_FIXED_DIAGNOSTIC' if physical['full_study_complete'] else 'PARTIAL_6X6_FIXED_DIAGNOSTIC_RETAINED',physical=physical,outcomes={b:dict(Counter(g['outcome']for g in rows if g['B']==b))for b in (720,1440)},recorded_game_seconds=sum(g['seconds']for g in rows),scope='ALL8largerboardqualifiedroots, fixedB1vs2/bothroles/foeB1; no training/selectedprice/holdoutclaim. SamePN1K/normal4096/actualmax96, no4x4census. Exposedinputs excluded fromfuturefresh validation. Original600cap preserved; partialunknownunscored andno missingcell contrast.')
 result['declared_complete_expected_games']=32;result['unrun_frozen_games']=32-len(rows)
 if physical['full_study_complete']:
  assert len(rows)==32 and all(g['outcome']!='UNKNOWN' for g in rows)
  cells={(g['family'],g['candidate_side'],g['B']):g for g in rows}
  ds=[sum(cells[f,s,1440]['finite_event_score']-cells[f,s,720]['finite_event_score']for s in (0,1))/2 for f in range(8)]
  result['fixed_B2_vs_B1']=dict(mean=sum(ds)/8,family_deltas=ds,bootstrap8family_interval=ci(ds,20261016682028))
 with(OUT/'result.json').open('x',encoding='utf-8')as f:json.dump(result,f,indent=2)
 print(json.dumps({k:v for k,v in result.items()if k!='physical'}))
if __name__=='__main__':run()
