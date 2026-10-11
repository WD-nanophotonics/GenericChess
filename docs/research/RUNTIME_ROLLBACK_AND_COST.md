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
