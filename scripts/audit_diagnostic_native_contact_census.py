"""One full optimistic diagnostic population within the existing small cap."""
from collections import Counter
from dataclasses import asdict
from fractions import Fraction as F
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.xiangqi_diagnostic import build_xiangqi_diagnostic_ruleset
from scripts.shared_contact_prefix import Profile
from scripts.native_cube_contact_qualified import QualifiedNativeCubeKernel
from scripts.native_cube_contact_closure import cube_contact_census
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/diagnostic_native_contact_census_20261005.json'
CACHE=ROOT/'docs/research/data/diagnostic_native_contact_kernel_20261005.json'
SOURCES=('scripts/audit_diagnostic_native_contact_census.py','docs/research/DIAGNOSTIC_NATIVE_CONTACT_CENSUS_PROTOCOL.md','scripts/native_cube_contact_qualified.py','scripts/native_cube_contact_closure.py','scripts/typed_sparse_contact_cubes.py','scripts/sparse_contact_cubes.py','scripts/intrinsic_action_events.py','scripts/intrinsic_occupancy_cubes.py','generic_chess/rules/xiangqi_diagnostic.py','docs/research/data/native_cube_contact_qualified_20261005.json','docs/research/data/sparse_contact_cube_controls_20261005.json')
if __name__=='__main__':
    if OUT.exists() or CACHE.exists():raise FileExistsError('full diagnostic construction never rerun')
    start=monotonic();r=dict(complete=False,rows=[],completed_target_slabs=[],public_transitions=0,virtual_materializations=0,source_queries=0,enumerated=0,human_reference_imported=False,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec complete diagnostic study')
    write_record(OUT,r)
    try:
        c=compile_ruleset_for_execution(build_xiangqi_diagnostic_ruleset());profiles=tuple(Profile(t,t) for t in ('A','C','E','H','R','S'))
        kernel=QualifiedNativeCubeKernel(c,profiles,owner=0,checkpoint=check);r['preprocessing']=kernel.stats
        if kernel.stats['canonical_candidates']>5000:raise ValueError('canonical cap')
        metadata_checks=0
        for pattern in c.ir.patterns:
            if not set(pattern.type_ids)&{p.current for p in profiles}:continue
            for gid in pattern.geometry_ids:
                g=c.ir.geometry[gid]
                if g.kind=='drop':continue
                if not g.owner_relative:raise ValueError('unqualified absolute geometry reflection')
                for source in range(90):
                    if tuple(g.paths.get('1',{}).get(source,()))!=tuple(89-d for d in g.paths.get('0',{}).get(89-source,())):raise ValueError('geometry owner reflection fails')
                    metadata_checks+=1
            if any(not guard.owner_relative for guard in pattern.square_zone_guards):raise ValueError('unqualified absolute zone reflection')
            for guard in pattern.guards:
                if any(not ref.owner_relative for ref in guard.spatial.refs):raise ValueError('unqualified absolute occupancy reflection')
        r['owner_reflection_geometry_checks']=metadata_checks
        snapshot=dict(area=kernel.area,profiles=[asdict(p) for p in profiles],stats=kernel.stats,
            quiet=[dict(profile=asdict(p),source=s,destination=u,next_profile=asdict(q),cubes=cubes) for (p,s),actions in kernel.quiet.items() for (u,q),cubes in actions.items()],
            capture=[dict(profile=asdict(p),source=s,target=d,cubes=cubes) for (p,s),actions in kernel.capture.items() for d,cubes in actions.items()])
        write_record(CACHE,snapshot);r['source_sha256'][str(CACHE.relative_to(ROOT)).replace('\\','/')]=hashlib.sha256(CACHE.read_bytes()).hexdigest();write_record(OUT,r)
        bins={p:Counter() for p in profiles};target0={p:hashlib.sha256() for p in profiles};observed=0
        def observe(target,blocker,p,source,distance):
            nonlocal_placeholder=None
            bins[p][distance]+=1
            if target==0:target0[p].update(f'{blocker},{source}:{distance};'.encode())
            if p==profiles[-1] and blocker==max(q for q in range(90) if q!=target) and source==max(q for q in range(90) if q not in (target,blocker)):
                check();r['completed_target_slabs'].append(dict(target=target,rows=[dict(profile=asdict(q),counts=dict(sorted(bins[q].items()))) for q in profiles]))
                for q in profiles:bins[q].clear()
                write_record(OUT,r)
        result=cube_contact_census(kernel,world_observer=observe)
        check();r['rows']=[dict(profile=asdict(p),**result['rows'][p],target0_ordered_sha256=target0[p].hexdigest()) for p in profiles]
        if len(r['completed_target_slabs'])!=90 or result['worlds']!=6*704880:raise ValueError('full world coverage mismatch')
        r['normalized_by_law']={}
        for law in ('geometric_half','linear_mixture'):
            means={p.current:result['rows'][p]['means'][law] for p in profiles};maximum=max(means.values())
            if maximum<=0:raise ValueError('no positive common scale')
            r['normalized_by_law'][law]=dict(maximum_types=sorted(t for t,v in means.items() if v==maximum),scale=maximum,weights={t:v/maximum for t,v in means.items()})
        r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','completed_target_slabs','normalized_by_law','source_sha256')}))
