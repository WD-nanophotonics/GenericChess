"""Recompute cost reference using OLD TRAIN observations/costs only."""
from pathlib import Path
import json,hashlib
R=Path('results/dev_aux')
def run():
 d=R/'task2546';n=sum(a['nodes']for a in json.loads((d/'result.json').read_text())['arms']if a['method']=='TreeStrap');k=sum(q['method']=='TreeStrap'and q['observed']for q in map(json.loads,(d/'queries.jsonl').open()));old=json.loads((R/'task2558/reference-check.json').read_text());assert n==old['nodes']==3200000 and k==old['observations']==27795 and hashlib.sha256((d/'queries.jsonl').read_bytes()).hexdigest()==old['source_queries_sha']
 p=json.loads((R/'task2558/plan.json').read_text());assert p['clock_reference']['nodes']==n and p['clock_reference']['observations']==k
 out=dict(status='PASS_TRAIN_ONLY_REFERENCE_RECOUNT',nodes=n,observations=k,source_sha=old['source_queries_sha'],no_DEV_scores=True);(R/'task2560/reference.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
if __name__=='__main__':run()
