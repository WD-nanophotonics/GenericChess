# Priced transfer, root order cost, and a legal PV witness

Science remains OPEN. This study keeps the shipped backend/default/UI unchanged
and adds a concrete behavioral regression. The canonical-root variant below is
a private research candidate, not a silent product replacement. Detailed curve
counts are generated from saved results; failures and source identities remain
in the accompanying archive.

## Frozen questions and actual interfaces

Ten new families are selected before results: sizes8/12/18/24/32, two seeds each
(3701/3702 through3741/3742), unchanged bilateral_random/hybrid generator,
32attempts,45s preparation cap and repr-sorted Random(seed+7000) walk to ply8.
All eight8..24families yield two roots. Both32families are45s censored without a
saved root; neither is replaced. Initial and played roots are dependent, and
opposite arm orders are repeated measurements, not independent samples.

Every available root preserves the complete rules, board/current/base, hands,
auxiliary state, SHA history and actor/check events. Native/Core full action sets
are compared before resource queries. This is generated legacy movement mixtures
compiled to semantic IR; it is not coverage of every semantic-DSL mechanism or
the full generated32domain. The separate legal witness exercises live aux state
and current-type effects. Complete generated rules remain the target.

Both Native arms own their creating modules without changing the default loader.
The oldV2 and shipped-scopeV2 source sets differ in only native_module.c: main
ordering plus its diagnostic/capability constant. Payload5/capsules and complete
state semantics remain private; the product V1/<=16 guard and Core fallback stay.
Both arms use the same existing rule-derived board/current and hand/base vectors,
rounded once to integers, with dynamic terms disabled. No price fitting, human
labels or Xiangqi holdout reads. Query budgets exclude IR/profile preparation;
caller and separately reported construction/compilation cost must not be hidden.

## Completion and choice evidence

|Comparison|Calls/pairs|Deeper / same / shallower|Matching policies with equal scores|Actual q4 calls|
|---|---:|---:|---:|---:|
|resource|128/64|12 / 44 / 8|44|16 -> 18|
|tt|128/64|12 / 48 / 4|48|24 -> 22|
|q0|128/64|22 / 36 / 6|36|0 -> 0|
|backend|128/64|28 / 36 / 0|36|8 -> 18|
|interior-transfer|128/64|6 / 54 / 4|54|18 -> 18|


Ordinaryq0 still preserves mandatory checked evasions with hard8. Different
ordinary-q policies or completed depths are different finite objectives; a
larger depth alone is not a score, WDL or strength improvement. Resource runs
include work in unfinished later iterations. They are not fixed-work timers.
DefaultTT64 cold and warm searches are separate; warm searches pay their preceding
cold call and retain only that same arm's table. Actual hits/cutoffs establish
reuse; no free warm-speedup claim or machine-exclusivity assumption.

Six unique changed actions from the original pricedq4 curve receive ONE common
pure-Core childD2/ordinaryq0/hard8 label, no TT/ordering/Native, max20000nodes/4s.
All six finish that objective. Of64 delivered-action pairs,58 are literally the
same action,4 improve the finite Core value,2 tie,0 worsen. These are three changed
positions observed in both orders, not six independent successes. The reference
is a stated shallow Core objective, not true WDL or the requestedq4 minimax.

At3702-ply8/8s both orders deliver a new action with a mate-valued reference.
A separate full Core enumeration checks4957 actions in11.930s. The new action
has one opposing legal reply, followed by actual checkmate. All opposing replies
are covered. The old action has48 opposing replies,44 without that short
certificate; its longer-term outcome stays UNKNOWN, not loss. A second verifier
reconstructs every opposing frontier, five saved winning-terminal witnesses and
literal Native state/history. This proves a <=3root-ply strategy for this one
selected action; it is not an implementation of an auxiliary generic prover,
a WDL gain over the old action, or a substituted rollout reward.

## Do not blame prices from different cohorts

The jointly closed actual-price D2/q4 sample has8pairs from only two families:
kernel/caller geometric ratios.53964/.54300, accepted-transition ratio.52894;
2pairs are slower. Unit leaves close14pairs, kernel.69081,4slower. On the SAME
8pair closure intersection, unit/priced transition ratios are.73434/.52894,
and kernel ratios.76112/.53964. Thus prior weaker-price results from another
cohort do not establish that prices themselves cause the slowdown. Both methods
solve their own leaf condition; these are within-condition work effects.

All pairs lacking jointD2/q4 closure remain in the data with actual policies and
termination reasons. This finite closure intersection is not the whole target
distribution. Separate timing batches, own builds/tests and ordinary concurrent
machine load limit timing interaction claims; deterministic work counts are
separate evidence. No result-driven cap extension or resampling.

## A direct intervention on an adverse root

At3701-ply0 the priced fixed-goal transition ratio is3.551, and unit3.657.
The failure is already present with unit leaves. Existing raw counters, captured
without new C instrumentation, show old0 versus fullmain8root tie refinements;
qnodes3561->16178, transitions11034->39183. Both orders reproduce the counts.

A private one-conjunct change, ply>0, retains canonical ROOT order but the same
interior binary hint and all existing replay/TT/hint/fullchecked semantics.
On that exposed root it removes the8refinements and lowers transitions to16989,
with score/action/PV unchanged in both orders. That is.43358xfullmain but still
1.53970xold. Root ordering is a causal intervention; this does not separately
time tie refinements or explain away all remaining traversal inflation.

The full interior-only comparison closes128calls/64pairs:6deeper,54same,4shallower; all54matching policies have equal scores,62same actions, q4calls18->18. This mixed result does not justify replacing the shipped ordering. The pilot root is also already an immediate win, making extra post-win analysis an especially weak proxy for useful decision latency.

The new method is chosen from an observed development failure. Its comparison
uses ALL original roots and unchanged budgets, and is exposed development, not
an untouched independent validation. No per-position price or rule patch.

## Decision goal versus post-win depth

The public AlphaBetaPlayer bridge uses static overrides, TT off but its default
ordering/root tactical shortcut. Native is plain exact-root TT0. These are
DIFFERENT algorithms, not a pure backend timer or the UI dynamic evaluator.
Actual routes are32NativeV1legal/CoreSearch,32CoreFallbacklegal/CoreSearch,
64ownedV2full. Core and Native mate scales are explicitly normalized.

Of28greater-depth pairs,16 already return the SAME immediate winning action
in Core (four roots, both budgets/orders). Core finishes in .00395-.07674s;
Native consumes2.003-8.038s. These16 are not useful decision gains. The remaining
48pairs have12greater/36same depth, still with retained-policy limitations.

Six very short Core API timers report zero because monotonic uses15.625ms
GetTickCount64. Raw zeros remain. Caller perf_counter uses high-resolution QPC;
Core API elapsed and C kernel elapsed are not interchangeable. The first
zero-division analysis failure is preserved and fixed without rerunning searches.

A new PRIVATE source-built decision-goal prototype physically applies the chosen
move and recomputes the full true terminal before returning. A mate-like score
only triggers this verification. It acts only after completedD1/exact-root,
nondeclaration rules; actual winner must equal root player. Cancellation/errors
retain their control path. The one extra checked transition is separately counted.
It reports actualD1/q0/root_immediate_win; it does not pretend q4 was completed.

All16original roots/bothorders/2s give64calls and32pairs. 8candidate calls stop with verified actual wins; 8return the same literal action as baseline. Caller range 0.003675-0.063278s versus 2.003197-2.097195s; paired saved caller time 16.036s. All other cases remain in the archive. This changes the requested finite-analysis goal: it is a decision-latency result, not same-analysis speedup or a universal certificate. Product defaults/C are unchanged. Next implement an explicit decision-goal interface while preserving finite-analysis callers, declarations and stop semantics. It neither implements nor modifies AUX's multi-step prover/verifier/cursor.

## An actual supported-rule PV counterexample

Dot's old source-level objection is now a real4x4 semantic-rule game, not a
mocked search function. Two stationary actors, a persistent global square-token
phase and a current-type material marker encode R->A; A->V,U; V has6; U->Q,C;
C has5; Q's defender can choose5or3. An enemy-target hint puts C before Q;
its actual effects change phase, rather than capture. Checked effects alone
remain authority. End-phase actions keep literal leaves ongoing.

Full Core minimax atD4/q0/TT0 gives5. The previously REJECTED unrestricted image
returns a legal PV whose ply2choice has value3 instead of5, while its root scalar
remains5. Shipped False/True and unrestricted True have optimal prefixes here.
All11finite-tree nodes/10edges agree on full Native/Core legality, board, hands,
auxiliary state, SHA keys and literal history. No claim about natural-game
frequency, a shipped limited-method failure, or all possible PVs.

The new product regression checks EVERY returned prefix with exhaustive Core
values, preserving state. It passes2cases on shipped source; the actual old
unrestricted binary fails False and passes True. The affected scope/root-tie
suite passes24cases. The previous product-source full2595run remains prior
validation; it is not relabeled a new full2597invocation.

## Source/input closure and collaboration

Four image source sets are rebuilt in a new export using the pinned project
Python source plus the new regression. It reads no older private inputs; a
Python open-audit guard rejects that layer outside the export. Replay verifies
32contexts/5380full action identities, full state/history and32boundedD1probes,
the physical certificate verifier, shipped2PVpasses and old expectedFalsefailure.
This uses the existing Windows/Python/Zig dependencies; it is not a clean-machine
installer, byte-reproducible binary claim or a rerun of long resource curves.
The later interior and goal candidates are separately source-built and evaluated as stated.

DEV_AUX53 fixed59f5eef is fully read: conditional RNP learning benefit and negative
RNB/scale/conversion findings are AUX-reported, not re-executed by primary.
At final recovery, AUX54 is now published at26fd52997023bf23dc58e8adc0e591ff43fd76d9; its full report was read without checkout writes. It reports56tests, zero observed false wins on3496KRK and922unfamiliar drop-rule roots, and PN42vsAND/OR19 at4096 visits on64roots. These are AUX-reported, not primary reruns/source certification. Capped learning remains unproven. AUX55 continues certificate-tail conversion; its full thread and Dot's fixed-denominator objection were read. Adopt that interpretation, leave implementation/experiments in AUX's lane. Dot's induction/empty-ALL advice is conditional evidence, not execution by Dot.
Primary sent concrete ownership/source boundaries without requiring replies,
waking another Agent, editing sidemission, building a competing prover/cursor
or altering shared runtime for it. The one-off M3check above only tests a
particular delivered action. No stockfish/primary-Native identity conflation.
See COLLABORATION_LOG for fixed revisions and delivery evidence/limits.

## Delivery and next action

The only product-code addition is the two-case optimal-PV-prefix regression; product implementation/defaults and UI remain unchanged. Relevant publisher tests and full remote SHA are recorded in the delivery receipt. Technical sources, complete inputs/results, failed diagnostics and source-build replay evidence are in ../archive/priced_transfer_20261015/evidence.zip with member hashes/restore mappings. Six36fileC/H source sets accompany executed drivers; binaries and personal/account records are excluded. Some publication copies have paths sanitized; exact private originals remain.

Next primary work is an explicit immediate-terminal decision-goal mode with finite-analysis compatibility, then bounded cost/stop/decl/TT checks. Canonical-root mixed results do not merit default adoption. V2 publicdispatch remains a separate later interface question. No solver/cursor duplication, universal price claim, Elo campaign or science-complete claim.
