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

The prospective24-call complete-view curve closed967.336s. Incremental readonly
compile and player initialization are charged to the same16/64s totalallowance.
All12 pairs retain identical complete action/score/PV/depth/policy tuples:
0deeper/12same/0shallower.12board retainsD2/D3 with effectiveq4;18/24 retainD1
with effectiveq0 at both16/64s, despite configuredq4 and higher candidatepartial
qnodes. No hardq/check-budget abort explains those outcomes: ordinary time
expires before the first q4D2 is retained. Compilation/preparation sometimes
costs0.16s at18 and0.61s at24 and is not excluded from this result. The8board
immediate tactical case remains in the fixed controls, explicitly not resampled.

Decision: preserve the readonly view as a finite viable primitive, defer
production/interface adoption and do not extend these budgets chasing depth.
Fixed-cost reductions did not change useful retained decisions here. The next
actual work began with one16s profiled Core pending-q4D2 consumer diagnostic on
2017/18board. It again retainsD1/effectiveq0. In the profiled call,301140 physical
transitions/to_position constructions and283024S3 trials accompany18116 runtime
push/check calls. iter_legal_action_bindings has10.621s inclusive, transitions
3.196s, terminalprobe4.344s and _gave_check0.777s; these overlap and cannot be
summed as recoverable walltime. Selftime separates7million checkpoints, board
candidate scheduling and repeated transition/materialization. Do not revive the
rejected old lazy/S3 route without a changed consumer premise and a finite test.
Choose one required Core trial/representation consumer next; no position patch,
Elo campaign, evaluator fitting, arbitrary cap lift or framework prerequisite.

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

Final explicit122-member archive:313901bytes, SHA256
3cfbfc28fcc62460f38e492c07050b50b56025c99b4c75ddb66ffd80b6add258.
All member hashes,39 Python ASTs and78 JSON records were checked. It excludes
raw Slack/account/receipts, pstats and binaries; both declared curves are closed.
The legacy imports counter for the last version counts carrier entries;
it does not mean a full native board projection was copied. Archive members preserve exact private-prototype bytes. Standalone published
source copies have only CRLF-to-LF normalization; code content is unchanged.

The all-check bridge is a temporary process-local attribution experiment that
restores the class method in finally. It is not a production injection interface.
Cancellation qualifications are finite tested cases, not a guarantee for every
unbounded guard list or no-checkpoint caller. Any later production integration
must retain explicit Core fallback and a local caller boundary; this is a
concrete consequence of the observed coverage/transport costs, not an approval
queue or demand for a new framework.

Publication workflow correction: git diff --check flagged CR line endings; the
PowerShell sequence did not halt before the first commit/push. That check was
not passed. Standalone public text is now normalized to LF, while the original
science ZIP remains unchanged. Relevant66 tests passed. Subsequent outgoing
checks stop on failure; this is a resolved workflow defect, not a private-data
publication or production-code change.

Actual research searches:299 as explicitly accounted in the data index;280 fixed/curve calls are not the total. Original failures, both cancellation versions and5profile calls remain separate. No active producer or necessary user action remains; science is OPEN.
