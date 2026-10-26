"""Consume published action truth without searching or generating candidates.

A matching context authorizes attribution, not independent verification of WDL.
The conservative contract retains full rules, replay record and Session outcome.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
from typing import Any

from generic_chess.core.actions import action_to_dict
from generic_chess.rules.compiler import compile_legacy_ruleset_for_semantic_execution
from generic_chess.rules.schema import ruleset_from_dict, ruleset_to_dict
from generic_chess.session.serialization import deserialize_game_record, serialize_game_record
from generic_chess.session.session import GameSession
from scripts.research_record import record_value


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


@dataclass(frozen=True)
class Context:
    """Literal replay plus a public summary; never a solver or a TT key."""
    session: GameSession
    identity: dict[str, Any]
    legal_actions: tuple[dict, ...]


def bind_context(rule_payload, record_payload, *, compiled=None):
    rule = ruleset_from_dict(rule_payload)
    compiled = compiled or compile_legacy_ruleset_for_semantic_execution(rule)
    # Do not accept a compiled object supplied for another full RuleSet.
    from generic_chess.rules.schema import compute_fingerprint
    if compiled.ruleset_fingerprint != compute_fingerprint(rule):
        raise ValueError("compiled rules differ from the supplied full RuleSet")
    record = deserialize_game_record(json.dumps(record_payload))
    session = GameSession.replay(compiled, record)
    state = record_value(session.state)
    canonical_record = json.loads(serialize_game_record(session.to_record()))
    identity = dict(
        ruleset_fingerprint=compiled.ruleset_fingerprint,
        rule_sha256=digest(ruleset_to_dict(rule, include_metadata=False)),
        record_sha256=digest(canonical_record),
        state_sha256=digest(state),
        position_sha256=digest(state["position"]),
        ply=state["ply_count"], max_ply=compiled.max_ply,
        repetition_limit=compiled.repetition_limit,
        repetition_counts=state["repetition_counts"],
        history_sha256=digest(state["history"]),
        terminal=record_value(session.result),
        side_to_move=state["position"]["side_to_move"],
        initial_setup_key=canonical_record.get("initial_setup_key"),
    )
    return Context(session, identity, tuple(action_to_dict(a) for a in session.legal_actions()))


def compare_contexts(target: Context, source: Context):
    differences = [key for key in source.identity if source.identity[key] != target.identity[key]]
    return dict(status="INCOMPATIBLE" if differences else "COMPATIBLE",
                differences=differences,
                scope="Exact conservative context match; not proof of source WDL.")



def _require_move_frontier_scope(context):
    # Claims/declarations are Session choices outside legal_successors. This
    # scoped move-certificate format must not silently omit them at AND nodes.
    if context.session is not None and getattr(context.session.compiled,"declarations",()):
        raise ValueError("declaration choices are outside this move-certificate scope")


def _bounds(value):
    if (not isinstance(value, (tuple, list)) or len(value) != 2
            or any(type(v) is not int or v not in (-1, 0, 1) for v in value)
            or value[0] > value[1]):
        raise ValueError("WDL bounds must be ordered integer endpoints in -1,0,1")
    return tuple(value)


def action_coverage(context: Context, labels, root_bounds=None, *, value_seat=0):
    """Report source-claimed bounds and conservative action classifications.

    Unknown actions stay [-1,1]. A known root may classify a partial certificate;
    no known root is inferred from an incomplete action set. Values are relative
    to the named fixed seat, not implicitly the player to move. Contradictory
    root/action intervals raise rather than silently selecting one claim.
    """
    _require_move_frontier_scope(context)
    if type(value_seat) is not int or value_seat not in (0, 1):
        raise ValueError("value_seat must be integer 0 or 1")
    legal = {digest(a): a for a in context.legal_actions}
    if len(legal) != len(context.legal_actions):
        raise ValueError("duplicate canonical legal actions")
    by_action = {}
    for row in labels:
        if "value_seat" in row and (type(row["value_seat"]) is not int or row["value_seat"]!=value_seat):
            raise ValueError("action-label perspective differs from requested value seat")
        key = digest(row["action"])
        if key not in legal:
            raise ValueError("action label is outside the replayed legal frontier")
        if key in by_action:
            raise ValueError("duplicate action label")
        by_action[key] = _bounds(row["wdl_bounds"])
    root = _bounds(root_bounds) if root_bounds is not None else None
    maximize = context.identity["side_to_move"] == value_seat
    result = context.identity["terminal"]
    status = result["status"]
    no_contest = status == "no_contest" or result.get("declaration_outcome") == "RESTART"
    terminal_value = None
    if status != "ongoing" and not no_contest:
        winner = result["winner"]
        terminal_value = 0 if winner is None else 1 if winner == value_seat else -1
        if root is not None and not root[0] <= terminal_value <= root[1]:
            raise ValueError("root bounds contradict actual Session terminal")
    if no_contest and root is not None:
        raise ValueError("no-contest/restart has no WDL label")
    intervals = [by_action.get(k, (-1, 1)) for k in legal]
    if intervals:
        op = max if maximize else min
        frontier = (op(b[0] for b in intervals), op(b[1] for b in intervals))
        if root is not None and (root[1] < frontier[0] or root[0] > frontier[1]):
            raise ValueError("root and action bounds are inconsistent")
    else:
        frontier = None
    # Move to the current actor's perspective for one exact interval argument.
    # This is arithmetic over attributed labels, not a game-tree search.
    relative = {k: b if maximize else (-b[1], -b[0])
                for k in legal for b in [by_action.get(k, (-1, 1))]}
    relative_root = root if maximize or root is None else (-root[1], -root[0])
    root_lo, root_hi = relative_root if relative_root is not None else (-1, 1)
    refined = {}
    for key, (lo, hi) in relative.items():
        other_hi = max((v[1] for k, v in relative.items() if k != key), default=-1)
        # If alternatives cannot attain the root lower bound, this action must.
        refined[key] = (max(lo, root_lo) if other_hi < root_lo else lo, min(hi, root_hi))
        if refined[key][0] > refined[key][1]:
            raise ValueError("root constraints leave an action interval empty")
    rows = []
    for key, action in legal.items():
        lo, hi = refined[key]
        other_lo = max((v[0] for k, v in refined.items() if k != key), default=-1)
        other_hi = max((v[1] for k, v in refined.items() if k != key), default=-1)
        minimum_regret = max(0, other_lo-hi, root_lo-hi)
        maximum_regret = max(0, other_hi-lo)
        if len(legal) == 1:
            minimum_regret = maximum_regret = 0
        kind = ("OPTIMAL_SOURCE_CLAIM" if maximum_regret == 0 else
                "SUBOPTIMAL_SOURCE_CLAIM" if minimum_regret > 0 else "UNKNOWN")
        bounds = (lo, hi) if maximize else (-hi, -lo)
        rows.append(dict(action=action, wdl_bounds=list(by_action.get(key, (-1, 1))),
                         feasible_wdl_bounds=list(bounds), labelled=key in by_action,
                         regret_bounds=[minimum_regret, maximum_regret],
                         classification=kind))
    return dict(legal_actions=len(legal), labelled_actions=len(by_action),
                exact_action_labels=sum(a == b for a, b in by_action.values()),
                unlabelled_actions=len(legal)-len(by_action), value_seat=value_seat,
                source_root_bounds=list(root) if root is not None else None,
                frontier_bounds=list(frontier) if frontier is not None else None,
                actual_terminal_value=terminal_value,
                no_contest=no_contest,
                rows=rows, label_authority="SOURCE_CLAIM_NOT_RESOLVED_HERE")


def qualify(target, source, labels=(), root_bounds=None, *, value_seat=0):
    compatibility = compare_contexts(target, source)
    if compatibility["status"] != "COMPATIBLE":
        return dict(compatibility=compatibility, coverage=None,
                    quality="UNKNOWN_CONTEXT_MISMATCH")
    return dict(compatibility=compatibility,
                coverage=action_coverage(target, labels, root_bounds, value_seat=value_seat),
                quality="SOURCE_CLAIM_ONLY")


def paired_action_bounds(context: Context, labels, baseline_action, candidate_action,
                         root_bounds=None, *, value_seat=0):
    """Sharp one-decision WDL improvement bounds on one matched context.

    This is not an Arena score or a confidence interval. The selected actions
    must both belong to this literal frontier. Identical actions have exactly
    zero difference even when their values are wholly unknown.
    """
    coverage=action_coverage(context, labels, root_bounds, value_seat=value_seat)
    by={digest(row["action"]):row for row in coverage["rows"]}
    bkey= digest(baseline_action);ckey=digest(candidate_action)
    if bkey not in by or ckey not in by:
        raise ValueError("selected action outside current legal frontier")
    if bkey==ckey:
        delta=[0,0]
    else:
        b=by[bkey]["feasible_wdl_bounds"];c=by[ckey]["feasible_wdl_bounds"]
        # Report improvement for the actual side to move, regardless of input seat.
        delta=[c[0]-b[1],c[1]-b[0]] if context.identity["side_to_move"]==value_seat else [b[0]-c[1],b[1]-c[0]]
    return dict(improvement_bounds=delta,same_action=bkey==ckey,
                baseline=by[bkey],candidate=by[ckey],
                interpretation="Fixed-context one-decision source-WDL bounds; not policy strength or independent holdout.")


def verify_saved_tree(context: Context, nodes, *, value_seat=0):
    """Check an already supplied complete finite proof tree against public Core.

    This never selects roots or fills a missing node. Every reached full state,
    edge, terminal and WDL label must already exist in the supplied certificate.
    A missing defense or any unprovided continuation is a failed certificate.
    """
    from generic_chess.core.transition import legal_successors
    if type(value_seat) is not int or value_seat not in (0,1):
        raise ValueError("value_seat must be integer 0 or 1")
    _require_move_frontier_scope(context)
    session=context.session
    if session.result.status.value != session.state.terminal_status.status.value:
        raise ValueError("rule proof cannot substitute a Session resignation/declaration")
    indexed={};counts={"nodes":0,"edges":0,"terminals":0}
    for node in nodes:
        key=digest(node["state"])
        if key in indexed:raise ValueError("duplicate certificate full state")
        if type(node["value"]) is not int or node["value"] not in (-1,0,1):
            raise ValueError("invalid certificate WDL label")
        indexed[key]=node
    queue=[session.state];seen=set()
    while queue:
        state=queue.pop();wire=record_value(state);key=digest(wire)
        if key in seen:continue
        if key not in indexed:raise ValueError("missing certificate continuation")
        node=indexed[key]
        if node["state"]!=wire:raise ValueError("certificate state payload differs")
        seen.add(key);counts["nodes"]+=1
        children=node["children"]
        if state.terminal_status.is_terminal:
            if children:raise ValueError("terminal certificate has outgoing children")
            if state.terminal_status.status.value=="no_contest":
                raise ValueError("no-contest is not a WDL terminal")
            winner=state.terminal_status.winner
            expected=0 if winner is None else 1 if winner==value_seat else -1
            if node["value"]!=expected:raise ValueError("certificate terminal label differs")
            counts["terminals"]+=1
            continue
        actual={digest(action_to_dict(a)):(action_to_dict(a),child)
                for a,child in legal_successors(state,session.compiled)}
        provided={digest(ch["action"]):ch for ch in children}
        if len(provided)!=len(children) or set(actual)!=set(provided):
            raise ValueError("certificate does not cover the exact legal frontier")
        values=[]
        for action_key,(action,child) in actual.items():
            entry=provided[action_key]
            if entry["action"]!=action or entry["state"]!=record_value(child):
                raise ValueError("certificate edge differs from literal Core transition")
            if child.ply_count!=state.ply_count+1:
                raise ValueError("non-increasing certificate clock")
            child_key=digest(entry["state"])
            if child_key not in indexed:raise ValueError("missing certificate continuation")
            values.append(indexed[child_key]["value"]);queue.append(child);counts["edges"]+=1
        if not values:raise ValueError("ongoing certificate has no legal children")
        expected=(max if state.position.side_to_move==value_seat else min)(values)
        if node["value"]!=expected:raise ValueError("certificate local WDL equation differs")
    if seen!=set(indexed):raise ValueError("unreachable extra certificate states")
    root=indexed[digest(record_value(session.state))]
    return dict(status="VERIFIED_SUPPLIED_COMPLETE_TREE",counts=counts,
                root_value=root["value"],value_seat=value_seat,
                action_labels=[dict(action=ch["action"],wdl_bounds=[indexed[digest(ch["state"])]["value"]]*2,value_seat=value_seat)
                               for ch in root["children"]],
                scope="Only the supplied full-history finite tree; no missing-state solving or cross-rule transfer.")


def verify_bound_tree(context: Context, nodes, bound, *, direction="lower", value_seat=0):
    """Verify a supplied finite one-sided AND/OR strategy, without tree search.

    LOWER: one move at the named seat, every legal reply at the other seat.
    UPPER: every move at the named seat, one reply at the other seat.
    Existential nodes use exactly one supplied move; unknown leaves fail closed.
    """
    from generic_chess.core.transition import legal_successors,apply_action
    from generic_chess.core.actions import action_from_dict
    _require_move_frontier_scope(context)
    if direction not in ("lower","upper"):
        raise ValueError("direction must be lower or upper")
    if type(bound) is not int or bound not in (-1,0,1):raise ValueError("invalid WDL bound")
    if type(value_seat) is not int or value_seat not in (0,1):raise ValueError("invalid value seat")
    session=context.session
    if session.result.status.value!=session.state.terminal_status.status.value:
        raise ValueError("rule bound cannot substitute a Session resignation/declaration")
    indexed={digest(n["state"]):n for n in nodes}
    if len(indexed)!=len(nodes):raise ValueError("duplicate bound-certificate full state")
    pending=[session.state];seen=set();counts=dict(nodes=0,edges=0,terminals=0,existential_nodes=0,universal_nodes=0,selected_apply_calls=0,full_frontier_enumerations=0,generated_successors=0)
    while pending:
        state=pending.pop();wire=record_value(state);key=digest(wire)
        if key in seen:continue
        if key not in indexed:raise ValueError("missing bound-certificate continuation")
        node=indexed[key]
        if node["state"]!=wire:raise ValueError("bound-certificate state differs")
        seen.add(key);counts["nodes"]+=1;children=node["children"]
        if state.terminal_status.is_terminal:
            if children:raise ValueError("terminal bound-certificate has children")
            if state.terminal_status.status.value=="no_contest":raise ValueError("no-contest is not WDL")
            winner=state.terminal_status.winner
            value=0 if winner is None else 1 if winner==value_seat else -1
            if (direction=="lower" and value<bound) or (direction=="upper" and value>bound):
                raise ValueError("terminal does not satisfy claimed bound")
            counts["terminals"]+=1;continue
        provided={digest(ch["action"]):ch for ch in children}
        if len(provided)!=len(children):raise ValueError("duplicate bound-certificate action")
        existential=(state.position.side_to_move==value_seat)==(direction=="lower")
        if existential:
            if len(provided)!=1:raise ValueError("existential certificate requires one move")
            entry=next(iter(provided.values()));action=action_from_dict(entry["action"])
            canonical=action_to_dict(action)
            if canonical!=entry["action"]:raise ValueError("noncanonical bound-certificate action")
            child=apply_action(state,action,session.compiled)
            actual={digest(canonical):(canonical,child)}
            counts["existential_nodes"]+=1;counts["selected_apply_calls"]+=1
        else:
            actual={digest(action_to_dict(a)):(action_to_dict(a),ch)
                    for a,ch in legal_successors(state,session.compiled)}
            counts["full_frontier_enumerations"]+=1;counts["generated_successors"]+=len(actual)
            if not actual or set(provided)!=set(actual):
                raise ValueError("universal certificate is missing a legal defense")
            counts["universal_nodes"]+=1
        for action_key,entry in provided.items():
            action,child=actual[action_key]
            if entry["action"]!=action or entry["state"]!=record_value(child):
                raise ValueError("bound-certificate edge differs from literal Core")
            if child.ply_count!=state.ply_count+1:raise ValueError("non-increasing bound-certificate clock")
            pending.append(child);counts["edges"]+=1
    if seen!=set(indexed):raise ValueError("unreachable bound-certificate states")
    return dict(status="VERIFIED_FINITE_STRATEGY_BOUND",direction=direction,bound=bound,value_seat=value_seat,
                wdl_bounds=[bound,1] if direction=="lower" else [-1,bound],
                context=context.identity,certificate_sha256=digest(nodes),counts=counts,
                scope="Supplied finite rule-terminal move strategy only; no missing-state solving, heuristic leaves, declaration choices or TT reuse.")


def verify_action_bound(context: Context, action_payload, nodes, bound, *, direction="lower", value_seat=0):
    """Bind a supplied child strategy to one literal parent action."""
    _require_move_frontier_scope(context)
    actions=[a for a in context.session.legal_actions() if action_to_dict(a)==action_payload]
    if len(actions)!=1:raise ValueError("action certificate does not bind a unique legal parent action")
    child_session=GameSession.replay(context.session.compiled,context.session.to_record())
    child_session.submit(actions[0])
    child=_child_context(child_session,context)
    proof=verify_bound_tree(child,nodes,bound,direction=direction,value_seat=value_seat)
    return dict(action=action_payload,wdl_bounds=proof["wdl_bounds"],value_seat=value_seat,qualification=proof)


def _child_context(session,parent):
    if session.compiled is not parent.session.compiled:
        raise ValueError("child context must retain the exact compiled rule")
    state=record_value(session.state);identity=dict(parent.identity)
    identity.update(record_sha256=digest(json.loads(serialize_game_record(session.to_record()))),
                    state_sha256=digest(state),position_sha256=digest(state["position"]),
                    ply=state["ply_count"],repetition_counts=state["repetition_counts"],
                    history_sha256=digest(state["history"]),side_to_move=session.state.position.side_to_move,
                    terminal=record_value(session.result))
    return Context(session,identity,tuple(action_to_dict(a) for a in session.legal_actions()))


def linear_interval_bounds(intervals,coefficients,root_bounds=None):
    """Sharp linear bounds in the interval relaxation with one root maximum.

    Variables are actor-relative WDL values. Root truth constrains their maximum.
    Additional game-theoretic correlations are deliberately not assumed.
    """
    from fractions import Fraction
    def rational(x):
        if type(x) not in (int,str,Fraction):raise ValueError("weights must be exact integers/rational strings")
        return Fraction(x)
    if not intervals or len(intervals)!=len(coefficients):raise ValueError("invalid interval coefficient arity")
    bb=[_bounds(b) for b in intervals];cc=[rational(c) for c in coefficients]
    a,b=_bounds(root_bounds) if root_bounds is not None else (-1,1)
    if max(x[0] for x in bb)>b or max(x[1] for x in bb)<a:
        raise ValueError("root maximum constraint is infeasible")
    bb=[(lo,min(hi,b)) for lo,hi in bb]
    def extremum(sign):
        costs=[sign*c for c in cc]
        values=[lo if cost>=0 else hi for (lo,hi),cost in zip(bb,costs)]
        if max(values)<a:
            # Force at least one variable to attain the root lower bound. Choose
            # the least objective penalty; no game state or WDL is being solved.
            j=min((j for j,(_,hi) in enumerate(bb) if hi>=a),
                  key=lambda j:costs[j]*(a-values[j]))
            values[j]=a
        return sum((c*v for c,v in zip(cc,values)),Fraction(0)),values
    lower,lw=extremum(1);upper,uw=extremum(-1)
    return dict(bounds=[lower,upper],lower_interval_completion=lw,upper_interval_completion=uw)


def bound_same_context_pairs(context: Context, labels, pairs, root_bounds=None, *, value_seat=0):
    """Fixed planned-weight bounds; repeated actions share a single unknown.

    This function accepts ONE complete context. Different complete histories
    must remain separate. Unknown/failed slots keep their planned denominator.
    Bounds describe one-decision WDL differences, not games or confidence.
    """
    from fractions import Fraction
    coverage=action_coverage(context,labels,root_bounds,value_seat=value_seat)
    rows=coverage["rows"];keys=[digest(r["action"]) for r in rows]
    coefficients={k:Fraction(0) for k in keys};total=Fraction(0);unknown=Fraction(0);matched=0
    for pair in pairs:
        raw=pair.get("weight",1)
        if type(raw) not in (int,str,Fraction):raise ValueError("planned weights must be exact")
        weight=Fraction(raw)
        if weight<0:raise ValueError("negative planned weight")
        total+=weight
        b=digest(pair.get("baseline_action"));c=digest(pair.get("candidate_action"))
        if b not in coefficients or c not in coefficients:
            unknown+=weight;continue
        coefficients[c]+=weight;coefficients[b]-=weight;matched+=1
    if total<=0:raise ValueError("planned total weight must be positive")
    actor=context.identity["side_to_move"]
    intervals=[r["feasible_wdl_bounds"] if actor==value_seat else
               [-r["feasible_wdl_bounds"][1],-r["feasible_wdl_bounds"][0]] for r in rows]
    root=root_bounds if actor==value_seat or root_bounds is None else [-root_bounds[1],-root_bounds[0]]
    result=linear_interval_bounds(intervals,[coefficients[k] for k in keys],root)
    low,high=result["bounds"];low-=2*unknown;high+=2*unknown
    return dict(planned_slots=len(pairs),matched_legal_slots=matched,unknown_slots=len(pairs)-matched,
                planned_weight=str(total),unknown_weight=str(unknown),
                weighted_sum_bounds=[str(low),str(high)],mean_improvement_bounds=[str(low/total),str(high/total)],
                coalesced_action_coefficients=[dict(action=r["action"],coefficient=str(coefficients[k])) for k,r in zip(keys,rows)],
                scope="One matched full context; deterministic shared action variables, fixed denominator. Interval-relaxation outer bounds, no statistical independence or policy-strength claim.")


def revalidate_bound_strategy(source: Context,target: Context,nodes,bound,*,direction="lower",value_seat=0):
    """Explicit checked simulation of a supplied strategy on another history.

    Default context matching is unchanged. Only existing source moves are tried;
    a missing defense, illegal move or unsupported nonterminal leaf returns no
    proof. A failure says nothing about whether another strategy could work.
    """
    from generic_chess.core.actions import action_from_dict
    from generic_chess.core.transition import apply_action,legal_successors
    _require_move_frontier_scope(source);_require_move_frontier_scope(target)
    required=("ruleset_fingerprint","rule_sha256","position_sha256","ply")
    if any(k not in source.identity or k not in target.identity for k in required):
        raise ValueError("revalidation needs fully bound literal contexts")
    differences=[k for k in required if source.identity[k]!=target.identity[k]]
    if differences:
        return dict(status="NOT_PROVED_BY_THIS_CERTIFICATE",reason="ROOT_SCOPE_MISMATCH",differences=differences)
    original=verify_bound_tree(source,nodes,bound,direction=direction,value_seat=value_seat)
    by={digest(n["state"]):n for n in nodes};new={};seen=set();counts=dict(nodes=0,edges=0,early_terminals=0,selected_apply_calls=0,full_frontier_enumerations=0)
    pending=[(source.identity["state_sha256"],target.session.state)]
    try:
        while pending:
            old_key,state=pending.pop();wire=record_value(state);key=digest(wire)
            pair=(old_key,key)
            if pair in seen:continue
            seen.add(pair);old=by[old_key];counts["nodes"]+=1
            if state.terminal_status.is_terminal:
                if state.terminal_status.status.value=="no_contest":raise ValueError("target no-contest is not WDL")
                winner=state.terminal_status.winner;value=0 if winner is None else 1 if winner==value_seat else -1
                if (direction=="lower" and value<bound) or (direction=="upper" and value>bound):
                    raise ValueError("target terminal violates the source bound")
                if old["children"]:counts["early_terminals"]+=1
                item=dict(state=wire,children=[])
            else:
                if not old["children"]:raise ValueError("target ongoing at an unproved source leaf")
                provided={digest(ch["action"]):ch for ch in old["children"]}
                existential=(state.position.side_to_move==value_seat)==(direction=="lower")
                if existential:
                    if len(provided)!=1:raise ValueError("source existential skeleton differs")
                    edge=next(iter(provided.values()));action=action_from_dict(edge["action"])
                    child=apply_action(state,action,target.session.compiled)
                    actual={digest(action_to_dict(action)):(action_to_dict(action),child)}
                    counts["selected_apply_calls"]+=1
                else:
                    actual={digest(action_to_dict(a)):(action_to_dict(a),ch) for a,ch in legal_successors(state,target.session.compiled)}
                    counts["full_frontier_enumerations"]+=1
                    if set(actual)!=set(provided):raise ValueError("target legal defenses differ from supplied skeleton")
                children=[]
                for action_key,(action,child) in actual.items():
                    edge=provided[action_key]
                    if edge["action"]!=action:raise ValueError("source action is not canonical")
                    if child.ply_count!=state.ply_count+1:raise ValueError("target clock did not increase")
                    children.append(dict(action=action,state=record_value(child)))
                    pending.append((digest(edge["state"]),child));counts["edges"]+=1
                item=dict(state=wire,children=children)
            if key in new and new[key]!=item:raise ValueError("conflicting target strategy choices at one full state")
            new[key]=item
        target_nodes=list(new.values())
        checked=verify_bound_tree(target,target_nodes,bound,direction=direction,value_seat=value_seat)
    except ValueError as error:
        return dict(status="NOT_PROVED_BY_THIS_CERTIFICATE",reason=str(error),simulation_counts=counts,
                    limitation="Failure is not disproof; no alternative action or missing-state search was attempted.")
    return dict(status="REVALIDATED_FINITE_STRATEGY_BOUND",source_context=source.identity,target_context=target.identity,
                source_certificate_sha256=original["certificate_sha256"],default_context_comparison=compare_contexts(target,source),
                simulation_counts=counts,target_certificate=target_nodes,verification=checked,
                scope="Explicit same-rule/Position/clock strategy simulation on the target full history; not automatic label transfer, heuristic-score or TT-key reuse.")
