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
    if type(value_seat) is not int or value_seat not in (0, 1):
        raise ValueError("value_seat must be integer 0 or 1")
    legal = {digest(a): a for a in context.legal_actions}
    if len(legal) != len(context.legal_actions):
        raise ValueError("duplicate canonical legal actions")
    by_action = {}
    for row in labels:
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
                action_labels=[dict(action=ch["action"],wdl_bounds=[indexed[digest(ch["state"])]["value"]]*2)
                               for ch in root["children"]],
                scope="Only the supplied full-history finite tree; no missing-state solving or cross-rule transfer.")
