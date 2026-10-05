"""Six frozen pure cached-proof computations; never reapply public actions."""
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.saved_contact_proof_graph import SavedContactProofGraph
from scripts.public_goal_intervals import observe
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/saved_goal_order_ablation_20261005.json'
SOURCES=('scripts/audit_saved_goal_order_ablation.py','scripts/saved_contact_proof_graph.py',
 'docs/research/SAVED_GOAL_ORDER_ABLATION_PROTOCOL.md','scripts/public_goal_intervals.py',
 'docs/research/data/chess_pinned_queen_mate_20261005.json',
 'docs/research/data/chess_pinned_queen_continuation_20261005.json',
 'docs/research/data/contact_depth2_dominance_20261005.json')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen saved-graph ablation')
    start=monotonic();r=dict(complete=False,public_transitions=0,source_queries=0,rows=[],
       source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    inputs=[json.loads((ROOT/p).read_text()) for p in SOURCES[-3:]]
    try:
        for depth in (2,3):
            for method in ('contact','unit','zero'):
                if monotonic()-start>=15:raise TimeoutError('15sec total arithmetic cap')
                graph=SavedContactProofGraph(*inputs,method)
                observation=observe((),graph,depth=depth,max_transitions=64,max_visits=256,seconds=15-(monotonic()-start))
                r['rows'].append(dict(method=method,depth=depth,root_order=graph.root_order,
                    saved_states=len(graph.states),saved_expansions=len(graph.full_actions),observation=observation))
                write_record(OUT,r)
        r['complete']=len(r['rows'])==6
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r)
    print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','rows')}))
    print(json.dumps([{k:v for k,v in row.items() if k not in ('root_order',)} for row in r['rows']]))
