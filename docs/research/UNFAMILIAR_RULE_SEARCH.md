# Unfamiliar-rule search: first interface/cost observations

2026-10-08. Primary search work measures efficiency, stability and rule support,
not Elo, learned prices or an increasingly strong Chess player. The first
declared tier3 set uses existing generator seeds7/21, board4/6, bilateral_random,
hybrid movement, existing promotion/drop derivation and playability filters.
These four initial positions do not cover the user's tier1/tier2 mechanics.

```powershell
.venv/Scripts/python.exe -m scripts.unfamiliar_search --output .local_agent/new-search.json --depth 3 --shared-profile
```

Output must be new; immutable earlier evidence is not overwritten. Same roots,
fixed generic-v1 evaluator/profile, depth/budget, q0, root tactical scan off,
fresh TT per repeat. Plain Python legality/noTT/noordering compares with the
existing public TT/ordering bundle, two repeats. All selected moves/PVs replay
through Core. Exhaustive minimax has its separate4096-evaluation/5sec fuse;
an aborted reference is unknown, not a candidate pass or speed comparator.
Generic-v1 includes existing heuristic terms and is not the contact formula.

| Root | Depth3 plain nodes | TT/ordering nodes | Plain search seconds, first | Bundle seconds, first |
|---|---:|---:|---:|---:|
|4x4 seed7|65|92|0.0118|0.0175|
|4x4 seed21|231|227|0.0460|0.0485|
|6x6 seed7|1270|544|0.5105|0.2784|
|6x6 seed21|2018|822|0.6545|0.2918|

All16depth2 calls are complete/repeat-stable/legal and equal reference scores.
All16depth3 calls also complete/repeat-stable/legal.4x4 references agree;
6x6 references stop at the declared fuse. Repetition/history beyond initial
roots, harder tactics and broad generated distributions remain untested.
Small controls can visit more nodes with ordering/TT. No universal speedup.

Profile construction initially costs about0.009/0.009/0.083/0.044seconds by
root; an uncached player repeats that work. Existing shared memory profile cache
reduces measured player setup to tens of microseconds. No production cache
change. High-resolution external search timing is now recorded, since Windows
decision.elapsed_seconds sometimes rounds tiny calls to zero. Original outputs
and source versions remain separate, rather than silently correcting old costs.

## Semantic/native route: actual support, not an assumed universal adapter

The generator returns legacy CompiledRuleSet. NativeSemanticLegalityProvider
requires CompiledSemanticRuleset, so the requested native legality flag falls
back here. Native extension is installed; this is a compilation/interface scope.
Direct semantic compilation rejects empty DSL actions (NO_SEMANTIC_ACTIONS).
A directly passed semantic IR also lacks the piece_types attribute required
by the AlphaBetaPlayer profile builder. Failures and exact source are retained;
no production compatibility shim or broad fallback framework was added.

A separate diagnostic adds an equivalent quiet anchor-leap replacement to
activate the existing semantic compiler. Complete depth2 successor positions
and terminal outcomes match the original generated rules:48root/676second
children, zero differences ignoring only compilation fingerprints. This is
local parity, not arbitrary-history equivalence or a newly invented mechanic.

Existing native fixed-depth semantic search then agrees with the existing
independent Python packed-action alpha-beta oracle on score/best/PV, four roots,
two calls each. Both use the same ordinal type-index+1 leaf values for an
interface test; those are not a useful price candidate. No TT or model training.
Native/Python first-call seconds:0.0013/0.0166,0.0033/0.0639,0.0666/4.6972,
0.0305/1.7156. Native compile and root packing are separate in the raw record.
Different representations/runtime/visited nodes contribute; this is not a pure
language comparison or evidence that every custom rule is supported efficiently.

The first full-dictionary parity assertion found47vs52 nodes but identical
mate score, best move and PV. Retain that interrupted record: node-count equality
is not semantic parity. The completed diagnostic compares decision fields and
reports both counts; no score or success rule was changed to favor a move.
The semantic fixed-depth API works on these inputs. The initial claim of a
missing public integration route was too broad: the failed call used raw IR.
The supported product compilation boundary already connects semantic rules
and the public player's geometry-derived profile, as tested below.

Exact declarations, all successes/failures and source recovery are indexed in
data/direction_reset_20261008.json and the matching archive. No learning/NNUE,
new worker, default search/evaluator change or amateur-strength claim.

## Subsequent single-root persistence control

One separately declared6x6 seed7 root, existing SemanticSearchEngine,1MiB TT,
depth3/4096nodes/5sec/q0, same ordinal leaf. A child is selected as the
lexicographically first Core legal action before searches, retaining its actual
one-ply history. Cold/warm initial roots and reused/fresh child roots all complete
at depth3 with score8; all PVs are Core-legal. Node counts1949/936/2001/2149,
TT hits110/242/156/115; observed seconds0.0591/0.0340/0.0612/0.0622.
This shows useful supported persistence on one unfamiliar-rule witness, not
universal history/adjudication coverage or statistically established speed gain.
It narrows the next task to one actual recombined mechanic, rather than building
a new engine or assuming persistence must be implemented from scratch.

## Recombined-mechanic control

Two fixed5x5 roots with the same inventory exercise an owner-relative blocked
leaper, capture-to-base-hand and explicit downgrade to a weaker step. Closing
the leg yields0custom actions; opening it yields1, with captured base J in hand
and the actor retaining base J/current W. Both depth2 native calls per root
match independent Python score/best/PV and every native PV is guarded-legal.
Scores are -1/7; no strength or price-quality inference follows. Three initial
producer construction errors (missing guard fields, missing promotion sets,
wrong promotion-set shape) remain separate incomplete records and source versions.
This is a small tier2 interface witness, not all mechanics or history coverage.

## Supported product boundary and actual history

Use the existing compile_ruleset_for_execution boundary, not raw semantic IR.
It returns ExecutableSemanticRuleset, retaining semantic legality and read-only
geometry compatibility for profile construction. No new adapter is required.
The same small comparison entry now accepts declarative rules:

```powershell
.venv/Scripts/python.exe -m scripts.unfamiliar_search --rules <rules.json> --output <new-result.json> --depth 3
```

Supplied and generated inputs share the same comparison loop and persist each
observed call. Both recombined roots complete depth2 public plain/bundle repeats
with reference parity; renaming type IDs preserves the same scores -686/3147.
Four6x6 familiar-movement mixtures combine R/B/Western N/G/S/F/K with mirrored
inventories. These are movement mixtures, not complete Chess/Shogi specials.
Their32 depth2/3 calls complete with legal PVs, repeat stability and independent
Core reference parity. Zero depth2 opening scores are interface checks, not
discrimination between piece prices. Fixed generic-v1 includes dynamic heuristic
terms; this is not evidence for the contact formula.

The open recombined root also follows actual capture, enemy reply and drop,
selected before search. Across four history roots,24 reused/fresh/warm native
calls at depth3/4 complete with equal scores and legal PVs. All8 independent
Core minimax cells match that same ordinal debug leaf, with135..4426 leaf
evaluations. This extends persistence beyond the earlier one quiet child;
it does not cover all repetition/declaration histories.

## Fixed leaf, incomplete cells and terminal units

Separate whole-native/Core controls freeze explicit existing generic-v1 board
and hand tables, with dynamic terms excluded. Six roots (two mixtures, two
recombined and two Shogi custody counterfactuals), depths3/5, cold/warm1MiB TT:
24native calls have Core-legal PVs. Six complete reference cells match; six
references hit their independent20000-leaf/15sec fuse and remain unknown.
Both Shogi depth5 cold/warm pairs stop at depth3 under20000nodes/5sec; they
are incomplete, not parity evidence. Reference and native budgets measure
different resources and do not establish a resource-matched speed ratio.

Source inspection raised a concrete terminal-score issue, checked separately
on an existing sparse semantic mate construction with unit static values.
At depth1/2, independent Core scores999999999, whole-native99999999; both
selected continuations give Core checkmate for player0. Their terminal sentinels
are1e9 and1e8 respectively. The earlier six matching cells contained ordinary
scores; they never established raw mate-scale parity. Retain this API distinction
and report outcome/mate distance separately when crossing these APIs; no
production constant, old result or pass criterion has been rewritten.

A separately declared equal-ceiling comparison selects mixture0, the open
recombined root and custody G before outcomes: both entries use identical
static tables,20000nodes/5sec, q0, cold/warm TT repeats at depth3/5. Five fully
completed cells agree on ordinary scores; Shogi depth5 is incomplete. Cold
whole-native search is faster in the completed cells despite visiting more
nodes. Warm public exact-root searches are faster, but their PV is empty;
whole-native keeps a full-depth principal line. Source inspection confirms
Core's exact-TT return versus native's non-PV cutoff/full-window PV replay.
This output distinction qualifies the apparent cache-speed advantage; do not
remove native replay just to match a cheaper, different output contract.
TT sizes, ordering and node definitions differ. Setup/search costs and incomplete
depths are separate in data/search_pv_contract_20261008.json. The first missing
capture-order method and interim custom ordering run survive separately; the
qualified comparison uses existing public capture ranking, not that custom rule.

Exact definitions, histories, costs, incomplete/failed versions and pinned
sources: data/joint_service_20261008.json and its indexed archive. Next useful
search work is an observed decision-changing mechanism/history or cost issue,
using this supported route; no new compatibility framework or Elo campaign.

## Optional complete principal lines

SearchTuning.require_full_pv defaults off. When enabled, an exact TT hit is
usable only with a complete legal principal chain for the requested main depth,
or a real earlier terminal. Missing/bounded/inconsistent links fall back to
principal re-search; non-principal cutoffs remain. The existing path-aware TT
and runtime own identity, legality, push/pop and cancellation; no extra cache.
Declaration endpoints retain existing out-of-band semantics. This fixes
cache-caused line truncation, not every possible interpretation of a PV.

Two frozen actual five-ply capture/drop/recapture histories have32 public
ablation calls; all16 enabled calls meet their completed-depth line contract.
Warm depth3 enabled replay is about10ms with score2205/3603 and length3;
default warm calls are cheaper but empty. A frozen recombined three-ply history
has12 complete depth3/4 public/native calls and two independent Core references
(85/506 leaves), all score-1363. These limited measurements do not establish
broad speed superiority. The first recombined control ran alongside the
default suite, so its timings are descriptive.

Full output can lower completed depth. On the return-hand depth4 ceiling,
some full-output warm calls stay atdepth3 while default calls reachdepth4.
The direct depth3 independent Core references hit15-second fuses and remain
unknown; no fixed-depth reference parity is claimed for those Shogi roots.

Persistent sufficient-depth TT reuse retains existing variable-horizon semantics.
Partial deeper searches can leave deeper child entries: a later nominal depth3
result can differ from the earlier depth3 result (P control:3603 versus2576).
A legal complete PV does not prove a uniform-horizon minimax value. Use fresh/
reset engines for declared fixed-depth comparisons, or report persistent cache
history and resource/result curves. No hidden change to depth acceptance,
terminal sentinels, evaluator or default tuning was made.
Exact controls/source versions: data/custody_continuation_20261008.json and
../archive/custody_continuation_20261008/index.json.

## Deterministic cache provenance and generated capture history

The next fixed-node control has36 calls, two repeats per output/cap condition,
and no time-limit cells. Retained deeper entries can change a shallower nominal
score reproducibly: full-output nominaldepth2 at1024nodes gives3603 retained
versus2557 reset; at16384nodes retained depth4 score2557 is reused for target3,
whose reset score is3603. Complete legal lines do not imply uniform-depth values.
Two product regressions cover deeper-cache/reset semantics and cancellation
during cached-line replay, including unchanged state/history and engine reuse.

A preselected generated6x6 seed21 history contains12 ordinary captures; despite
the declared selection preference it contains no actual promotion or drop.
Its32 fixed-table cold/warm calls expose the same output/resource distinction:
at4096nodes full warm completeddepth2 can score2716 versus cold121, while at
16384nodes default warm reachesdepth4 and full warm stays atdepth3. The complete
Core depth2 reference is121; depth3 remains unknown at its declared cost
checkpoint. These are cache/history interface measurements, not new price
deployment evidence. Defaults and sufficient-depth reuse remain unchanged.
Sources, exact histories, failed initial versions and results:
data/contribution_model_20261008.json and
../archive/contribution_model_20261008/index.json.

## Supported promotion outcomes and actual callers

Eight predeclared sparse8x8 roots use canonical movement/anchor legality but
remove castling, double-step and en-passant. Four promotion interventions and
4/8/12ply terminal-outcome utility give77/96 complete cells under equal200000
calls/30sec ceilings. Incomplete cells remain unknown. Exact occupancy caches
are justified only in this no-aux, repetition100000/maxply1000, short-horizon
subset; they are not a replacement for product full-history TT identity.

Reusing proven terminal wins at adequate remaining horizons raises complete
ablation cells from29/48 (geometric-ordering only) to33/48 (proof only/both).
Nonterminal zeros are never reused this way. These finite +/-1 outcomes are
not product heuristic scores or shortest-mate distances; reusing a witness
does not establish an exact deeper product score. Defaults remain unchanged.

Restricting only the winning player's promotion choices to Q, with every enemy
defense retained in the full rules, proves wins in contexts3/4/6 within8plies.
All eight policy checks cost about3.39sec; independent Core verifies each winning
strategy. Failure of the restricted policy does not imply a full-game draw/loss.

The existing public interface then completes64 cold calls with zero nonterminal
evaluation, the same ordering tables,4096/16384nodes, targetdepth8 and5sec/q0.
No time fuse fires; all32 within-configuration repeats agree. Existing default
and staged ordering have equal depths/scores/node counts on16 paired conditions,
but context3 can choose different equally scored actions. They show no general
speed/depth benefit here. Only context7 at16384 completesdepth8; other calls
stop atdepth5..7. A completed shallower mate is not a completeddepth8 result.

Crucially, context5 reveals a real underpromotion mechanism. After the same
two-ply prefix, Q immediately stalemates the opponent while R retains one reply.
Independent plain Core search at5plies proves R-only/full-policy wins and no
B/N/Q-only win within that horizon. Thus geometry ordering may prioritize Q,
but removing the other legal choices would lose useful options. This is a
scoped semantic/terminal diagnostic, not an estimate of pawn material value.

Source inspection finds that UI move acceptance and match traces consume the
action, not a uniform-depth score/full PV. The analysis CLI does print score/PV
and already offers `--fresh-tt`. Its supplied-rule loader now uses the existing
execution compiler, so semantic definitions no longer hit the legacy-only
rejection. A cannon-rule CLI regression exercises two fresh-TT calls. No new
interface or global full-PV default is needed. Static-profile input limitations
are independently explained in SEMANTIC_CAPABILITY.md.

Exact declarations, incomplete/failed versions and measured costs:
data/promotion_rule_probe_20261008.json and
../archive/promotion_rule_probe_20261008/. These are on-demand research evidence.
