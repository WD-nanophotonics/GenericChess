"""Necessary material choice-cell conditions, not a rule/layout generator.

Capture-removal count boxes overapproximate reachable search leaves. A cell
crossing is necessary for a complete exact minimax choice to change, but does
not prove that a legal common frontier realizes it, has WDL headroom or is
visited. Fixed A=1, positive B and material-blind ordering remain explicit.
"""
from fractions import Fraction as F
from itertools import combinations,product


def count_box(roster):
    """(owner,type,count) -> all surviving signed (A,B) count vectors."""
    if any(owner not in(0,1)or tid not in('A','B')or type(n)is not int or n<0 for owner,tid,n in roster):raise ValueError('unsupported count roster')
    points=set()
    for surviving in product(*(range(n+1)for owner,tid,n in roster)):
        points.add(tuple(sum(z*(1 if owner==0 else-1)for(owner,tid,n),z in zip(roster,surviving)if tid==t)for t in('A','B')))
    return sorted(points)


def crossings(points):
    result=[]
    for a,b in combinations(points,2):
        da=a[0]-b[0];db=a[1]-b[1]
        if db==0:continue
        price=-F(da,db)
        if price<=0:continue
        value=a[0]+price*a[1]
        result.append(dict(leaves=[a,b],B=str(price),common_value=str(value),nonzero=value!=0))
    return result


def examples():
    cases=dict(one_kind_split=[(0,'A',1),(1,'A',1)],
        one_each_split=[(0,'A',1),(1,'B',1)],
        two_types_same_owner=[(0,'A',1),(0,'B',1)],
        two_identical_same_owner=[(0,'A',2)],
        five_actor_split=[(0,'A',2),(1,'B',1)])
    return dict(cases={name:dict(roster=roster,points=count_box(roster),positive_crossings=crossings(count_box(roster)))for name,roster in cases.items()},
        theorem='Forafixedfiniteexactminimaxtree, leaf-scoretotalpreorderdeterminesalloptimalactionsets. Apositivecommonrescalingofone-kindmaterialpreservesthatpreorderwhileterminal/drawdominanceisfixed. Thisdoesnotclaimidenticalpaidcost, partial/time-limitedreturns, floatingroundingororder-pruningbehaviour.',
        consequence='FouractorswithoneAversusoneBpermitonlythezero-valuedB1crossing. FouractorswithAandBonthesamesidesufficeforapositive-valuedA-vs-Btradeinthiscountbox. IfbothsidesscoreandoneAversusoneBismandatory, athirdordinaryactorallowsnonzeroongoingcrossings. Noextraactorisuniversallynecessary.',
        next_admission='PRIMARYmustsupplyactualfullrules/unfilteredmu/recordswhoselegalfrontiersrealizethetrade. AUXthenchecksfullhistoryWDLheadroomandusefulexposurebeforemorelearning. Countboxexamplesarenotexperientialstarts, truepricesornewgeneratorcampaigns.')
