"""New conditional deployment histograms, no unweighted board recount output."""
from collections import Counter,deque
from fractions import Fraction as F
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.shogi_coordinate_distance_oracle import neighbors,variants,MODES
from scripts.shogi_complete_board_intervals import moment
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/shogi_exact_held_reweight_20261005.json'
SOURCES=('scripts/audit_shogi_exact_held_reweight.py','docs/research/SHOGI_EXACT_HELD_REWEIGHT_PROTOCOL.md',
 'scripts/shogi_coordinate_distance_oracle.py','docs/research/data/shogi_coordinate_comparison_20261005.json',
 'docs/research/data/shogi_random_deployment_20261005.json','scripts/shogi_complete_board_intervals.py')
TYPES=('P','L','N','S','G','B','R')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen exact held conditional law')
    start=monotonic();r=dict(complete=False,public_transitions=0,source_queries=0,blockers_completed=0,empty_drop_frames=0,
       source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec conditional reweight cap')
    qualified=json.loads((ROOT/SOURCES[3]).read_text())
    if not qualified['complete']:raise ValueError('independent board law qualification required')
    buckets={mode:Counter() for mode in TYPES};index={mode:i for i,mode in enumerate(MODES)}
    for blocker in range(81):
        check();reverse=[[] for _ in range(729)]
        for mode in MODES:
            for source in range(81):
                if source==blocker:continue
                parent=index[mode]*81+source
                for target in neighbors(mode,source,blocker,0):
                    for current in variants(mode,source,target,0):reverse[index[current]*81+target].append(parent)
        for target in range(81):
            if target==blocker:continue
            distances=[-1]*729;queue=deque()
            for i in range(9):node=i*81+target;distances[node]=0;queue.append(node)
            while queue:
                child=queue.popleft()
                for parent in reverse[child]:
                    if distances[parent]<0:distances[parent]=distances[child]+1;queue.append(parent)
            for mode in TYPES:
                cases=((False,6),(True,1)) if mode=='P' else ((False,7),)
                for nifu,weight in cases:
                    eligible=[s for s in range(81) if s not in (target,blocker) and
                        (s//9<8 if mode in ('P','L') else s//9<7 if mode=='N' else True) and
                        (not nifu or s%9!=blocker%9)]
                    size=len(eligible)
                    if not size:r['empty_drop_frames']+=weight;continue
                    for source in eligible:
                        distance=distances[index[mode]*81+source]
                        buckets[mode][(0 if distance<0 else distance+1,size)]+=weight
        r['blockers_completed']=blocker+1
    r['rows']=[]
    old=json.loads((ROOT/SOURCES[4]).read_text());old={row['type']:row for row in old['rows']}
    for mode in TYPES:
        masses={}
        for (time,size),count in buckets[mode].items():masses[time]=masses.get(time,F(0))+F(count,size)/(81*80*7)
        if sum(masses.values())!=1:raise ValueError('conditional world mass lost')
        if (masses[2],masses[3],masses.get(0,F(0)))!=tuple(F(old[mode]['masses'][k]) for k in ('direct','second','zero')):
            raise ValueError('old conditional prefix/zero mismatch')
        means={law:sum(mass*moment(law,time) for time,mass in masses.items() if time) for law in ('geometric_half','linear_mixture')}
        if any(not F(old[mode]['bounds'][law][0])<=value<=F(old[mode]['bounds'][law][1]) for law,value in means.items()):
            raise ValueError('exact held mean outside old envelope')
        r['rows'].append(dict(type=mode,masses=dict(sorted(masses.items())),means=means,buckets={str(key):value for key,value in buckets[mode].items()}))
    r['complete']=r['blockers_completed']==81 and len(r['rows'])==7 and r['empty_drop_frames']==0
    r['seconds']=monotonic()-start
    r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('source_sha256','rows')}))
