"""Independent analytic class-weight histogram for the frozen radius5 pool.

Only arithmetic of spatial classes. Inverse concentration and hypothetical
partition overlap are NOT estimates of independent game samples or strength.
"""
from collections import Counter
from fractions import Fraction
from pathlib import Path
import argparse,gzip,json
from datetime import datetime,timezone

from scripts.leaper_prospective_geometry import joint_key,stable
from scripts.leaper_prospective_geometry_analysis import burnside
from tools.local_agent.common import write_json


def analytic_histogram(n):
    m=n-1;u=(2*n-1)**2-1;b=120-u
    empty=int(b>0)
    c1=m*(m+3)//2
    c2=burnside(n)-c1-empty
    pair_count=u*(u-1)//2
    orbit2=2*m
    orbit4=(8*c2-6*orbit2-pair_count)//4
    orbit8=c2-orbit2-orbit4
    assert 2*orbit2+4*orbit4+8*orbit8==pair_count
    h=Counter()
    if b:h[b+b*(b-1)//2]+=1
    h[4*(b+1)]+=2*m
    h[8*(b+1)]+=m*(m-1)//2
    h[2]+=orbit2;h[4]+=orbit4;h[8]+=orbit8
    return {k:v for k,v in h.items() if v}


def run(input_file,output):
    if output.exists():raise ValueError("new derivation output required")
    boards=json.loads(gzip.decompress(input_file.read_bytes()));rows=[]
    for board in boards:
        n=board["n"];weights=Counter(joint_key(n,{"T":r["effective"]}) for r in board["rows"])
        observed=dict(Counter(weights.values()));expected=analytic_histogram(n)
        assert observed==expected,(n,observed,expected)
        total=sum(k*v for k,v in expected.items());assert total==7260
        squared=sum(v*k*k for k,v in expected.items())
        b=120-((2*n-1)**2-1)
        equal_raw=Fraction(b+b*(b-1)//2,7260)
        balanced_k=Fraction(b,240)+Fraction(b*(b-1)//2,2*(120*119//2))
        # An illustration under INDEPENDENT raw-item 80/20 assignment, not the
        # deterministic hash split and not a model of game outcomes.
        overlap=sum(float(Fraction(v)*(1-Fraction(1,5)**k-Fraction(4,5)**k))
                    for k,v in expected.items())
        rows.append({"n":n,"raw_mass_per_spatial_class_histogram":expected,
            "analytic_matches_all_recorded_classes":True,
            "inverse_concentration":str(Fraction(total*total,squared)),
            "empty_probability_uniform_raw_subsets":str(equal_raw),
            "empty_probability_balanced_1or2_atom_count":str(balanced_k),
            "empty_probability_uniform_effective_relation":str(Fraction(int(b>0),len({stable(r["effective"]) for r in board["rows"]}))),
            "empty_probability_uniform_spatial_class":str(Fraction(int(b>0),len(weights))),
            "hypothetical_expected_overlap_groups_iid_raw_80_20":overlap,
            "not_game_ESS":True})
    result={"at":datetime.now(timezone.utc).isoformat(),"rows":rows,"Core":0,"Player":0,"solver":0,
            "claim":"declared abstract sampling-law comparisons only, not actualgenerator/game probabilities"}
    write_json(output,result);print(stable(result));return result


if __name__=="__main__":
    p=argparse.ArgumentParser(__doc__);p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args();run(a.input,a.output)
