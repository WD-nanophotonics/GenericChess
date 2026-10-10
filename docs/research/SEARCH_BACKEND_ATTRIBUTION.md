# Search backend and algorithm attribution

This development assay implements the search-first direction. Its entry is
`scripts/search_backend_comparison.py`; it does not replace the product player
or propagate research changes into `ui-test`.

## Frozen first comparison

Eight source-declared roots cover Chess middle game, immediate mate, promotion
and en passant; Shogi middle game, a tactical sparse position, promotion and
held-piece drops. Played roots replay their entire declared opening. Sparse
snapshots start a new history explicitly. These are exposed development controls,
not human-labelled holdouts or a representative strength population.

The source fixes arbitrary, distinct integer material controls. They are neither
human-price fits nor proposed universal prices. Both leaf and ordering tables
are explicit. Shogi held pieces use their base-type values, promoted board pieces
their current-type values. King material is zero. Terminal scores have a separate
mate range and distance convention.

One lexical-order negamax alpha-beta drives Core and specialized libraries.
There is no TT, PVS, quiescence, reduction, tactical prescan or hidden heuristic.
Native legality is a third arm using the same Core state/history/algorithm, not
a claim that the entire search runs in native code. The fourth arm uses current
production iterative search with cold TT and ordering, the same material, q0
and tactical root scan off. Its node definition differs from the minimal search.

First declare D2, two order-counterbalanced repeats and a30second safety ceiling.
Then D6, two repeats,45seconds and1000000 recursive-entry ceiling per call.
Four arms x8roots x2repeats x45seconds has a48minute maximum requested search
budget; individual calls are interruptible and below the long-run threshold.
Audit/initialization/save overhead is outside the timed search, counted separately.
Do not extend these frozen calls after adverse completion or utility results.

## Semantic boundaries

Current Western Chess production declares repetition100000 and max-ply1000.
The specialized arm follows that scoped policy: it does not silently enable
FIDE claim,75move or insufficient-material draws. The finite assay cannot reach
100000 repeated occurrences. This is not certification of standard draw rules.

Shogi now declares no-legal-move loss, fourfold repetition/continuous-check
loss and the existing500ply no-contest extension. The first pilot exposed
non-check no-move draws in the previous product. The frozen D6 cohort retained
that previous rule fingerprint ac987c3f and its explicit draw adapter; after
completion, the product changed to ba3518b9. Historical fixtures are not rewritten.
The new rule follows the no-legal-move loss condition in
[CSA competition rules, Article27](https://www.computer-shogi.org/wcsc36/rule.pdf).
This does not adopt the competition's other adjudication or time policies.

A second discrepancy appeared only deeper: on the promotion root, old Core
visited850 recursive entries while the specialist visited795. cshogi's
[Position::isDraw source](https://github.com/TadaoYamaoka/cshogi/blob/master/src/position.cpp)
checks an earlier matching position without requiring four occurrences. It is
a search repetition detector, not a strict fourfold adjudication oracle.
The repaired specialist adapter owns exact SFEN piece/hand/turn identities plus
actor/check history, requires four occurrences and applies continuous-check loss.
Tests cover second-occurrence nontermination, fourfold draw, checker loss and
complete D6 trace/work alignment. Identity construction overhead remains in
specialist timing; it is not hidden behind a claim of native-only execution.

Entering-king declarations and the500ply extension boundary are outside this
board-action assay. Crossing500 raises unsupported rather than silently drawing.
Promotion, drops, base/current identity, auxiliary state and replayed history
remain. These scoped controls do not replace the complete generated-rule target.

Audits compare full represented board/base/promotion/hand/side/auxiliary/ply
states, legal sets, material and terminal values at each visited position.
Search tests compare complete D2 path hashes, work, scores and choices across
the minimal adapters. Abort tests require actual push/pop and history restoration.
This establishes the tested scope, not arbitrary rule equivalence.

## Interpretation

Keep three questions separate: cost of identical primitive work; actual work,
coverage and completion of a defined search; usefulness at the same time budget.
Minimal recursive nodes include root and terminal/static leaves; push counts
are child transitions. Production main+q counts span iterative depths. Neither
node total may be converted into playing strength or equated across algorithms.
Same score with another tied move is not a gain. A capped result is not a
completed D6 reference. Separate initialization, warmed execution, diagnostic
instrumentation and operational timing. Record actual Native calls/fallbacks,
not merely the requested switch or import availability.

Mature engines are overall references unless their complete evaluation and
terminal/search conditions are aligned. A material-leaf override alone still
leaves mature SEE, pruning and capture-order constants coupled to other prices.
No mature node count is equivalent to a Python recursive entry.

Primary adapter documentation: [python-chess core](https://python-chess.readthedocs.io/en/latest/core.html)
and [cshogi](https://github.com/TadaoYamaoka/cshogi). Exact results/source pins and
failures are added below after the frozen run, rather than inferred from these APIs.

## Observed frozen D6 controls (old rule/adapter version)

All64 original calls are retained, including caps and one Native Chess-middle
row contaminated by a concurrent2.44second pytest run. Do not infer clean timing
ratios from that row. Only the two completed Chess roots below have equal
minimal recursive-entry totals across all three backends in this old cohort:

|Root|Entries|Core seconds|Specialized seconds|Native legality seconds|Production seconds / entries|
|---|---:|---:|---:|---:|---:|
|Chess immediate mate|46059|11.77–12.04|0.65–0.66|8.11–8.27|22.79–22.86 /63368|
|Chess promotion|12055|2.66–2.69|0.15–0.16|1.91–2.00|1.57–1.61 /4112|

Production ordering/TT therefore does not uniformly beat bare lexical AB on
these roots: more scheduled work hurts the mate control, fewer entries help
promotion. This is a scoped algorithm/work effect, not evidence to disable
ordering generally. Most other Core calls hit45seconds; several specialized
calls hit the separate1000000entry cap. Neither is a completed D6 comparison.
The old Shogi promotion850/795 discrepancy invalidates its identical-work timing
interpretation. New strict-history controls supersede it without altering it.

## Native provider accounting repair

The common-time pilot's production Native counters reported calls but zero
payload/decode time. Inspection showed SearchPathRuntime read metadata only
from callable.__self__; NativeSemanticLegalityProvider is a callable object.
The same issue ignored its strict flag on operational failure. Resolve the
owner as bound-method owner or the callable object itself. Dedicated tests
cover both forms, strict propagation, explicitly non-strict fallback and metric
aggregation. Old timing/results remain old-source records; subsequent profiles
use the repaired accounting. This repairs observability/declared failure behavior,
not search evaluation or legal action definitions.

## Common-time useful-decision diagnostic (repaired rules)

Frozen budgets0.25/1/4seconds, two reversed-order repeats, eight roots and five
arms produced240 legal choices. Both full-root D4 and selected-child D3 references
completed for every row. Regret uses the same arbitrary material table and mate
distance, not game outcome, independent generalization or strength. These are
exposed controls and repeated correlated roots, not240 independent samples.

|Arm|Positive D4 regret /48 choices|
|---|---:|
|Bare AB/Core|14|
|Bare AB/specialized|2|
|Bare AB/Native legality|12|
|Supported search/Core|18|
|Supported search/Native legality|16|

At1second, the ep control gives100 material regret for completedD3 versus0
for specializedD4; Shogi middle gives200 for Core/native/production choices
versus0 for specializedD4; held-piece drop gives400 for shallow Core/production
versus0 for specializedD4. In four other controls all arms have0 regret and
alternative promotion/terminal choices are ties. A deeper search can also choose
a move worse under this finite D4 teacher; two specialized positives are retained.
These outcomes justify investigating backend execution cost, not adopting a
specialist-only player or claiming a general chess-strength gain.

The first utility attempt failed because a child search compared restoration
against the parent's stored root. It was repaired by constructing a child case
with the entire replayed prefix, leaving the parent untouched. No failed result
was promoted into the completed cohort. The final cohort retains the original
(runtime-accounting pre-fix) source and declares its missing minimal-iterative
provider counters; following profiles measure actual provider counters.

## Fixed primitive question and cost boundary

After whole-search profiling, isolate the same eight roots with20 cold-front
queries,100 cached-parent push/pop pairs and5000 static evaluations per backend.
Core cache clearing is explicit assay instrumentation; initialization is separate.
Specialist libraries retain their own internal representation/caches. All fronts
must stay identical within each row, roots must restore and repeated scores agree.
This is a new component-attribution question, not another price/strength test.
If generation/transition dominate rather than evaluation, the next investment
is an evidenced generator/reuse or bridge bottleneck; otherwise leaf-cost work
must be reconsidered. Estimated incremental local run is under two minutes;
no sample growth or larger training follows. Count actual times and source pins.

## Fixed-work and primitive results; next choice

All four clean25000-entry arms have identical complete work counters on each
profiled root. Chess middle costs9.79sec Core,13.08 with inner cooperative
checks,0.62 specialized and6.19 Native legality. Shogi drop costs34.48/51.43/
0.225/9.99 respectively. cProfile inflates times; cooperative drop reaches its
120second fuse at20708 entries, so that instrumented row is not an equal-work
speed comparison. All16 rows remain, including the fuse.

Core's Python trial transitions are153760/889594 in the two instrumented roots;
Native reduces them to50332/51883, with zero observed fallback and nonzero
payload/decode accounting. Native still uses Python transition/check/history.
The Shogi Native path also decodes763665 legal actions for25000 recursive
entries: binding/public-action conversion is material at high branch counts.
Packing alone is a smaller cost; do not prioritize it merely because it is an
obvious interface boundary. Profile cumulative times overlap; never add them
as independent costs.

Primitive cold fronts on Chess middle average1.691ms Core,0.050ms specialized,
0.630ms Native. Shogi drop averages3.478/0.030/1.384ms. Core static evaluation
averages2.535us on Chess middle and1.114us on the drop root; it is cheaper here
than specialist Python-adapter scoring. Parent-cache push/pop and these two
fixed root snapshots are not averages over search trajectories. These small
primitive measurements support the generator/conversion diagnosis but do not
supply universal performance ratios.

Next isolate high-branch conversion versus residual Core trial/check work,
using the same ordering/material/cancellation and full-state trace witnesses.
A lazy binding or existing successor-reuse candidate must retain legal-front
validation, failure semantics and exact history; it needs a bounded finite-work
and common-time comparison plus unfamiliar generated-rule transfer before a
product change. No default algorithm or evaluation change is adopted here.

Existing mature references are presently unavailable: Stockfish launch returns
App Control4551; the Fairy-original USI handshake lacks a full9x9shogi variant.
Hashes/options/protocol/failures are retained. No security workaround, binary
substitution, claimed mature comparison or heavy new build follows.

Validation:85 affected bridge/runtime/terminal/native/Chess-perft/Shogi tests
pass; frozen old-rule eight-frontier recovery passes, all archive hashes and
source/rule version boundaries are checked. Evidence:
[data index](data/search_attribution_20261010.json) and its purpose archive.

## New binding-path premise (predeclared isolated ablation)

Inspection of `_make_binding_from_action` shows that naive lazy binding would
also delay geometry/type/source/path validation. Do not adopt that shortcut.
A smaller existing-equivalence candidate is `_path_for_geometry`: it still
allocates all geometry endpoints through `geometry_candidates` before finding
one target. Reuse `geometry_paths_to` and its first matching prefix instead.
All prior checks and exact geometry identity remain, with no new cache/API.

Before seeing results, freeze strict Native minimalAB on Chess-middle/Shogi-drop,
25000entries,D8,30second fuse,two reversed-order repeats, with every finite
owner/source/target geometry query compared first. This new premise concerns
binding reconstruction, not the earlier attacked-square iterator experiment.
Possible outcomes determine whether to retain this small cleanup or defer it;
no larger budget, evaluator change or omitted validation follows.

Result:1310162finite geometry queries agree and eight25000-entry calls retain
all work counters. Relative target-directed wall changes are+1.669/-3.631% on
Chess middle and+0.436/-1.183% on Shogi drop. The direction is unstable at this
scale. Preserve the candidate as an isolated diagnostic; no production path
change or larger repeat budget is justified by this result.
