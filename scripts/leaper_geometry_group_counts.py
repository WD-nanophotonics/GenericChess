"""Independent Burnside counts for common versus per-type spatial grouping."""
from collections import Counter
from itertools import combinations,product
from math import gcd
import argparse,json
from pathlib import Path
from datetime import datetime,timezone

from scripts.leaper_prospective_geometry import joint_key,descriptor,stable
from tools.local_agent.common import write_json


def fixed_counts(n,include_empty):
    u=(2*n-1)**2-1
    f=2*(n-1);e=int(include_empty)
    reflect=f+f*(f-1)//2+(u-f)//2+e
    return (u+u*(u-1)//2+e,e,u//2+e,e,reflect,reflect,reflect,reflect)


def counts(n,include_empty):
    fixed=fixed_counts(n,include_empty)
    assert sum(fixed)%8==sum(x*x for x in fixed)%8==0
    single=sum(fixed)//8
    return {"n":n,"include_empty":include_empty,"fixed_counts_by_D4":fixed,
            "single_type_classes":single,
            "labelled_two_type_common_D4_classes":sum(x*x for x in fixed)//8,
            "independent_per_type_D4_tuples":single*single}


def full_orbit(r,s):
    return tuple(sorted({(a*x,b*y) for x,y in ((r,s),(s,r)) for a,b in product((-1,1),repeat=2)}))


def run(output):
    if output.exists():raise ValueError("new output required")
    results={"at":datetime.now(timezone.utc).isoformat(),"main_counts":[counts(n,n<6) for n in (4,5,6)]}
    toys=[]
    for n in (2,3):
        vv=tuple((x,y) for x,y in product(range(1-n,n),repeat=2) if (x,y)!=(0,0))
        choices=((),)+tuple((v,) for v in vv)+tuple(combinations(vv,2))
        # Explicit orbit enumeration is independent of the fixed-point formula.
        joint={joint_key(n,{"A":a,"B":b}) for a,b in product(choices,repeat=2)}
        one={joint_key(n,{"T":a}) for a in choices}
        expected=counts(n,True)
        assert len(joint)==expected["labelled_two_type_common_D4_classes"]
        assert len(one)==expected["single_type_classes"]
        toys.append({**expected,"explicit_pairs":len(choices)**2,
                     "explicit_joint_classes":len(joint),"explicit_single_classes":len(one)})
    results["independent_small_board_checks"]=toys
    orbit_checks=[];unions=[]
    # Knuth Theorem1 applies ONLY to the complete +/- and coordinate-swap orbit.
    for n in (4,5,6):
        pool={(r,s):full_orbit(r,s) for s in range(1,6) for r in range(1,s+1)}
        dd={k:descriptor(n,v) for k,v in pool.items()}
        for (r,s),d in dd.items():
            predicted=gcd(r+s,r-s)==1 and n>=2*s and n>=r+s
            actual=d[2]==(n*n,)
            assert predicted==actual,(n,r,s)
            assert d[2]==d[3] # The fully symmetric geometry is bidirectional.
            orbit_checks.append({"n":n,"r":r,"s":s,"connected":actual})
        for (a,aa),(b,bb) in combinations(pool.items(),2):
            if dd[a][2]!=(n*n,) and dd[b][2]!=(n*n,):
                union=tuple(set(aa)|set(bb))
                if descriptor(n,union)[2]==(n*n,):
                    unions.append({"n":n,"orbit1":a,"orbit2":b,
                                   "individual_components":[dd[a][2],dd[b][2]],"union_components":[n*n]})
    results["Knuth_theorem_checks"]=orbit_checks
    results["union_connected_individual_disconnected"]=unions
    results["directed_subset_negative"]={"n":4,"full_knight_components":descriptor(4,full_orbit(1,2))[2],
        "subset_offsets":[[1,2],[2,1]],"subset_weak":descriptor(4,((1,2),(2,1)))[2],
        "subset_strong":descriptor(4,((1,2),(2,1)))[3],
        "conclusion":"single-complete-orbit theorem cannot be applied to a directed subset or as a game-quality filter"}
    results.update(Player=0,solver=0,games=0,literature="https://arxiv.org/pdf/math/9411240 Theorem1 pp1-3; source-only theorem application")
    write_json(output,results)
    print(stable({k:v for k,v in results.items() if k not in ("Knuth_theorem_checks","union_connected_individual_disconnected")}))
    print("complete-orbit checks",len(orbit_checks),"union counterexamples",len(unions))
    return results


if __name__=="__main__":
    p=argparse.ArgumentParser(__doc__);p.add_argument("--output",type=Path,required=True);a=p.parse_args();run(a.output)
