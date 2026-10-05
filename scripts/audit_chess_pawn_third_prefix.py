"""New third contact distance and exact old-support overlap, no game events."""
import hashlib,json,sys
from pathlib import Path
from time import monotonic
from fractions import Fraction as F
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.compiler import compile_ruleset_for_execution
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.qualified_western_pawn_prefix import QualifiedWesternPawnPrefix
from scripts.shared_contact_prefix import Profile
OUT=ROOT/'docs/research/data/chess_pawn_third_prefix_20261005.json'
SOURCES=('scripts/audit_chess_pawn_third_prefix.py','scripts/qualified_western_pawn_prefix.py',
 'scripts/western_pawn_contact_prefix.py','scripts/shared_contact_prefix.py',
 'docs/research/CHESS_PAWN_THIRD_PREFIX_PROTOCOL.md','docs/research/data/western_pawn_qualified_prefix_20261005.json')
if __name__=='__main__':
    if OUT.exists():raise FileExistsError('frozen third-prefix producer never rerun')
    start=monotonic();out=dict(complete=False,direct=0,second=0,third=0,overlap2={k:0 for k in range(1,8)},
       overlap3={k:0 for k in range(1,8)},physical_events=0,goal_queries=0,
       source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    def check():
        if monotonic()-start>=15:raise TimeoutError('15sec new third-prefix computation cap')
    try:
        c=compile_ruleset_for_execution(build_western_chess_ruleset());kernel=QualifiedWesternPawnPrefix(c,checkpoint=check)
        profile=Profile('P','P');out['stats']=kernel.stats
        for s in range(64):
            check()
            for d in range(64):
                if s==d:continue
                a,b=kernel.pair_success(profile,s,d);remaining=((1<<64)-1)&~((1<<s)|(1<<d)|a|b);exact=0
                for u,m1,p1 in kernel.quiet[profile,s]:
                    if u==d or m1&(1<<d):continue
                    for v,m2,p2 in kernel.quiet[p1,u]:
                        if v==d or m2&(1<<d):continue
                        for m3 in kernel.capture[p2,v].get(d,()):exact|=remaining&~((1<<u)|(1<<v)|m1|m2|m3)
                out['direct']+=a.bit_count();out['second']+=b.bit_count();out['third']+=exact.bit_count()
                if s//8<7 and d%8!=s%8:
                    support=sum(1<<x for x in range(64) if x%8!=s%8 and x!=d)
                    k=7-s//8;out['overlap2'][k]+=(support&b).bit_count();out['overlap3'][k]+=(support&exact).bit_count()
        if (out['direct'],out['second'])!=(6076,16112):raise ValueError('old prefix mismatch')
        if list(out['overlap2'].values())!=[6596,770,770,770,770,1540,770]:raise ValueError('old support mismatch')
        out['residual_rank_support']={k:23870-out['overlap2'][k]-out['overlap3'][k] for k in range(1,8)}
        if min(out['residual_rank_support'].values())<0:raise ValueError('negative residual')
        out['unknown_nonzero']=249984-56952-out['direct']-out['second']-out['third']
        if out['unknown_nonzero']<0:raise ValueError('lost mass')
        out['raw_bounds']={}
        for law,m in (('geometric_half',lambda t:F(1,2)**t),('linear_mixture',lambda t:F(2,(t+1)*(t+2)))):
            prefix=out['direct']*m(1)+out['second']*m(2)+out['third']*m(3)
            lo=(prefix+sum(n*m(k+3) for k,n in out['residual_rank_support'].items()))/249984
            hi=(prefix+out['unknown_nonzero']*m(4))/249984
            out['raw_bounds'][law]=[str(lo),str(hi)]
        out['complete']=True
    except Exception as e:out['error']=f'{type(e).__name__}: {e}'
    out['seconds']=monotonic()-start
    out['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in out['source_sha256'].items())
    OUT.write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps({k:v for k,v in out.items() if k!='source_sha256'}))
