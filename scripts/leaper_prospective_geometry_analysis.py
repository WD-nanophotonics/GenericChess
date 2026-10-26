"""Correct/derive geometry statistics from the SAME retained raw masks.

No new census, Player or game; v1 faulty bipartite fields stay in their original
archive. This reader rejects changed raw/effective/spatial keys.
"""
import argparse
from collections import Counter,defaultdict
from fractions import Fraction
import gzip,hashlib,json,time
from pathlib import Path
from datetime import datetime,timezone

from scripts.leaper_prospective_geometry import descriptor,effective,joint_key,stable
from tools.local_agent.common import write_json


def burnside(n):
    u=(2*n-1)**2-1
    f=2*(n-1)
    identity=u+u*(u-1)//2
    halfturn=u//2
    reflection=f+f*(f-1)//2+(u-f)//2
    empty=int(n<6) # Empty relation appears only when raw pool has inactive atoms.
    total=identity+halfturn+4*reflection+8*empty
    assert total%8==0
    return total//8


def split(key):
    return int(hashlib.sha256(("GC-PROSPECTIVE-GEOMETRY-SPLIT-v1:"+stable(key)).encode()).hexdigest(),16)%5==0


def run(census_dir,output):
    if output.exists(): raise ValueError("new derivation output required")
    output.mkdir(parents=True)
    tick=time.perf_counter();start=datetime.now(timezone.utc).isoformat()
    original=json.loads(gzip.decompress((census_dir/"rows.json.gz").read_bytes()))
    answer=[];summaries=[]
    for board in original:
        n=board["n"];counts=Counter();descs=defaultdict(set);keysplits=defaultdict(set)
        exact_splits=defaultdict(set);rows=[];corrections=0;cache={}
        for row in board["rows"]:
            raw=row["raw"];eff=effective(n,raw);key=joint_key(n,{"T":eff})
            assert stable(row["effective"])==stable(eff)
            assert stable(row["spatial_key"])==stable(key)
            if eff not in cache:cache[eff]=descriptor(n,eff)
            d=cache[eff];corrections+=int(stable(d)!=stable(row["descriptor"]))
            counts[key]+=1;descs[d].add(key)
            keysplits[key].add(split([n,raw]))
            exact_splits[eff].add(split([n,raw]))
            rows.append({**row,"descriptor_v1":row["descriptor"],"descriptor":d,
                         "raw_hash_reserved":split([n,raw]),
                         "group_hash_reserved":split(key)})
        total=sum(counts.values());squared=sum(c*c for c in counts.values())
        nonempty={k:v for k,v in counts.items() if k[1][0][1]}
        nz=sum(nonempty.values());nzsquared=sum(c*c for c in nonempty.values())
        # ESS is a concentration index of GEOMETRY-category weights, not game sample ESS.
        m={"n":n,"raw_sets":total,"fixed_coordinate_relations":len(exact_splits),
           "spatial_classes":len(counts),"burnside_expected":burnside(n),
           "descriptor_groups":len(descs),"descriptor_collision_groups":sum(len(s)>1 for s in descs.values()),
           "bipartite_field_corrections":corrections,
           "raw_hash_split_leaking_spatial_groups":sum(len(s)>1 for s in keysplits.values()),
           "raw_hash_split_leaking_exact_relations":sum(len(s)>1 for s in exact_splits.values()),
           "raw_weight_concentration":str(Fraction(squared,total*total)),
           "geometry_inverse_concentration":float(Fraction(total*total,squared)),
           "nonempty_raw_sets":nz,"nonempty_spatial_groups":len(nonempty),
           "nonempty_geometry_inverse_concentration":float(Fraction(nz*nz,nzsquared)),
           "max_class_raw_weight":max(counts.values())/total,
           "bipartite_spatial_classes":len({joint_key(n,{"T":k}) for k,v in cache.items() if v[-1]}),
           "not_game_ESS":True,
           "collision_example":next(({"descriptor":d,"spatial_keys":list(sorted(ks))[:2]}
                                      for d,ks in descs.items() if len(ks)>1),None)}
        assert m["spatial_classes"]==m["burnside_expected"]
        summaries.append(m);answer.append({"n":n,"rows":rows})
    with gzip.GzipFile(filename=str(output/"rows-corrected.json.gz"),mode="wb",mtime=0) as f:
        f.write(stable(answer).encode())
    result={"status":"DERIVED_FROM_SAME21780_RAW_MASKS","started_at":start,
        "ended_at":datetime.now(timezone.utc).isoformat(),"seconds":time.perf_counter()-tick,
        "source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "geometry_source_sha256":hashlib.sha256(Path(__file__).with_name("leaper_prospective_geometry.py").read_bytes()).hexdigest(),
        "input_sha256":hashlib.sha256((census_dir/"rows.json.gz").read_bytes()).hexdigest(),
        "summaries":summaries,"new_Player":0,"new_solver":0,"new_games":0,
        "claim":"abstract direction catalogue only; corrected derived coloring and declared hypothetical split, not WDL/heldout/strength"}
    write_json(output/"summary.json",result);print(stable(result));return result


if __name__=="__main__":
    p=argparse.ArgumentParser(__doc__);p.add_argument("--census",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args();run(a.census,a.output)
