"""TDLeaf receipt adapter for the existing public mainline q0 search.

No rules, tree walk, move ordering or qsearch implementation lives here. Full
GameSession PV replay supplies the learner's player-0 material feature. A score
without a matching literal leaf is unusable as an exact TDLeaf target.
"""
from __future__ import annotations

from math import isclose, isfinite
from time import perf_counter

from ..ai.alphabeta.player import AlphaBetaPlayer
from ..ai.alphabeta.tuning import SearchTuning
from ..ai.limits import SearchLimits
from .incremental import (
    BudgetEnd, FixedScaleSessionEnv, MATE, NonScoringTerminal, Receipt,
    SearchAttempt, SessionChoice, _material_features,
)


def search(env, model, *, depth=2, nodes=8192, seconds=5., seed=0,
           cancel=lambda: None, use_tt=True, use_ordering=True,
           pv_reserve_fraction=0.):
    """One mainline iterative q0 call; seed does not alter lexical ordering.

    Reuse mainline TT and ordering within this call. All captures have equal
    ordering value: no direct learned or human material price enters ordering.
    TT moves and cutoff-derived history still depend on this call's search
    results; ordering is not invariant to changes in the leaf model.
    Root tactical scans and optional pruning stay off. A new player per call
    prevents stale model epochs and deeper warm scores on shallower requests.
    Mainline terminal distance preferences remain. This is a different search
    policy from the historical randomized learner reference, not a speed alias.
    Qsearch is intentionally not exposed: its public PV omits q continuations.
    An optional fraction of the SAME full-query time allowance is reserved for
    literal PV replay. Zero preserves the historical allocation; a reserve is
    a different time-allocation policy, not permission to extend the deadline.
    """
    if not isinstance(env, FixedScaleSessionEnv):
        raise ValueError('mainline learner search requires a full Generic session')
    if depth < 1 or nodes < 1 or seconds <= 0:
        raise ValueError('invalid search budget')
    if not isfinite(pv_reserve_fraction) or not 0 <= pv_reserve_fraction < 1:
        raise ValueError('PV reserve fraction must be finite and in [0,1)')
    began = perf_counter()
    attempts = []
    decision = None

    def receipt(reason, *, action=None, value=None, phi=None, terminal=False, pv_choices=()):
        return Receipt(action, value, phi, terminal, (),
            0 if decision is None else decision.nodes + decision.qnodes,
            action is not None or terminal, 0, perf_counter() - began, reason,
            0 if decision is None else decision.completed_depth,
            attempts[-1].depth if attempts else 0, tuple(attempts), tuple(pv_choices))

    class Stop:
        reason = None
        last = float('-inf')
        def is_cancelled(self, force=False):
            # Mainline polls inside semantic operations. Avoid re-reading all
            # role stop files at every primitive; its own deadline still polls.
            now = perf_counter()
            if force or now - self.last >= .05:
                self.last = now
                try:
                    cancel()
                except BudgetEnd as error:
                    self.reason = str(error)
            return self.reason is not None

    stop = Stop()
    if stop.is_cancelled(force=True):
        return receipt(stop.reason)
    try:
        actual = env.terminal()
    except NonScoringTerminal:
        return receipt('NON_SCORING_UNKNOWN')
    if actual is not None:
        return receipt('terminal', value=MATE * actual, terminal=True)

    class Material:
        def evaluate(self, state):
            value = model.raw(_material_features(state.position,
                env.session.compiled, env.names))
            return value if state.position.side_to_move == 0 else -value

        def capture_order_value(self, mover, victim):
            # Existing orderer supplies TT/capture/promotion/killer/history
            # stages. Equal capture priority supplies no piece-value prior.
            return 0

    previous_nodes, previous_seconds = 0, 0.
    def progress(completed_depth, main_nodes, qnodes):
        nonlocal previous_nodes, previous_seconds
        paid = main_nodes + qnodes
        elapsed = perf_counter() - began
        attempts.append(SearchAttempt(completed_depth, paid - previous_nodes,
            elapsed - previous_seconds, True, 'complete'))
        previous_nodes, previous_seconds = paid, elapsed

    player = AlphaBetaPlayer(env.session.compiled, evaluator_override=Material(),
        use_tt=use_tt, use_ordering=use_ordering, use_disk_cache=False,
        tuning=SearchTuning(use_root_tactical=False, require_full_pv=True))
    remaining = seconds * (1 - pv_reserve_fraction) - (perf_counter() - began)
    if remaining <= 0:
        return receipt('time_limit')
    decision = player.choose_action(env.session, SearchLimits(max_depth=depth,
        max_nodes=nodes, max_time_seconds=remaining, quiescence_max_depth=0,
        quiescence_hard_max_depth=0), cancel_token=stop,
        progress_callback=progress)
    paid = decision.nodes + decision.qnodes
    if paid > previous_nodes:
        attempts.append(SearchAttempt(decision.completed_depth + 1,
            paid - previous_nodes, perf_counter() - began - previous_seconds,
            False, decision.termination_reason))
    if stop.is_cancelled(force=True):
        return receipt(stop.reason)
    if decision.result_source not in ('main_iteration', 'root_declaration', 'terminal'):
        return receipt('NO_LITERAL_COMPLETED_RESULT:' + decision.result_source)
    if decision.choice_kind == 'DECLARATION':
        choice = SessionChoice('DECLARATION', declaration_id=decision.declaration.declaration_id)
    elif decision.action is not None and decision.completed_depth:
        choice = SessionChoice('ACTION', action=decision.action)
    else:
        return receipt('NO_COMPLETED_ACTION')

    # Copy the already authoritative full session, then submit the public PV.
    # Replaying the entire played prefix at every query would duplicate root
    # history admission. The episode/auditor still independently replay records.
    leaf = FixedScaleSessionEnv(env.session, unit_type=env.unit_type,
                               use_runtime=env.use_runtime)
    if perf_counter() - began >= seconds:
        return receipt('PV_REPLAY_TIME_CAP')
    try:
        pv_choices=[]
        if choice.kind == 'DECLARATION':
            leaf.push(choice)
            pv_choices.append(choice)
        else:
            for action in decision.principal_variation:
                if stop.is_cancelled(force=True):
                    return receipt(stop.reason)
                if perf_counter() - began >= seconds:
                    return receipt('PV_REPLAY_TIME_CAP')
                step=SessionChoice('ACTION', action=action)
                leaf.push(step)
                pv_choices.append(step)
        actual = leaf.terminal()
        if actual is None:
            # Public q0 may stop just before a node-local winning declaration.
            win = leaf.winning_declaration()
            if win is not None:
                leaf.push(win)
                pv_choices.append(win)
                actual = leaf.terminal()
        if stop.is_cancelled(force=True):
            return receipt(stop.reason)
        if perf_counter() - began >= seconds:
            return receipt('PV_REPLAY_TIME_CAP')
        if actual is not None:
            # Preserve actual rule draws, and never turn NO_CONTEST into one.
            signed = decision.score * (1 if env.player() == 0 else -1)
            if (actual == 0 and signed != 0) or (actual != 0 and signed * actual < 900_000_000):
                return receipt('TERMINAL_VALUE_MISMATCH')
            return receipt(decision.termination_reason, action=choice,
                           value=MATE * actual, terminal=True,pv_choices=pv_choices)
        if any(d.outcome in ('RESTART', 'NO_CONTEST') for d in leaf.session.available_declarations()):
            return receipt('UNEXPORTED_NEUTRAL_DECLARATION_UNKNOWN')
        phi = leaf.features()
        value = model.raw(phi)
        signed = decision.score * (1 if env.player() == 0 else -1)
        if not isclose(signed, value, rel_tol=1e-12, abs_tol=1e-10):
            return receipt('PV_VALUE_MISMATCH')
        if len(decision.principal_variation) != decision.completed_depth:
            return receipt('TRUNCATED_PV_UNKNOWN')
        return receipt(decision.termination_reason, action=choice, value=value, phi=phi,pv_choices=pv_choices)
    except NonScoringTerminal:
        return receipt('NON_SCORING_UNKNOWN')
