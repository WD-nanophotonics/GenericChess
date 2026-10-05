"""Independent reverse-coordinate qualification within the original census cap."""
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.shogi_coordinate_distance_oracle import coordinate_histograms,neighbors,variants,MODES
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/shogi_coordinate_closure_20261005.json'
SOURCES=('scripts/audit_shogi_coordinate_closure.py','scripts/shogi_coordinate_distance_oracle.py',
 'docs/research/SHOGI_FULL_CONTACT_DISTANCE_PROTOCOL.md','docs/research/data/shogi_full_contact_distance_20261005.json')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen independent coordinate qualification')
    start=monotonic();compiled=json.loads((ROOT/SOURCES[3]).read_text())
    r=dict(complete=False,public_transitions=0,source_queries=0,blockers_completed=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start+compiled['seconds']>=15:raise TimeoutError('same15sec census/qualification cap')
    try:
        for blocker,rows in coordinate_histograms(check):
            r['blockers_completed']=blocker+1;r['rows']=rows
            write_record(OUT,r)
        by_current={row['profile']['current']:row for row in compiled['rows']}
        if not compiled['complete']:raise ValueError('compiled census incomplete')
        r['all_histograms_match']=all(rows[mode]['histogram']==by_current[mode]['histogram'] and rows[mode]['unreachable']==by_current[mode]['unreachable'] for mode in MODES)
        r['owner_reflection_checked']=0
        for mode in MODES:
            for source in range(81):
                check()
                for blocker in range(81):
                    if source==blocker:continue
                    if set(neighbors(mode,source,blocker,1))!={80-t for t in neighbors(mode,80-source,80-blocker,0)}:
                        raise ValueError('owner coordinate reflection mismatch')
                    r['owner_reflection_checked']+=1
        r['complete']=r['all_histograms_match'] and r['owner_reflection_checked']==58320
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['cumulative_seconds']=r['seconds']+compiled['seconds']
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','rows')}))
