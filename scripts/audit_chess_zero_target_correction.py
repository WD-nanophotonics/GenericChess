"""Only previously misclassified target index0, not a repeated full census."""
from collections import Counter,deque
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.chess_coordinate_distance_oracle import moves,MODES
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/chess_zero_target_correction_20261005.json'
SOURCES=('scripts/audit_chess_zero_target_correction.py','docs/research/CHESS_ZERO_TARGET_ORACLE_CORRECTION.md',
 'scripts/chess_coordinate_distance_oracle.py','docs/research/data/chess_coordinate_closure_20261005.json',
 'docs/research/data/chess_full_nonpawn_distance_20261005.json','docs/research/data/chess_full_pawn_distance_20261005.json')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen zero-target qualification')
    start=monotonic();old=json.loads((ROOT/SOURCES[3]).read_text());index={m:i for i,m in enumerate(MODES)}
    r=dict(complete=False,public_transitions=0,source_queries=0,target=0,rows={},
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    hist={mode:Counter() for mode in MODES};zeros={mode:0 for mode in MODES}
    for blocker in range(1,64):
        if monotonic()-start+old['cumulative_seconds']>=15:raise TimeoutError('same15sec qualification cap')
        reverse=[[] for _ in range(320)];distances=[-1]*320;queue=deque()
        for mode in MODES:
            for source in range(1,64):
                if source==blocker:continue
                parent=index[mode]*64+source
                if any(True for _ in moves(mode,source,blocker,0,capture=True)):distances[parent]=1;queue.append(parent)
                for destination in moves(mode,source,blocker,0):
                    currents=('N','B','R','Q') if mode=='P' and destination//8==7 else (mode,)
                    for current in currents:reverse[index[current]*64+destination].append(parent)
        while queue:
            child=queue.popleft()
            for parent in reverse[child]:
                if distances[parent]<0:distances[parent]=distances[child]+1;queue.append(parent)
        for mode in MODES:
            for source in range(1,64):
                if source==blocker:continue
                value=distances[index[mode]*64+source]
                if value<0:zeros[mode]+=1
                else:hist[mode][value]+=1
    a,b=[json.loads((ROOT/p).read_text()) for p in SOURCES[-2:]]
    compiled={row['profile']['current']:row for row in a['rows']};compiled['P']=b
    norm=lambda values:{int(t):n for t,n in values.items()}
    for mode in MODES:
        corrected=Counter(norm(old['rows'][mode]['histogram']));corrected.update(hist[mode])
        unreachable=old['rows'][mode]['unreachable']-3906+zeros[mode]
        r['rows'][mode]=dict(histogram=dict(sorted(corrected.items())),unreachable=unreachable,
            target0_histogram=dict(hist[mode]),target0_unreachable=zeros[mode],
            match=dict(corrected)==norm(compiled[mode]['histogram']) and unreachable==compiled[mode]['unreachable'])
    r['complete']=old['blockers_completed']==64 and all(row['match'] and sum(row['histogram'].values())+row['unreachable']==249984 for row in r['rows'].values())
    r['seconds']=monotonic()-start;r['cumulative_seconds']=r['seconds']+old['cumulative_seconds']
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','rows')}))
