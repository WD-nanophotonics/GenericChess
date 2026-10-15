"""Experimental retained-tree threshold scheduler on complete rule horizons.

Finite-domain prototype, not a general depth-cutoff DFPN implementation. Uses
public-Core forward children and requires actual Session witness verification.
No TT, material, score prior, heuristic tie break or default solver change.
Threshold recursion can avoid repeated root descent; it does not promise fewer
expanded nodes. Full ordered histories remain separate tree paths.
"""
from dataclasses import dataclass
from math import isfinite
from time import perf_counter
from generic_chess.session.result import SessionStatus
from scripts.generic_win_proof import _Budget, _Interrupted, _same_state
from scripts.generic_session_win_proof import (
    SessionWinCertificate, SessionProofNode, replay_bound)
from scripts.generic_session_win_proof_batch_pn import (
    SessionBatchPNResult, _Forward, _Node, _children)


@dataclass(frozen=True)
class SessionThresholdResult(SessionBatchPNResult):
    recursive_calls: int = 0
    selections: int = 0


def _below(value, threshold):
    # None means unbounded, without undefined infinity-minus-infinity.
    return threshold is None or value < threshold


def _minimum(left, right):
    if left is None: return right
    if right is None: return left
    return min(left, right)


def _remaining(threshold, siblings):
    if threshold is None: return None
    total = sum(siblings)
    assert isfinite(total), 'finite rule-horizon open sum must be finite'
    out = threshold - total
    assert out > 0
    return out


def prove_session_win_threshold(session, *, target=None, max_nodes=4096,
        seconds=1., max_depth=8, cancel=None, _clock=perf_counter):
    target = session.state.position.side_to_move if target is None else target
    if type(target) is not int or target not in (0, 1):
        raise ValueError('invalid target')
    if type(max_depth) is not int or not 0 <= max_depth <= 128:
        raise ValueError('invalid depth')
    b = _Budget(max_nodes, seconds, cancel, _clock)
    inf = float('inf')
    frontiers = transitions = iterations = peak = calls = selections = 0
    cost = [0, 0]
    state, record, outcome = session.state, session.to_record(), session.result

    def result(status, reason, tree=None):
        cert = SessionWinCertificate(session.compiled.ruleset_fingerprint,
            record, state, target, tree) if tree is not None else None
        return SessionThresholdResult(status, cert, reason, b.nodes,
            b.elapsed(), 0, frontiers, transitions, iterations, peak,
            *cost, calls, selections)

    def visit(current, depth):
        nonlocal peak
        b.visit()
        node = _Node(current, depth)
        terminal = current.result
        b.poll()
        peak = max(peak, depth)
        if terminal.status is not SessionStatus.ONGOING:
            node.open = False
            node.terminal = terminal
            node.pn, node.dn = (0, inf) if terminal.winner == target else (inf, 0)
        elif depth >= max_depth:
            # The admission contract must make this impossible. Never label
            # this unknown leaf a draw/refutation to force threshold progress.
            raise ValueError('nonterminal beyond admitted rule horizon')
        return node

    def update(node):
        children = [child for _, child in node.edges]
        if node.session.state.position.side_to_move == target:
            node.pn = min(n.pn for n in children)
            node.dn = sum(n.dn for n in children)
        else:
            node.pn = sum(n.pn for n in children)
            node.dn = min(n.dn for n in children)
        node.open = node.pn != 0 and node.dn != 0 and any(n.open for n in children)
        if node.open:
            assert isfinite(node.pn) and isfinite(node.dn)

    def expand(node):
        nonlocal frontiers, transitions, iterations
        frontiers += 1
        iterations += 1
        own = node.session.state.position.side_to_move == target
        edges = []
        for choice, child in _children(node.session, b, cost):
            transitions += 1
            b.poll()
            inspected = visit(child, node.depth + 1)
            edges.append((choice, inspected))
            if (own and inspected.pn == 0) or (not own and inspected.dn == 0):
                break
        b.poll()
        if not edges:
            # No synthetic non-win when an unsupported ongoing frontier is empty.
            raise ValueError('ongoing session without choices')
        node.edges = edges
        update(node)

    def search(node, proof_limit, disproof_limit):
        nonlocal calls, selections
        calls += 1
        while node.open and _below(node.pn, proof_limit) and _below(node.dn, disproof_limit):
            b.poll()
            if not node.edges:
                expand(node)
                continue
            own = node.session.state.position.side_to_move == target
            ordered = sorted(((i, n) for i, (_, n) in enumerate(node.edges) if n.open),
                key=lambda row: (row[1].pn if own else row[1].dn, row[0]))
            index, child = ordered[0]
            others = [(i, n) for i, (_, n) in enumerate(node.edges) if i != index]
            next_value = None
            if others:
                j, second = min(others, key=lambda row: (row[1].pn if own else row[1].dn, row[0]))
                value = second.pn if own else second.dn
                # Preserve the old leftmost tie order exactly, including when
                # the selected child lies after an equally rated earlier sibling.
                if isfinite(value): next_value = value + (index < j)
            if own:
                pt = _minimum(proof_limit, next_value)
                dt = _remaining(disproof_limit, [n.dn for _, n in others])
            else:
                pt = _remaining(proof_limit, [n.pn for _, n in others])
                dt = _minimum(disproof_limit, next_value)
            before = b.nodes
            selections += 1
            search(child, pt, dt)
            assert b.nodes > before, 'threshold re-entry without progress'
            update(node)

    def certificate(node):
        b.poll()
        assert node.pn == 0
        if node.terminal is not None:
            return SessionProofNode(0, terminal=node.terminal)
        edges = node.edges if node.session.state.position.side_to_move != target else [
            next((c, n) for c, n in node.edges if n.pn == 0)]
        branches = tuple((c, certificate(n)) for c, n in edges)
        return SessionProofNode(1 + max(n.rank for _, n in branches), branches)

    try:
        b.poll()
        replay_bound(session)
        b.poll()
        if outcome.status is not SessionStatus.ONGOING:
            return result('ALREADY_TERMINAL', 'actual_session_terminal')
        # Conservative admission: root may have a played prefix, but this
        # sufficient bound uses the entire declared rule max_ply. Claims end
        # immediately, so do not increase the maximum ongoing action depth.
        if session.compiled.max_ply > max_depth:
            return result('UNKNOWN', 'requires_complete_rule_horizon')
        root = visit(_Forward(session.compiled, state, record, outcome), 0)
        search(root, None, None)
        b.poll()
        if root.pn == 0:
            tree = certificate(root)
            b.poll()
            return result('PROVEN_WIN', 'finite_session_all_defense_certificate', tree)
        return result('UNKNOWN', 'no_forced_win_in_exhausted_tree')
    except _Interrupted:
        return result('UNKNOWN', b.reason)
    except (NotImplementedError, ValueError):
        return result('UNKNOWN', 'unsupported_or_unreplayable_session')
    finally:
        assert _same_state(session.state, state) and _same_state(session.to_record(), record) and session.result == outcome
