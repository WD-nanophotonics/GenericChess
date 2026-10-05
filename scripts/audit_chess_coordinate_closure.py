"""Independent native five-mode comparison; preserve failed final Pawn flag."""
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.chess_coordinate_distance_oracle import coordinate_histograms
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/chess_coordinate_closure_20261005.json'
SOURCES=('scripts/audit_chess_coordinate_closure.py','scripts/chess_coordinate_distance_oracle.py',
 'docs/research/CHESS_FULL_DISTANCE_QUALIFICATION_SCOPE.md','docs/research/data/chess_full_nonpawn_distance_20261005.json',
 'docs/research/data/chess_full_pawn_distance_20261005.json','docs/research/data/chess_pawn_third_prefix_20261005.json')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen independent five-mode qualification')
    start=monotonic();a,b,old=[json.loads((ROOT/p).read_text()) for p in SOURCES[-3:]]
    prior=a['seconds']+b['seconds'];r=dict(complete=False,public_transitions=0,source_queries=0,blockers_completed=0,
       source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start+prior>=15:raise TimeoutError('same15sec full census/qualification cap')
    try:
        for blocker,rows in coordinate_histograms(check):
            r['blockers_completed']=blocker+1;r['rows']=rows;write_record(OUT,r)
        compiled={row['profile']['current']:row for row in a['rows']};compiled['P']=b
        norm=lambda hist:{int(t):n for t,n in hist.items()}
        r['all_histograms_match']=all(norm(rows[mode]['histogram'])==norm(row['histogram']) and rows[mode]['unreachable']==row['unreachable'] for mode,row in compiled.items())
        r['pawn_inferred_zero']=249984-old['direct']-old['second']-old['third']-old['unknown_nonzero']
        r['complete']=a['complete'] and len(b['slabs'])==64 and r['all_histograms_match'] and r['pawn_inferred_zero']==rows['P']['unreachable']
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['cumulative_seconds']=r['seconds']+prior
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','rows')}))
