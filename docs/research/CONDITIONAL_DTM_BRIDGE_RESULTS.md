# Pure DTM/horizon guard qualification

2026-10-04. The previously proposed conditional arithmetic now has a small
prototype in scripts/conditional_dtm_bridge.py and3 independent test groups.
No table files, external positions, source probes, downloads or outcome labels.
This is not an operational certificate source or an admitted deployment corpus.

For an ongoing root, accept only exact signed DTM half-moves consistent with
independently established side-to-move WDL. DTZ, ambiguous zero, contradictory
sign, missing source/semantic premises and possible earlier repetition remain
unknown[-1,1]. Source/state conversion, same moves/goals, exact minimax DTM,
mate priority and absence of other earlier draw mechanisms are explicit
UNVERIFIED premises until an actual independently audited source supplies them.
Passing True flags is not evidence that the premises hold.

Remaining H=max_ply-absolute_ply, never a reset FEN clock. Conservative bound
max_current_repetition_count+H<repetition_limit excludes an earlier repetition
trigger; if it fails, the prototype refuses an exact label. Other history rules
are a separate premise, not inferred from that count. For DTM sign s, |D|<=H
retains owner-zero sign s*(1 for owner0-to-move else-1); |D|>H yields0 only
under ALL premises. Unlimited draw remains finite draw. Mate at the final ply
precedes horizon draw, consistent with the local rule contract.

Independent abstract signed-terminal trees validate minimax horizon truncation
for both owners, winning/losing orientation, distance3..10 and horizons1..12.
They are arithmetic controls, not newly observed Chess tablebase positions.
Terminal-first wrapper asks the authoritative game interface first; cached
terminal inconsistency is rejected by PublicGame. Local terminal wins/draws
override all certificate arguments. RESTART/NO_CONTEST and explicit censored
terminals remain unknown rather than being overridden by a favourable DTM.

Remaining work is substantial: real source/checksum/library verification, board
and provenance conversion, position/certificate association, trusted history,
castle/en-passant scope and exact same rules/goal semantics. The wrapper does
not authenticate arbitrary certificate argument dictionaries or associate them
with a real ongoing state. It must NOT be placed in production label collection
before that adapter exists. Current <=5-piece Gaviota possibility still cannot
label full-inventory Chess contexts or supply Shogi outcomes.

This completes memo's pure arithmetic/terminal-guard backup while leaving the
independent deployment evidence gap open. No old mate fixture was deepened and
no observer budget, Goal, worker or workflow machinery was added.
