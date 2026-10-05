"""Read two complete numerical censuses; fix integer/string key comparison only."""
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.shogi_coordinate_distance_oracle import variants,MODES
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/shogi_coordinate_comparison_20261005.json'
SOURCES=('scripts/audit_shogi_coordinate_comparison.py','docs/research/SHOGI_COORDINATE_COMPARISON_CORRECTION.md',
 'docs/research/data/shogi_full_contact_distance_20261005.json','docs/research/data/shogi_coordinate_closure_20261005.json',
 'scripts/shogi_coordinate_distance_oracle.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen corrected comparison')
    start=monotonic();a=json.loads((ROOT/SOURCES[2]).read_text());b=json.loads((ROOT/SOURCES[3]).read_text())
    r=dict(complete=False,public_transitions=0,source_queries=0,rows=[],
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    if not a['complete'] or b['blockers_completed']!=81 or b['owner_reflection_checked']!=58320:
        raise ValueError('complete saved numerical/movement evidence required')
    for row in a['rows']:
        current=row['profile']['current'];coordinate=b['rows']['G' if current in ('TP','TL','TN','TS') else current]
        norm=lambda hist:{int(t):n for t,n in hist.items()}
        match=norm(row['histogram'])==norm(coordinate['histogram']) and row['unreachable']==coordinate['unreachable']
        r['rows'].append(dict(current=current,match=match,total=sum(coordinate['histogram'].values())+coordinate['unreachable']))
    r['promotion_reflection_controls']=0
    for mode in MODES:
        for source in range(81):
            if monotonic()-start+b['cumulative_seconds']>=15:raise TimeoutError('same15sec qualification cap')
            for target in range(81):
                if source==target:continue
                if set(variants(mode,source,target,1))!=set(variants(mode,80-source,80-target,0)):
                    raise ValueError('promotion reflection mismatch')
                r['promotion_reflection_controls']+=1
    r['complete']=len(r['rows'])==13 and all(row['match'] and row['total']==511920 for row in r['rows'])
    r['seconds']=monotonic()-start;r['cumulative_seconds']=r['seconds']+b['cumulative_seconds']
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k!='source_sha256'}))
