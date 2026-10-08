# Unfamiliar-rule search: interface, controls and cost

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
ratios are about0.75–0.83; no universal acceleration follows.

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
root, median ratio1.194846 (range1.038410–1.219925). Public binding identities and
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
110 yielded Core transitions take.051seconds. This local check confirms the
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
