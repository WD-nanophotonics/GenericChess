"""Standalone pure-Leaper WDL teacher, reusing the existing exact solver.

This is a scoped entry, not a new rule engine/search algorithm. Every legal
transition and terminal is Core's; a node-budget failure is UNKNOWN, not DRAW.
"""
import argparse,json
from scripts.leaper_neural_rules import admitted
from scripts.exact_generic_preference_solver_v3 import solve_root_threshold_v3
from generic_chess.rules.schema import ruleset_from_dict
from generic_chess.rules.compiler import compile_ruleset
from generic_chess.session.session import GameSession
from generic_chess.session.serialization import deserialize_game_record


def solve_session(rules,session,max_nodes=1500):
    admitted(rules);terminal=session.result
    if terminal.status.value not in ('ongoing','no_contest'):
        label='DRAW' if terminal.winner is None else 'WIN' if terminal.winner==session.state.position.side_to_move else 'LOSS'
        value={'LOSS':-1,'DRAW':0,'WIN':1}[label]
        return dict(label=label,status='EXACT',bounds=[value,value],basis='Core_terminal',nodes=0,all_root_actions_solved=True,action_values=[])
    solved=solve_root_threshold_v3(session.compiled,session.state,max_nodes=max_nodes,max_depth=None)
    label=solved.root_value if solved.strong else None
    # A proven winning legal action suffices for the root maximum even when
    # other actions remain unresolved. No analogous inference certifies DRAW
    # or LOSS while an action can still improve the root value.
    if label is None and any(x['value']=='WIN' for x in solved.action_values):label='WIN'
    rank={'LOSS':-1,'DRAW':0,'WIN':1}
    if label is not None:
        bounds=[rank[label],rank[label]]
    else:
        # One certified draw action proves nonloss; unresolved alternatives
        # may still win. Preserve UNKNOWN instead of inventing a draw target.
        lower=max((rank[x['value']] for x in solved.action_values if x['value'] is not None),default=-1)
        bounds=[lower,1]
    return dict(label=label,status='EXACT' if label is not None else 'UNKNOWN',bounds=bounds,
        basis='all_root_actions' if solved.strong else 'proven_winning_action' if label=='WIN' else 'budget_unresolved',
        nodes=solved.stats.get('states_expanded',0),all_root_actions_solved=solved.strong,action_values=list(solved.action_values))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--nodes',type=int,default=1500);a=p.parse_args()
    raw=json.load(open(a.input,encoding='utf-8'));rules=ruleset_from_dict(raw['rules']);c=compile_ruleset(rules)
    session=GameSession.replay(c,deserialize_game_record(json.dumps(raw['record'])))
    print(json.dumps(solve_session(rules,session,a.nodes),indent=2))
