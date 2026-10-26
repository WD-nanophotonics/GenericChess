"""One-step Core terminal facts on explicit full-history contexts, not a Player.

New hypothetical successors are generated and counted. Ongoing children stay
[-1,1]; this is a depth-one bound inspection, not a complete-game solve.
"""
from generic_chess.core.actions import action_to_dict
from generic_chess.core.transition import legal_successors
from scripts.leaper_truth_compatibility import action_coverage,digest
from scripts.paired_path_bounds import _rule_wdl_scope
from scripts.research_record import record_value


def terminal_frontier(context,*,value_seat=0):
    _rule_wdl_scope(context)
    if type(value_seat)is not int or value_seat not in (0,1):
        raise ValueError('value seat must be integer0/1')
    session=context.session
    if getattr(session.compiled,'automatic_adjudications',()):
        raise ValueError('automatic adjudications are outside this finite WDL inspection scope')
    if session.result.status.value!='ongoing':
        raise ValueError('an ongoing parent context is required')
    before=record_value(session.state)
    if (context.identity['state_sha256']!=digest(before)
        or context.identity['record_sha256']!=digest(record_value(session.to_record()))
        or context.identity['ruleset_fingerprint']!=session.compiled.ruleset_fingerprint):
        raise ValueError('stale or mismatched full context snapshot')
    expected={digest(a):a for a in context.legal_actions}
    labels=[];children=[];seen=set()
    for action,child in legal_successors(session.state,session.compiled):
        wire=action_to_dict(action);key=digest(wire)
        if key not in expected or wire!=expected[key]or key in seen:
            raise ValueError('Core successor frontier differs from bound legal actions')
        seen.add(key)
        terminal=record_value(child.terminal_status)
        if terminal['status']=='no_contest':
            raise ValueError('no-contest child cannot receive a WDL value')
        bounds=None
        if child.terminal_status.is_terminal:
            value=0 if child.terminal_status.winner is None else 1 if child.terminal_status.winner==value_seat else -1
            bounds=[value,value]
            labels.append(dict(action=wire,wdl_bounds=bounds,value_seat=value_seat))
        children.append(dict(action=wire,state_sha256=digest(record_value(child)),
            ply=child.ply_count,terminal=terminal,wdl_bounds=bounds or[-1,1],
            truth='CORE_TERMINAL'if bounds is not None else'UNKNOWN_ONGOING'))
    if seen!=set(expected)or not children:
        raise ValueError('complete nonempty ordinary legal frontier required')
    if record_value(session.state)!=before:
        raise ValueError('hypothetical frontier mutated the actual parent')
    coverage=action_coverage(context,labels,value_seat=value_seat)
    child_by_action={digest(c['action']):c for c in children}
    for row in coverage['rows']:
        child=child_by_action[digest(row['action'])]
        row['absolute_WDL_authority']=child['truth']
        row['relative_WDL_optimality']=('PROVED_OPTIMAL'if row['regret_bounds'][1]==0 else
            'PROVED_SUBOPTIMAL'if row['regret_bounds'][0]>0 else'UNKNOWN')
        row['qualification']='Core terminal child facts plus complete bound ordinary frontier; arithmetic source-claim names retained below'
    return dict(context=context.identity,value_seat=value_seat,
        ordinary_legal_actions=len(children),new_hypothetical_Core_successors=len(children),
        Core_terminal_children=len(labels),ongoing_children=len(children)-len(labels),
        root_WDL_outer_bounds=coverage['frontier_bounds'],children=children,
        action_bounds=coverage['rows'],local_root_action_WDL_facts_created=len(labels),
        scope='One-step complete ordinary Core frontier at the exact supplied full history. Actual terminal child facts and Bellman outer bounds only; ongoing children are not solved or draws. No Player, new played game, training, TT substitution or complete-game solver.')
