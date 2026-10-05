"""Changed compiled alive support; retain rejected count and reuse unchanged map."""
from collections import Counter
from dataclasses import asdict,replace
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.core.pieces import Piece
from generic_chess.core.transition import initial_state
from generic_chess.core.semantic_executor import semantic_engine_for
from generic_chess.rules.compiler import compile_ruleset_for_execution
from scripts.physical_promotion_contact_cubes import PhysicalPromotionContactCubes,ContactUnsupported
from scripts.promotion_mobility_micro import build,steps,distance
from scripts.shared_contact_prefix import Profile
from scripts.native_cube_contact_closure import cube_contact_census
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/promotion_mobility_gate_20261005.json'
SOURCES=('scripts/audit_promotion_mobility_gate.py','scripts/physical_promotion_contact_cubes.py','scripts/promotion_mobility_micro.py','docs/research/PROMOTION_MOBILITY_GATE_PROTOCOL.md','docs/research/data/promotable_cube_qualified_20261005.json','scripts/promotable_contact_cubes.py','scripts/promotable_micro_qualified.py','scripts/native_cube_contact_closure.py')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('changed alive-result study never rerun')
    start=monotonic();r=dict(complete=False,rows=[],controls=[],rejections={},canonical_candidates=24,enumerated=1,public_transitions=0,source_queries=0,new_worlds=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start+0.063>=15:raise TimeoutError('15sec cumulative changed study')
    try:
        old=json.loads((ROOT/SOURCES[4]).read_text());assert not old['complete'] and len(old['rows'])==2
        p0=Profile('opaque_initial','opaque_initial');p1=Profile('opaque_initial','opaque_changed',True)
        for live in (False,True):
            for owner in (0,1):
                c=compile_ruleset_for_execution(build(live=live));profiles=(p0,) if not live and owner==0 else (p0,p1)
                kernel=PhysicalPromotionContactCubes(c,profiles,owner=owner,checkpoint=check);r['canonical_candidates']+=kernel.stats['canonical_candidates']
                counts={p:Counter() for p in profiles};digests={p:(hashlib.sha256(),hashlib.sha256()) for p in profiles};mismatch=[]
                def observe(target,blocker,p,source,value):
                    check();expected=distance(source,target,blocker,int(p.promoted),owner,live=live);counts[p][expected]+=1;r['new_worlds']+=1
                    prefix=f'{target},{blocker},{source}:';digests[p][0].update((prefix+str(value)+';').encode());digests[p][1].update((prefix+str(expected)+';').encode())
                    if value!=expected and not mismatch:mismatch.append(dict(source=source,target=target,blocker=blocker,profile=asdict(p),actual=value,expected=expected))
                census=cube_contact_census(kernel,world_observer=observe)['rows']
                for p in profiles:
                    row=dict(live=live,owner=owner,profile=asdict(p),worlds=sum(counts[p].values()),census=census[p],ordered_cube_sha256=digests[p][0].hexdigest(),ordered_coordinate_sha256=digests[p][1].hexdigest(),first_mismatch=mismatch[0] if mismatch else None,reused=False,preprocessing=kernel.stats);r['rows'].append(row);write_record(OUT,r)
                    if row['worlds']!=504 or mismatch or row['ordered_cube_sha256']!=row['ordered_coordinate_sha256']:raise ValueError('changed promotion worldwise mismatch')
                if not live and owner==0:
                    r['rows'].append(dict(old['rows'][1],live=False,reused=True,reuse_reason='promoted profile maps untouched by alive filter'))
                engine=semantic_engine_for(c);initial=initial_state(c).position
                for src,tgt,blk,p in ((0,1,8,p0),(3,6,0,p0),(3,0,8,p0),(4,5,0,p1)):
                    if owner:src,tgt,blk=8-src,8-tgt,8-blk
                    board=[None]*9;board[src]=Piece(owner,p.base,p.current,p.promoted);board[tgt]=Piece(1-owner,'target','target');board[blk]=Piece(owner,'blocker','blocker')
                    acts=engine.legal_actions(replace(initial,board=tuple(board),side_to_move=owner),checkpoint=check);r['enumerated']+=len(acts)
                    actual=sorted(set((a.target,int(a.promotion_target_id is not None or p.promoted)) for a in acts if a.source==src))
                    expected=sorted(set((d,q) for d,q in steps(src,int(p.promoted),owner,live=live) if d!=blk))
                    r['controls'].append(dict(live=live,owner=owner,source=src,target=tgt,blocker=blk,profile=asdict(p),actual=actual,expected=expected,all_actions=[asdict(a) for a in acts]));write_record(OUT,r)
                    if actual!=expected or len(acts)>128:raise ValueError('actual whole semantic list mismatch')
        renamed=PhysicalPromotionContactCubes(compile_ruleset_for_execution(build('renamed_initial','renamed_changed',live=True)),(Profile('renamed_initial','renamed_initial'),Profile('renamed_initial','renamed_changed',True)),checkpoint=check)
        r['canonical_candidates']+=renamed.stats['canonical_candidates'];r['renamed_census']={str(p.promoted):x for p,x in cube_contact_census(renamed)['rows'].items()}
        for control in ('none','guard','promoted_promotable'):
            try:PhysicalPromotionContactCubes(compile_ruleset_for_execution(build(live=True,**{control:True})),(p0,p1),checkpoint=check)
            except ContactUnsupported as error:r['rejections'][control]=str(error)
        r['complete']=len(r['rows'])==8 and len(r['controls'])==16 and len(r['rejections'])==3 and r['new_worlds']==3528 and r['canonical_candidates']<=5000 and r['enumerated']<=5000 and all(r['renamed_census'][str(p.promoted)]==r['rows'][4+i]['census'] for i,p in enumerate((p0,p1)))
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['cumulative_seconds']=r['seconds']+0.063;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in r['source_sha256'].items());write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('rows','controls','source_sha256','renamed_census')}))
