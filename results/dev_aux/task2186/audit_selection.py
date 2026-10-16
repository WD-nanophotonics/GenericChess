"""Post-study independent reconstruction of declared62-context selection.

DirectGitaddendum AFTER74capsule, not an original executed generator or part
of the85-test fresh restore receipt. No new proof/fitness query.
"""
from pathlib import Path
from collections import defaultdict
from scripts.generic_proof_rnb_bridge import orbit
import json,random,time
OUT=Path('results/dev_aux/task2186')
def run():
 start=time.perf_counter();labels=[json.loads(x)for x in Path('results/dev_aux/task2172/labels.jsonl').open(encoding='utf-8')];selected=[];seen=set();counts=defaultdict(int)
 for l in labels:
  raw=tuple(l['board'])
  if raw[-1]!=0 or l['status']!='ongoing'or l['label']=='DRAW'or raw in seen or counts[l['rank']]>=2:continue
  selected.append(l);seen.update(orbit(raw));counts[l['rank']]+=1
 for l in labels:
  raw=tuple(l['board'])
  if raw[-1]==0 and l['status']=='ongoing'and l['label']!='DRAW'and l['inventory']=='KKNn'and raw not in seen:selected.append(l);seen.update(orbit(raw))
 for mode in('KKBN','KKBb','KKBn','KKNn'):
  l=next(l for l in labels if l['board'][-1]==0 and l['status']=='ongoing'and l['label']=='DRAW'and l['inventory']==mode and tuple(l['board'])not in seen);selected.append(l);seen.update(orbit(tuple(l['board'])))
 random.Random(20261016742177).shuffle(selected);roots=json.loads(Path('results/dev_aux/task2177/inputs.json').read_text(encoding='utf-8'))['roots'];assert len(selected)==len(roots)==62
 for i,(a,b)in enumerate(zip(selected,roots)):
  assert b['family']==i and a['index']==b['original_label_index']and a['board']==b['root']and a['label']==b['label']and a['rank']==b['rank']and a['inventory']==b['inventory']and b['target']==(1 if a['label']=='LOSS'else 0)
 result=dict(status='PASS_EXACT62_DECLARED_RANK_ORBIT_SELECTION_RECONSTRUCTED',ranks=dict(counts),cases=62,positive=58,controls=4,seconds=time.perf_counter()-start,new_search_or_game_or_fit=0,scope='Aftersealedcapsule independentselectionaudit; doesnotpretendoriginalgeneratorfileexisted. Allinputsandoutcomesremainfrozen; label-stratifiedcapabilitybenchmarknotnaturalWDLpopulation.');(OUT/'selection-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':run()
