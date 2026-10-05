"""Independent coordinate union, saved compiled evidence replay; no new events."""
import hashlib,json
from pathlib import Path
from fractions import Fraction as F
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'docs/research/data'

def coordinate_tables():
    quiet={};capture={}
    for t in ('P','Q','N'):
        for s in range(64):
            x,y=s%8,s//8;rows=[]
            if t=='P':
                if y<7:rows.append((x,y+1,0,False))
                if y==1:rows.append((x,y+2,1<<(s+8),False))
                if y<7:
                    for dx in (-1,1):
                        if 0<=x+dx<8:rows.append((x+dx,y+1,0,True))
            elif t=='N':
                for dx,dy in ((1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1)):
                    if 0<=x+dx<8 and 0<=y+dy<8:rows.append((x+dx,y+dy,0,None))
            else:
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                    mask=0
                    for k in range(1,8):
                        xx,yy=x+k*dx,y+k*dy
                        if not (0<=xx<8 and 0<=yy<8):break
                        rows.append((xx,yy,mask,None));mask|=1<<(yy*8+xx)
            quiet[t,s]=[];capture[t,s]={}
            for xx,yy,mask,capt in rows:
                d=yy*8+xx
                if capt is not True:
                    # R/B are subsets of Q after promotion in this passive task.
                    variants=('Q','N') if t=='P' and yy==7 else (t,)
                    quiet[t,s].extend((d,mask,v) for v in variants)
                if capt is not False:capture[t,s][d]=mask
    return quiet,capture

def test_full_coordinate_third_mass_and_support_partition():
    quiet,capture=coordinate_tables();counts=[0,0,0];overlap=[0]*7
    for s in range(64):
        for d in range(64):
            if s==d:continue
            universe=((1<<64)-1)&~((1<<s)|(1<<d))
            first=universe&~capture['P',s][d] if d in capture['P',s] else 0
            second=third=0
            for u,m1,p1 in quiet['P',s]:
                if u==d or m1&(1<<d):continue
                if d in capture[p1,u]:second|=universe&~((1<<u)|m1|capture[p1,u][d])
                for v,m2,p2 in quiet[p1,u]:
                    if v==d or m2&(1<<d) or d not in capture[p2,v]:continue
                    third|=universe&~((1<<u)|(1<<v)|m1|m2|capture[p2,v][d])
            second&=~first;third&=~(first|second)
            for i,mask in enumerate((first,second,third)):counts[i]+=mask.bit_count()
            if s//8<7 and d%8!=s%8:
                eligible=sum(1<<b for b in range(64) if b%8!=s%8 and b!=d)
                overlap[6-s//8]+=(third&eligible).bit_count()
    report=json.loads((DATA/'chess_pawn_third_prefix_20261005.json').read_text())
    assert counts==[6076,16112,32926]
    assert overlap==[17274,5826,770,770,770,770,1540]
    assert report['third']==counts[2] and list(report['overlap3'].values())==overlap
    # Pure native two-quiet routes: rank1's dr3 paths already distance2 via double;
    # rank0/1 each add14*59 double-plus-single dr4 worlds.
    assert 4*14*60+2*14*59==5012

def test_all_preserved_prefix_hashes_and_zero_event_scope():
    for name in ('western_pawn_compiled_prefix','western_pawn_qualified_prefix','chess_pawn_third_prefix'):
        report=json.loads((DATA/f'{name}_20261005.json').read_text())
        assert report['physical_events']==report['goal_queries']==0
        for name,pin in report['source_sha256'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==pin
    good=json.loads((DATA/'western_pawn_qualified_prefix_20261005.json').read_text())
    assert good['complete'] and good['stats']['geometry_candidates']==1954
    assert len(good['discarded_ep'])==2 and len(good['reduced_double'])==1

def test_third_interval_strictly_tightens_without_erasing_rank_support():
    from scripts.native_chess_contact_intervals import native_contact_intervals
    report=json.loads((DATA/'chess_pawn_third_prefix_20261005.json').read_text())
    assert sum(report['residual_rank_support'].values())==127384
    assert 6076+16112+32926+56952+137918==249984
    for law,m in (('geometric_half',lambda t:F(1,2)**t),('linear_mixture',lambda t:F(2,(t+1)*(t+2)))):
        q=(87696*m(1)+162048*m(2)+240*m(3))/249984
        lo,hi=map(F,report['raw_bounds'][law]);oldlo,oldhi=native_contact_intervals(law)['board','P']
        assert oldlo<lo/q<hi/q<oldhi
