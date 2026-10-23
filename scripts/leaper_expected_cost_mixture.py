"""Derived finite expected-node mixture curve; no new games or policy adoption.

The coin chooses an entire L or H policy once per deployment, independently of
role/context and separately from actor RNGs. Equality is aggregate EXPECTED
nodes, not a hard per-game allocation or a timed execution of the mixed policy.
"""
import argparse
from pathlib import Path
from fractions import Fraction as F
from scripts import leaper_design as L
from scripts.leaper_budget_calibration import serial


def analyze(d):
    r=L.load(d/'results.json');assert r['status']=='CLOSED';ww=L.load(d/'inputs.json')['worlds'];ss={(s['world'],s['pair']):s for s in r['slots']};n=len(ww);cost={};utility={}
    assert all(s['status']=='finished'and s['utility'][0]==s['utility'][1]for s in r['slots']),'Missing outcomes keep mixture unidentified, not known-only imputation'
    for w in ww:
        for p in ('LL','HL','LH'):
            sl=ss[w['world'],p];g=L.load(d/sl['receipt']);cost[w['world'],p]=sum(q['decision']['nodes']+q['decision']['qnodes']for q in g['queries']);utility[w['world'],p]=F(sl['utility'][0])
    CL=2*sum(cost[w['world'],'LL']for w in ww);CH=sum(cost[w['world'],'HL']+cost[w['world'],'LH']for w in ww);CA=sum(cost[w['world'],'LL']+cost[w['world'],'LH']for w in ww)
    UL=F(0);UH=sum(utility[w['world'],'HL']-utility[w['world'],'LH']for w in ww)/(2*n);UA=sum(utility[w['world'],'LL']-utility[w['world'],'LH']for w in ww)/(2*n)
    out={'status':'CLOSED','physical_input_worlds':n,'physical_games_referenced':len(r['slots']),'new_physical_games':0,'old_recorded_endpoints':{'always_low':{'mean_utility':UL,'sum_two_role_nodes':CL},'always_high':{'mean_utility':UH,'sum_two_role_nodes':CH},'role_adaptive':{'mean_utility':UA,'sum_two_role_nodes':CA}},'mixture_definition':'Separate independent external coin once per deployment chooses complete L or H candidate, fixed L reference unchanged; same p for every input and physical role. Actor RNG stream/caller/history/TT policy retained.','UNKNOWN':0}
    if CH==CL:out['identified']=False;out['reason']='Endpoint node costs equal; no unique probability matches adaptive cost.'
    else:
        p=F(CA-CL,CH-CL);out['identified']=0<=p<=1;out['probability_high']=p
        if 0<=p<=1:
            UM=UL+p*(UH-UL);CM=F(CL)+p*(CH-CL);assert CM==CA
            # Independent second derivation directly mixes each role payoff.
            direct=sum((1-p)*(utility[w['world'],'LL']-utility[w['world'],'LL'])+p*(utility[w['world'],'HL']-utility[w['world'],'LH'])for w in ww)/(2*n)
            assert direct==UM
            out.update(matched_expected_nodes=CM,mixture_mean_utility=UM,role_policy_minus_uninformed_mixture=UA-UM,scope='POSTHOC exact finite expected-node curve, not preregistered selection/promotion, a played mixed policy, per-game equal resource, IID generalization, or a wall-time guarantee. Coin/selector engineering and timing overhead not measured. All endpoint records are complete; shared LL/complementary roles are derived reuse.')
        else:out['reason']='Adaptive cost outside convex endpoint support; do not extrapolate.'
    L.write_record(d/'expected-node-mixture-curve.json',serial(out));print(serial(out),flush=True)


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();analyze(a.output)
if __name__=='__main__':main()
