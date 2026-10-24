"""Finite material-order cells, not intrinsic prices or whole-game utility.

For the two expressly admitted removal-only source laws there is at most one
A and B per owner and no hand contribution. Every material leaf is a+B*b with
a,b in {-1,0,1}. Exact finite min/max depends only on the weak order of those
leaf values (and fixed, dominating terminal scores).
"""
from pathlib import Path
from fractions import Fraction
from itertools import product,combinations
import json
from scripts import leaper_design as L
from scripts.leaper_ab_learner_exposure import source_documents,write


def signature(lines,price):
    groups={}
    for a,b in lines:groups.setdefault(Fraction(a)+Fraction(b)*price,[]).append([a,b])
    return [sorted(groups[v])for v in sorted(groups)]


def analyze():
    lines=list(product((-1,0,1),repeat=2));knots=set()
    for (a,b),(c,d)in combinations(lines,2):
        if b!=d:
            crossing=Fraction(c-a,b-d)
            if crossing>0:knots.add(crossing)
    return dict(lines=[list(x)for x in lines],positive_possible_knots=[str(x)for x in sorted(knots)],
        below_unit_signature=signature(lines,Fraction(3,4)),second_below_unit_signature=signature(lines,Fraction(7,8)),unit_signature=signature(lines,Fraction(1)))


def run(panel,output):
    cfg=json.loads((panel/'plan.json').read_bytes());result=json.loads((panel/'result.json').read_bytes());docs=source_documents();fingerprints={}
    for group,world in cfg['worlds'].items():
        assert world['rule']==json.loads(docs[group+'/inputs.json'])['rule']
        c=L.compile_rule(L.ruleset_from_dict(world['rule']));fingerprints[group]=c.ruleset_fingerprint
        for root in world['roots']:
            from scripts.leaper_ab_learner_exposure import restore
            s=restore(c,root['record']);pieces=sorted((p.owner,p.current_type_id)for p in s.state.position.board if p)
            assert pieces==[(0,'A'),(0,'B'),(0,'K'),(1,'A'),(1,'B'),(1,'K')]
    algebra=analyze();assert algebra['positive_possible_knots']==['1/2','1','2']
    assert algebra['below_unit_signature']==algebra['second_below_unit_signature']
    learned={k:v[1]for k,v in result['models'].items()if not k.endswith('-Unit')}
    assert len(learned)==4 and all(.5<b<1 for b in learned.values())
    out=dict(verified=True,fingerprints=fingerprints,algebra=algebra,actual_final_learned_B=learned,Player_queries=0,training_updates=0,
        proposition='On each fixed finite full-width q0 tree in these removal-only laws, all B in the open cell(1/2,1) induce the same root optimal-action SET. All material leaves have the enumerated support; terminal values/order remain fixed and dominating, and finite min/max preserves weak order. This concerns policy-set identifiability, not equal numeric values/TD gradients or a unique price.',
        scope='Exact algebra for the complete finite material-support superset, whose possible knots need not all be realized at any root. It does not assume timed/public search is an independently proved full tree, equal paid work, equal arbitrary tie selection, or utility/learning equivalence. The observed16/16same D4-trained versusD6-trained frozen records are separate empirical evidence. Unit B1 is a boundary and can merge ties; no promotion/drop/aux expansion or oracleTRAIN.')
    write(output,out);return out
