# Wide readonly scalar feasibility and actual caller cost

Science remains OPEN. This is an isolated Windows/Python C-API prototype and
development evidence, not a new production backend or deployment. Existing
Native board/action caps, ABI, defaults and UI are unchanged. The complete
generated-rule target retains promotion, drops, auxiliary state and history.

## Decision and mechanism

A readonly large-board seam is feasible without routing through the old
8-bit action codec. The useful reading representation is the complete immutable
Core board tuple, with compile-owned capture rows and complete required square
auxiliary values. It reads actual actors/path occupancy rather than rebuilding
a projected full board on every query. No position/check/terminal cache is added.

The prototype compiles the existing semantic IR mechanically. Its declared
scalar subset supports ray/leap capture geometry, no-path/path-clear predicates
and source/target square-slot equality/inequality with global/per-owner scope.
State/zone guards, other path predicates, other square references and boolean
auxiliary slots explicitly decline compilation. Core continues to own all
transitions, legality, S3/S4, promotion/drop execution, history and adjudication;
this subset is not a substitute for the full generic domain. It provides only
scalar queries, not a legal-action or availability position capsule.

The private C capsules have distinct names, checked sizes and indices. Actual
old/new rules and position capsule exchanges reject with incorrect-name errors.
Paths use uint16 and row/query coordinates use wider integer fields; indices
255,256 and final cells323/575 are represented without the old packed action.
The primary C source is available beside this report's science archive.

## Cost-driven representation changes

|Version|Observed result|Decision|
|---|---|---|
|Full ctypes numeric carrier|Complete import dominates; actual push/pop is slower despite cheap C scan|Reject|
|C-owned compact Python payload|Local scalar/push reduction; narrow hook whole search remains mixed|Keep only as control|
|All actual SemanticEngine.in_check callers, same payload|More coverage alone remains mixed|Do not infer gain from coverage|
|Bounded empty-row polling|Synthetic q4 fixed-work reduction; generated12/18 cases become slower|Synthetic gain does not transfer|
|C direct full board import|Generated18/24 q4 cheaper,12 still mixed/slower|Full import remains a cost|
|Complete immutable board view|Six ordinary q4 generated pairs locally0.910–0.973x, with equal full decision/work tuples|Select one prospective end-to-end budget check|

Six fixed-work series contain192 actual searches/96 pairs. All recorded
non-timing decision, PV and work-counter fields agree, not merely selected
actions. The8-board generated control finishes an immediate tactical decision
at depth0; it is not ordinary qsearch evidence. Configured q0 also consumes the
child-check hook, so it is not a zero-query control. Subsequent representation
comparisons reuse exposed development roots, not independent validation data.

The extra4 profiled searches attribute only6.1%/10.6% of profiled q0/q4 whole
baseline time to _gave_check, while many S3/root checks remain elsewhere.
These inclusive profiler shares are not unprofiled wall-time savings.
Actual narrow/all-check query counts are reported separately. Numeric static
payload sizes range0.14–8.60MB for generated8/12/18/24 rules; these exclude
Python retained rows, copies, offsets and mapping/object overhead. Static
compile/initialization costs are reported separately and must be charged before
claiming an end-to-end first-call gain.

## Semantics and real stopping evidence

Five carrier versions each match3600 Core target/owner queries on the four
18/24 aux-flip controls. The compact-import and immutable-view versions each
also match115200 queries on128 declared typed states across16 mechanical
global/per-owner × equality/inequality × source/target variants. These are
finite scalar qualifications, not a legal reachable training curriculum or
full-domain theorem. Complete caller state/history/identity/depth rollback is
checked on normal pushes, failed pushes and actual searches.

Actual49-pattern compiled24-board controls execute cancellation requests while
the C scan is active. A bounded same-process request thread changes the existing
token; no Agent, delegation, extra model or inserted scan wait is involved.
Scheduled request, actual execution, exception and safe rollback are separate.
The last view version yields the GIL at bounded checkpoint groups and checks
inside the scan; it does not promise cancellation for a no-checkpoint caller.

The six actual AlphaBeta token controls all return cancelled, a legal retained
fallback and unchanged full session/history. Four observe the cancelled token
at an actual C callback; two short scans finish before the request executes.
A request can arrive in a later query than the one that scheduled it; query IDs
and timestamps preserve that distinction. Observed execution-to-safe-return is
roughly83–140us for the latest six, but scheduled-to-executed reaches about19ms. There is no
guaranteed scheduler latency or claim that a Python post-return poll interrupted
C. The first too-short-window assertion failure is preserved. Required active
RuntimeError/KeyboardInterrupt keep their exact objects and restore the runtime.

## Resource curves and publication state

The predeclared64-call narrow-hook16/64-second curve closed in2565.031s.
Of32 pairs,1 retains a deeper layer and31 the same; no shallower case. The
single crossing is24-board/aux-on/q0/16s, D9 versusD8 in one order, with the
same action/score and a different longer PV. The other order isD9/D9. All31
other retained tuples agree. This is an observed development threshold crossing,
not stable/general gain or strength. Partial work differs at time cutoffs;
ordinary concurrent load is an interpretation limit. This curve compares search
allowances, reporting extra static preparation separately; its budgets were not
extended.

A distinct prospective24-call immutable-view curve is running for the exposed
generated12/18/24 q4 roots,16/64 seconds and both orders. Incremental readonly
compile and player initialization are deducted from the same end-to-end allowance.
The8-board immediate tactical control is already retained in the fixed study
and is explicitly excluded from an ordinary-q curve, not resampled. This new
premise followed the recorded representation failures; the two different curves
are not a split of one planned>1hour run. No result is claimed before it closes.

## Failures and collaboration limits

Private script failures include an undefined Provider alias, a ne-guard initial
position rejected by Core, an unimported exception class, a profile.py standard
library shadow, a legacy/semantic fixture mismatch, and a short cancellation
window assertion. They were diagnosed and repaired with original evidence kept.
One initial alias-failed search and125568 differential query pairs completed before failed
scripts' final saves; they are counted as executed, not qualified saved results.
One additional cancelled search failed its active-window assertion before its final save. The initial smoke declaration says8 normal pushes; the actual per-version result is4.
The invalid spatial selector is not a valid state-guard decline; a separate
valid-Core state-guard/bool-aux control supplies that evidence.

Fresh channel roots and complete primary/AUX41 threads were privately saved.
Primary advice is unchanged. AUX41 reports new small-rule price experiments and
a finite inventory plateau; those games, trees and UCI isolation are not
independently reproduced here. Adopt the interpretation limits: strictR>kN,
R262 is not a uniform k=3/N90 saturation threshold, and changing both candidate
and opponent cannot isolate a candidate scale effect. Defer that line while
completing search attribution. No auxiliary wake, checkout write, merge or
resource exclusivity request occurs. No measured team-efficiency percentage
is inferred. Raw Slack/account/receipts remain private and excluded from Git.

## Reproducible science checkpoint

Explicit115-member archive:299594bytes, SHA256
7eaef48f6e6e7a4091879220884c7825ea6d592b32227e5d437c3e64e269b15b.
All member hashes,38 Python ASTs and72 JSON records were checked. It excludes
raw Slack/account/receipts, pstats, binaries and the still-running view curve.
The legacy imports counter for the last version counts carrier entries;
it does not mean a full native board projection was copied. Published source
copies and archive members are exact private-prototype versions.

The all-check bridge is a temporary process-local attribution experiment that
restores the class method in finally. It is not a production injection interface.
Cancellation qualifications are finite tested cases, not a guarantee for every
unbounded guard list or no-checkpoint caller. Any later production integration
must retain explicit Core fallback and a local caller boundary; this is a
concrete consequence of the observed coverage/transport costs, not an approval
queue or demand for a new framework.
