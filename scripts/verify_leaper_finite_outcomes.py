"""Independent leaf-weight verifier using public GameSession copies.

No producer ExactTree, cached values, outcome-set recursion or Position merge.
Each complete history contributes its exact product-of-legal-counts mass.
"""
from copy import copy
from fractions import Fraction as F
from collections import Counter
import argparse
import json
import time

from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.session.session import GameSession
from scripts.leaper_explorer_truth import load,save
from scripts.leaper_design import state_sha
from scripts.leaper_microgames import role_stop_requested


def verify(packet,seconds=300):
    assert packet['status']=='COMPLETE'
    c=compile_rule(ruleset_from_dict(packet['rule']));start=time.perf_counter();counts=Counter();last=0.;weighted=Counter();event_sums=Counter()
    for root in packet['roots']:
        s=GameSession(c,initial_setup_key=root['setup']);assert state_sha(s.state)==root['id']
        mass=Counter();outcomes=set()
        def walk(session,weight):
            nonlocal last
            counts['contexts']+=1
            now=time.perf_counter()
            if now-start>=seconds:raise RuntimeError('VERIFICATION_CAP_UNKNOWN')
            if now-last>=.2:
                last=now
                if role_stop_requested():raise RuntimeError('USER_STOP')
            if session.result.status.value!='ongoing':
                value=0 if session.result.winner is None else 1 if session.result.winner==0 else -1
                mass[value]+=weight;outcomes.add(value);counts['leaves']+=1
                weighted['terminal_ply']+=weight*session.state.ply_count
                return value,{value},F(0),F(0)
            actions=session.legal_actions();assert actions
            child_results=[]
            for action in actions:
                child=copy(session);child.submit(action);counts['edges']+=1
                child_results.append(walk(child,weight/len(actions)))
            child_values=[r[0]for r in child_results];outcome_set=set().union(*(r[1]for r in child_results))
            value=(max if session.state.position.side_to_move==0 else min)(child_values)
            is_draw=outcome_set=={0};is_fork=len(set(child_values))>1
            weighted['decisions']+=weight;weighted['universal_draw_decisions']+=weight*is_draw;weighted['fork_decisions']+=weight*is_fork
            sign=1 if session.state.position.side_to_move==0 else-1;qualities=[sign*v for v in child_values]
            weighted['suboptimal_decisions']+=weight*F(sum(v<max(qualities)for v in qualities),len(qualities))
            any_draw=F(1)if is_draw else sum((r[2]for r in child_results),F(0))/len(child_results)
            any_fork=F(1)if is_fork else sum((r[3]for r in child_results),F(0))/len(child_results)
            return value,outcome_set,any_draw,any_fork
        value,_,any_draw,any_fork=walk(s,F(1));event_sums['first_ongoing_universal_draw']+=any_draw;event_sums['first_fork']+=any_fork
        assert value==root['wdl_player0'] and sorted(outcomes)==root['terminal_outcomes_player0']
        assert [mass[k]for k in(-1,0,1)]==list(map(F,root['uniform_policy_wdl_LDW']))
        assert sum(mass.values())==1
        counts['roots']+=1
    assert counts['contexts']==packet['counts']['contexts']
    if packet.get('occupation')is not None:
        expected=packet['occupation']['uniform_policy_occupation_mu']['unnormalized_expected_counts_per_game'];n=len(packet['roots'])
        for k,v in weighted.items():assert v/n==F(expected[k])
        for k,v in event_sums.items():assert v/n==F(expected[k])
        assert F(expected['draw_without_ongoing_universal_draw'])+event_sums['first_ongoing_universal_draw']/n==F(packet['uniform_policy_mu_mean_LDW'][1])
    return dict(verified=True,counts=dict(counts),occupation_verified=packet.get('occupation')is not None,seconds=time.perf_counter()-start,
                scope='Independent full-history leaf-probability and minimax check of the existing H6 rule; no E0 or new policy rollout.')


def main():
    p=argparse.ArgumentParser();p.add_argument('--packet',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    result=verify(load(args.packet));save(args.output,result);print(json.dumps(result))


if __name__=='__main__':main()
