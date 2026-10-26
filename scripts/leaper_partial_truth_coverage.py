"""Exact label-subset identifiability on old source truth, not new game solving.

No candidate roots are selected. Equal label count is a hypothetical information
budget, not measured proof verification cost. Root/action values remain source
claims; this finite post-hoc diagnostic is not a prospective test panel.
"""
from collections import Counter,defaultdict
from fractions import Fraction
from itertools import combinations
import argparse,gzip,json,math,time
from pathlib import Path
from scripts.leaper_truth_compatibility import Context,action_coverage,digest


def analyze_pattern(values):
    n=len(values);context=Context(None,dict(side_to_move=0,terminal=dict(status="ongoing",winner=None)),
                                tuple(dict(kind="abstract_source_action",index=i) for i in range(n)))
    root=max(values);result={}
    for root_known in (False,True):
        minimum_one=None;minimum_all=None;by_k=[]
        for k in range(n+1):
            total=Counter()
            for subset in combinations(range(n),k):
                labels=[dict(action=context.legal_actions[i],wdl_bounds=[values[i]]*2) for i in subset]
                out=action_coverage(context,labels,[root]*2 if root_known else None)
                classified=[r["classification"] for r in out["rows"]]
                optimal=classified.count("OPTIMAL_SOURCE_CLAIM");bad=classified.count("SUBOPTIMAL_SOURCE_CLAIM")
                # Every reported classification must agree with complete source labels.
                for i,kind in enumerate(classified):
                    if kind=="OPTIMAL_SOURCE_CLAIM" and values[i]!=root:raise ValueError("false optimal")
                    if kind=="SUBOPTIMAL_SOURCE_CLAIM" and values[i]>=root:raise ValueError("false suboptimal")
                total.update(subsets=1,optimal_actions=optimal,suboptimal_actions=bad,
                             unknown_actions=n-optimal-bad,has_optimal=int(optimal>0),all_classified=int(optimal+bad==n))
            denominator=math.comb(n,k)
            if total["subsets"]!=denominator:raise ValueError("subset denominator differs")
            if total["has_optimal"] and minimum_one is None:minimum_one=k
            if total["all_classified"] and minimum_all is None:minimum_all=k
            by_k.append(dict(labels=k,counts=dict(total),
                             uniform_subset_probability_has_optimal=str(Fraction(total["has_optimal"],denominator)),
                             uniform_subset_expected_unknown_actions=str(Fraction(total["unknown_actions"],denominator))))
        result["known_root" if root_known else "unknown_root"]=dict(
            minimum_labels_for_some_subset_to_identify_an_optimal_action=minimum_one,
            minimum_labels_for_some_subset_to_classify_all_actions=minimum_all,by_label_count=by_k)
    return result


def study(directory):
    tick=time.perf_counter();raw=(Path(directory)/"truth.json.gz").read_bytes();truth=json.loads(gzip.decompress(raw))
    patterns=Counter();by_family=defaultdict(Counter)
    for row in truth["roots"]:
        values=tuple(b["wdl_bounds"][0] for b in row["action_bounds"])
        if not values or any(b["wdl_bounds"]!=[v,v] for b,v in zip(row["action_bounds"],values)):
            raise ValueError("requires already published complete exact source action labels")
        if row["wdl_bounds"]!=[max(values)]*2:raise ValueError("source root orientation differs")
        # Sorting only reorders an algebra diagnostic; actual action IDs are retained elsewhere.
        pattern=tuple(sorted(values));patterns[pattern]+=1;by_family[row["family_index"]][pattern]+=1
    pattern_results={p:analyze_pattern(p) for p in patterns}
    for values, result in pattern_results.items():
        n=len(values);best=max(values)
        one_unknown=0 if n==1 else 1 if best==1 else n-1 if sum(v>-1 for v in values)<=1 else n
        one_known=0 if n==1 or best==-1 else 1
        all_unknown=0 if n==1 else n
        all_known=0 if n==1 or best==-1 else n-1 if values.count(best)==1 else n
        for mode,one,all_labels in (("unknown_root",one_unknown,all_unknown),("known_root",one_known,all_known)):
            if result[mode]["minimum_labels_for_some_subset_to_identify_an_optimal_action"]!=one:
                raise ValueError("closed-form optimal-certificate lower bound differs")
            if result[mode]["minimum_labels_for_some_subset_to_classify_all_actions"]!=all_labels:
                raise ValueError("closed-form full-classification lower bound differs")
    totals={mode:Counter() for mode in ("known_root","unknown_root")}
    family_results=[]
    for family,pp in sorted(by_family.items()):
        rows={mode:Counter() for mode in totals}
        for p,count in pp.items():
            for mode in totals:
                result=pattern_results[p][mode]
                for label,field in (("one_optimal", "minimum_labels_for_some_subset_to_identify_an_optimal_action"),
                                    ("all_classified","minimum_labels_for_some_subset_to_classify_all_actions")):
                    key=f"{label}:"+str(result[field]);rows[mode][key]+=count;totals[mode][key]+=count
        family_results.append(dict(family=family,roots=sum(pp.values()),minimum_label_histograms={k:dict(v) for k,v in rows.items()}))
    return dict(status="PASS",source_truth_sha256=__import__("hashlib").sha256(raw).hexdigest(),
                roots=sum(patterns.values()),source_rule_families=len(by_family),patterns=len(patterns),
                minimum_label_histograms={k:dict(v) for k,v in totals.items()},families=family_results,
                pattern_details=[dict(values=p,roots=patterns[p],analysis=pattern_results[p]) for p in sorted(patterns)],
                seconds=time.perf_counter()-tick,new_Core_calls=0,new_Player_calls=0,new_solver_calls=0,
                scope="All label subsets on existing source-labelled frontiers. Known-root and unknown-root assumptions distinct; no measured label cost, heldout evidence, candidate selection or policy-strength claim.")


def main():
    p=argparse.ArgumentParser();p.add_argument("--directory",type=Path,default=Path("docs/research/data/leaper_h6_initial_truth_20261023"));p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    result=study(a.directory);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items()if k not in("families","pattern_details")}))

if __name__=="__main__":main()
