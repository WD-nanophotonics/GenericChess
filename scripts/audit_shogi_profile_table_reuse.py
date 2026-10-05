"""Whole physical edge/path identity against independent Shogi coordinates."""
from dataclasses import asdict,replace
import hashlib,json,sys
from pathlib import Path
from time import monotonic
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.standard_shogi import build_standard_shogi_ruleset
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.core.semantic_executor import semantic_engine_for,SemanticEngine
from generic_chess.core.transition import initial_state
from generic_chess.core.pieces import Piece
from scripts.physical_profile_event_cubes import PhysicalProfileEventCubes
from scripts.shared_contact_prefix import Profile
from scripts.research_record import record_value,write_record
OUT=ROOT/'docs/research/data/shogi_profile_table_reuse_20261006.json'
SOURCES=('scripts/audit_shogi_profile_table_reuse.py','docs/research/SHOGI_PROFILE_TABLE_REUSE_PROTOCOL.md','scripts/physical_profile_event_cubes.py','docs/research/data/shogi_full_contact_distance_20261005.json','docs/research/data/shogi_coordinate_comparison_20261005.json','generic_chess/rules/standard_shogi.py')
GOLD=((0,1),(-1,1),(1,1),(-1,0),(1,0),(0,-1));ORTH=((1,0),(-1,0),(0,1),(0,-1));DIAG=((1,1),(1,-1),(-1,1),(-1,-1))

def coordinate_edges(profile,source):
    kind=profile.current;steps=GOLD if kind in ('G','TP','TL','TN','TS') else ((0,1),) if kind=='P' else ((-1,2),(1,2)) if kind=='N' else ((0,1),(-1,1),(1,1),(-1,-1),(1,-1)) if kind=='S' else ORTH if kind=='TB' else DIAG if kind=='TR' else ()
    rays=((0,1),) if kind=='L' else DIAG if kind in ('B','TB') else ORTH if kind in ('R','TR') else ()
    for offsets,is_ray in ((steps,False),(rays,True)):
        for df,dr in offsets:
            f,r=source%9+df,source//9+dr;path=0
            while 0<=f<9 and 0<=r<9:
                dest=f+9*r;choices=(profile,)
                if not profile.promoted and kind in ('P','L','N','S','B','R') and (source//9>=6 or r>=6):
                    result=Profile(profile.base,'T'+kind,True);forced=kind in ('P','L') and r==8 or kind=='N' and r>=7
                    choices=(result,) if forced else (profile,result)
                for q in choices:yield dest,q,path
                if not is_ray:break
                path|=1<<dest;f+=df;r+=dr

def cube_path(cube,source,target,capture):
    literals=dict(cube)
    if tuple(literals.pop(source,()))!=('own',) or tuple(literals.pop(target,()))!=(('enemy',) if capture else ('empty',)):raise ValueError('unexpected source/target occupancy')
    if any(tuple(labels)!=('empty',) for labels in literals.values()):raise ValueError('extra occupancy semantics')
    return sum(1<<s for s in literals)

if __name__=='__main__':
    if OUT.exists():raise FileExistsError('new table qualification no rerun')
    start=monotonic();r=dict(complete=False,table_rows=[],controls=[],canonical_candidates=0,candidates=0,returned_actions=0,public_transitions=0,source_queries=0,distance_worlds=0,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES});original=SemanticEngine._iter_candidates
    def check():
        if monotonic()-start>=15:raise TimeoutError('whole15sec cap')
        if r['canonical_candidates']+r['candidates']+r['returned_actions']>5000:raise ValueError('whole5000 enumeration cap')
    def counted(self,*args,**kwargs):
        for item in original(self,*args,**kwargs):
            r['candidates']+=1;check();yield item
    try:
        old=json.loads((ROOT/SOURCES[3]).read_text());independent=json.loads((ROOT/SOURCES[4]).read_text());assert old['complete'] and independent['complete']
        for report in (old,independent):
            for path,pin in report['source_sha256'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==pin
        pp=tuple(Profile(**row['profile']) for row in old['rows']);compiled=compile_ruleset_for_execution(build_standard_shogi_ruleset());k=PhysicalProfileEventCubes(compiled,pp,checkpoint=check);r['canonical_candidates']=k.stats['canonical_candidates'];r['preprocessing']=k.stats;check()
        for p in pp:
            for source in range(81):
                check();actual={(d,q,cube_path(cube,source,d,False)) for (d,q),cubes in k.quiet[p,source].items() for cube in cubes};expected=set(coordinate_edges(p,source))
                captures={(d,cube_path(cube,source,d,True)) for d,cubes in k.capture[p,source].items() for cube in cubes};expected_capture={(d,mask) for d,q,mask in expected}
                row=dict(profile=asdict(p),source=source,quiet_edges=len(actual),capture_edges=len(captures),match=actual==expected and captures==expected_capture);r['table_rows'].append(row)
                if not row['match']:r['first_mismatch']=dict(row,actual=record_value(sorted(actual,key=str)),expected=record_value(sorted(expected,key=str)));raise ValueError('whole profile table mismatch')
            write_record(OUT,r)
        SemanticEngine._iter_candidates=counted;engine=semantic_engine_for(compiled);base=initial_state(compiled).position
        for p in pp:
            for source,target,blocker in ((40,41,0),(0,1,80),(67,76,40)):
                check();board=[None]*81;board[source]=Piece(0,p.base,p.current,p.promoted);board[target]=Piece(1,'G','G');board[blocker]=Piece(0,'G','G')
                acts=engine.legal_actions(replace(base,board=tuple(board),side_to_move=0),checkpoint=check);r['returned_actions']+=len(acts);check()
                actual=sorted(set((a.target,a.promotion_target_id or p.current) for a in acts if a.source==source));expected=sorted(set((d,q.current) for d,q,mask in coordinate_edges(p,source) if d!=blocker and not mask&((1<<blocker)|(1<<target))))
                r['controls'].append(dict(profile=asdict(p),source=source,target=target,blocker=blocker,actual=actual,coordinate=expected,all_actions=[asdict(a) for a in acts]));write_record(OUT,r)
                if actual!=expected or len(acts)>128:raise ValueError('virtual actor list mismatch')
        r['reused_distance_rows']=old['rows'];r['complete']=len(r['table_rows'])==1053 and len(r['controls'])==39
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    finally:SemanticEngine._iter_candidates=original
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items());write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k not in ('table_rows','controls','reused_distance_rows','source_sha256')}))
