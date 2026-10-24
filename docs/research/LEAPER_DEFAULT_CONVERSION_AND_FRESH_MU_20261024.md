# Default conversion, first-action interventions and prospective fresh inputs

PRIMARY_SANDBOX; research remains OPEN. This is a finite forward study, not a
new evaluator default, learned price, minimax-WDL result or independent-rule
holdout. DEV_AUX's solver and learners remain its independent work.

## What changed and what is being tested

The preceding relative-price/contact report retained twelve draws even though
prices changed three full trajectories. Six cold calls had already shown that
complete DEFAULT changes the first capture. Chat1792799049 recommended one real
complete game, followed only on a payoff difference by two first-action swaps.
That recommendation was read from its complete thread, saved exactly before
assessment, and adopted. Its correction of the earlier cold/service objection
was also consumed. No real-time contact or extra worker was used.

The new local game uses the original complete contact0 record:
K0=20,A0=12,B0=15,K1=24,A1=6,B1=8 on5x5; King8/FerzA/WazirB,
remove/H64/repeat4/stalemateDRAW. Complete rule fingerprint:
`da92b6a1c814795b455875a48540227f34c94807932a559d309c67ccc6a520e5`.
Both search actors use N8192, requestedD64,3s/query,Q0/check-onlyOFF/hard8,
Native legality ONLY, availability/checkFALSE, fresh game players/TT retained
within the game, diskOFF. Actual completed depths, counters and clocks are
retained rather than treated as equal computation.

DEFAULT has board A891/B1109/K0 and complete hand A802/B998/K0. Its dynamics
and ordering are active. UNIT uses board1000/hand900 for every nonanchor,
anchor0, dynamicsOFF. This is the actual constructor, not an assumed geometry-
only replacement. The original natural UNIT game is reused exactly once as a
reference, not paid again under a new seed.

## The first capture does not explain the local payoff difference

| Controller after its normal root query | Execute first capture A12xA6 | Execute first capture A12xB8 |
|---|---:|---:|
| UNIT | DRAW,H64; old natural reference | DRAW,H64; new intervention |
| DEFAULT | WIN,mate27; new intervention | WIN,mate27; new natural game |

Each intervention completes its own normal root query, preserves that controller's
TT, changes only the submitted first action, then returns to normal control.
The original proposed action and PV remain separate from `executed_action`.
The reader rejects unregistered substitutions. All four complete histories and
PV paths pass literal Core replay. This identifies the local complete-controller
factor, including its root-query cache state and later search; it does not isolate
one evaluation term or establish a forced win.

## Fixed ordering separates material from the dynamic bundle

All four cells below use UNIT ordering, including capture-order values. Three
new games supplement the same old natural UNIT reference.

| Leaf material | Dynamic bundle | Outcome |
|---|---|---|
| UNIT | OFF | DRAW,H64; reused |
| DEFAULT | OFF | DRAW,H64 |
| UNIT | ON | WIN,mate27 |
| DEFAULT | ON | WIN,mate27 |

The two dynamic fixed-order games and natural DEFAULT have identical complete
records here. Static DEFAULT and UNIT-with-firstB also have identical complete
records. Thus default material prices are unnecessary for this particular gain;
the finite payoff interaction is zero in this local2x2. This does not prove
universal price irrelevance, individual-term usefulness or interaction absence
on other inputs. The quiet-home dynamic negative controls were not substituted
for these actual contact cells.

Across the seven local games, including the old UNIT reference, the reader checks
300 recorded Player queries/1802PV plies. Exactly236 of those game queries are
NEW. On251 nonterminal selected-PV leaves the independently recalculated formula
is material +2*pseudo-attack-union difference +5*empty pseudo-safe anchor-step
escape difference +50*check difference. These are selected leaves, not every
searched leaf or a decomposition of every returned TT score. Promotion terms
are inactive in this expressly no-promotion prototype.

The first actual divergence after either shared capture/reply prefix is atply2.
Twenty-four NEW coldTT calls cover both such attacker histories and a laterply15
history, at completedD3/D6 with N65536/15s. After captureB, the coldD6 actions all
agree even though earlier warm/resource-limited paths diverged. After captureA,
dynamic/static choices remain different at both common depths. The third history
is the DEFENDER's turn; its alternative dynamic choices are counterfactual defense
policies, not evidence about the actual UNIT defender or attacker conversion.
No deeper sweep or full-WDL claim follows.

## Prospective fresh-safe mu

To test whether the contact example transfers, twelve layouts were fixed before
queries using seed202610240951. Six labelled occupied squares are drawn uniformly;
only initial checked kings, terminal/no-legal-move starts and exact duplicates
are rejected. The21 attempts accepted12 and rejected9. All12 accepted layouts
remain, without WDL, price, PV or payoff filtering. This is one finite chosen
rule family, not an independent-rule sample or population confidence interval.

The new complete RuleSet has fingerprint
`5a7347963497efade9ed90d4fa9c4d8a670c6d95b6219b1ac8bcb7c4c9c11596`.
Movement/terminal semantics match the contact family; initial setup law and full
identity differ. Each layout has one UNIT and one natural DEFAULT game against
fixed UNIT under the same limits. Root/policy order is frozen, pairs consecutive,
TT fresh/game and retained within. No actor RNG is consumed by these deterministic
players; the sampler seed is not an independent game replication.

All24 games finish with0missing: DEFAULT1WIN/11DRAW versus UNIT12DRAW.
The one positive pair is root0 (DEFAULTmate25 versus UNITrepeat64); the other11
paired payoff differences are0. The finite mean difference is1/12; both completion
bounds equal1/12. This describes the declared12contexts and fixed opponent,
not a population confidence interval or a price-only effect.

| Controller | WIN | DRAW | Played plies / queries | Main nodes | Sum of game seconds |
|---|---:|---:|---:|---:|---:|
| UNIT |0|12|647|3,942,964|1,755.871|
| DEFAULT |1|11|729|4,161,303|1,952.128|

UNIT has7clock/5repeat draws. DEFAULT has10clock/1repeat draw and1mate.
DEFAULT spends about11.18% more summed game time and5.54% more main nodes in
this finite comparison. No timing advantage or equal actual-work claim follows.
All8,367 NEW fresh-game PV plies pass Core replay. Batch time is3709.736s;
summed game clocks, actual search clocks and effective Agent work remain distinct.
Stop expanding the same six-actor price/seed/budget panel. Preserve the positive
whole-configuration candidate and the negative local material-only result,
without selecting a new evaluator default or forbidding bounded learning.

The forecast202s/game x24 with15% reserve plus900s preparation/qualification/
analysis gives6475.2s, below the user120minute single-run assessment threshold.
It is a forecast, not a measured upper bound. The cooperative panel cap4200s and
per-game cap240s remain unchanged; missing/censored slots stay UNKNOWN and are
included in finite paired bounds, never silently filled. No current result
extends an old cap or refills a closed panel.

## Smaller next input, already begun without search or training

Eight complete fresh-safe layouts are prepared for King8+A(mask3) versus
King8+B(mask10), with just one ordinary actor per side on5x5, remove/H64/repeat4.
This metadata-selected case reduces six actors to four; it is not an unseen-rule
holdout or a requirement that all training rules have any special mating capacity.
Seed202610241015 accepted8 of17 attempts;9 checked-king starts were rejected,
with no truth/outcome selection. Full fingerprint:
`173bd8ad8bc61414547559bea1bd9196f9d03f8fb5f3e0f35673f14c5108df77`.
DEFAULT board prices are A949/B1051; UNIT initial material is0.

The material expression is wA-wB, so zero value at unit weights does not remove
the free wB coefficient -1. This is algebra, not an executed learner Jacobian.
All576 literal CoreD1/D2 edges over all8 roots are retained. Root argmax sets
are invariant at B500/1000/2000 with fixed A1000. In this one-A0/one-B1 removal
scope, nonterminal material leaves belong to {wA-wB,wA,-wB,0}. Their positive,
mate-dominated weak order changes only at wA=wB; the three cells cover those
orders, and finite max/min preserves them. The observed initial D1/D2 support
invariance therefore extends within that scoped positive cone, not to deeper
Player choices, all reachable histories or arbitrary signed weights.

No starts are discarded and no learner is blocked by that negative diagnostic.
Player/training/full-WDL queries on this next input remain0. The next own step
is a freshly registered complete-controller whole-game cost case, with explicit
reuse if it later becomes a fitness slot, before any new panel. AUX can consume
published complete inputs within its own independent lane; PRIMARY does not
execute its learner or prescribe its truth queue.

## Provenance, failures and limits

The exact technical source/input/registration/record/PV originals are in the
compact packet. Its reader never executes source capsules and makes no new
Player/training calls. Shared Core replay is not an independent engine or an
independent search rerun.

The two initial sampler preparations failed before any Player query because the
compiler rejects checked kings/no-legal-move starts before post-compile checks.
Only those already declared admission codes are now counted as rejections;
unrelated validation errors still raise and have a regression. No expected
value or selected outcome was changed. A global pytest temporary-directory
WinError5 prevented fixture setup; the supported fresh ignored project basetemp
resolved it without changing assertions or machine permissions.

The executed row field `profile` binds generated DEFAULT metadata, even for UNIT;
it is not UNIT's actual leaf profile. The separate controller-field interpretation
was saved before the first prospective game closed. Actual constructors, complete
leaf/dynamic/order profiles and labels determine execution. Future metadata names
were clarified only after every producer closed; existing originals are unchanged.


The closed `slot.policy` field also retained a hardcoded DEFAULT literal for
UNIT and the three fixed-order controls. The actual constructor selection,
registration, `row.controller` and every query controller agree; the label error
could nevertheless corrupt naive aggregation. Correct-contract zero-query tests
first failed on that old writer. Future output now uses the registered slot
controller and separate generated/actual leaf/order metadata. The archive reader
accepts the16 historical mislabels ONLY for the two exact faulty source hashes
with all actual labels matching, reports each erratum, and rejects unknown-source
or corrupted-query mismatches. No scientific outcome or original was rewritten.

A later relevant regression hit a separate transient `common.write_json`
replacement denial in its project-local fixture. Target and closed temporary
were both complete JSON/non-readonly; originals were preserved, and the SAME
path later replaced successfully without changing permissions. The precise OS
holder remains unknown. The workflow writer now retries only that same complete
temporary for Windows5/32/33, at most3 attempts with10/20ms backoff. Persistent
errors still raise and leave the old state/stops authoritative. A controlled
transient test was RED before this fix, then all atomic/read-before-commit and
permanent-stop-preservation regressions passed. No machine security or ACL changed.
This post-experiment workflow maintenance adds no effective research time.

Natural source bytes were captured before extension. Intervention source was
not separately snapshotted before component extension: exact reverse construction
with WindowsCRLF matches BOTH pre-query frozen source hashes. This reconstruction
and the initially rejected LF mismatch are disclosed, not called an independent
old snapshot. Component/fresh source bytes were captured and hash-verified while
stable; no active source was edited. Plain source presentation/new writer metadata
and executed capsule hashes are kept distinct.

AUX703f0fc's published report was actually read at its fixed public revision.
Its full-history DRAW and nominal Uniform/oracle results concern the OLD
fingerprint1988f7df..., not this six-actor rule. They are attributed published
results, not independently rerun labels transplanted into new games. Its advice
against nonzero-value/positive-payoff/forced-WDL training gates is adopted.
Claude's universal WIN/rank gate and exclusion of fixed-opponent utility are not.
Minimax DRAW and a win against a particular imperfect policy are different targets.

The complete generated domain still includes promotion, drops, auxiliary state
and relevant history. This explicitly scoped prototype does not redefine that
target. No Elo, human-heldout fitting, sampler/default activation, package runtime,
AUX checkout/state or schedule change is made.

## Evidence and validation

The87-document packet is747,013bytes, SHA256
`fd42b8775902f79bdb44ca6a2dc21d2d42a3bb2a03df99391de1cea405395f9d`.
Its data-only public reader passes in17.863s:1,676 retained game queries and10,169
PV plies (including64 OLD reference queries),24 NEW cold calls/108PV plies,
all complete histories,251 selected-leaf decompositions and576 next-input edges.
New experimental Player queries total1,636; regression fixtures are separate.
No source capsule is executed and no Player query is issued by that reader.

Local pre-publication checks:45 relevant Leaper/atomic tests and45 session tests
pass. The prescribed publisher repeats these90 tests as its required gate;
full remote SHA and anonymous Git-byte verification are recorded at delivery.
Full sources, controls, limits, costs, missing bounds and the16 label errata are
in [the packet guide](data/leaper_default_conversion_20261024/README.md),
[summary](data/leaper_default_conversion_20261024/summary.json) and
[qualification](data/leaper_default_conversion_20261024/qualification.json).
