# Unfamiliar-rule search: interface, controls and cost

The2026-10-09local seed102q-frontier replay and changed mixed-hand custody
controls are routed through TASK_PREDICTION_DIAGNOSTIC.md/data/qfrontier_20261009.json.
They explain scoped horizon/stock effects, not strength or a widened classifier.

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

## Core eager successor cost

The previously unknown C-drop-history reference was profiled. Its eager semantic
path generated the complete legal set once, then `engine.apply` generated that
set again for every child. `legal_successors` now reuses the canonical iterator's
verified binding and the existing full-history transition constructor, as lazy
successors do. Public single-action validation, S0-S4 filtering, repetition,
auxiliary state, terminal adjudication and action order remain intact. No Native
dependency or search/evaluation policy is added.

A separately declared development batch gives both versions16384 leaves/20sec
at depth2 on the same root/history/evaluator. All four calls complete with6126
leaves, score-98 and the same action: old10.492/10.525sec, new0.644/0.658sec.
Immediate73 full child states also agree. Earlier capped records remain unknown;
new completion does not rewrite them. This is local Core eager cost, not default
public-player acceleration.

Two sets of20 history roots compare complete old/new successor GameState and
independently replay Native actions/positions/terminal semantics. The original
canonical routes did not exercise nifu/uchifuzume hands; its optimistic declaration
is retained with a correction. A changed capture-then-drop-priority route obtains
actual P hands and drops in both fixtures, alongside cannon capture, castling
and off-target en-passant. Small enumeration timings are exploratory; the
controlled6126-leaf batch owns the performance claim. Product regressions also
compare every child against validated public `apply_action` and verify one parent
enumeration. See data/lifecycle_20261008.json and its isolated archive.

A new explicit recombination adds a current-type zone-capacity drop guard to
promotion with a transient right. Nine actual-history roots preserve complete
old/new child GameState and independent Native route/action/terminal parity.
Two captures create hand2; promotion of a zone R to TP opens capacity, the enemy
turn expires the right,58 drops become legal, and filling the zone blocks the
remaining hand. Nine fresh/reused/repeat public depth2 calls agree with three
complete Core references under fixed generic-v1/static conditions. Warm PV may
remain empty under the existing contract; no new public speed/price claim follows.

This execution uncovered a compile-only test fixture error: it changed the
current type at an empty target before moving there. Declaration-order effects
require moving first. The fixture and one real-history regression are corrected;
the semantic executor was not changed. Exact original/qualified definitions,
failed route and old fixture recovery are isolated under
../archive/paired_context_20261008/; compact results are
data/paired_context_20261008.json. Compile capability and executed event coverage
are distinct; future fixture checks should follow actual histories.

## Filtered generated roots and deeper mechanism controls

A pre-valuation population declares seeds0..11 for each4/6board. Existing
generator filters remain, with a simple additional exclusion for initial
terminal/no-action or any immediate winning first action. Six of24 openings
are excluded,18 accepted. First3 accepted per size select4x4 seeds2/3/4 and6x6
seeds0/1/2, before evaluation. This purpose-biased exposed population does not
establish balanced rules, good games or representative all-rule performance.
All24 initial-root depth2 calls complete, repeat and equal six Core references.

Before deeper evaluation, advance each selected rule through four actual plies
using a fixed lexical-index rollout, preserving full history. Both controls
retain4096nodes/5sec/q0, targetdepth4 and two fresh-TT repeats. Plain completes
two of six roots, public TT/ordering four; no time fuse fires. One exhaustive
Core reference completes and agrees; five capped references remain unknown.
Different completed depths can have different scores and are not parity failures.
All generated roots use the legacy fallback: no Native legality provider exists
here. Completed-depth benefit must not be attributed to Native acceleration.

An additional equal-budget TT-only/order-only ablation reuses the frozen plain/
combined endpoints. Every repeat is stable; completed depth4 scores agree.

| Four-ply history root | Plain nodes/depth | TT-only nodes/depth | Order-only nodes/depth | Both nodes/depth |
|---|---:|---:|---:|---:|
|4x4/2|1616/4|1616/4|556/4|801/4|
|4x4/3|4096/3|4096/3|1580/4|1599/4|
|4x4/4|1734/4|1734/4|607/4|562/4|
|6x6/0|4096/3|4096/3|4096/3|4096/3|
|6x6/1|4096/3|4096/3|2237/4|2294/4|
|6x6/2|4096/3|4096/3|4096/3|4096/3|

Ordering supplies the observed completion benefit. TT-only does not reduce
nodes here; TT-best-move ordering can change the combined traversal, with mixed
node costs. Keep existing defaults; this small set does not select a globally
superior configuration or justify dropping full-history/repetition identity.

The actual nine-root capture/promotion/right/drop history also survives an
opaque lexical type rename. Complete mapped legal sets and18 exhaustive depth2
root-action spectra agree;108 fresh/reused/warm calls across default/full-PV
contracts are legal and optimal. Compiler IDs change structurally. Equal-score
ties can select different actions/PVs because lexical tie-breaking contains IDs;
score/optimality invariance is the supported observation, not exact tie identity.

## Reuse within one evaluation

The existing evaluator separately recomputed current-position pseudo-attacks
for mobility, each candidate anchor escape and check status. It now builds each
owner's map once per evaluation and shares it across those unchanged features.
Nothing is retained across calls/positions. Both zero-weight features still skip
the maps entirely. This preserves legacy pseudo-attack semantics, including its
known semantic-movement limitations; it adds no position feature or cache policy.

Six fixed history roots plus all immediate children, four configurations and
three passes give1524 exactly equal old/new evaluations. The381 full-feature
evaluations reduce actual map calls2577 to762; anchor-only1815 to762, mobility-only
762 unchanged and zero0 unchanged. All24 matched searches preserve exact chosen
action, score, completed depth and nodes. Summed local plain timing13.747 to
10.704sec and combined12.505 to9.889sec suggest useful savings on this cohort,
not a universal speed ratio. Earlier capped depths remain capped and unknown.
Regression checks cover fixed blocked-ray/check scores, orientation, per-call
map counts and disabled features. Source snapshots and measurements remain separate.

A further27 actual-history roots cover combined mechanisms, three Shogi
variants and Western capture histories. All108 old/new evaluations across four
feature configurations match exactly, including hands and auxiliary state.
This qualifies the reuse change on these semantic roots; it does not repair
the existing pseudo-attack versus semantic-movement valuation gap.

[Compact controls](data/generated_search_controls_20261008.json) and
[isolated archive](../archive/generated_search_controls_20261008/README.md)
retain definitions, actual routes, source snapshots, parity and cost records.

## Semantic root recovery

Actual R-to-TP effects exposed a Native import error: continuously advanced
states agreed, but fresh roots at combined plies5..8 failed a legacy promotion
whitelist. Pack now validates structural identity, preserving the false-flag
implies equal-types check. Actual self-promotion R/R/true and anchor-preserving
K-to-K2 effects show why stronger legacy restrictions are incorrect. It does
not certify external reachability or rewrite base identity. Capture/reply/drop
tests retain baseR acquisition and unpromoted R redeployment.

Fresh mirrors also omitted actor/check history. Six-word imports now preserve
it: an actual eight-ply continuous-check loss agrees with Core/carried Native.
Digest-only imports previously misreported draw; at the continuous-check
repetition threshold, missing events now reject adjudication instead.

Old/new extension processes give5/9 versus9/9 direct root acceptance. Twelve
matched public calls preserve action/score/depth/nodes/qnodes/PV. Each of six
old Native-on calls falls back once; new calls return546 provider results with
no failure. Earlier scores remain valid, but provider presence never proved
exclusive Native execution. Public decisions now expose the existing successful
call/fallback/failure counters. Fixed static generic-v1 controls qualify timings.

A separate bulk attack prototype matches scalar Core and Native on64 owner
maps;22 differ from legacy maps (cannon/Western pawn). Local0.0037sec versus
0.0673sec scalar cost is feasibility evidence, not a new evaluator/default,
legal mobility or universal speed claim. All failed prototypes remain isolated.
Only the needed installed-Zig build entry was restored from cleanup history.
[Compact controls](data/semantic_root_recovery_20261008.json) and
[sources/failures](../archive/semantic_root_recovery_20261008/README.md).

Two actual quiet-move cannon roots isolate a concrete dynamic-term confound.
Without a screen, Core/Native report no enemy check while legacy ray attacks
report check; with an immobile screen they report check while legacy reports
none. With only the existing anchor term enabled and identical zero material
controls, replacing the map changes scores by+55/-55 in side-to-move units.
The local monkeypatch is restored after the probe; legacy anchor-escape geometry
is still approximate. Semantic price comparisons should retain a static/no-dynamic
control, rather than attributing these map errors to the price table. The first
direct initial-root attempt was rejected by the legacy initial-anchor validator;
the qualified probe reaches each root through a real legal quiet move. That
separate compile-time semantic-authority issue is now repaired: internal baseline
metadata construction defers position checks to the final semantic executor.
Public legacy compilation, schema/inventory and round-trip validation stay intact.
Paired default/alternate starts admit the semantically safe no-screen layout and
still reject the screened attacked layout. Four public depth2 Core/Native calls
on admitted starts agree in action/score/depth/nodes/qnodes/PV; each Native call
returns17 successful legality results without fallback. This is entry/routing
evidence, not validation of the unchanged legacy dynamic evaluation terms.

## Explicit semantic attack authority

Core `SemanticEngine.attacked_squares` and Native `attacked_squares` collect the
same S0/S1 capture-eligible targets as their existing scalar queries. They do
not apply S3 anchor safety or S4 postconditions and are not legal-action counts.
Every square matches through four actual plies of twelve supported fixtures,
including cannon screens, Western/Shogi, temporary rights and postconditions.
Native collects paths once, rather than repeating a whole traversal per target.

`SemanticAttackEvaluator(compiled, profile, config, backend='core'|'native')`
is explicitly passed through the existing `evaluator_override`. It changes only
the attack-map source of existing dynamic terms. Static tables/weights,
promotion potential and approximate anchor-escape geometry remain separate.
There is no hidden backend fallback or persistent position cache. Native packs
current board/hand/aux state at each evaluation, not historical adjudication
claims. The first full-history implementation failed on actual runtime search
views; the failed producer/partial is retained. A real-search regression covers
that boundary. Default Evaluator and player configuration are unchanged.

The existing `scripts.unfamiliar_search.run_rule` accepts `attack_authority`
independently of `semantic_candidate` and records the choice. Its Core minimax
and both public controls share the selected leaf evaluator: they test search
consistency, not independent leaf authority. `python_plain` describes search
legality/TT/ordering, not the evaluator backend. No new command entry is needed.

A fixed three-root/two-table/four-feature/depth2,3 factorial completes96 calls;
all48 depth2 Core references agree and12 static map pairs are identical.
Among36 dynamic pairs,21 scores and6 actions change when only attack authority
changes. Twenty-four calls with the product opt-in evaluators reproduce those
frozen semantic actions/scores/nodes/depths/PVs. Local Native/Core full-search
ratios are about0.75 to0.83; no universal acceleration follows.

Production leaf measurements on27 actual-history states use five rotated-order
paired batches. Native/Core evaluation ratios are approximately0.35,0.42,0.42
for Western, Shogi and the cannon mixture; Native/legacy ratios are1.40,1.26,1.48.
Semantic correctness has a measurable cost relative to the simpler legacy map.
The first Native target-scan batch was slower than Core on Shogi and is retained.
The production-cost record contains all three completed measurement cohorts,
but final replacement failed with Windows error5: its completion flag stays
false. The shared atomic writer now retries only Windows5/32/33, at most three
attempts on the same closed record with30ms total delay. Permanent failure
preserves the prior frontier; this does not rerun experiments or hide failure.

A prospectively fixed12-seed inner-board placement cohort keeps six original
C/R identities and two fixed anchors. All12 compile and have no immediate win.
The192 equal-budget calls complete114 target depths, with zero Native fallback;
78 depth3 cells remain unknown. All24 depth2 static map pairs match exactly.
Dynamic maps change9/24 chosen actions and24/24 scores; changing the two frozen
tables changes only1/24 dynamic actions. Both static table changes are the same
layout under two maps. Cross-scoring every changed table-choice pair shows an
old static tie versus48-point candidate preference; legacy dynamics produce a
7/41-point reciprocal tradeoff. That dynamic change disappears with semantic
attacks. These are heuristic sensitivity/localization results, not better prices,
independent deployment validation or strength. No weights or defaults were fitted.

With evaluation fixed, an existing TT/ordering2x2 ablation on all12 roots uses
depth3/4, cold players,4096nodes/2sec and no quiescence/root tactical scan.
Atdepth3, neither nor TT-only completes a root; both ordered configurations
complete12/12. TT plus ordering has median paired node ratio0.83147 against
ordering alone, but seed202610081004 regresses2016 to2433 nodes. Atdepth4 both
ordered configurations complete2/12, with different roots: seed1008 completes
with ordering alone but caps with TT; seed1007 does the reverse. This local
completion benefit is attributed to ordering, not a universal TT/Native gain.

The subsequent depth3 table comparison fixes semantic attacks and TT/ordering,
and separately supplies old static ordering prices with candidate leaf prices.
All36 calls complete. Old-table outputs reproduce the prior ablation; candidate
ordering controls agree on score. Neither table nor ordering changes any of
the12 chosen actions, although eight root scores change. Wall clocks overlap
full regression testing, so they are excluded from fair timing claims. Low
choice sensitivity does not identify bad/good prices or justify dynamic patches.

Compact results, source pins, exact failures and recovery:
data/semantic_attack_authority_20261008.json and
../archive/semantic_attack_authority_20261008/README.md.


## TT hint mechanism and equivalent-encoding cost

A48-call repeated mechanism study separates TT score reuse from ordering hints
on exposed roots1004/1007/1008. At the original4096-node budget, seed1008 completes
with noTT3308 or bounds-only3677, while fullTT and hint-only cap. A new paired
8192-node/4sec trace completes all modes with the same score8: full4815 versus
hints-only5716. Old capped records remain unknown. The root hint is also the
depth4 best action, so the regression is not simply a wrong shallow root choice.

Keeping bounds, root-only versus internal-only hint interventions give seed1008
3471 versus4985 nodes, compared with full4815/no-hints3677. Traversal changes
history and future ordering; these are not additive causal costs. Root-only is
better on all three exposed roots, but a predeclared12-new-layout paired cohort
completes all24 depth4 calls and saves nodes on only5 while regressing7. Its median
ratio is1.010767, mean0.998660. An immediate-win root is retained/labeled. This
fails to justify a product switch/default change or a global superiority claim.

A separate equivalent quiet-action copy on those12 now-exposed layouts preserves
completed scores under the same evaluator/budget, but increases nodes on every
root, median ratio1.194846 (range1.038410 to1.219925). Public binding identities and
lexical traversal can incur representation cost even when physical effects agree.
This is an observed efficiency issue, not permission to merge arbitrary moves
by coordinates/Position: action-dependent history and triggers must remain valid.
No search/player setting, Core identity or production code changed in this study.
Local interventions and all earlier records are isolated, not active imports.

Exact producers, original caps/failures and new synthetic inputs:
../archive/joint_context_search_20261008/README.md;
compact data/joint_context_search_20261008.json. Native wall-cost claims exclude
instrumented runs; node counts and completed scores are the comparison here.


## Duplicate-binding cost: existing identity and evaluator work (2026-10-08)

On the first frozen exposed root,42 public actions give32 physical successors
with10 duplicate groups. Full Core and Runtime search keys and terminals agree
within each group; full history records differ by action signature, while the
current rule's required runtime history context agrees. No public action or
history is merged. Negamax evaluates depth-zero leaves before its internal-node
TT probe, so existing state identity does not eliminate repeated leaf work.

A3-root trace observes repeated evaluator calls with no score conflicts; one
instrumented duplicate call hits the4-second cap at depth3, so it is not a fair
completed-depth speed comparison. Its first failure incorrectly requested full
GameState history from RuntimeSearchState; the correction uses its authoritative
runtime search_key. That lightweight view is intentional, not missing history.

A separate cold rotated36-call pilot compares no cache,256-entry attack-map cache
and256-entry whole-evaluation cache on6 exposed original/duplicate roots. All
complete depth4 with exactly equal paired score/nodes/action/PV. Summed search
time is21.689/21.326/20.639 seconds; both caches hit15068 times. The fixed evaluator
reads Position/ply with fixed rules/profile/config; this is not a generic claim
that arbitrary evaluators or terminal values are history-independent. Modest
local gain does not warrant another product cache/flag now. Keep search defaults
and action identity. Full evidence is in data/target_context_20261008.json and
../archive/target_context_20261008/; only source/target legal binding queries are
added to the product this segment.

## Frozen task-table deployment and a recombined drop-cost caller

24 fresh C/R/N inner-board placements compare old generic-v1, direct-task and
preparation-task leaf tables under the same Native semantic attacks, old generic
ordering weights, TT/order and8192nodes/4seconds. Quiescence and root tactical
scan are off. All72 depth3 cells complete and72 cold repeats match action/score/
nodes/depth/PV exactly. Depth4 completes69/72; all three caps belong to seed4016.
Every PV replays through Core; Native legality fallback is0. Direct/preparation
tables change0/24 depth3 actions and1/23 complete depth4 actions. The changed
pair has independently completed plain Core conditional values995/749 versus
995/1310. This is an exchange-weight preference, not strength or preparation-policy
learning. Fixed additive weights cannot distinguish equal-inventory quiet states.
Summed search times and node curves are recorded; no default is changed.

The next caller is the existing supported recombined lifecycle fixture, not a
new framework: real captures create hands, a diagonal move promotes R to TP and
sets an expiring slot, and a zone-capacity guard enables/disables R drops. Actual
public GameSession history reaches ply4..8.20 cold depth2/3 calls retain legal
PVs and repeat exactly. Seven of ten independently bounded Core reference cells
complete and agree; three4096-leaf references stay unknown. Public depth3 completes
on four frontiers; ply6 has92 legal actions/58 drops and both repeats hit8192nodes.
The post-expiry state is not replaced by a history-free board snapshot.

An observed-cost followup pairs the existing staged move picker with baseline
on ALL five frontiers, two depths/two cold repeats (40 calls), with every other
condition fixed. Completed scores agree and repeats are exact. It does not
resolve ply6's cap. At ply5 depth3 it regresses963 to1213 nodes; ply4/7 save just
one node each, and ply8 regresses2561 to2607. Thus this switch is not adopted or
expanded into a blind tuning sweep. Instrument the actual caller cost before
another optimization; preserve action legality, state/history and price conditions.
Exact sources, failures, profiles and per-call curves:
data/preparation_transfer_20261008.json and ../archive/preparation_transfer_20261008/.

## Actual evaluator cost and the node-cap distinction

Those quiescence-off callers revealed a product telemetry defect: negamax static
leaves and the no-action fallback omitted evaluation counters; root tactical
scans counted calls but omitted elapsed time. A single accounted evaluator entry
now covers these paths plus both quiescence paths. Terminal/TT results remain
unevaluated. Eight deterministic public-path tests independently count calls and
elapsed work across legacy/semantic rules, qsearch off/on and root scan off/on.
The accounting is attempts, including failure cost, rather than completed leaves.

Independent timing on actual callers exposed a second issue: Windows monotonic
clock increments are too coarse for these short evaluations, and an initial
aggregate measurement fell below the independently measured evaluator duration.
That failed replay is retained. The helper now uses high-resolution perf_counter;
budget/deadline semantics remain unchanged. Ten existing depth2/3 real-history
cells preserve every action/score/depth/PV/node signature and exactly match actual
evaluation counts. Old archived zero counts are missing telemetry, not zero work.

The ply6 depth3 cap uses7897 evaluations; independent evaluator time is about27%
of whole wall time and its nested semantic attack maps about21%. A separate
8192-node cProfile run retains the same decision with its wall cap omitted solely
to avoid instrumentation aborting the node work. It sees482053 geometry-candidate
derivations and23538 Core attacked-square calls. Nested cumulative profile times
must not be added or treated as an uninstrumented speed comparison.

Two motivated local interventions use all five frontiers, depth3, two cold
rotated repeats each under the unchanged8192nodes/5sec conditions. Fixed compiled
geometry memoization saves about5.3% on ply6, with one small-frontier regression.
A Native current-position gave_check bridge saves about5.6% on ply6; a separate
dual pass verifies15711 bridge answers against Core. The bridge leaves runtime
history, terminal adjudication and before/after cooperative checkpoints intact;
it does not import history into Native. All decisions/nodes/PVs remain exact.
Neither intervention resolves the node cap, and neither is added to the product.
This cost curve motivates a bounded node-budget diagnostic before another cache
or bridge interface. No strength, cross-rule speed guarantee or default change.
Data/recovery: data/evaluation_cost_20261008.json and
../archive/evaluation_cost_20261008/index.json.

## Bounded budget increment completes the drop mate

A separate predeclared development curve gives BOTH baseline and staged ordering
16384/32768nodes and10seconds on all five existing real-history frontiers, depth3,
two cold rotated repeats (40 calls,41.122seconds total). Old8192-node failures
remain unchanged. All40 cells now complete, agree on scores and repeat exactly.
The two larger caps produce identical completed work at the fixed requested depth.

The58-drop ply6 frontier finishes at9544 baseline/9569 staged nodes, score
999999997 rather than the earlier completed-depth2 score9203. The actual root
choice stays R-drop(6,6); the new iteration recognizes its forced mate. Actual
used baseline nodes rise only16.5% above8192; the configured doubled ceiling is
headroom, not consumed work. One representative baseline call takes2.826seconds.
Staged ordering still has no clear benefit and is not adopted.

An independent full-history Core replay after that root drop enumerates both
legal opponent defenses. Each has a legal reply ending in mate for owner0;
110 visited successors take.051seconds. The API constructs successor tuples
eagerly; a separate counted replay measures215 actually constructed successors
including the root, with the same mate result (~.052seconds). Both original and
corrected cost records remain; visited count must not be used as total work.
This local check confirms the
observed new terminal conclusion; it is not a new WDL gate for development.
Per-node5% speedups alone cannot fix a hard node-cap failure. Here a small bounded
increment yields more useful information than adding cache/bridge interfaces.
No default budgets, evaluator, action/history identity or active workflow changes.
Exact raw curve/declaration, mate branches and recovery:
data/drop_budget_20261008.json and ../archive/drop_budget_20261008/.

## Fresh generated movement with recombined mechanics

Four predeclared fresh seeds202610081100..1103 use the existing4x4 bilateral-
random hybrid generator and simple filters. X gains the supported quiet X-to-P
current-type change with expiring slot; X drops use the existing zone-capacity
guard. A declared twelve-ply capture/semantic/drop coverage policy retains full
public history, hands and aux; it is not a strength policy or population.
All four rules compile and reach twelve nonterminal plies. Four bounded plain
Core depth2 references complete and agree with public search. All16 cold depth2/3
calls complete and repeat exactly, every PV replays, Native fallback is zero.

Two routes exercise slot1 then expiry0, and one exercises the guarded X drop.
Final12ply checks alone have expired slots. A separate ALL-observed-event check
covers both active states, both immediate expiry states and the guarded drop:
ten public Core/Native-legality calls under one fixed evaluator agree exactly
on action/score/nodes/depth/PV, with no fallback. This is finite interface transfer,
not universal support, speed or static-price completeness.

The slot in that original fixture is not consumed by any guard. Its successful
state replay tests representation/expiry but would be weak evidence of behavioral
relevance. A further explicit mechanism check reuses those four active/expired
frontiers, fixes the zone rule on P drops, and varies only temp_right==0 versus1.
With slot1, matching guard enables4/7 P drops while the opposite enables0; after
expiry0, matching guard enables5 on the nonempty-hand frontier, opposite0. The
other expired frontier has no P hand and retains its zero. All16 Core/Native
depth2 public calls agree exactly, PVs replay and fallback is0. History and the
actual slot value determine legality; no board-only reconstruction is substituted.
No product/default changes follow. Next inspect scaling on a predeclared larger
generated cohort, keeping mechanical coverage separate from useful play.
Exact inputs, declarations, zero coverage and recovery:
data/generated_recombination_20261008.json, data/expiry_guard_20261008.json and
their purpose-specific archives.

## Generated6 scaling with consumed expiry

Four predeclared seeds202610082000..2003 use6x6 bilateral-random hybrid rules,
the same supported X-to-P quiet transformation/expiring slot and zone-limited
P drops consuming slot==0. Existing generator filters are unchanged. The original
capture-first12ply route gives one checkmate at ply10 and three nonterminal roots
with89/3/101 legal actions. No original route exercises the transformation or
expiry: the zero coverage is retained rather than described as full transfer.

A separately declared16ply semantic-first route exercises transformations in
two rules and guarded drops in two. One route ends in mate; every one of the22
observed active/expiry/guarded-drop frontiers has exact public Core/Native
action/score/depth/node/PV parity (44calls,9.739seconds), with no Native fallback.
These selected policies are mechanism coverage, not useful-play populations.

Both original and extended routes have24 cold searches under one fixed Native
attack evaluator, TT/order on,q0,8192nodes/5seconds, varying legality alone.
Completed same-depth results agree exactly. Seed2003 is a useful scaling failure:
Core legality completes only depth2 before5seconds, while Native completes depth3
at7858nodes on the original root and7736 on the coverage root. A separately
declared fair10second increment for BOTH modes (eight calls) completes all cells
with exact signatures. Representative original Core/Native costs are5.485/3.174s;
coverage costs5.326/3.096s. This is wall-limited depth completion, not price or
semantic improvement. No defaults or original caps change.

The original4000-leaf Core reference fuse aborts on seed2001/2003. A separate
20000-leaf/10second increment finishes at5565/9413 leaves, matching depth2 public
scores3413/-9. A node-bounded Core profile of seed2003 completes the same7858-node
signature as Native. Core is_square_attacked consumes8.206 nested instrumented
seconds of14.193 total; checkpoint callbacks and geometry contribute overhead.
These profiling times are not fair speed measurements or additive cost buckets.
The existing Native boundary already addresses this cost; no new cache/flag is
justified by these callers. Full declarations, zeros/caps and recovery:
data/generated6_20261008.json and ../archive/generated6_20261008/.

The first actual transformations of seeds2000/2003 also supply a finite price
scope check. Changing only the effect destination P versus X leaves generic-v1
and semantic-opportunity-v1 raw scores/tables unchanged; the latter explicitly
excludes compound/state effects. Both variants have the same39/23 legal opponent
reply actions. Across that common support,51 continuation movement-endpoint sets
and25 capture-endpoint sets differ. Raw binding counts are retained separately;
endpoint equality is not a physical-successor quotient. This exposes a qualified
missing future-capability input, not executor failure, a material-value relation
or permission to mix preparation utility into static prices.

## Generated8 width and existing PVS

New seeds202610082100..2103 use8x8 bilateral_random/hybrid rules with the same
consumed-slot/expiry transformation and guarded P-drop. The semantic-first
16-ply route leaves four ongoing roots with126/123/61/90 legal actions. These
are coverage routes, not independent playing-strength samples. All four
Core depth2 references finish within20000leaves/10sec (15054/14217/3384/10135
leaves), matching completed public depth2 scores1225/288/5943/-4217.

At depth3,8192nodes/10sec, fixed Native attack evaluator, TT/order on and q0,
two cold Core/Native legality calls per root retain original partial results.
Native completes only seed2102:5115nodes/score9432. Seeds2100/2101/2103 remain
node-capped under Native;2103 Core also hits its cooperative wall checkpoint.
Native addresses observed legality wall costs, not tree width.

The existing opt-in PVS flag, changed alone, completes seed2103 at8150nodes
with score-1042; seed2102 uses4657nodes.2100/2101 still cap at8192. A separately
declared paired16384/32768-node20sec curve tests all four roots, rotating
baseline/PVS order and repeating each cold. Every32768 cell completes depth3:

| Seed suffix | Baseline nodes | PVS nodes | Score | PVS/baseline wall ratio |
|---|---:|---:|---:|---:|
|2100|17884|16716|3131|0.943|
|2101|19999|10275|701|0.589|
|2102|5115|4657|9432|0.910|
|2103|9027|8150|-1042|0.924|

Completed same-depth scores agree; cold repeated action/score/nodes/PV match
within each configuration. At16384, seed2101 completes only with PVS; seed2100
still caps with both methods. Partial scores are not depth3 certificates.
Local wall ratios include validation overhead and are not hardware-independent.
This selects fresh transfer validation of an existing option, not a new cache,
default, price or strength claim.32 curve calls took203.49sec; baseline16calls
and references took116.69sec. Recovery: data/generated8_20261008.json and
../archive/generated8_20261008/index.json (10 extracted/rehashed members).

## Fresh PVS transfer, qsearch and honest cost accounting

Eight predeclared fresh seeds202610082200..2207 use the same8x8 mechanism
mixture,16-ply coverage route, Native attack/legality, TT/order and q0.
Root tactical scan is off solely to isolate PVS. Two rotated cold repeats at
depth3/32768nodes/20sec complete five baseline roots and seven PVS roots.
Every common completed-depth score agrees; completed repeated signatures match.
Seed2200 regresses805->938nodes and about0.57->0.80sec;2201/2202 gain essentially
nothing.2204 improves20534->10919nodes,2206 improves5397->4809. Seeds2205/2207
complete only with PVS at this budget; seed2203 caps with both. Thus this is
heterogeneous transfer, not a universal speedup or default promotion.

A separately declared fair65536node/40sec extension of2205 completes both:
baseline38829/PVS25011nodes, same score1794.2207 baseline depth3 stays unknown.
Seed2203's retained action independently replays to immediate mate; restoring
the existing default root scan finds it in81nodes/~0.088sec. That deliberately
disabled-scan diagnostic does not justify a new cache or termination patch.
Original failed Core references and search caps remain in the records.

With q4/hard8 instead of q0, fixed32768node/20sec calls on2200/2205 all wall-cap
at retained depth2/depth1 respectively. q0 PVS gains do not establish q4 gains.
An actual generation-cost audit exposed missing qsearch timing and Windows
coarse-clock zeros. One helper now times explicit root/main/q/TT-PV runtime
generation requests with perf_counter, including aborted attempts. Budget
deadlines still use monotonic time; internal cached push-validation calls are
not counted again. Existing main-only successor counters remain qualified.
Four fixed4096-node caller signatures, public PVs and runtime pushes are exactly
unchanged before/after the repair; measured generation costs become0.295..0.703sec
instead of zero. Nine focused tests independently charge real generation/cache
misses under a deliberately frozen coarse budget clock and cover cancellation.

Profiling2200 identifies repeated attack/probe work, not static leaf evaluation,
as the next mechanism. The default qsearch classifies all legal quiet actions
before a cutoff; existing opt-in ordered qsearch classifies lazily. Changing
only that flag at depth2/4096nodes/q4hard8 reduces2200 runtime pushes25853->6106,
qnodes2850->1227 and local wall9.72->2.45sec with the same completed score-1537.
2205 reduces pushes43678->27975 and wall19.35->13.11sec but both still hit the
node limit at depth1; requested depth2 remains unknown. Cold signatures repeat.
Instrumented nested profiling times overlap and are not speed comparisons.

The follow-up fixes all four previously exposed2100..2103 roots before observing
outcomes, rotates two cold repeats, changes only ordered-qsearch, and gives both
methods depth2/8192totalnodes/20sec with q4hard8. Every failure is retained in
data/pvs_transfer_20261008.json and its extracted/rehashed source archive.
These are finite development controls, not exact WDL, material utility or Elo.

The four-root follow-up completes no requested depth2 cell: all retained depth1
scores agree (2440/523/6286/-691). Ordered2100 stops at7.82sec on the qsearch
in-check hard-depth safeguard rather than finishing sooner; its14970 pushes
versus baseline~40k do not establish a completion speedup. Ordered2101/2102
reach the8192 total-node cap, while baseline wall-caps;2103 wall-caps both.
Thus lazy classification can expose a new safeguard/node bottleneck without
improving completed depth. Preserve those failure kinds rather than counting
every reduction in elapsed time as a gain. The next useful check is the first
actual hard-check path, not an unchanged larger-budget rerun or default flip.

One diagnostic replay captures that exception path without changing conditions:
qdepth4..8 are all in check, and the depth8 position remains ongoing. None of
the nine recorded qpath positions repeat; this does not prove full history
repetition semantics, but supplies no evidence for a repetition-loop fix. Keep
the hard safeguard. Separate hard-trace-index.json archives the actual positions,
action/check history, producer and final accounting assertion/comment updates.

## Quiet-check support versus repeated execution cost

The existing capture-only option is a different qsearch approximation, not a
cost-only repair. Two rotated cold repeats on the exposed2200/2100 roots fix
depth2/8192totalnodes/20sec, ordered qsearch, q4/hard8, Native attack/legality,
TT/order and root-scan-off. On2200 it keeps depth2/score-1537 while reducing
pushes6106->2940 and local wall2.49->0.97sec. On2100 it avoids the hard-check
abort and completes depth2/score1234, but needs45269pushes/~19.7sec instead of
14970pushes/~8sec retaining only depth1/score2440. Different completed depths
and qsupport cannot be called equivalent decisions or a universal saving.

A concrete4x4 diagnostic establishes the omitted consequence. Owner0 has one
R in hand; high-rank-first board is `..../R.../..../K.k.`. The quiet move
R(0,2)->(2,2) checks. Both legal defenses, K(2,0)->(3,1) and ->(3,0), are
answered by R-drop(3,2) checkmate. Core enumerates all defenses and both final
terminals. Full q4/hard8 scores999999997 in83qnodes, with both immutable and
mutable paths; capture-only returns stand-pat1896 in one node. This selected
witness is not a population or strength estimate. Keep quiet-check support
and the hard safeguard; a cheap approximation can discard a real tactic.
The first diagnostic producer failed on a reversed runtime constructor after
finding the witness. Its incomplete output remains beside the corrected version.

A separate cost-only change reuses the exact child-side check already computed
by a nonpass runtime push. The answer belongs to the current DFS frame/identity,
not arbitrary imported history; roots, passes and the other owner use fresh Core
queries. A pass deliberately records no checking responsibility, which need not
equal the actual child check. Pop/exception undo restores the frame, and cached
queries still execute the cancellation checkpoint. Public action/history support,
attack authority, prices, order and depth limits stay unchanged; no new option.

The local prototype first repeats2200/2100 without a wall timer, then transfers
to the seven remaining fixed exposed2201..2207 roots at20sec. Completed-depth
evidence and all failure causes are retained.2202 improves from a wall-capped
depth1 to completed depth2;2205 still wall-caps. These observations motivated
the narrow product method, not a claim that every cap or search cost is solved.

Actual product replay separately fixes three preselected mechanism roots
2200/2100/2202 at depth2/8192nodes/40sec/q4hard8 and rotates two cold repeats.
Compare the new method with the same product patched to fresh authoritative
queries. All12 action/score/main+qnodes/depth/PV/stop signatures and runtime
push/pop/legality counts agree exactly. Local baseline versus reuse seconds:
2200 2.465/2.520 vs2.118/2.063;2100 8.015/7.832 vs6.980/6.670;
2202 22.837/22.813 vs18.658/18.737. Both2202 methods now finish depth2 under
the separately declared fair40sec continuation; the old20sec failure remains.
2100 still stops at the hard-check safeguard. This is execution savings on
exposed development roots, not new prices, strength or an independent holdout.

Default lexical qsearch is checked separately:2200/2100, depth2/4096nodes/40sec,
q4/hard8 and two rotated cold repeats per method. All eight exact signatures
and runtime work agree.2200 completes depth2/score-1537 at baseline9.675/9.771sec
versus reuse8.030/7.915;2100 retains depth1/score2440 at the node limit, with
15.568/15.572 versus12.863/12.883sec. An unchanged incomplete result is still
incomplete, even though executing the same fixed-node work costs less.

The existing caller hard-check-depth control gets its own finite curve on2100:
q4, hard8/12/16, depth2/8192totalnodes/30sec, ordered qsearch and two rotated
cold repeats. Hard8 stops at the original safeguard (~6.75sec);12 and16 both
reach the node limit (~19.5sec). All retain depth1/score2440; none completes
depth2. Longer check horizons expose a tree-work bottleneck, not a demonstrated
solution. Keep every old failure and default; do not extend this curve unchanged.

A local source-clone experiment also classifies each ordered quiet action and
recurses inside the same push, preserving the same action support and q counters.
2200 pushes6106->5866,2100 14970->14357; completed signatures agree. This later
prototype is retained as development evidence, separate from the deployed
current-child check method. It does not yet justify a second product refactor.

Four separately predeclared fresh8x8 callers2300..2303 then test actual product
reuse at depth2/4096nodes/20sec/q2hard8, default lexical qsearch, Native attack/
legality, TT/order and root-scan-off. Each executes the fixed16-ply mechanical
coverage route and four rotated cold calls. All16 exact signatures and completed
scores agree with fresh Core queries.2301/2303 finish depth2;2300/2302 retain
depth1 at the node limit. Local baseline/reuse seconds are12.71/10.76,
8.41/7.99,7.52/6.72,5.99/4.87 in the first rotation, with the second retained
in the raw record. This extends execution evidence to a declared fresh cohort,
not independent material validation or a reason to hide the two failed depths.

Another local cost hypothesis is rejected. Runtime terminal probing asks Core
whether any legal action exists; substituting the existing Native FULL transient
legal list and taking its nonemptiness regresses2200 ~1.97->2.97sec and2100
~6.61->9.89sec under the same fixed-node ordered-qsearch calls. All signatures/
runtime work agree. Independent dual-query calls verify6680 predicates, including
36 false cases, but correctness alone does not make full-list construction a
good replacement for Core early exit. No Native terminal/history authority, new
provider contract or cache is added. The first bridge matched engine-instance
identity despite per-query engine creation; its zero-call interrupted record
is retained as a failed local harness, not included as speed evidence.

With q2, the existing PVS option does not repeat its old q0 completion advantage.
All four now-exposed2300..2303 roots get a separately declared fair4096/8192node,
20sec, two-rotation curve. Both methods complete two depth2 roots at4096 and
three at8192;2300 wall-caps with both at the larger budget. At2301 total nodes
rise3044->3071;2303 rises2343->2744. At2302,8192 permits both to complete:
baseline6481/PVS6114nodes, but local PVS wall is higher (11.44/12.04 versus
10.05/11.09sec). All common completed depth2 scores agree. More configured
headroom is not equal to actual work; fewer nodes are not necessarily less time.
These results support retaining the current defaults and checking the actual
caller/q configuration rather than extrapolating from the old q0 cohort.

## Open: equivalent transformation encodings change q support

A new4x4 witness fixes K(0,0), enemy K(3,3), own A(1,0), with A one forward
leap and B four orthogonal rays. A semantic forward empty-target move sets the
actor's current type to B. Compare promotion_mode none against explicit B;
the latter redundantly sets exactly the same final type/promoted state.
In a combined definition both public bindings produce the EXACT same child
Position/terminal under one fingerprint, while promotion_target_id is null/B.
There are no hands or history/aux triggers in this finite control.

Frozen generic prices are A274/B1726 in both definitions, with dynamic terms0.
Existing classification excludes the effect-only quiet action but includes its
explicit-promotion equivalent. q1/hard8 therefore returns274 versus1726 on both
immutable and mutable paths. The combined definition returns1726. This is a
concrete representation-dependent approximation, not a Core execution error,
price-fit result or playing-strength estimate. Current-child check reuse preserves
it; that execution optimization does not claim to repair all qsearch semantics.

The next action is a narrowly validated classification fix, separating actual
type/inventory change from public promotion labels. Actor-local detection and a
price-free owner/current-type inventory comparison including hands have different
scope/cost; normal drops and pure aux changes need explicit controls. Do not
silently broaden all quiet actions or add a price-specific rule. The witness and
source are retained before any fix. One concrete advisor question was sent;
independent work continues, without an approval gate.

Exact declarations, producers, failed versions, all caps and recovery for this
section: data/qsemantics_20261008.json and ../archive/qsemantics_20261008/index.json.

No-change followup (promotion-nochange-v4): initial baseA/currentB promoted actor
with valid legacy targets and empty promotion-pair masks. Effect setB and
redundant explicitB produce identical physical child/terminal in the combined
fingerprint, but classify false/true. Frozen q1 scores both1726, qnodes5/6 in
both mutable/immutable paths. Three fixture-validation failures are retained.
This confirms the advisor objection: an inventory fallback after unconditional
semantic promotion metadata does not establish representation-invariant support.
Adopt actual-effect controls before a limited classification correction; inventory
count cancellation and unrelated auxiliary changes remain explicitly outside any
complete-tactics claim. Public action/history identities are never quotiented.

Balanced-type followup: ownA(1,0) moves to(1,1) asB, while ownB(2,0)
becomesA. Actual per-owner current-type counts and total material2000 stay
constant despite spatial capability changes. Effect/explicit same-child
encodings still split support(false/true) and qnodes5/6; scores both2000.
Thus inventory alone cannot detect all actual transformations. The next finite
contract must state this limitation and resolve encoding equality, rather than
claiming a complete detector or keeping unconditional semantic metadata authority.

A separate local inventory prototype removes unconditional semantic promotion
authority (legacy shortcut retained), snapshots parent counts before push and
compares actual board-current plus hand-base owner/type counts.18 finite calls
give effect/explicit1726/2qnodes, no-change1726/5 and balanced2000/5, matching
mutable/immutable. Combined transform retains both public actions:3qnodes,
not2. The first assertion wrongly demanded identical combined traversal and is
retained; corrected comparison preserves duplicate identities. This limited
signal resolves the tested support split, still misses count-conserving type
swaps, and has no drop/pass/terminal/cost acceptance. Not deployed. Supplement
recovery: archive/qsemantics_20261008/inventory-followup/index.json.

Additional inventory-only controls cover ordinary Rdrop and both legacy/semantic
pass through immutable successors and mutable push/pop: counts stay unchanged.
They check only the proposed signal, not full qsupport or terminal precedence.
An initial missing fixture import path is retained alongside the corrected run.

## Actual-effect qsupport correction and shared ordered-q push,2026-10-08

The above pending prototype is superseded by a finite product correction.
Semantic public promotion labels and enemy target occupancy are not authoritative
effects. A real enemy-target no-op and an empty-target no-op can produce identical
physical children; target occupancy alone falsely called one a capture. Current
classification uses actual enemy-board decrease, then actual owner/current-board
plus owner/base-hand inventory change, then terminal/check inclusion. Normal
drops/pass conserve counts. Legacy execution retains metadata shortcuts.
Material changes are a limited signal: balanced type swaps, spatial/auxiliary and
base-only changes may conserve counts. No tactical completeness is claimed.
Promotion metadata is only a diagnostic subset after semantic material change;
do not sum promotion_qactions and material_change_qactions as disjoint classes.

One noisy_child policy is shared by immutable, eager-runtime and ordered-runtime
entries. Parent counts are copied before pushing the mutable view. Ordered q
now classifies and recurses within one push; eager lexical traversal keeps its
previous ordering/work contract. Check remains lazy. No new flag/cache or
default tuning is added; the semantic default classification itself is corrected.

The transform q1 witness now gives1726 for either encoding. No-change/balanced
controls, off-target friendly type change, no-op target, normal drop/pass,
terminal/check precedence and public counter propagation have product tests.
A focused one-push test checks both score/qclasses and exact push reduction.
Independent Counter/actual-effect predicates cover56 fresh route roots and3580
legal successors in both capture-only modes. Three branch-observable qroots
agree with independent full-width Core references and operational Native legality
(positive calls,zero fallback). The earlier D1 transfer's zero material counters
alone did not exercise the corrected branch; that limitation is retained.

Original-to-corrected default q2: all16 rotated calls keep choice/score/completed
depth, but actual qwork and local wall increase about1-7%; do not call it speedup.
Pre-fusion-to-shared ordered q4:16 rotated calls keep exact signatures/qclasses,
reduce actual pushes and local wall about4-23%. This separate cost result does
not attribute gains to changed qsupport. Four final default replays keep all
pre-fusion actual-effect decisions/work.16 legacy controls retain exact results
and work; wall noise is not a legacy gain. Full suite1648 passes, including the
old Shogi test after supplying its missing mandatory SearchTuning fixture field.

Exact declarations, every cap/source/failure and isolated recovery are in
data/qeffects_20261008.json and ../archive/qeffects_20261008/index.json.

Record audit correction: earlier prose61roots was wrong; recount56nonterminal
roots/3580children. The first audit executed both kernels but saved only Native
qrows due a one-line-if. final-v2 repeats and persists all6Core/Native calls,
with the same independent full-width scores. Old outputs remain recoverable.


## Fixed q2 factorial and target-directed attack cost (2026-10-09)

After the actual-effect correction, four exposed generated8x8 callers2300..2303
receive the same D2/8192-node/30sec/q2-hard8 conditions, Native attack/legality,
TT/main ordering on and root scan off. Two rotated cold repeats per PVS x
ordered-q cell give32 calls. Plain completes D2 on3/4 roots; each other cell
completes4/4. Common completed-depth scores agree, but PVS is not uniformly
better than ordered q alone. For2301 its work rises3045->3072 and the combined
cell rises3498->3525. For2302 ordered q takes6452 work versus combined5934.
The matrix separates search-tree changes from equal-work execution speed;
it does not select a default or establish strength.

One2300 profile keeps exactly the unprofiled completed signature. Its120sec
headroom is solely cProfile overhead, not a fair-budget extension. Attack
queries cost22.31sec cumulatively of37.68profiled wall; their4.65sec own time,
geometry construction and nested budget callbacks expose avoidable work.
A square-specific query was constructing every geometry endpoint and prefix,
then discarding every nonmatching target. The narrow change iterates matching
compiled prefixes directly. Order, minimum distance, duplicate target prefixes,
path/state/slot guards and S0/S1 authority remain; no atom reinterpretation,
cache, price/default change or general callback throttling is introduced.

Before deployment,2306346 compiled target queries across Chess/Shogi and four
actual generated8x8 rules match the original all-endpoint filter exactly.
8994 attack queries on70 initial/route positions also match the unchanged
full-map authority. Cancellation propagates on all six rules. Six product
cases cover minimum distance, repeated prefixes, leaps, absent owners and
rectangular flat-index geometry. The full active regression suite exits0.
A separate16-call cold original/prototype comparison retains choices, scores,
PV, nodes, pushes and every qclass, with local wall reductions about5-14%.
Actual product replay and post-change residual profile are recorded separately;
use their exact data rather than projecting prototype timings to other rules.

Recovery: data/qfactorial_20261009.json and
../archive/qfactorial_20261009/index.json. The pawn-scope/law study is a separate
archive and research layer, not an active search dependency. Next inspect the
post-change hotspot and choose one interface cost with unchanged semantics;
do not promote PVS/ordered flags solely from these four exposed roots.

Actual product16-call replay is exact on all four roots. Before/product wall
medians are12.103/10.524,6.048/5.274,6.599/5.989 and3.344/3.175sec
(about5.1-13.1% lower locally). All actual pushes and qclasses remain identical.
The post-product2300 profile retains that same completed signature:31.996sec
profiled wall, attack predicate16.71sec cumulative/3.85own, matching-prefix
iterator2.99cum/1.87own. Budget-check own costs remain substantial but nested
callback time must not be summed into an alleged independent fraction. This
motivates examining compiled candidate/guard dispatch, not weakening deadline
or cancellation checks. Full1654 active regression cases pass (quiet dots,exit0).

A changed-premise immutable compiled-target index pilot retains16exact calls
and all runtime work. Lookup warm-index wall changes are+2.8/+3.4/+2.5/-0.6%
reduction across the four roots;16148entries/105geometries cost.010sec to build.
Subsequent calls share the index; memory bytes and per-caller cold allocation
were not measured. This modest inconsistent observation does not justify a
product cache/index or more framework. Keep the simple iterator; retain the
local pilot separately in index-pilot.zip/index-pilot-index.json.

Transfer followup uses all four existing6x6 semantic-first routes (68positions,
including active/expired auxiliary states). Actual product matches original
committed target predicate and unchanged full maps on4896attack queries;
306432compiled target/path queries agree. Cancellation propagates in all four
rules. This is recombined-mechanism semantic transfer, not another timing or
strength sample. Source/result/dependency: transfer6.zip/transfer6-index.json.

## Event-cost transfer and rectangular public interface (2026-10-09)

All22 existing6x6 event frontiers receive88 rotated cold original/product q0
calls under identical limits. Choices/PV/nodes and all recorded work agree;
local median wall reduction8.35% is descriptive on sub.12sec calls. A separate
tuple-membership miss guard avoids Python scanning without a cache:16 cold q2
calls keep exact signatures/work, median local reductions2.64/3.55/2.55/0.22%.
Four actual product replays are exact; their timing is not a fair new comparison
because regression execution briefly overlapped.306432 geometry and4896 attack
controls agree. Constructor-only pattern filtering was not executed: engine
creation per call invalidated its proposed amortization. No compiled index or
deadline/cancellation relaxation follows. data/query_transfer_20261009.json
routes declarations, failed premises, sources and complete outputs.

Two fresh7x5/9x10 cannon recombinations exposed a concrete interface defect.
AlphaBetaPlayer built an unused square-only default profile even with a supplied
evaluator; both orderers then called square-only board_size(). The constructor
now builds a default profile only when needed, and orderers index board_shape.
evaluation_profile is None and cache_hit false with an override; the ordinary
square default still builds/reuses its cache. Native's unsupported size is a
typed NativeUnsupportedRuleError; requesting Native on these rectangles uses
Core. This does not implement Native rectangle kernels or default rectangle
prices, nor prove every compiled rule is searchable by every evaluator.

12 public q0 calls match two full-width Core D2 references.16 further cold q2
calls (plain, TT/sorted, TT/staged, TT/root scan; two repeats) all complete D2,
retain legal PVs/roots and balanced pushes/pops. Captures create real hand/drop
branches. Separate7x5 temporal-transform and compound-friendly-shift roots and
their actual effect successors give20 public calls; all12 q0 scores agree with
four full-width references, all8 q2 calls complete.12 ordinary temporal replies
actually expire the global right; one opponent transformation sets it anew.
Compound movement changes four board cells. Complete state/history witnesses
are retained, rather than installing a Position while inventing session history.

The supplied unit evaluator is an execution control, not useful material prices;
changed search work or tied choices are not strength gains. Full active suite
1667 cases passed before the final typed-Native test was added; final49 relevant
cases pass after that addition. An early provider-present assertion failed on
six rectangle cases because it confused a Native request with actual capability;
the test and claim were corrected. Recovery, scopes and all capped conditions:
data/rect_search_20261009.json and ../archive/rect_search_20261009/index.json.

A boundary check separates raw opportunity from profile assembly. On the same
two cannon rectangles, ten existing-density quiet/capture curves match an
independent width/height endpoint sum: quiet=(1-d)^distance and capture=
(d/2)*k*d*(1-d)^(k-1), k=distance-1 (zero at k=0). Raw semantic opportunity
already uses board area correctly; candidate profile assembly explicitly rejects
square-only legacy metadata. This is not a reason to bolt an approximate price
table or Native kernel onto a validated Core search fix. Preserve the raw/table
boundary and choose the next actual interface need, not another density sweep.

One changed-premise followup reuses TT/ordering across actual initial, right-set
and ordinary-expired states. An explicitly artificial aux-sensitive evaluator
makes the state change observable; root controls are0/-100/0, D2 references
0/0/-200. Sorted/staged warm players and their cold controls give12 complete
calls matching six full-width checks with legal PVs/unchanged roots. Real TT
hits occur and work can differ. This checks stateful interface reuse, not useful
prices or generalized TT correctness; it does not extend the frozen q2 cohort.

An existing equivalent-transform fixture changes semantic action rank from
fourth (implicit effect) to first (explicit promotion) in both orderers, but
all eight D3 public calls still use51 nodes and score1726, matching full-width
Core. No cost/result reason for another ordering patch was observed. The first
probe's final cross-rule Position equality assertion failed on fingerprints;
that incomplete output remains intact. A separate no-search qualification
confirms every other physical field agrees; it never merges rules/TT identity.
Sources/failures and scope: data/encoding_order_20261009.json.

Next-cost localization selects the largest saved q0-push event among the22
existing frontiers: seed2001, ply16. One Native-authority profiled q2 call keeps
the5sec cap, completing D1 before time_limit,1667 qnodes/8268 balanced pushes.
Runtime noisy-action classification costs3.475sec cumulative (.013own), attack
predicate2.332cum (.583own). These overlap; do not sum independent percentages.
The subsequent frozen22-event comparison completes all44 calls at D2 with the
same decisions/PVs. Ordered q reduces pushes133480 to50224, but increases qnodes
in four mate cells; this is scoped execution evidence, not a default or strength
recommendation. Personal-path binary profiling stays local.

Isolating push sharing from ordering gives a simpler product improvement. Both
sides retain lexical q order; all22 pairs agree on decisions, main nodes and
qnodes, while pushes fall133480 to63829. Local median wall reduction44.19% is
descriptive. Runtime q now classifies each child in its recursion push and stops
classification after cutoff, matching immutable q's demand-driven structure.
No heuristic, tactical definition, deadline or callback is relaxed. Existing
eager classification remains a parity/historical reference, not a live caller.

Four actual product cold callers retain frozen results/work. Cancellation at
positive runtime depth unwinds state/history/witnesses and balances pushes/pops.
The first warm-resume attempt wrongly demanded cold node equality; its incomplete
six-record output remains intact. A separate three-call continuation confirms
the same warm decision/PV/depth, with legitimately changed work from partial TT.
Four existing8x8 rules give16 rotated cold original/product calls: all semantic
and node/qnode signatures match, including one rule remaining D1/node_limit.
No cap was extended to force completion.128/512-node and hard-q2 controls retain
legal fallbacks or completed results; before-D1 stop reporting now preserves
node_limit instead of calling the cause fallback. First-completion latency now
stays at the first completed depth; historical overwritten metrics are qualified,
not rewritten. Final active regression passes1673 cases.

A further push-only prototype prefilled complete Native legal sets for terminal
probing. It regressed the selected event from D2 in2.924/2.954sec to D1/time_limit
in both5sec-capped calls: roughly547k provider actions instead of27k. Many quiet
children never recurse, so eager full-set work is wasted. Reject this prototype;
retain Core first-legal streaming and ordinary Native generation at actual nodes.
These capped calls do not support an equal-work timing ratio or a new kernel.
Exact sources, incomplete attempts, controls and recovery:
data/event_qsearch_20261009.json and ../archive/event_qsearch_20261009/index.json.


## First-legal Native candidate: deferred, not deployed

A different candidate reuses transient generation but stops after its first
legal action, retaining Core history adjudication. On68 existing contexts it
uses158 S3 trials versus3270 full-generation trials. Earlier connected builds
retain decisions/PV/depth/main/qnodes on22 frozen event roots/44 cold matched
calls; local median wall reduction31.64% is descriptive and pre-final-fix only.
This differs from the rejected eager full-set probe above.

Audit/checkpoint callbacks can reenter Native code, so the final candidate
pauses/restores transient history/audit mode around each callback. That final
DLL is blocked by Windows Application Control. Nine final Native cases skip:
they are not passing acceptance. Earlier8 Native cases/117 focused passes and
timings precede this correction and cannot certify the final candidate.
All product source changes were restored to e16451b; the candidate patch/full
source/tests are isolated in the tasklaw archive, marked DEFERRED_NOT_DEPLOYED.
No security policy was changed or bypassed. Core remains operational:71 focused
cases pass; eight actual fallback callers preserve valid roots/PVs, but two
frontiers still hit their original5sec caps. Do not claim equal-work timing from
those capped calls. Native unavailability is a real local execution limitation,
not scientific completion or a reason to stop Core research.
Recovery, candidate hash and exact scoped evidence: data/tasklaw_20261009.json.

## Legacy target queries and capture-disposition repair

A frozen8-game development pilot uses4rules (4x4/6x6,seeds7/21), paired colors,
fixed unit ordering, D2q2hard8,4096nodes/2seconds per move, cold Core. Four small
games end in1/5plies with opener wins; four6x6 games censor after3/4playedplies.
Incomplete D2 is never scored as a draw/win. Existing playability filters do
not ensure informative game length. No population-strength inference follows.

At the four exact capped roots,16new matched4096node/10second q0/q2 calls
complete;8q0 scores equal full-width references. q0 costs.031-.119seconds,
q2.663-3.034seconds with568-2588qnodes. The original2second cells stay censored.
Leaf-dependent tree size differs; this is not price quality. Profiling locates
legacy legal/attack-query work rather than leaf scoring as the main cost.

Core is_square_attacked now queries the requested compiled target directly
instead of constructing a full pseudo-attack map. Leap tables and ordered ray
paths preserve owner frames, current types, pinned pseudo-attacks and protection
of the first occupied square. The unchanged pseudo_attacks remains the oracle;
no qsupport/pruning, ordering, terminal, cancellation or budget policy changes.
On34actual positions,1808all-square/owner queries agree.32cold AB/BA q2caller
controls retain every nontiming decision/work field and query count; median
new/old wall ratio.5637 is a local43.63% reduction, not universal performance.
16final-product callers agree. Constructed8/16board ray cases also agree, with
speed ratios varying greatly; the blocked16case is only modestly faster.

Prospective fixed seeds100..107 at6x6 yield181actual root successors, no strict
unit/v3 leaf-delta ordering inversion, so the declared selection remains empty.
No replacement seeds or tie-split-as-gain interpretation.189actual root/child
positions pass13608full-map attack queries. On the first4no-immediate-win roots,
16old/product D3q0/D2q2 calls retain all nontiming fields. Short timings are
descriptive only. The deferred Native first-legal candidate remains unaccepted; these timings are Core work. The restored baseline Native module is available in the current environment.

The custody pilot also caught a real execution defect: legacy Core always added
captured base type to hand even when compiled capture_disposition was
remove_from_game. The shared immutable/search-path transition now honors that
field. Promoted-base captures for both owners, child hash/reply push-pop and
root restoration are tested under both dispositions. Legacy Native cannot
represent removal: its compiler/payload boundary explicitly rejects the rule
before loading, rather than silently applying capture-to-hand. Semantic Native
is a separate existing route; no DLL was rebuilt or security control bypassed.

Recovery, frozen caps, failures, actual callers and product source pins:
[leaf/order/search index](data/leaf_order_20261009.json) and
[archive manifest](../archive/leaf_order_20261009/index.json).

The separate exchange frontier keeps the same frozen seeds and existing no-root-
win filter:433actual transitions,22root captures and23equal-unit/nonzero-v3
capture/recapture witnesses. A declared first-two-rule selection (102/104)
then runs8fixed-order Core D2q0/q2 calls, all complete; q0 equals full-width
references. Seed102 retains unit0 versusv3+1273 through q2 with different
choices. Seed104 retains score0 despite a choice change. This repairs the
unhelpful demand that an equal-unit baseline first show a strict opening
inversion; these intended tie splits expose price sensitivity, never gains.
No seed replacement, budget extension or independent-validation claim.

Final1758active regressions pass after the shared-IR/version-report correction;
17affected report/boundary tests also pass separately. The72archive members
were extracted into an isolated project-local recovery tree and every hash
matched. Raw private-path failure logs stay local; redacted failures/partial
outputs are retained publicly, not recast as successful runs.

A separate first-root102D3 development curve completes all4matched4096node/
10second calls: unit q0/q2 score2000 (choicea2-d5), v3q0 score3507 andq2score2552
(choicef2-c5). Thus D2 scores are horizon-dependent even when the v3 choice
persists. Both independent q0 full-width references hit their unchanged4096
actual-evaluation fuse (4097attempted counter), so this curve does not claim
reference equality. No D4 or reference-cap extension follows. The adapted
producer retains a stale D2 template phrase in its docstring; code/output and
this correction identify D3. Exact sources/results are manifest supplements.

The actual frozen seed102 B-captures-X/recapture witness decomposes the D2
material contrast1273 into board670 and hand603. B has board506/hand455; X has
board1176/hand1058. This is an explicit inventory/table contrast, not an
independent task utility or strength gain. Raw quiet/capture density curves
remain in exchange-decomposition.json; the reconstructed producer records the
executed interactive calculation without claiming another independent run.

For these B/X curves, at each retained density rho, capture equals quiet times
rho/[2(1-rho)]. X/B quiet and capture ratios are identical at each positive
density (about2.31-2.38). These are two views of a common occupancy/geometry
count, not independent support for capture utility. A useful follow-up needs
conditional task information beyond recounting the same marginals; no formula
or default is changed. Arithmetic rows: opportunity-components.json supplement.

## Evaluator scale and TT ordering contract

The full-sort Core orderer represented TT-first by numeric priority-1000.
A capture value10000produces-10100and silently outranks that TT action;
default rule prices can also trigger this. TT priority is now the leading
structural sort key. The legal action set and exact nonTT relative ordering
remain unchanged, including negative capture values and an absent TT action.
This is an interface contract repair, not rescaling prices or a new search mode.

A frozen isolated256call control uses16preselected generated roots, capture
scales500/10000,2048/8192nodes, D3q0/5seconds, two balanced repeats and identical
Unit leaves/full history. All84jointly completed D3pairs agree in score and all
PVs replay. Scale500negative-control action/score/depth/nodes are identical.
At scale10000/2048, completed calls change10to12out of32, but known positive
regret stays2/30. At8192both complete32calls with0/30known positive regret;
old/structural nodes93590/91772 and seconds66.65/65.89. Other arms retain
cost regressions:10000/2048seconds48.49to49.14; a selected root's8192cost grows
about1.54to1.87seconds. Changed choices, extra depth or node savings are not
price/strength gains. Original teacher/caller data keep the old source snapshot.
Three regression failures precede the repair;34related regressions pass after it.
The complete active suite also passes all1774collected tests after the repair.
Evidence and frozen method snapshots: partial-preference-index.json under
docs/archive/search_compression_20261009. Staged and Native ordering are unchanged.

## Public player cache scope when q depths change

A same-player public q0/q2 switch reused completed main-search TT bounds whose
leaf values belonged to the old q policy. Three existing small rook fixtures
reproduce the mismatch in both directions, all cold/warm calls completing D2.
One checking-drop fixture has cold q0 score2024 and cold q2 mate999999997;
warm q0-to-q2 returns2024 and selects a different action. The reverse retains
the old mate value. A TT generation change does not invalidate those entries.

AlphaBetaPlayer now clears its existing TT when soft/hard q depth changes,
preserving reuse for unchanged q configuration. Reset also forgets that scope.
Budget-only fields are not used to erase compatible completed bounds. The
same six repaired controls match cold scores; an unchanged-q repeated call
keeps lower node cost. A separate hard-depth-only check preserves the cold
qsearch_check_hard_limit abort instead of reusing an earlier completed mate.
This is a public search contract repair, not a price or strength gain, new
search mode or evaluator-mutation protocol. The408 source-prior caller data
use cold players and retain the pinned pre-repair product base.

Raw pre/post probes and original player snapshot are recoverable through the
source-prior-diagnosis index in docs/archive/search_compression_20261009;
tests/product/test_player_q_cache.py owns the public regression.
All1778active tests pass after the repair. Initial full-suite attempts hit the
system temporary-directory permissions and one transient atomic rename in a
workflow test; its isolated recheck and final fresh-local-temp full suite pass.
No retry framework or operating-policy change follows from that transient error.

## Scalar attack owner-key cost (2026-10-09)

The prior visit audit retained lazy generation rather than building child caches.
Its next128node q2 profile keeps cold action/score/PV/depth/main/qnodes and stop
cause identical.1340scalar attacks lead project self time62.97ms;80706target
geometry calls cost18.38ms self, while cooperative checkpoints remain substantial.
Self times are disjoint but profiling amplifies Python overhead; do not treat
the inclusive legal-generation total as removable cost or weaken polling.

An owner-only source-index proposal receives all68frozen route roots/8704scalar
square-owner controls and544cold calls (q0/q2,256total nodes,no deadline,two
balanced timing rounds). It preserves signatures/work but paired median wall
ratios.98645/.98702 are modest; defer the optional-owner helper. Independently,
the same frozen experiment hoists `str(by_owner)` once per scalar attack instead
of once per eligible geometry. Signatures/work agree throughout; local paired
median ratios are.94988q0/.96022q2, and all eight rule/q cell medians are favorable.
This is local timing on short fixed-work calls, not universal speed or strength.

The product change is one query-local immutable string and its use in the
existing target traversal. Pattern/source/geometry ordering, guard checks and
every cooperative checkpoint stay in place. No cache, new dispatch index,
constructor filtering, history merging or rule restriction follows. Full1778
active tests pass in135.65seconds after this change;41target/attack/executor/cache
tests also pass. The unrelated pytest cache-write warning is retained locally.
Exact snapshots, failed preflights, paired controls and product validation are
recorded in the owner-key supplement under data/query_transfer_20261009.json.

The baseline/product direct control also preserves9344scalar query answers and
the exact cooperative callback counts, with438paired cancellation positions.
An independent non-generator empty-target proposal preserves8704queries and
544fixed-work calls but local ratios1.00359q0/1.00179q2 show no useful reduction.
Reject that iterator-form change; keep the existing public lazy geometry helper.
The relative18-member supplement preserves baseline/product source snapshots,
all three cost proposals and raw results. Fresh isolated restoration verifies
all bytes/hashes and containment. It does not reproduce machine timings; replay
uses the declared baseline or owner-key snapshot, not an unspecified newer build.

Additional actual rectangle transfer on7x5/9x10 cannon histories retains2000
scalar queries with exact callback counts and128cold fixed256node q0/q2 calls
with equal signatures/work. Local paired wall ratios.98592/.98419 are smaller
than the square cohort. Keep this measured scope, not a promised global gain.

## Frozen affine forward and ordering cost, 2026-10-09

Fixed Unit leaves,204 cold callers: Unit/proxy/hand-aware ordering each completes
D3 on5/34 q0 roots and0/34 q2 roots; D2 on34/34 q0 and5/34 q2. No completion
increment. Some cells overlap independent qualification; timings are descriptive,
not causal speed measurements. Retain every cap and adverse result; no adoption.

Exact algebraic folding retains original current/base/owner-hand/promoted/side/
bias terms, unlike the board-only proxy. On3128 children maximum full error is
3.56e-15, projected error5.33e-15.160 predeclared cold scoring-discard callers
retain Unit leaves/order and identical action/score/PV/nodes/depth/stop/generation
signatures in all arms. No CPU experiment overlaps these calls. Median matched
root wall ratios q0/q2: original encoder1.0383/1.0338, folded0.9980/0.9953,
double-encoder projection1.0931/1.0681, folded projection1.0059/1.0035.
Only representation overhead is measured: extracted scores are discarded.
Setup builds encoder first and ledger second with a warm opportunity cache;
no comparative constructor advantage is claimed. Exact numeric projection does
not prove a rule transform is valid. No new live leaf/default/strength claim.
Recovery and full cost records: frozen-ledger-transfer-index.json under
../archive/search_compression_20261009; data/qfrontier_20261009.json.

## Actual affine leaves and finite-budget coverage, 2026-10-10

This is an offline real-leaf adapter comparison, distinct from scoring-discard
and ordering-only controls. Original34full-history2118/2119 roots, fixed Unit
ordering and cold public Core players share D4/8192nodes/5sec/q0-or-q2/hard8.
Full affine values use declared mechanical normalization, integer rounding and
mate-band clipping; all original terms remain. No fit/default/strength claim.

All three q0arms complete D3 on25/34 and D4 on3/34, with nine stopped atD2.
q2completes D2 on23full/23v3/24Unit roots, D3 on5/5/6; all102q2calls time out.
Full q0totals:193948main nodes,176957evaluations,1.14sec scoring versus95.40sec
legal generation; full q2:21207main/48546qnodes,0.29sec scoring/91.28sec legal
generation. These measured categories are not a disjoint total-work accounting
or evidence that semantic generation/checkpoint time may be removed. Zero hard
check-chain and qnode-budget aborts distinguish time exhaustion from those caps.

Another204scale/role calls preserve the same completion pattern except Unit's
separately recorded original extra q2D3root. Positive0.25/4scales do not remove
the frozen full arm's finite errors. Projection reduces one q0and one q2error,
without generalized utility or completion gain. Actual selected-action reply
replay confirms mate holes in partially completed q2searches; terminal/legality
authority remains intact. Intermediate q1uses the same in-check evasions/hard
abort rules, not capture-only filtering or a cheaper legality substitute.
All102q1calls time out; D3completion full/Unit/v3 is9/12/10, improved versus
q2's5/6/5 but with remaining finite errors4/3/3. Keep both coverage and adverse
results, no qdefault adoption. Selected D3action checks separate a persisting
200unit gap from another shallow loss that becomes a tie, without whole fronts.

Some original callers overlap the small capability audit; scale and q1batches
run separately from other CPU experiments. Accordingly, elapsed times remain
local descriptive resource records, not causal comparative speed promises.
TASK_PREDICTION_DIAGNOSTIC.md owns target losses, replay and exposure boundaries;
capability-transfer-20261010-index.json routes exact producers/results/dependencies.

## Interrupted root-scan fallback, 2026-10-10

The cheap root scan previously discarded completed child evaluations when its
node/deadline/cancellation check interrupted the scan. The product now retains
the best completed legal child; an evaluator that aborts before returning a
score cannot replace it. Legacy and semantic paths share this behavior. No
additional nodes/evaluations, cancellation relaxation or tactical extension is
introduced. An interrupted scan still returns score0, empty PV and depth0;
it is a fallback, not a completed-search certificate.

Eight interruption regressions fail against pinned9734226 and pass with the
change. The candidate passes1784 active tests; the subsequently added two
evaluator-internal interruption cases pass with all22 final upgrade tests.
An initial full-test run failed at Windows temporary-directory setup; a fresh
project-local basetemp passes without weakening product assertions.

Matched exposed64/512node controls retain identical work. At64 eight choices
change and two exposed v3 immediate-loss holes disappear; at512 choices stay
unchanged. Four prospectively declared2146-2149 rules supply96 cold calls at
opening0/4/8, Unit/v3 and64/128nodes: six choices change, immediate-loss pairs
stay4to4. Actual24 fixed64node games then retain696plies and five changed
terminal categories. Same-parent selected-reply checks find one introduced
and one avoided immediate-loss hole. Adoption is based on preserving completed
computation under the existing fast-evaluation criterion, with these adverse
outcomes retained; no safety, playing-strength or price improvement is claimed.

Recovery: ../archive/search_compression_20261009/root-scan-20261010-index.json.
FINITE_SEARCH_COMPRESSION.md owns the separate guard/hand-price interpretation.
