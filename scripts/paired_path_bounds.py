"""Bounds on observed path regret, distinct from unobserved episode scores.

Replays saved records only. No Player, game generation, missing-state solving,
source value labels, policy optimization or production changes.
"""
from fractions import Fraction

from generic_chess.core.terminal import TerminalStatus
from generic_chess.session.result import session_result_from_terminal
from scripts.leaper_truth_compatibility import bind_context, digest, linear_interval_bounds
from scripts.research_record import record_value


def _rule_wdl_scope(context):
    session=context.session
    horizon=session.compiled.max_ply
    if type(horizon)is not int or horizon<=0:
        raise ValueError('finite positive rule horizon required')
    if session.compiled.declarations:
        raise ValueError('declaration choices outside move-only path scope')
    if record_value(session.result)!=record_value(session_result_from_terminal(session.state.terminal_status)):
        raise ValueError('external Session ending is not a Core path endpoint')
    if session.state.terminal_status.status is TerminalStatus.NO_CONTEST:
        raise ValueError('no-contest has no WDL endpoint potential')


def _qualified_endpoint(rule,initial,record):
    if record is None:
        return dict(status='MISSING_UNOBSERVED_PATH',context=None,error=None)
    try:
        endpoint=bind_context(rule,record,compiled=initial.session.compiled)
        _rule_wdl_scope(endpoint)
        root_record=record_value(initial.session.to_record())
        end_record=record_value(endpoint.session.to_record())
        length=len(root_record['actions'])
        if (len(end_record['actions'])<length or end_record['actions'][:length]!=root_record['actions']
            or {k:v for k,v in root_record.items()if k!='actions'}!={k:v for k,v in end_record.items()if k!='actions'}):
            raise ValueError('endpoint does not extend the exact initial full record')
        return dict(status='TERMINAL'if endpoint.session.result.status.value!='ongoing'else'ONGOING',context=endpoint,error=None)
    except (ValueError,KeyError,TypeError)as error:
        return dict(status='INVALID_SOURCE',context=None,error=str(error))


def _potential(context):
    result=context.session.result
    if result.status.value=='ongoing':return[-1,1]
    return[0,0]if result.winner is None else([1,1]if result.winner==0 else[-1,-1])


def analyze_pair(rule,initial_record,end_a_record,end_b_record,*,candidate_seat_a=0,timing_eligible=(True,True)):
    """Fixed two-slot pair, candidate seats exactly swapped by construction.

    V*(endA)-V*(endB) is a PREFIX regret contrast with candidate in seat0
    of A. It is not the counterfactual terminal outcome after an ongoing end.
    Both raw records must extend the one provided full initial record.
    Missing/invalid paths keep planned score-completion bounds, never a draw.
    """
    if type(candidate_seat_a)is not int or candidate_seat_a not in(0,1):
        raise ValueError('candidate seat must be integer0/1')
    if len(timing_eligible)!=2 or any(type(v)is not bool for v in timing_eligible):
        raise ValueError('timing qualifiers must be two explicit booleans')
    initial=bind_context(rule,initial_record)
    _rule_wdl_scope(initial)
    if initial.session.result.status.value!='ongoing':
        raise ValueError('planned initial context must be ongoing')
    endpoints=[_qualified_endpoint(rule,initial,r)for r in(end_a_record,end_b_record)]
    coefficient=1 if candidate_seat_a==0 else-1
    slots=[]
    for index,entry in enumerate(endpoints):
        context=entry['context'];terminal=entry['status']=='TERMINAL'
        candidate_seat=candidate_seat_a if index==0 else 1-candidate_seat_a
        actual_score=None
        if terminal:
            z=_potential(context)[0]
            actual_score=Fraction(1+(z if candidate_seat==0 else-z),2)
        slots.append(dict(slot=index,candidate_seat=candidate_seat,status=entry['status'],error=entry['error'],
            context=context.identity if context else None,
            observed_path_actions=(context.identity['ply']-initial.identity['ply'])if context else None,
            endpoint_minimax_WDL_bounds=_potential(context)if context else None,
            actual_candidate_game_points=str(actual_score)if actual_score is not None else None,
            candidate_score_completion_bounds=[str(actual_score)]*2 if actual_score is not None else['0','1'],
            timing_eligible=timing_eligible[index]))
    qualified=all(e['context']is not None for e in endpoints)
    complete=all(e['status']=='TERMINAL'for e in endpoints)
    prefix=None;same_endpoint=None
    if qualified:
        variables={}
        for entry,c in zip(endpoints,(coefficient,-coefficient)):
            context=entry['context'];key=digest(context.identity)
            if key not in variables:variables[key]=dict(bounds=_potential(context),coefficient=0)
            variables[key]['coefficient']+=c
        result=linear_interval_bounds([v['bounds']for v in variables.values()],[v['coefficient']for v in variables.values()])
        prefix=[str(v)for v in result['bounds']]
        same_endpoint=len(variables)==1
    # These are completions of actual GAME SCORES, not shared V* potentials.
    # Even identical ongoing endpoints can have different policy/TT futures.
    point_bounds=[sum((Fraction(s['candidate_score_completion_bounds'][j])for s in slots),Fraction())/2 for j in(0,1)]
    return dict(planned_games=2,qualified_observed_paths=sum(e['context']is not None for e in endpoints),
        actual_Core_terminal_games=sum(e['status']=='TERMINAL'for e in endpoints),
        same_complete_endpoint_context=same_endpoint,
        baseline_minus_candidate_observed_prefix_actor_WDL_regret_bounds=prefix,
        complete_episode_actor_WDL_regret_contrast=prefix[0]if complete else None,
        candidate_planned_mean_game_point_completion_bounds=[str(v)for v in point_bounds],
        complete_pair_timing_eligible=complete and all(timing_eligible),slots=slots,
        local_action_WDL_labels_created=0,
        scope='Fixed planned two-slot score-completion bounds, not actual utility for missing/invalid episodes. Prefix regret uses observed records only; true finite-game endpoint potentials are not expected continuation-policy outcomes.')


def observed_regret_sum(paths):
    """Weighted experienced actor-regret difference over explicitly named paths.

    This is a different target from a complete paired experiment. Opposite
    seat weights cancel an initial potential only for the same full context.
    Missing requested paths invalidate the target instead of being dropped.
    """
    terms={};failures=[];qualified=0
    def add(context,coefficient):
        key=digest(context.identity)
        if key not in terms:
            terms[key]=dict(bounds=_potential(context),coefficient=Fraction(),
                rule_fingerprint=context.identity['ruleset_fingerprint'],
                record_sha256=context.identity['record_sha256'],ply=context.identity['ply'])
        terms[key]['coefficient']+=coefficient
    for index,path in enumerate(paths):
        seat=path['candidate_seat'];raw_weight=path.get('weight',1)
        if type(seat)is not int or seat not in(0,1):raise ValueError('candidate seat must be integer0/1')
        if type(raw_weight)not in(int,str,Fraction):raise ValueError('path weights must be exact')
        weight=Fraction(raw_weight)
        if weight<=0:raise ValueError('observed target weights must be positive; exclude a path explicitly')
        initial=bind_context(path['rule'],path['initial_record'])
        _rule_wdl_scope(initial)
        endpoint=_qualified_endpoint(path['rule'],initial,path.get('endpoint_record'))
        if endpoint['context']is None:
            failures.append(dict(index=index,status=endpoint['status'],error=endpoint['error']));continue
        qualified+=1;sign=1 if seat==0 else-1
        add(endpoint['context'],sign*weight);add(initial,-sign*weight)
    active=[dict(context_sha256=key,**{k:v for k,v in term.items()if k!='coefficient'},coefficient=str(term['coefficient']))
            for key,term in terms.items()if term['coefficient']]
    bounds=None
    if not failures:
        bounds=['0','0']
        if active:
            result=linear_interval_bounds([t['bounds']for t in active],[t['coefficient']for t in active])
            bounds=[str(v)for v in result['bounds']]
    return dict(requested_paths=len(paths),qualified_paths=qualified,unqualified=failures,
        baseline_minus_candidate_experienced_actor_WDL_regret_bounds=bounds,
        residual_context_potentials=active,
        local_action_WDL_labels_created=0,
        scope='Explicit observed-path target, not completion of missing planned episodes or policy strength. Terms are full-context endpoint potentials; unequal/missing colors leave initial terms. Bounds are deterministic interval relaxations.')


def verify_forced_link(rule,parent_record,child_record):
    """Check one supplied forced edge; fixed-seat value equality, not identity.

    No missing edge is generated and no numeric state/action WDL is labelled.
    A failure means only that this exact supplied relation was not verified.
    """
    parent=bind_context(rule,parent_record);_rule_wdl_scope(parent)
    if parent.session.result.status.value!='ongoing':
        return dict(status='NOT_PROVED',reason='TERMINAL_PARENT')
    child=_qualified_endpoint(rule,parent,child_record)
    if child['context']is None:return dict(status='NOT_PROVED',reason=child['status'],error=child['error'])
    end=child['context']
    if end.identity['ply']!=parent.identity['ply']+1:
        return dict(status='NOT_PROVED',reason='ONE_RECORDED_EDGE_REQUIRED')
    if len(parent.legal_actions)!=1:
        return dict(status='NOT_PROVED',reason='MULTIPLE_ORDINARY_CHOICES')
    return dict(status='VERIFIED_FORCED_VALUE_EQUALITY',value_seat=0,acting_regret=0,
        parent_record_sha256=parent.identity['record_sha256'],child_record_sha256=end.identity['record_sha256'],
        rule_fingerprint=parent.identity['ruleset_fingerprint'],parent_ply=parent.identity['ply'],child_ply=end.identity['ply'],
        states_merged=False,numeric_WDL_labels_created=0,
        scope='Equality of true fixed-seat minimax potentials along this supplied sole-choice edge. Not equality of full state, player-to-move value, controller/TT memory or eventual policy return; no runtime quotient or substitution.')
