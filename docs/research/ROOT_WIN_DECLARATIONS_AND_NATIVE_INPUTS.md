# Root-win semantics and actual Native input delivery

Science is OPEN. Python search now includes a supported NO_CONTEST declaration
as a value-zero defensive option. The correctness fix and33 added regression
cases are published at932f03b268c2eecd4e3347219ded566d89e8872a; the complete
four-layer suite passes2502 tests. Native ABI, search/evaluation defaults,
Core rules and UI are unchanged. Private payload prototypes are not deployed.

## Observed defect and repair

The prior Python recursive search assessed WIN and RESTART but omitted
NO_CONTEST. Adding an always-qualified owner1 NO_CONTEST to the existing
four-board H3 analysis root made the old99-node search return
completed_root_win/MATE-3. Actually submitting that selected root action then
calling GameSession.declare ends with NO_CONTEST and winner=None. This is a
concrete false winning proof, not just a missing display field or an equality
window problem. Earlier independent H3 certificates without this declaration
remain valid; their scope is not silently enlarged.

The shared neutral selector now supplies both RESTART and NO_CONTEST to
negamax, mutable and immutable qsearch, and reference_minimax. It preserves
the previous RESTART preference when both qualify, actions winning value ties,
WIN priority and reconstruction of the actual neutral declaration from real
TT entries. LOSS or an unqualified neutral declaration is not a zero option.
Core retains adjudication and actual declaration execution.

A64-query old/fixed intervention crosses declaration check qualification,
default/PVS/aspiration/combined-MDP,99/full budgets and genuine cold/warm TT:
27 old results falsely claim an H3 win; actual immediate NO_CONTEST defenses
were independently executed for every distinct affected root action, covering
all27 rows. Zero fixed results do.12 fixed positive
wins remain when the defender's neutral declaration is unqualified. This
explicitly checks that the repair does not suppress all winning opportunities.
Corrected regression controls give9 failures/5 passes on old functions and
14 passes after repair. The broader affected suite passes68. Tests additionally
cover actual Native routes, provider failure, cancellation, zero-action winning
claims and strict window equality, for33 added cases over the prior2469 suite.

## Winning-band interpretation and the useful Dot objection

Dot source-reviewed ac34a183 and recommended the equality boundary control.
For root alpha=A, a child fail-high c>=-A yields a root upper bound -c<=A;
the strict root score>A rejects it. A child fail-low can legitimately provide
a root winning lower bound after negation. The earlier question's loose
fail-low wording is corrected here. PVS/aspiration need not finish the whole
root re-search for a completed child's valid lower bound to remain useful.

40 direct queries include8 cold full-window references,16 equality-window
negatives and16 improving-window positives, across Core/actual Native,
PVS/MDP and genuine warm child entries. All equality cases save nothing;
all improving cases retain independently verified H3 actions. Root TT entries
are removed and actual root-child pushes observed, avoiding a vacuous cached
root return. The returned PV remains a line, not an all-defense certificate.

This is conditional on correct terminal/declaration options, all legal
evasions, nonterminal utility staying outside terminal bands, propagated
interruptions and valid state/history/depth/distance TT semantics. Noncheck
qsearch stand-pat prevents inventing a negative terminal-band upper bound just
by omitting quiet defenses; checked nodes retain every evasion. A hard q limit
aborts rather than completes a child. The NO_CONTEST counterexample demonstrates
why the recursive-option premise matters. Future defense-skipping pruning or
incompatible caches cannot inherit an unconditional proof claim. No exact full
WDL calibration or shortest-win assertion is made.

## Transfer controls with complete played state

Six98/99/fullD2 Core/Native calls agree; actual Native legality calls are
21/21/124 with zero fallback.60 provider/tuning combinations retain16 completed
wins, all independently H3-verified, and36 H3-positive choices. The same node
boundary is not universal: PVS99 has no proof while aspiration98 does.
NativeAll and check/availability-only each execute3075 actual queries of both
predicates. A zero-step zone-claim control is negative at13nodes, retains
MATE-2 at14nodes with D1/node_limit, and independently verifies all3 defenses.

18 unavailable/controlled-operational-failure/short-maxply comparisons preserve
exact Core action/score/PV/work/history. A third-attempt fault after2 actual
Native successes produces exactly1 operational fallback and still retains the
99-node proof. The no-S4 maxply2 sample has zero declines and prevents H3;
its old intent label does not establish a capability miss. A separate S4
cohort actually declines1/72/13 times at maxply1/2/3, with zero operational
failures and matching Core decisions.

The prospective seeds2051–2058,4/8 boards, root0/played-ply8 cohort closes120
searches/60 old-new pairs.15 roots are included;2055 naturally terminates at7,
so its missing ply8 root is retained and not resampled. Native is actually
active on60 calls, with831967 legality calls and no fallback. Every paired
retained tuple matches; there are no new completed_root_win results here.
These are exposed development seeds, not a universal independent holdout.

Eight semantic roots replay actual R-to-TP transformation, capture resetting
base identity into hand, a later drop, live/expired auxiliary rights, compound
king/rook and adjacent shifts, and live/consumed off-target square tokens.
64 searches/32 old-new pairs preserve tuples and full history, including
negative mate-band controls.24 requested calls actually use Native;8 requests
on the two unsupported action-base EP roots stay Core. The remaining32 are
explicit Core controls. No unsupported path is relabelled Native.

Eight distinct positive outcomes from these cohorts receive independent
finite Core certificates: five H1, one H3 and two H5.Producing the proof trees
takes13475 transitions; a separate consumer verifies their required defensive
coverage in24 transitions. Compact certificates discard failed attacking
alternatives, so these counts are deliberately different. No score or
cooperative PV is used as the independent label.

## Existing optional Native inputs: cost and actual one-second choices

The48-query assay fixes q2/hard8, the evaluator and requested work/budget.
Four roots compare Core, Native legality, added Native availability, and added
Native check with its existing one-use input sharing.512-node controls match
retained non-timing tuples/work.32 resource calls use16seconds including player
preparation and two opposite orders. First completed positive-root-bound times
below are descriptive means of two calls, not independent samples:

|Root|Core|Native legality|+availability|+check/shared input|
|---|---:|---:|---:|---:|
|H3 board12|0.572s|0.507s|0.332s|0.297s|
|H3 board16|1.433s|1.321s|0.802s|0.807s|
|2054 played-ply8 H5|9.982s|6.725s|5.368s|5.000s|
|2053 root0|not found|not found|not found|not found|

For2053, Core completesD7 and Native variantsD8 with different static results;
this is not a demonstrated move-quality gain. All three winning roots retain
their finite goal under16seconds. Check input sharing adds little beyond
availability on board16, so the whole gain is not attributed to check alone.

A distinct predeclared1second caller counterfactual uses the two H3 boards,
four arms and two opposite orders, without the proof-timing observer.
On board12 all8 returned actions satisfy H3. On board16 Core and Native
legality each fail H3 in both orders; added availability and NativeAll each
satisfy it in both. All16 report completed_depth=1. Positive returns identify
completed_root_win/q2; negative returns keep main_iteration/q0.
Independent label production takes182 Core transitions and a separate complete
positive/counterexample replay takes72, with zero unknowns.
Failure of H3 is not a game loss. Two roots/two orders are not an Elo or
statistical generalization result. Actual wall reaches about1.004s: cooperative
limits are not hard real-time guarantees. Defaults and UI remain unchanged.

Another16 fixed2048-node searches qualify optional inputs on all8 played
semantic roots.25,037 actual check and25,037 availability queries match Core
one by one, retaining exact action/score/PV/work/history. Six roots activate
Native; the two EP roots remain Core. Shadow overhead is not a speed result.

## Next bottleneck, without deploying another carrier

Four8192-node profile/control pairs retain work and decisions; instrumentation
raises wall cost about2.5–2.8x. Nested cumulative times overlap. In the16-board
profile, Core push includes5.538s of8.504s wall, Native check1.850s and full
state-only payload1.333s/39045 calls. These cannot be summed or treated as
unprofiled removable percentages. The neutral selector itself costs about8ms,
so another rewrite of that correctness repair is not the priority.

One private C-API builder emits the complete existing Python payload; the
unchanged production packer/kernel still validates and executes it. There is
no new position cache, rule subset, Native ABI or production binary. Each
version checks48 typed input variants,5 invalid owner/type/hand error cases,
and4600 actual complete payloads in four512-node NativeAll callers.

|Root|V1 C/Python caller cost|V2 interned-name C/Python|
|---|---:|---:|
|H3 board16|0.9985|0.9518|
|2054 played-ply8|1.0461|0.9740|
|Transformed live auxiliary|1.0241|0.9696|
|Compound shift|1.0222|0.9668|

Each ratio uses two opposite-order8192-node caller means with identical
non-timing tuples/work/history. V1 is rejected. V2 changes one premise:
interned attribute names remove repeated C-string-to-Unicode conversion.
Its2.6–4.8% local reduction justifies considering one bounded integration
decision, not immediate general adoption or a strength claim. Current Native
module ownership/method initialization was inspected; production integration,
old-binary fallback, lifetime/error/interruption qualification and maintenance
cost remain next work. The old wide-readonly/import failures remain unchanged;
this candidate only replaces a complete mapping into the existing Native path.

## Collaboration, failures and delivery

DEV_AUX46 fixed a4fb396e00349d0c57321174b8ccaeab5196f90d report was read in full
and its exact Git blob967c28495453a63b251e339a4c35727a268b5ad6 verified.
Listed game counts sum6656 and cumulative producer cost1311.782s; endpoint
interaction is-3/64, budget-gain difference5/256 and observed lower-budget
wall reduction28.906%, not8x. The250go saving is separate from team efficiency.
Scale uncertainty, no unique ratio, pawn boundary and zero DEV EP remain.
Raw games, bootstrap intervals, binaries, training and archive restoration were
not independently reproduced. No auxiliary work was duplicated, branch merged,
worker launched or routine acknowledgement requested. Detailed coordination
and adoption limits are in COLLABORATION_LOG.md.

All516 research search attempts are accounted in the data index:515 complete
and one failed incomplete-evaluator harness query. Pytest calls, primitive
payload checks and Core proof transitions are separate. Some early completed
calls have source/stdout/event evidence rather than a full decision row; do not
reinterpret516 as516 complete row records.

The S4 constant-evaluator harness initially lacked capture_order_value; explicit
equal ordering-off repaired it. A sample assertion confused typed square(2,2)
with flat18; corrected full-root replay precedes queries. Two initially attacked
anchor test setups were replaced with declared checked analysis roots. These
are harness errors, not Native/OS/SAC failures or extra product defects.
A private source-generation regex assertion and an archive packager scanning
its own literal deny patterns were corrected before building the affected
artifact; original private failure evidence remains. No machine security change
or user intervention was needed.

Evidence: data/root_transfer_20261014.json and the74-member Agent-only archive
../archive/root_transfer_20261014/evidence.zip with its exact manifest.
Raw Slack/account/private inputs, credentials, compiler logs/caches, profiles
and binaries stay in the ignored private layer. Each published archive member
is hash-verified; the immutable ZIP is not rewritten to add later receipts.
The full2502-test pass and prescribed68-test fix publication precede report
delivery; a local commit is never counted as publication.

Late private-payload stop supplement: two actual NativeAll cancellation searches
retain the same H3 proof, D1/cancelled provenance and full history with Python
and V2 C payloads. Required invalid-owner and postquery errors remain explicit,
pending input is cleared and retry imports fresh. Exact source/results are
beside the immutable ZIP and hashed in the data index; no inside-C polling or
production integration is claimed. These two calls raise the segment total
from514 archive-accounted attempts to516 total,515 complete/1 harness failure.

Segment closure: UTC03:42:53.001619 to04:43:39.634021,60.777minutes,
nine validated research stages, safe_checkpoint accepted. All producers closed;
science remains OPEN and the compact memo has executable next tasks. Duration
comes from the actual session clock, not summed overlapping compute or idle wait.
