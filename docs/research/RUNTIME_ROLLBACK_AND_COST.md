# Runtime rollback and caller-cost controls —2026-10-11

Base200608a6550f76da271389076da65aca04eb75a6. This record separates a real
exception-safety repair from private cost prototypes; evaluator, q, UI and
installed Native defaults stay unchanged. Results are exposed development
controls, not independent strength/WDL evidence.

## Selected repair

An ordinary SearchPathRuntime.push adds a child occurrence before constructing
its persistent snapshot and appending history. If snapshot construction raises,
old cleanup removes that occurrence only when an imported-key bridge exists.
Without a bridge, root position/search key/snapshot/history appear restored but
the actual mutable occurrence table retains a child count. Remove only the
bridge-key condition; retain child_occurrence_added and removed_history==0.
The latter prevents a second decrement after post-history cleanup.

Four Chess/Shogi ordinary/forced-hash reproductions fail before repair. Twelve
new product controls exercise repeated pre-history failure, complete/opaque
history, old child count1, forced collisions and post-history terminal failure.
They compare copied numeric counts and entry multiplicity within each hash bucket,
not root-only projections, table size or list order. Successful retry preserves
public state/terminal semantics and old1→2 counts.79 related tests pass.
The first test version had a tuple-count lookup error; two later collision tests
mistook bucket order for state. Both failures/source versions are retained.

Four real player controls use Core/installed Native on Chess/Shogi. Injected
MemoryError propagates, leaves GameSession unchanged and restores actual counts;
the next same-player call constructs a different Runtime and returns legally.
UI worker source catches Exception and exits. There is no observed UI false draw,
natural allocation-failure frequency or globally exhausted-memory recovery claim.
Independent DEV_AUX Task007–010 on sidemissiona58f1e40 separately found a same-
Runtime false repetition after the old fault, tested16 original/candidate lifecycle
cells, and calibrated multiplicity-aware detection. Task008 AST comparison matches
this working Runtime to its candidate; it is not execution of primary tests.
Its prior root-projection restoration claim is explicitly corrected. Independent
outputs stay in that branch, rather than copied into this publication archive.
Task010 additionally shows a same-fault nonterminal retry can desynchronize the
persistent digest from actual counts before repair; no TT wrong-cutoff run or
natural incident is claimed. Key equality alone is therefore insufficient.

## Private cost alternatives

|Mechanism|Finite semantics/work evidence|Caller result and selection|
|---|---|---|
|Strict canonical hand sharing/lazy owner dictionaries|275 mixed children,108 typed/noncanonical controls,8 minimal-AB D2 traces;4066 Chess hands and6070/7022 Shogi hands avoid reconstruction|No controlled wall/utility claim; retain private|
|Direct immutable BoardShape reuse, bounded128 entries|Arithmetic/invalid-input controls;8 D2 traces;64 fixed calls plus4 completed D2 calls|D2 about0.980x, short roots mixed/adverse;64 controlled1/4s calls change no action/score/depth; defer|
|Provider-owned static decoded syntax, bounded2048 entries|Fresh owner/base/actor validation and binding;275 mixed children;8 D2 traces;7168 Chess/24300 Shogi eviction checks|64 fixed+4 D2 mixed;64 controlled1/4s calls no action/score/depth gain; defer. Owned carrier bytes217408/385912 exclude borrowed IDs|
|Executed-write hash witness|275 mixed children,296 distant/stale controls,8 D2 traces; full nonboard projection retained|64 fixed+4 D2: most roots adverse despite fewer scanned cells; defer without time expansion|
|Evaluator-owned legacy occupancy indices|3469 original-map/weighted-score comparisons,48 generated-state comparisons and8 D2 exact traces; fixed compile metadata assumption|64 warm fixed+4 completed D2 costs improve locally (quiet D2 about0.985x);32 fresh-evaluator fixed calls include setup and retain adverse cases.64 controlled1/4s calls change no action/score/depth. Defer deployment;38/42 old tests passed under hook and4 pseudo_attacks-spy tests fail because hook bypasses helper|

The first extent time batch overlapped primary CPU tests and is descriptive only;
its failure is preserved. Subsequent direct-extent and syntax time batches used
explicit auxiliary source-only windows with no primary CPU overlap. Such ACKs
are observed coordination, not an atomic lease or uptime guarantee. Native
accepted-frontier counts do not include every C entry/return when decoding aborts.
DEV_AUX Task005 verifies that split; unchanged completed-no-abort controls retain
their scope. Active product fields currently copy accepted validated frontier
counts into decisions; no budget/backend retry consumer was found in the bounded
core/AI/script source search. Do not add a production counter without a concrete use.

## Validation and reproducibility

The first full regression wrapper timed out at180s without saved partial stdout;
that is incomplete, not passing. The later600s wrapper preserves stdout/status and exposes default sandbox
temporary-directory setup errors. A third unchanged-suite run uses a fresh
workspace-owned basetemp; previous outputs remain separate. That run executes
the entire active suite with one local-only Git delivery test failing during its
temporary bare-origin push. This is not a passing full-suite claim; the failing
workflow case passes unchanged under the Git subprocess permission boundary.
Thus 2076 active tests pass in the complete workspace-temp run and the
remaining local-only Git workflow test passes in the focused permission-aware
run. This is composed validation, not a single all-green full-suite run.
Data index runtime_cost_controls_20261011.json pins explicit Agent-only producers,
results, failure versions and local-slot metadata. No Slack bodies/account/private
inputs are included. Dependencies include earlier availability/provider/physical
archives and weighted bridge source. Reproduction restores producer-relative paths,
uses the pinned base plus this one-condition Runtime diff, installed supported
Native binary and existing pytest environment. Windows-blocked DLL is not rebuilt.
write_witness_time.py remains prepared but unexecuted. Index warm fixed, equal-time and fresh-evaluator calls ran serially inside04:06:30–04:11:30 UTC auxiliary source-only window; each caller owns fresh session/player and installed supported Native route. Candidate evaluator metadata is prepared before warm calls, but inside fresh-evaluator calls. Setup1.2–9.9ms and owned metadata costs remain visible, not universal compile gains.

Next choose one residual caller mechanism only when fixed work and equal-time
usefulness justify it; scoped legacy indexing never substitutes semantic attack
authority or claims complete generated-rule support. Keep original adverse rows,
failed premises, backend routes and setup/memory costs visible.

## Changed witness premise

The all-trial witness negative motivated a distinct formal-only prototype:
AST wraps exactly Runtime._push_impl's formal engine._transition call. Only its
first same-parent WorkingPosition records actual writes; legality/nested work
uses original allocation. Full typed nonboard diff and exact parent/child fallback
remain.275 mixed public children/full hashes and18 typed/trial checks pass;8
minimal-AB D2 pairs retain full trace/work. One setup error captured the original
hash function in copied AST globals, so tracking-only first outputs are retained
and explicitly separated; the corrected hook records actual witness hits.
This is a private prototype, not a deployed generic execution interface.

Formal-only witness controlled64 fixed+4 completed D2 calls remain mostly adverse:
Chess-middle1.002x, tactic1.449x, EP1.019x; Shogi-middle1.062x, tactic1.053x,
promotion1.070x, drop1.143x. Chess-promotion0.973x is favorable. Counts2726
tracked formal and2818 untracked legality/nested work are from8 minimal-AB roots,
not the q4 caller's transition totals. Defer product and equal-time expansion;
fewer scanned cells alone did not offset witness/factory/bookkeeping cost.

Remaining hand copy-on-access cost runner is prepared but unexecuted: the fixed
resource window could not safely contain it, so its start guard stopped before
any engine work. See hand_cost_pending_20261011.json; renew the ACK before reuse,
without automatic window extension or a performance claim.

## Subsequent hand and evaluator ownership controls

The previously prepared hand caller experiment was unexecuted because its
latest-start guard had expired. That record remains unchanged. A fresh declared
04:25-04:30 UTC auxiliary source-only window allowed the same64 fixed512node
calls plus4 completedD2 calls at04:25:01-04:25:42. Actual batch40.85seconds;
all non-time decisions/work match. Seven of eight fixed-root aggregate costs
are adverse; quiet ChessD2 ratio1.027. Shogi-drop ratio0.904 is a mixed
short-call observation, not a deployed gain. Counter bookkeeping belongs to
this private copy-on-access implementation's measured cost. Defer it without
an equal-time expansion. Its setup field measures counter clearing only and
cannot establish constructor savings.

A distinct candidate reads the actual execution facade's six evaluator metadata
fields into an evaluator-owned shallow view. It retains original pseudo_attacks
and anchor_square helpers, friendly blockers, pin convention and legacy geometry;
it does not replace them with an occupancy index or semantic attack authority.
The actual facade fingerprint and board size are retained; referenced tables
are borrowed.3517 finite map/score checks and24 foreign-fingerprint rejection
checks agree; eight lexical minimalD2 full traces/work agree. Four generated
4/6 seed7/21 roots and their first16 legal children remain development inputs.
Nineteen original evaluation tests, including the original helper spies, pass
under the constructor hook. Pytest reports a cache-write permission warning;
this is distinct from a test failure. Raw stdout was observed in the tool result,
while the saved helper-test record contains exit/status and scope only.

The unchanged original evaluator can evaluate a material-only pure semantic
compiled input with no legacy metadata. Unconditionally preparing the view
instead raises AttributeError(types_by_id). Preserve this negative: finite
weighted-legacy equivalence does not establish complete evaluator-interface
support. No product integration or task-domain reduction follows.

The construction-inclusive64 fixed+4D2 caller assay ran04:31:23-04:32:03 UTC
inside a separately confirmed04:31-04:36 source-only window. An invocation
before04:31 hit its guard before engine execution; retain that preflight failure.
Actual batch39.45seconds, matched actions/scores/non-time counters,3179 accepted
Native calls per completed quietD2 and no fallback. QuietD2 ratio0.997;
fixed aggregates range0.891-1.470, five of eight adverse. Defer the unconditional
view and equal-time expansion. No evaluator/q/UI defaults change.

All four paired repeats remain. For both candidates, Chess-tactic aggregate
adversity is dominated by the first candidate call15/16ms versus5ms. Shogi-drop
aggregate favorability is dominated by baseline82/87ms and71/72ms calls,
while other pairs are near unity. Cause is unknown. No outlier removal,
after-result success-standard change or improved-outcome rerun was performed.
Resource ACKs constrain DEV_AUX's work, not an atomic machine lock or a claim
of all-machine idle. Fixed work, cost and completion utility stay distinct.

Evidence: data/hand_and_metadata_cost_20261011.json,20 hashed archive members,
with the installed-control/weighted-bridge/hand-probe sources in its declared
prior archives. Agent-owned producer output only; no raw Slack/account records
or user inputs. The next concrete correctness issue is the opaque imported-key
bridge's target allocation before mutation; its source plan is retained pending
the independent auxiliary allocator witness, without an asserted repair.


## Opaque migration preparation and comparison boundary

Independent DEV_AUX Task014 isolated a new target-occurrence constructor failure:
the old opaque count was removed before target allocation; cleanup raised an
AssertionError while retaining the original MemoryError in its context and lost
one actual count. Complete-history controls did not reach that constructor.
The primary target-first candidate restored the selected constructor boundary
in four normal/colliding/nested controls and passed69 related/2081 full tests.
Those results are retained, but are not complete transaction acceptance.

Task016 then exposed a different operation. With an equivalent public imported
repetition mapping reordered and exact identities sharing a forced hash bucket,
list.remove compares an earlier dataclass occurrence before deleting the old one.
One comparison allocation failure left the old entry present; target-first rollback
added its count again,1 to2, while the root snapshot projected recovery. This
counterexample is preserved at independent revision
[6ec3e20d](https://github.com/WD-nanophotonics/GenericChess/tree/6ec3e20d72cd7c29febdffbff39e39e777a0165a/results/dev_aux/task016).

The final repair locates the old removal index before any target/count/journal
mutation, prepares target storage, then deletes the already located entry by
index. The original bridge restoration remains. This retains the constructor
repair and moves the allocation-capable comparison to the unmodified state.
Two new comparison/no-fault controls check the original exception object,
actual count multiplicity, snapshot items/digest and same-instance retry/pop.
Prior snapshot, history, nested and collision controls remain unchanged.
These are finite one-fault boundaries, not general persistent OOM immunity,
asynchronous interruption safety or a reproduced natural UI incident.
Final71 focused/2083 full active tests pass; own primary evidence:
data/opaque_migration_preparation_20261011.json.
