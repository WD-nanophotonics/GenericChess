# Quiet-drop bookkeeping and semantic PVS

The new exclusion prototype reduces the cost of rejected quiet drops while
retaining Core's complete mechanical transition. It does not infer outcomes
from move names or geometry. Existing PVS also gains completed support under
the current semantic evaluator. Both remain explicit research choices; product
and UI defaults are unchanged. The completed four-arm scaling adds no delivered support beyondPVS at64/256s; keep the exclusion seam research-only.

## Execution boundary

The hook runs only in the non-check branch of runtime quiescence, after stand
pat and ordinary depth exits. The earlier in-check branch searches every legal
evasion and never calls the hook. Core remains the sole owner of accepted-child
history, identity, hash, TT eligibility and terminal precedence. There is no
second runtime, history cache or metadata-only rule executor.

For each candidate drop, the prototype executes the real semantic transition,
including ordered effects, auxiliary expiry and promotion. Enemy removal,
changed board/hand type inventory and checks retain the original push. A child
without legal moves also retains it, preserving mate/stalemate even in capture-
only qsearch. Existing bool/None availability providers retain Core fallback;
invalid returns and operational exceptions propagate.

A parent guard declines near maximum ply, any automatic trigger, repetition
threshold, opaque imported keys, repeated-cycle targets, consecutive-action
adjudication or no-progress configuration. Scanning all exact occurrence buckets
proves a one-child repeat threshold cannot be reached; this is conservative and
its cost is paid at every eligible q parent. No-progress search is already
unsupported by Core; the guard test does not claim that missing capability.
Balanced swaps and spatial/auxiliary changes that conserve inventory retain the
existing limited q inclusion policy, not a complete tactical classifier.

## Fixed work and transfer

A 4096-node shadow call executes the original push for every predicted exclusion:
12792 exclusions match complete Core child equality, ongoing terminal state and
noisy-false classification. It performs additional work and is not a speed test.
13373 drop trials include581 checking drops retained.

Eight actual8192/16384-node calls match action, score, PV, returned depth/q
support and recursive work in all four baseline/exclusion pairs. Caller cost
ratios are0.642-0.682. Full pushes decrease42583 to12157 at8192nodes,
89653 to27979 at16384nodes. Retained drops still pay a duplicate transition;
that cost is included. These calls deliverD1/q0 with partial deeper work.

A separate32768-node four-arm comparison includes existingPVS. Within both
baseline/exclusion andPVS/joint pairs, all decisions and recursive counters
match. Exclusion ratios are0.694/0.697 withoutPVS and0.796/0.796 withPVS.
ThePVS arm changes the main/q work mix; its cross-arm work is not equated.
All eight calls deliverD1/q0. This demonstrates independent cost savings at the
fixed condition, not independently stronger decisions or completed fullq4.

Eight completeD2/q4 generated1006/1008 calls preserve all four paired decisions
and recursive counters. Ratios are0.748 for1006 and0.909/0.915 for1008.
1006 excludes17393 drops;1008 excludes4358. Although1008 has no initial legal
drops, later captures create hands and drops: initial drop count is not a safe
whole-search capability test. These are exposed developmental transfers.

## Equal deadlines and PVS transfer

Twelve16/64/128second Shogi calls retain legal actions and balanced roots.
At16seconds both returnD1/q0. At64seconds exclusion returnsD2/q4 versus
baselineD1/q0 in both orders. At128seconds both returnD3/q4 and match action,
score and PV exactly. Different-depth scores2461/3034 are not useful-move gains.

Sixteen familiar PVS16/64second calls use identical Native semantic leaves,
Native legal/availability and Core history/check/TT. At16seconds both arms
returnChessD4 andShogiD1 with exact paired decisions/q support. At64seconds
PVS returnsChessD5 versusD4, andShogiD3/q4 versusD1/q0 in both orders.
The earlier weighted-leaf PVS negative results remain; this changed evaluator
premise does not erase them. Another16calls on1053/1054 preserve decisions;
1053 costs are mixed and1054 is immediate-win only, providing no recursive gain.

The separately predeclared64/256second four-arm comparison tests whether a
new exclusion seam adds completed support beyondPVS and whether interactions
scale. It fixes depth12, one million combined nodes andq4/hard8 for every arm.
Its declared maximum2560search seconds stays below one hour. Larger resource
points do not change earlier frozen limits or grant holdout status.

All16 factorial calls now complete with balanced Core roots, no Native fallback
or operational error. At64s baselineD1/q0, exclusionD2/q4 andPVS/jointD3/q4;
at256s all four arms returnD3/q4 and the same action/score/PV. PVS/joint match
retained decision and support in every group. Joint explores more partial nodes,
but all arms exhaust time before the one-million-node cap, and the extra work
crosses no additional delivered depth here. Fixed-work savings are real finite
observations; they do not require adding a product hook without another concrete
use benefit. Prefer the already-existing PVS option for these semantic-leaf cells,
retain the new exclusion prototype and its boundaries for later targeted use.

Four further public calls on an existing compound-rule castling fixture return
identicalD2/q4 decisions/score1922. PVS increases main/q counts83/436 to92/481
and costs0.155/0.156s versus0.146/0.140s. The actually legal semantic action moves
four cells and clears a per-owner auxiliary right; its implicit initial value1
and explicit child0 are checked. This tests persistent rights/triggers, not expiry.
No direct capture of the internal search runtime was installed in these four
calls; unchanged source-session identity is not a separate search-root audit.
This adverse tiny-root transfer prevents treating PVS as universally cheaper.


## Remaining actual consumer

Two profiled32768-nodePVS/joint calls preserve decisions and recursive work.
Full Core pushes decrease149302 to80272; availability queries remain149302.
Mechanical transitions increase149302 to151722 because2420 retained checking
drops repeat their projection. Thus the gain removes history/hash/snapshot and
Core adjudication bookkeeping, not all rule execution or terminal queries.
The guard runs6964 times,0.061s inclusive in this short-history profile.

Joint profile self costs include Native transient legal generation2.689s,
availability payload1.411s and Core square attack1.013s. Native legal generation
is unchanged by exclusion. Inclusive times overlap and profiler overhead changes
wall cost;38.480/30.809 profile totals are not a clean speed comparison.
Do not reopen the closed check hook or add a history cache on this evidence.
A separately declared played-history transfer measures conservative scan/decline
cost on deterministic16/32/64ply Shogi snapshots, without replacing finished roots.

The actual played-history transfer completes12calls on16/32/64ply snapshots.
All six decisions and recursive-work pairs match.16ply209exclusions has cost
ratios1.001/1.004 (no demonstrated saving);32ply4858exclusions ratios0.950;
64ply7185exclusions ratios0.927/0.928. No guard declines occur in this finite
walk. The64ply mate-range score is not independent tactical validation.
History length and drop opportunity change together; this does not isolate a
causal slope for history scanning or justify a history cache.

## Broader search comparison

Source review finds Fairy-Stockfish qsearch uses depth-dependent checks, TT,
futility/SEE and continuation-history pruning. Its mature q support differs
from the local unpruned effect-based q4 policy, so it remains an overall engine
reference. [Fixed official search source](https://github.com/fairy-stockfish/Fairy-Stockfish/blob/9f778da667f6e07dae1e85d3e2ea204fc6dee94d/src/search.cpp).

A new bounded minimalAB/q4 bridge compares Core and existing Chess/Shogi rule
executors with one lexical algorithm and frozen arbitrary material values. It
includes complete child/snapshot classification costs; it is a scoped execution
bridge, with no TT/PVS, not product ordering/evaluator equality. Mature execution
remains unmeasured; source access does not repair the retained Windows launch
failure. Its declaration and failures are separate from older q0 measurements.

The16-call common minimalAB/q4 bridge has six complete pairs with identical
move, score, recursive work and trace. Python Core ChessD2 costs0.597/0.618s
versus specialized0.177/0.179s; ShogiD1 costs6.000/6.042s versus0.345/0.347s.
Both ShogiD2 arms remain partial: Core hits15s before the specialized16384node
cap, so that cell has no equal-work timing ratio. This bridge uses Python Core
legality, not the current Native default. Checked-q fail-soft returns also differ
from product alpha-bound returns; shared bridge policy does not imply product parity.

Twelve additional actual Native-dispatch calls retain exact D1 decisions/work/
trace across Python, Native legality and Native legality+availability. ShogiD1
costs6.196/6.195,2.892/2.878 and2.430/2.425s respectively. The latter two arms
also retain an identical16384node partialD2 prefix at9.907/9.896 and8.790/8.811s;
Python instead stops at15s after fewer root children. Native legality is actually
active, with zero fallbacks/operational failures in all Native cells. Availability
has17363 D1 and66650 D2 queries/imports, zero declines. Specialized Shogi remains
substantially cheaper in its separate block, even after the Native dispatch
control, but blocks are not simultaneous noise-free comparisons. The residual
includes complete Core transition, snapshots, history and algorithm callback
costs; this does not assign all of it to one component or justify a second runtime.


One further predeclared NativebothD1 profile preserves the completed decision,
work and trace:17363 Core pushes cost3.043s inclusive, mechanical transitions
0.239s,32850 bridge snapshots0.331s and semantic hash diff0.558s. Native legal
self cost is0.586s. Inclusive costs overlap and profiling roughly doubles wall
cost, so these are consumer attribution, not attainable speedup estimates.
The profile invocation itself is inline; the reused producer and control hash
are archived, but there is no exported standalone profile runner. Reject porting
bridge-only snapshot logic. Full semantic diff cannot use source/target as a
footprint because compound effects and auxiliary expiry touch other cells; any
future narrowing first measures actual product board/nonboard hash consumers
and keeps the unchanged full hash and exact Core history as its oracle.

A one-call portion diagnostic then verifies all17363 hashes against the original
function and the complete D1 decision/work/trace. Board scanning including tokens
costs0.093s across1406403cell pairs, nonboard maps/tokens0.162s; the2.585s caller
also pays duplicate oracle work. These timers are not a clean speed prediction,
but board-only narrowing is too small to prioritize a new effect-footprint seam.
Defer it and return to actual legal-action enumeration/q scheduling consumers.

## Validation and failures

Twenty-two new finite tests cover standard checking/quiet drops, capture-only
counters, terminal/history guards, actual compound auxiliary/type/removal/
quantity effects and a nonchecking queen drop that causes stalemate. The focused
43case suite and2192-case active regression pass. Finite controls are not full generated-domain proof.

The first fixed-work producer accidentally iterateddepth12 as a node cap;
its four12-node calls are preserved and excluded from the planned comparison.
A separate V2 uses the actual8192/16384node loop. Inherited metadata fields and
old attribution prose are retained in raw declarations; execution scope above
uses actual limits and row counters. This is a producer correction, not a cap
extension or replacement result.

Fixture failures include missing required DSL fields, incomplete/opaque history,
invalid capture disposition and top-first coordinate mistakes. They are corrected
with actual effects and canonical complete witnesses; no engine defect is claimed.
Two verification scripts initially failed before writing evidence (syntax and
wrong row-field name), yet structural checkpoints accepted their absent paths.
Corrected verification explicitly records this premature checkpoint failure.
The validator is not evidence-existence or research-quality verification.

A first full regression run encountered the existing Windows temporary-directory
access failure. Its raw host-path log stays private; a fresh project-local test
directory is used for the rerun. No permissions or other projects are changed.

## Evidence and limits

Raw declarations, producers, complete outputs and verification bind to
`data/quiet_drop_20261012.json` and its reviewed archive. Raw Slack/account data,
binary profiling files and credentials are excluded. Core source snapshots and
prototype/test versions distinguish old private and exported research imports.
Native binary is unchanged, not archived. Ordinary concurrent computation and
regression overlap limit timing interpretation; paired orders and actual work
counts are retained. Engineering, failed scripts, tests, archive and token costs
also count; no net productivity saving is claimed without a counterfactual.


The next source review has begun: Native transient legality checks every candidate
and constructs a full packed tuple before Core decoding and lexical q ordering.
Current Core pushes require membership and bindings from the legal cache; complete
check evasions remain a separate branch. A noisy-only provider cannot silently
replace this full cache. Next count candidates generated versus visited before
choosing any filtered/lazy interface. This is source attribution under the pinned
base, not a changed generator.137actual search calls include four failed12node
calls, two profiled PVS/joint calls, one additional Native bridge profile and one
hash-portion diagnostic; their overheads are distinguished in raw records.
