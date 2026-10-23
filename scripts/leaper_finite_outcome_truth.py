"""Full-history outcome-set and exact uniform-policy truth for an old H6 rule.

Consumes the previously frozen homogeneous3x3 rule and all288 saved layouts.
No new rule/layout generator, Player rollout, learning or E0 prediction. The
new estimands are all reachable terminal outcomes and an ideal independent
uniform-legal-action policy at BOTH seats, not a finite PRNG-seed average.
"""
from collections import Counter
from fractions import Fraction as F
import argparse
import hashlib
import json
from pathlib import Path
import time

from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution as compile_rule
from generic_chess.core.transition import initial_state
from generic_chess.core.actions import action_to_dict
from scripts.leaper_microgames import ExactTree,Exhaustion,role_stop_requested
from scripts.leaper_explorer_truth import load,save,digest
from scripts.leaper_design import state_sha

RULE=Path('artifacts/leaper-all-quiet-h6-20261021/M_M-rules.json')
SUMMARY=Path('artifacts/leaper-all-quiet-h6-20261021/summary.json')


def occupation_statistics(tree,roots,future):
    """Three explicit mu laws; never pool roots with late decision histories."""
    weighted=Counter();terminal=Counter();ongoing=[s for s in tree.values if tree.edges[s]]
    def fork(s):return len({tree.values[ch]for _,ch in tree.edges[s]})>1
    for previous,root in roots:
        def visit(state,mass,saw_draw=False,saw_fork=False):
            children=tree.edges[state]
            if not children:
                terminal[state.terminal_status.status.value]+=mass
                weighted['terminal_ply']+=mass*state.ply_count
                if state.terminal_status.winner is None and not saw_draw:weighted['draw_without_ongoing_universal_draw']+=mass
                return
            weighted['decisions']+=mass
            d=future[state]=={0};f=fork(state)
            if d:
                weighted['universal_draw_decisions']+=mass
                if not saw_draw:weighted['first_ongoing_universal_draw']+=mass
            if f:
                weighted['fork_decisions']+=mass
                if not saw_fork:weighted['first_fork']+=mass
            sign=1 if state.position.side_to_move==0 else -1
            quality=[sign*tree.values[ch]for _,ch in children]
            weighted['suboptimal_decisions']+=mass*F(sum(v<max(quality)for v in quality),len(quality))
            for _,ch in children:visit(ch,mass/len(children),saw_draw or d,saw_fork or f)
        visit(root,F(1,len(roots)))
    assert sum(terminal.values())==1 and weighted['terminal_ply']==weighted['decisions']
    uniform=dict(nonterminal_histories=len(ongoing),universal_draw=sum(future[s]=={0}for s in ongoing),forks=sum(fork(s)for s in ongoing))
    root_mu=dict(histories=len(roots),universal_draw=sum(future[s]=={0}for _,s in roots),forks=sum(fork(s)for _,s in roots))
    return dict(uniform_initial_layout_mu=root_mu,uniform_all_ongoing_history_mu=uniform,
                uniform_policy_occupation_mu=dict(unnormalized_expected_counts_per_game={k:str(v)for k,v in weighted.items()},
                                                 universal_draw_decision_rate=str(weighted['universal_draw_decisions']/weighted['decisions']),
                                                 fork_decision_rate=str(weighted['fork_decisions']/weighted['decisions']),
                                                 suboptimal_decision_rate=str(weighted['suboptimal_decisions']/weighted['decisions']),
                                                 terminal_reason_probability={k:str(v)for k,v in terminal.items()}),
                scope='Occupation mu weights each ongoing decision by its probability of being visited, then normalizes by expected decisions/game. This differs from sampling a game then a uniform turn. Counts of visits are not probabilities of at least one event.')


def run(*,occupation=False):
    raw=RULE.read_bytes();rule=ruleset_from_dict(json.loads(raw));c=compile_rule(rule)
    old=next(w for w in load(SUMMARY)['worlds']if w['kinds']==['M','M'])
    assert len(old['roots'])==288 and c.max_ply==6 and c.repetition_limit==2
    started=time.perf_counter();tree=ExactTree(c,max_states=200000,seconds=300)
    spec=dict(question='For the same closed H6 homogeneous rule, do minimax DRAW, all-continuation DRAW and exact uniform-policy DRAW coincide?',
              source_rule_sha256=hashlib.sha256(raw).hexdigest(),source_summary_sha256=hashlib.sha256(SUMMARY.read_bytes()).hexdigest(),
              source_execution_sha='6ea35571272708f7e220fa3868f2ca1a4d0cf7ca',
              caps=dict(seconds=300,history_contexts=200000),
              mu='Uniform all288 previously frozen safe four-actor layouts; each starts with its declared fresh full history.',
              policy='At both seats independently choose uniformly among actual Core legal actions at each turn. This is a declared analytical policy, not an average over frozen finite PRNG seeds.',
              exposure='All old rules/layouts/WDL/depth results exposed. New terminal-set/policy diagnostics only, not blind tests.',
              stop='Only this existing rule; CLOSED on cap, no refill or widening.')
    roots=[]
    try:
        for previous in old['roots']:
            if role_stop_requested():raise Exhaustion('USER_STOP')
            state=initial_state(c,previous['setup']);value=tree.solve(state)
            assert value==previous['value']
            roots.append((previous,state))
    except Exhaustion as exc:
        return dict(format='leaper-finite-outcome-truth-v1',spec=spec,status=str(exc),roots=[],
                    unqualified_partial_contexts=len(tree.values),seconds=time.perf_counter()-started,rule=json.loads(raw))
    # Successor states always have strictly greater actual ply, so this order
    # does not identify distinct histories through Position or repetition keys.
    future={};policy={};counts=Counter()
    for state in sorted(tree.values,key=lambda s:s.ply_count,reverse=True):
        children=tree.edges[state]
        if not children:
            t=state.terminal_status
            v=0 if t.winner is None else 1 if t.winner==0 else -1
            future[state]=frozenset((v,));policy[state]=tuple(F(int(k==v))for k in(-1,0,1))
        else:
            future[state]=frozenset().union(*(future[ch]for _,ch in children))
            policy[state]=tuple(sum((policy[ch][j]for _,ch in children),F(0))/len(children)for j in range(3))
        assert sum(policy[state])==1 and all(p>=0 for p in policy[state])
        counts['contexts']+=1;counts['all_future_draw']+=future[state]=={0};counts['singleton_outcome']+=len(future[state])==1
        counts['minimax_draw_with_decisive_exit']+=tree.values[state]==0 and bool(future[state]-{0})
    rows=[]
    for previous,state in roots:
        rows.append(dict(id=state_sha(state),setup=previous['setup'],layout=previous['layout'],
                         wdl_player0=tree.values[state],terminal_outcomes_player0=sorted(future[state]),
                         uniform_policy_wdl_LDW=[str(p)for p in policy[state]],
                         all_future_draw=future[state]=={0},cooperative_decisive=bool(future[state]-{0}),
                         singleton_outcome=len(future[state])==1,
                         branches=[dict(action=action_to_dict(a),wdl_player0=tree.values[ch],
                                        terminal_outcomes_player0=sorted(future[ch]),uniform_policy_wdl_LDW=[str(p)for p in policy[ch]])for a,ch in tree.edges[state]]))
    dist=Counter((r['wdl_player0'],tuple(r['terminal_outcomes_player0']))for r in rows)
    exact_mean=[sum((F(r['uniform_policy_wdl_LDW'][j])for r in rows),F(0))/len(rows)for j in range(3)]
    extra=occupation_statistics(tree,roots,future)if occupation else None
    if extra is not None:
        occ=extra['uniform_policy_occupation_mu']['unnormalized_expected_counts_per_game']
        assert F(occ['first_ongoing_universal_draw'])+F(occ['draw_without_ongoing_universal_draw'])==exact_mean[1]
    return dict(format='leaper-finite-outcome-truth-v1',spec=spec,status='COMPLETE',rule=json.loads(raw),roots=rows,occupation=extra,
                root_joint_counts=[dict(wdl=k[0],terminal_outcomes=list(k[1]),count=n)for k,n in sorted(dist.items())],
                uniform_policy_mu_mean_LDW=list(map(str,exact_mean)),counts=dict(counts),seconds=time.perf_counter()-started,
                original_minimax_root_counts=dict(Counter(str(r['wdl_player0'])for r in rows)),
                source_code=Path(__file__).read_text(encoding='utf-8'),
                scope='Exact finite H6 full-history/declared-policy census. No inference about clock128 canonical openings, other policies, deployment strength or previously unseen rules.')


def main():
    cli=argparse.ArgumentParser();cli.add_argument('--output',required=True);cli.add_argument('--occupation',action='store_true');args=cli.parse_args()
    result=run(occupation=args.occupation);save(args.output,result)
    print(json.dumps({k:result.get(k)for k in('status','counts','root_joint_counts','uniform_policy_mu_mean_LDW','seconds')}))


if __name__=='__main__':main()
