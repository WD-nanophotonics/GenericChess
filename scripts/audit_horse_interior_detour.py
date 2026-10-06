from pathlib import Path
from time import monotonic
from fractions import Fraction
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.research_record import write_record,record_value
OUT=ROOT/'docs/research/data/horse_interior_detour_20261006.json'
OLD='docs/research/data/horse_target_entry_20261006.json'
SOURCES=('scripts/audit_horse_interior_detour.py','docs/research/HORSE_INTERIOR_DETOUR_PROTOCOL.md',OLD,
 'scripts/research_record.py','scripts/horse_target_graph.py')


def leg(a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    if sorted((abs(dx),abs(dy)))!=[1,2]:raise ValueError('not ordinary Knight edge')
    return (a[0]+(1 if dx>0 else -1),a[1]) if abs(dx)==2 else (a[0],a[1]+(1 if dy>0 else -1))


def main():
    if OUT.exists():raise FileExistsError('directed bypass stencil never rerun')
    start=monotonic();r=dict(complete=False,new_terms=0,public_transitions=0,forward_nodes=0,compiled_queries=0,
       routes=[],source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    try:
        old=json.loads((ROOT/OLD).read_text())
        if not old['complete'] or not old['source_hashes_unchanged']:raise ValueError('prior qualified budget required')
        for p,pin in old['source_sha256'].items():
            if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=pin:raise ValueError('prior source drift')
        def term():
            if r['new_terms']>=40 or monotonic()-start>=15:raise ValueError('remaining40 terms/15sec cap')
            r['new_terms']+=1
        base=[(-1,0),(0,-2),(2,-1),(1,1)]
        for swap in (False,True):
            for sx in (-1,1):
                for sy in (-1,1):
                    def transform(p):
                        x,y=(p[1],p[0]) if swap else p
                        return (sx*x,sy*y)
                    path=[transform(p) for p in base];legs=[]
                    if leg(path[0],path[-1])!=(0,0):raise ValueError('original edge not center-blocked')
                    for a,b in zip(path,path[1:]):
                        term();l=leg(a,b);legs.append(l)
                        if l==(0,0) or a==(0,0) or b==(0,0):raise ValueError('center remains occupied')
                        if max(abs(c) for p in (a,b,l) for c in p)>2:raise ValueError('margin/distant-hole guarantee fails')
                    r['routes'].append(dict(path=path,legs=legs))
        if len({tuple(p) for row in r['routes'] for p in [row['path'][0]+row['path'][-1]]})!=8:raise ValueError('eight blocked orientations required')
        sums=[]
        for size in (5,6):
            values=[]
            for d in range(-2,3):term();values.append(size-abs(d))
            sums.append(sum(values))
        pairs=30*30-sums[0]*sums[1]
        r.update(close_displacement_sums=sums,ordered_distant_pairs=pairs,qualified_worlds=pairs*88,
          qualified_mass=Fraction(pairs*88,704880),ordinary_path_bound=88,removed_leg_edge_bound=16,
          sufficient_horse_contact_bound=88+2*16,
          cumulative_analytic_terms=4960+r['new_terms'],cumulative_forward_nodes=1579,
          external_theorem='Schwenk1991 closed ordinary Knight tour on9x10; not an H theorem',
          not_proved='remaining target/blocker pairs,full H distances,disjoint mass refinement,natural-game strength')
        if r['cumulative_analytic_terms']>5000:raise ValueError('cumulative budget')
        r['complete']=True
    except Exception as error:r['error']=f'{type(error).__name__}: {error}'
    r['seconds']=monotonic()-start;r['source_hashes_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==v for p,v in r['source_sha256'].items())
    write_record(OUT,r);print(json.dumps(record_value({k:v for k,v in r.items() if k not in ('routes','source_sha256')})))


if __name__=='__main__':main()
