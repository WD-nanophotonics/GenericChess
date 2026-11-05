# Root allocation and bound-return studies —2026-10-31

Three finite default-OFF candidates are CLOSED without decision-quality success.
All96 Player returns were saved. All five edited production files were restored
byte-for-byte to45af8cf27c089f128a7017cb209e8a97c485eddd before publication.
No product default, game, training, Native build, worker or AUX state changed.
Publication resumed2026-11-05 after a gap; no offline time was credited.

| Candidate | Actual fitness | Result | End point |
|---|---:|---|---|
| Strict prior root-gap extension |32returns/16pairs/8families|2active families,16same complete choices|Frozen4-family gateFAIL;PN not started|
| MTD(f) root driver with existing Q|32returns/16pairs/8families|7different choices,5calls hit256-pass guard beforeD1|Only2changed families retained any completed iteration;stop engineering failure,PN not started|
| Fail-soft Q return with common PVS|32returns/16pairs/8families|All8families actual tighter-upper activity,16same complete choices|Frozen changed-choice gateFAIL;PN not started|

All calls used a fresh public AlphaBetaPlayer/TT, commonPVS ON, diskOFF,
explicit Native legality/check/availability, DEFAULT evaluation,Q4/hard8,
D64/500k nodes and one second constructor+packing+choose budget. Input Core
compilation is outside that per-call clock but inside batch cost. Final JSON
encoding is outside the per-call clock and inside batch cost. All returns met
predeclared1.1s timing tolerance; atomic/cooperative service is not a hard OS
preemption guarantee. Complete literal rules/layouts were saved before Core or
fitness, every slot retained, OFF/ON order counterbalanced; no replacement,
refill, threshold relaxation or old cap extension followed the results.
These are prospective DEVELOPMENT combinations with exposed primitive/parent
rules, not independent population holdouts. They cannot establish class strength.

## Strict root-gap allocation

A completed ordinary iteration could nominate one strict best action using its
returned lower bound versus all alternative upper bounds. The next iteration
gave that action one extra main ply, at root only. A selective iteration could
not nominate another target. Root numeric TT cutoff/store was suppressed while
prior best-action ordering and ordinary childTT remained. This uses existing
search-policy bounds, not a proof of uniform leaf horizon or WDL.

The32-return batch took32.629499s. Independent saved-data acceptance replayed
166Core PV plies and checked99root attempts/754completed child-bound rows.
There were63complete ordinary attempts without strict bound separation,
16first-Q/D1 attempts,16incomplete attempts,2strict seeds and2selective attempts.
Only families5,7 actually extended and neither changed the final choice. Every
paired full choice is identical, hence its selected-action value difference is
exactly[0,0] even where absolute WDL is unknown. This is not whole-policy equality.
No true-action gap can be inferred merely from a loose/tied returned bound.

## MTD(f) compatibility failure

The [primary author page](https://people.csail.mit.edu/plaat/mtdf.html) was read
in full; exact HTML remains private. Its zero-window memory driver motivated
one root-only implementation using existing negamax/TT. The complete typed
LOWER-bound witness was retained when intervals met; the last fail-low action
need not achieve the converged value. Shared node/time/cancellation budgets
never reset; a256-pass guard prevented uncontrolled convergence loops.

The batch took27.864828s. Seven pairs changed full action, but five ON calls
hit the pass guard before completingD1, spending only about0.03–0.04s and
returning legal fallback. That lower time is **not acceleration**. The other
changed completed-result families were only1,7. Original metadata's simple
activity/changed-choice gate passed; this newly observed engineering failure
separately disqualified optional PN, rather than rewriting the frozen gate.
No pass-limit increase, pivot tuning or repaired fitness rerun occurred.
Saved acceptance replayed102Core PV plies and checked1713returned zero-window
passes, including exact bracket convergence and retained typed LOWER witness.
Different-choice true value intervals remain[-2,2]; none is silently DRAW.

Six separately registered underlying D1 diagnostics on exposed root6 used
beta0/1/255 and Q4-first-iteration reserve versus directQ0. The former returned
root bounds0/1/255, each from inherited-alpha clipping; direct static evaluation
returned1564 in all three windows. These are valid but loose fail-hard bounds,
not an established Core correctness defect. One first recorder invocation failed
before imports; then one real zero-duration UTC interval was rejected. Its saved
return stayed intact and uncredited; only four unexecuted slots resumed.
No frozen Player fitness slot was repeated.

## Optional fail-soft Q return study

A separate default-OFF option returned the best encountered bound rather than
inherited alpha on Q fail-low exits, preserving terminal/declaration priority,
mandatory evasions, noisy frontier,Q depths and budget aborts. Runtime and
portable routes both changed. This did not change the baseline's intended
contract or fit a test expectation to current output.

Finite qualification saved448underlying calls:384Q and64main calls on32complete
root/one-ply-prefix states. Saved-data verification confirms32Core/runtime wide-Q
pairs,32wide-main style pairs and256valid narrow returns, with no censoring or
value mismatch. These use shared Core and finite Q policy, not an independent
rules engine or universal proof. Two new causal D1 controls then found value1564
and two-pass MTD convergence with the new option. This does not repair/relabel
the original five guard failures or authorize their rerun.

The subsequent Q-only quality trial left MTD(f) OFF in both arms. Its32returns
on16new6x6literal layouts took32.728703s; all8families exercised tighter upper
returns, but all16paired complete choices stayed identical. One root retained
an extra completed iteration without changing choice; that is not quality gain.
Saved acceptance replayed105Core PV plies. PN remained NOT_STARTED_GATE_FAILED.

Necessary controls passed: initial root-gap target runs19and40;MTD abstract16,
Core/product41, then expanded Core8;Q-specific11 and relevant Q/Native/declaration93.
Repeated invocations are validation, not independent samples. Metadata erratum:
a frozen preparation note says45unique Core/product MTD checks; the distinct
scope is44(8Core+36product), plus16abstract=60. Exact originals remain unchanged.
A proposed64x30s fixed-depth cost matrix was deferred before any such call, in
favor of the bounded actual-quality trial. No new identity/cache framework or
extra chooser was built.

## Delivery and next decision

[Lossless project-only originals and frozen source DATA](data/leaper_bound_trials_20261031/manifest.json)
contain587individually gzip-compressed members,4,424,788decoded bytes. Each has
compressed/decoded SHA256 and exact original bytes. Never execute capsule strings;
only ordinary saved-data readers reproduce acceptance. External-paper contact
information and Slack/account wrappers remain private. Final saved readers
replayed373Core PV plies in total; this is finite semantic binding, not new games
or independent solving. Frozen source versions correspond to their measured
stages, including the pre-counter semantic option and later countered quality
option. Restored production is not presented as measured candidate code.

Latest autonomous dd70abef442f95afe97dbb1aa001254e58bd9584 review was fully read
on resumption. Adopt STOP on these closed panels and further excluded-TT/bias
prerequisites. The next actual research is its one bounded runner-up root resource
allocation, not another variant of these thresholds. Matched games remain a
separate future decision after stable real action differences; no strength claim
or additional game/parameter matrix follows from this report.
