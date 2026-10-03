# Frozen movement-inclusion versus task-dominance check

The task algebra proves monotonicity when an unchanged context gains an optional
action with unchanged successor/payoff semantics. It does not automatically
prove type dominance from geometric movement inclusion: replacing R by Q also
changes checks, opponent legality and terminal outcomes. Resolve this premise
before treating the composer/type lattice as a prior validation constraint.

One sparse Chess context, owner0 to move: own K=(6,4), own B=(5,5), focal
type R or Q=(3,3); enemy K=(7,6), enemy P=(3,4). Empty hands/history rights.
Common-frame condition: all five ordinary focal substitutions start with
neither King in check and nonterminal status. No other pieces or repairs.
This is a semantic context, NOT a member of the frozen full-inventory sampling
population; do not use it to tune that population or average it into scores.

Pre-execution prediction: R capture(3,3)->(3,4) leaves the legal noncapturing
King escape(7,6)->(6,7) with positive ongoing custody. Q's same capture is
stalemate, since it additionally controls(6,7) without checking enemy K; all
other escapes are controlled by own K or B. Terminal draw scores zero by the
unchanged task. R legal coordinate actions are included in Q's, but mapped
successors/payoffs differ. Prediction for complete root scores: R1,Q0; if Q
has another winning action, record it rather than repair the context. Even
then the capture-level premise check remains interpretable.

Enumerate all focal actions/opponent replies, then replay each target capture.
Verify raw-position legal replies, enemy check and Core terminal result.
Compare canonical(from,to,promotion) action sets; preserve distinct typed public
action identities in evidence. At most two scored roots, 2,000 materializations,
ten seconds, external15-second timeout. No deeper search or coefficient sweep.

A pass refutes a naive implication from movement inclusion to task dominance,
not the proved pure optional-action monotonicity theorem and not approximate
material usefulness. Terminal semantics and context matter. Human Chess values,
Xiangqi holdout, installed engine profile and context weights stay untouched.
