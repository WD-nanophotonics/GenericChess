"""Research-only root-WDL teacher using Core transitions and interval negamax.

The existing reference certifies every root ACTION. This finite-clock entry
answers only root WDL: a proven winning child suffices. No heuristic scores,
transposition quotient, replacement move engine or player integration.
"""
from dataclasses import dataclass
import time
from generic_chess.core.search_runtime import SearchPathRuntime
from generic_chess.core.terminal import TerminalStatus
from scripts.leaper_neural_rules import admitted


@dataclass(frozen=True)
class Bounds:
    lower: int
    upper: int


def solve_value(rules,session,max_nodes=1500):
    admitted(rules)
    if max_nodes<0:raise ValueError('node budget must be nonnegative')
    started=time.perf_counter()
    # Core, including complete repetition state and authoritative max-ply,
    # owns every transition and terminal. The finite clock bounds recursion.
    runtime=SearchPathRuntime.from_state(session.state,session.compiled)
    expanded=0;frontiers=0;shortcuts=0;terminal_count=0
    def visit():
        nonlocal expanded,frontiers,shortcuts,terminal_count
        terminal=runtime.terminal_status
        if terminal.status is not TerminalStatus.ONGOING:
            terminal_count+=1
            value=0 if terminal.winner is None else 1 if terminal.winner==runtime.position.side_to_move else -1
            return Bounds(value,value)
        if expanded>=max_nodes:return Bounds(-1,1)
        expanded+=1
        actions=runtime.legal_actions();frontiers+=len(actions)
        if not actions:
            # Ongoing without a legal action is not a DRAW certificate.
            return Bounds(-1,1)
        lower=upper=-1
        for a in actions:
            runtime.push(a)
            try:child=visit()
            finally:runtime.pop()
            lower=max(lower,-child.upper);upper=max(upper,-child.lower)
            if lower==1:
                shortcuts+=1
                return Bounds(1,1)
        return Bounds(lower,upper)
    result=visit();runtime.assert_balanced()
    label={-1:'LOSS',0:'DRAW',1:'WIN'}[result.lower] if result.lower==result.upper else None
    return dict(label=label,status='EXACT' if label is not None else 'UNKNOWN',bounds=[result.lower,result.upper],
                nodes=expanded,legal_actions_enumerated=frontiers,terminal_count=terminal_count,win_shortcuts=shortcuts,
                pushes=runtime.pushes,pops=runtime.pops,seconds=time.perf_counter()-started,
                scope='root WDL only; no certificate of every optimal action, finite authoritative clock, Core rules/history')
