from pathlib import Path
from time import monotonic
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from generic_chess.rules.western_chess import build_western_chess_ruleset
from scripts.research_record import write_record
OUT=ROOT/'docs/research/data/bare_minor_mate_geometry_20261006.json'
SOURCES=('scripts/audit_bare_minor_mate_geometry.py','docs/research/BARE_MINOR_MATE_GEOMETRY_PROTOCOL.md',
 'generic_chess/rules/western_chess.py','generic_chess/core/semantic_executor.py',
 'generic_chess/core/terminal.py','scripts/research_record.py')


def neighbors(square,offsets):
    x,y=square%8,square//8
    return tuple((y+dy)*8+x+dx for dx,dy in offsets if 0<=x+dx<8 and 0<=y+dy<8)

def audit(r):
    start=monotonic();rules=build_western_chess_ruleset()
    if rules.declarations or rules.automatic_adjudications or rules.consecutive_action_adjudications or rules.repeated_cycle_target_conditions or rules.no_progress_draw or rules.stalemate_result!='draw' or rules.repetition_policy!='draw' or rules.max_ply!=1000:raise ValueError('extra local goal/history policy')
    r['rule_scope']=dict(max_ply=rules.max_ply,repetition_limit=rules.repetition_limit,stalemate=rules.stalemate_result)
    kings=[neighbors(s,tuple((dx,dy) for dx in (-1,0,1) for dy in (-1,0,1) if dx or dy)) for s in range(64)]
    knight=[set(neighbors(s,((1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1)))) for s in range(64)]
    bishops={}
    for minor in range(64):
        for wk in range(64):
            attacked=set()
            for dx,dy in ((1,1),(-1,1),(1,-1),(-1,-1)):
                x,y=minor%8+dx,minor//8+dy
                while 0<=x<8 and 0<=y<8:
                    s=y*8+x;attacked.add(s)
                    if s==wk:break
                    x+=dx;y+=dy
            bishops[minor,wk]=attacked
    for mode in ('N','B'):
        row=dict(worlds=0,checked_worlds=0,escape_witnesses=0,capture_witnesses=0);h=hashlib.sha256()
        for bk in range(64):
            if monotonic()-start>30:raise TimeoutError('30sec geometry safety fuse')
            for wk in range(64):
                if wk==bk or wk in kings[bk]:continue
                protected=set(kings[wk])|{wk}
                for minor in range(64):
                    if minor in (bk,wk):continue
                    row['worlds']+=1;attacked=knight[minor] if mode=='N' else bishops[minor,wk]
                    if bk not in attacked:continue
                    row['checked_worlds']+=1
                    escapes=[s for s in kings[bk] if s not in protected and (s==minor or s not in attacked)]
                    if not escapes:r['counterexample']=dict(mode=mode,bk=bk,wk=wk,minor=minor);raise AssertionError('bare-minor mate geometry counterexample')
                    witness=min(escapes);row['escape_witnesses']+=1;row['capture_witnesses']+=witness==minor
                    h.update(bytes((bk,wk,minor,witness)))
        row['ordered_witness_sha256']=h.hexdigest();r['modes'][mode]=row
    r.update(complete=True,no_bare_minor_checkmate=True,seconds=monotonic()-start,
      scope='complete geometry, conditional inspected native/current promoted move correspondence; not semantic replay of every world')


if __name__=='__main__':
    if OUT.exists():raise FileExistsError('preserve geometry proof')
    r=dict(complete=False,modes={},source_calls=0,public_transitions=0,
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    start=monotonic()
    try:audit(r)
    except Exception as e:r['error']=f'{type(e).__name__}: {e}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==pin for p,pin in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps({k:v for k,v in r.items() if k!='source_sha256'}))
