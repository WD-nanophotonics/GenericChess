"""One frozen arithmetic Gold2 frontier, no engine producer."""
import hashlib
import json
from pathlib import Path
import sys
from time import monotonic
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.gold_two_frontier import gold_two_counts,gold_partial_interval

OUT=ROOT/'docs/research/data/gold_two_frontier_20261005.json'
SOURCES=('scripts/audit_gold_two_frontier.py','scripts/gold_two_frontier.py',
         'scripts/shogi_direct_mode_bounds.py','docs/research/SHOGI_GOLD_TWO_ACTION_DESIGN.md',
         'generic_chess/core/semantic_executor.py')

if __name__=='__main__':
    if OUT.exists():
        raise FileExistsError('frozen arithmetic report never rerun')
    start=monotonic()
    pins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}
    r=dict(complete=False,source_sha256=pins,public_transitions=0,goal_queries=0)
    try:
        r.update(gold_two_counts())
        r['raw_intervals']={m:[str(v) for v in gold_partial_interval(m)] for m in ('geometric_half','linear_mixture')}
        r['seconds']=monotonic()-start
        if r['seconds']>=15:
            raise TimeoutError('15sec arithmetic cap')
        r['complete']=True
    except Exception as e:
        r['error']=f'{type(e).__name__}: {e}'
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in pins.items())
    OUT.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(r))
