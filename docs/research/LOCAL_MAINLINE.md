# Current local research mainline

AGENTS.md and user directions govern. Science is OPEN. This file contains current
questions and decision boundaries; detailed history is routed below, not a backlog.
Milestones, tests, consultation and publication are research checkpoints.

## Current priority — 2026-10-10 user-requested handoff review

Latest direction review (2026-10-10): first diagnose the actual remote UI
one-second Chess path against a clearly configured minimal alpha-beta control.
Pin the UI revision, actual backend/material, requested/effective budget,
completed depth, fallback and final committed action. A small predeclared pair
of short games can locate an explainable direct loss; fixed-state replay then
separates insufficient completion from evaluation/selection/commit defects.
There is no supplied user game record yet; a reported UI loss is not a reproduced
bug. Diagnose the frozen UI version without modifying its branch. The existing
indexed Core/specialized bridge remains the subsequent attribution tool.

Retain generality while removing measured shortcomings. Specialized engines
are diagnostic references, without a speed/strength parity threshold. Prioritize
small mechanical board/basic-move compilation improvements, retain dynamic
guards, promotion, drops, auxiliary state and history, and extend mechanism
coverage from evidence. Representation/search joint optimization is a research
question, not a claim of a universally best pairing or a new search-family task.
Cold compilation, cache hits, search and return validation have separate costs.
Basis: complete Dot reply to the user's new direction inquiry; private-user
discussion is advisor-relayed context, not independently verified observations
or new permissions. Agent adopted this bounded diagnostic within the current
user request. No operational-rule change follows.

Search diagnosis comes first; rule-derived/statistically averaged prices and
small learned evaluators remain subsequent goals, not equally scheduled tracks.
Compare (1) generated-rule backend with the current supported generic search,
(2) minimal alpha-beta with Chess/Shogi specialized rule libraries, and (3)
mature engines. Add a thin same-minimal-AB/generic-backend bridge to separate
backend costs from algorithm effects. Minimal AB fixes move order, terminal and
material evaluation; no implicit TT/PVS/qsearch/reductions. Retain legality,
promotion, drops, auxiliary state and relevant history. Familiar games are
necessary special cases, not substitutes for generated-rule transfer.

Report fixed primitive cost, actual search work/completion, and equal-time
decision utility separately. Record actual Core/Native/fallback, node definitions,
initialization versus warm execution, instrumentation overhead, root coverage,
exit cause and proven terminal versus heuristic result. Mature engines whose
evaluation cannot be aligned are overall references, not material-only controls
or isolated evidence about search. First inventory runnable entries and aligned
small Chess/Shogi positions; fix material as a control rather than fit it.

Infrastructure repair is research work when a demonstrated semantic, execution,
scheduling or comparability gap blocks judgment. State the gap and verify cost
and decision/completion effects; avoid an unbounded redesign. Older anti-engineering
or narrow-track guidance must not keep an evidenced bottleneck in place.

Later price work may estimate fixed relative vectors from dynamic contributions
under an explicit meaningful play distribution. Context dependence does not by
itself refute averaging. Separate sampling error, conditional variation and
distribution shift; examine multiple extreme starting prices without human-table
fitting, exposed-label reuse or treating forced normalization as convergence.
Generic methods may yield different vectors for different rules. Small networks
are eligible candidates; search evidence determines the next investment.

Basis: current user instruction to absorb dot's complete three-part handoff.
Dot relayed direction and proposed the bridge/metrics; it did not independently
run the benchmarks or inspect every manual line. No change to single writer,
duration, heartbeat, stops, publication or the >1hour-run necessity consultation.

## Actual UI completion and mechanical cost checkpoint —2026-10-10

The pinned remote UI99c97 service/controller path yields30 returned=committed
moves in two predeclared short games;24D1 completions include two direct queen
losses. Full-history finiteD2 exposes better choices. First ordinary q is
reserved as0 beforeD1; deeper timeouts can leave that approximate greedy result.
Diagnostic first-q1 improves8/worsens1/ties21 on30cold parents, but short50/100ms
controls lose all completed iterations where baseline completesD1. Retain it
as diagnostic only; no default/q/evaluation/UI change. Four q4D2 caps stay UNKNOWN.

Compiled-owned fixed event-trigger dispatch preserves dynamic references,
owner filters, explicit aux order and missing-metadata fallback. Engine-owned
plans regressed and remain archived. Current fixedD2 local cost falls11-13%;
1424child/45legal-frontier controls and1897active regressions pass. On30cold
one-second parents, indexOFF/ON completesD1/2/3=21/7/2->18/10/2 with one finite
material-loss improvement; both queen failures persist. This is scoped useful
execution savings, not a first-reserve fix or strength estimate. UI stays frozen.
Next compare one budget-aware tactical reserve against a completed cheap result,
or use the indexed thin Core/specialized bridge to attribute remaining work.
Sources/failures/limits: UI_PRODUCT_DIAGNOSTIC.md; data/ui_product_20261010.json.

## Search attribution checkpoint —2026-10-10

Thin identical lexical alpha-beta now drives Core, python-chess and cshogi;
Native legality and cold supported search are separate controls. Eight exposed
roots yielded64old D2 and64old D6 calls, followed by240repaired-rule common-time
choices. Do not equate their node definitions or convert them to strength.
D6 exposed cshogi search repetition ending before four occurrences; strict exact
history in the adapter restores the deeper promotion trace. Independently,
Standard Shogi no-legal-move adjudication is corrected from draw to loss under
CSA Article27; old rule manifests/results remain recoverable, UI stays frozen.

Every common-time choice is legal; finite D4 material regret is lower for the
specialized backend on ep/middle/drop controls, with many tied controls and
retained contrary/deeper-reference rows. Native only removes part of the backend
cost. Profile/primitive evidence distinguishes attack/generation, trial transition,
state/history and provider conversion from leaf evaluation. Callable-object
provider strict/metric ownership was repaired without weakening cancellation.
Next choose one measured generic execution bottleneck and test finite-work plus
common-time impact, including generated-rule transfer; no automatic algorithm
replacement, price fitting, bigger game cohort or training from these controls.
Evidence and limits: SEARCH_BACKEND_ATTRIBUTION.md;
data/search_attribution_20261010.json. Older Native App-Control failures remain
historical; current constructor/call observations certify only this measured build.

## Native conversion and terminal checkpoint — 2026-10-10

Bounded immutable public-action reuse is installed; position bindings and legality
checks still rebuild.16 fixed-work calls improve local wall by about2.6–8.4%;
192 same-time choices remain unchanged, so no decision/strength gain.803 generated
children and176 q0/q2 calls preserve tested semantics. Sparse identity, typed
board-token memo and child Native-check substitution stay archived prototypes.

The separate full Native pilot exposes a no-move-loss gap: current Standard
Shogi terminal policy never reaches C. Public full-Native terminal/search now
reject it explicitly; Native legality plus Core remains usable. Affected roots
cannot support correct-search cost attribution. Next prioritize versioned payload/
kernel terminal repair, including fixed/probe winner scoring, then re-establish
affected correctness/cost controls. Dot supports this order without an independent
rerun. Establish approved build execution first; otherwise retain this boundary
and profile supported rules. UI stays frozen. Evidence/source boundaries:
SEARCH_BACKEND_ATTRIBUTION.md; data/native_conversion_20261010.json.
Post-publication controls identify unused zero-weight dynamic-feature work in
full Native:12 reversed512node Chess calls preserve action/score/PV/work with
absent features but take6–18times less wall than explicit zero tuples. Default
already uses absence; future material-only attribution must use that control.
Keep the old zero-profile pilot and semantic defect distinct. This scoped result
does not establish strength or a universal factor. No timing/workflow policy change.

## Semantic dispatch and scheduling checkpoint — 2026-10-10

The simplest Core semantic checkpoint now inlines budget dispatch, retaining
every poll, live deadline and node/cancel/time precedence.40 fixed-work q2
calls retain exact decisions/PVs/non-time counters, with local mean reductions
4.49–12.60%;96 common-time calls mostly keep completion/choices, with EPq0
at4seconds reachingD4 versusD3 twice.24 real external cancellations unwind;
observed latency is descriptive, not a responsiveness guarantee or strength gain.

Terminal-prefix reuse regresses5–11% and is rejected. Compile-owned compatibility
atlas preserves3974 states/9928 pseudoattack queries but saves only1.27–1.97%,
without timed completion gain; defer integration. Post-repair direct geometry
bodies are only6.38%/2.21% of two instrumented totals, not all attack cost.
Native training trace costs3.29–4.09x and lacks re-search phase labels; keep OFF.
Same-backend fixedD3 work comparisons motivate scheduling attribution but cannot
isolate PV/iteration causes: counts, order/ties and mate scales differ. Final C
deployment remains blocked/restored; no retry, default change or UI propagation.
Dot's complete fresh-thread review is adopted without an independent rerun or
workflow change. Initial overlapping timing sets are retained as ineligible;
formal curves are serial. Evidence: SEARCH_BACKEND_ATTRIBUTION.md and
data/terminal_frontier_20261010.json. Next quantify one supported scheduling or
attack-dispatch mechanism by useful completion and actual cost, not hotspot alone.

## Cooperative budget and window attribution — 2026-10-10

Internal live semantic polling matters: 72 serial resource controls remove some
of the thin diagnostic's apparent completion advantage. Preparation and caller
PV replay remain separately measured, with observed cancellation rather than
a response guarantee. Native results now expose optional kernel generation and
ordinary-transition counts; missing observations are None, not zero.

The installed TT0/rootOFF kernel does not execute canonical selected-PV replay.
An exact source model reproduces its D1-D3 counts, values and packed routes;
changing internal full-window dispatch cuts work while keeping root children
full-window. Cold TT64 replay subtrees are only about 1-7% of measured entries.
Completed q0 replay-entry accounting fails on interrupted calls, including a
negative residual. Warm TT cutoffs require separate attribution.

Core controls with matched live polling retain fixed-D3 window savings but no
1/4second completion gain. Existing configured Core takes about0.7seconds,
versus6-7seconds for the plain alternative on the two generated D3 roots:
retain current search, not automatic replacement. Synthetic equal-bound PV ties
can return suboptimal interior replies despite a correct root/leaf value;
strict interior improvement repairs these scoped complete noTT controls, not
all TT/interruption contracts. Independent selected-response audits are recorded.

Owner-only attack enumeration and Core-runtime caller validation stay deferred:
modest measured gains, no broad deployment evidence. Captured legal-frontier
labels are an explicit diagnostic option; independent replay stays default and
product validation is unchanged.16 product-only TT/order factorial calls preserve
D3 scores; both OFF still take about0.9-1.0seconds on these roots. The large gap
therefore remains after removing those features. Next isolate root shared-window
and contender-verification scheduling on the same finite generated roots.
Dot's complete fresh-thread review guided the matched-budget check; it did not
rerun experiments. No workflow/default/UI/C deployment change follows.
SEARCH_BACKEND_ATTRIBUTION.md and data/cooperative_budget_20261010.json own
exact sources, negative controls, failures and measured cancellation costs.

## Retained lines and prior evidence

Latest search-first continuation: narrowed-root bound equality is reproduced by
an explicit Python diagnostic; verifying a contender in the original shared
budget restores exact canonical selection on the scoped controls. Three isolated
C builds executed successfully; root-only repair exposed warm-TT horizon mixing,
and exact-depth eligibility removed the72-cell discrepancy. The final
capability-tagged product build was blocked by Windows Application Control.
Active product source and installedv4 were restored; public ON remains rejected,
full-rootOFF remains default. Executed variants are not final deployment evidence;
terminal-v5 remains separately unexecuted. UI stays frozen.

Current warm64 full-root completed depth is cache/path dependent, not uniform
finite-horizon VD:48 deep-to-shallow calls have6 D2 disagreements; their
2-move PV leaf values also disagree with the report, including a nonterminal
mate-in3 estimate. TT0 controls match. Returned PVs are illustrative, not finite
value/mate witnesses; this alone does not prove the chosen move strategically bad. Keep same-horizon/noTT controls for attribution, distinguish selective
mature-engine references, and retain rule/evaluator/history/q/mate/bound conditions.
Dot's complete review supports this distinction without independent execution.
No workflow, duration, budget or publication rule changes follow.

Python exact-candidate scheduling completes deeper on4of6 fixed4096 controls,
with scoped1second improvements and jitter. No new utility oracle or strength
claim: existing finiteD4 labels cover only16of48 choices. Immutable syntax reuse
helps fixed cost but adds no completion in the crossed1second cells. Existing
transient legality avoids unused trial-history work while retaining authoritative
terminal and real full-history pushes:3974 D2 Core/Native state audits pass,
fixed signatures agree, generated2001 gainsD4 versusD3 in both timed pairs.
A128-entry exact-parent successor cache is rejected at its tested capacity:
small transition savings do not repay overhead. Keep both as isolated diagnostics.

Corrected identical lexical scheduling across Core/Native/specialized backends
retains26 identical fixed signatures and distinct26 resource-capped completions.
All52 choices match old finiteD4 labels: EP regret100-to0 and Shogi drop400-to0
are scoped useful differences, not strength. Specialized Shogi hits100000entries
before1second. Next choose remaining terminal/frontier cost or approved C
deployment verification by measurable decision benefit. Do not reconstruct
terminal authority from mere legal availability, increase frozen teacher budgets,
retune failed caches or automatically install a kernel. SEARCH_BACKEND_ATTRIBUTION.md
and data/root_bound_20261010.json own exact controls, failures and source closure.

1. Rule-only generic piece-value generation: cross-game ordering/ratios and bias.
   Games diagnose price holes; no human-price fitting, Elo or positional patches.
2. Efficient, stable search through the generic interface on unfamiliar rules:
   familiar-piece mixtures, recombined mechanics and generated playable rules.
   Learning-based evaluation candidates may receive low-cost feasibility review;
   no large training or extra worker follows from that choice.

Subsequent evaluation priority after search attribution: compare rule-generated constants, learned/frozen constants
and small state-interaction evaluators by supported state domain, useful signal
and end-to-end cost. EVALUATION_ROUTES.md records the first evidence-based choice.
Static tables remain a candidate/baseline, not a mandatory predecessor. Generic
targets the complete generated rule domain; scoped approximations must declare
missing promotion/drop/auxiliary/history semantics rather than shrink the target.
Existing conditional tasks distinguish utility from mobility; further template
precision is optional only when opposite outcomes change a concrete decision.
Exactness, full explanation and a new task family are not development gates.
Rule-specific coefficients cannot be treated as shared merely by type label.
Keep raw quiet/capture components, normalization and approximation scope separate.
Current search question: which supported semantic mechanism still leaks a
square-only evaluation or execution assumption through the public interface?
Supplied evaluators now bypass unused default profiles; both orderers use shape.
Rectangular Core searches pass bounded cannon, temporal and compound controls.
Opt-in semantic v3 profiles now use stripped type metadata and shape area;
16fixed-evaluator rectangle calls pass. Anchor/promotion dynamics stay disabled.
Native and default price generation remain separate unsupported boundaries.
Lexical q classification now shares recursion pushes without changing ordering;
first-legal Native candidate is isolated/deferred after final DLL App Control
block; product remains e16451b/Core fallback. No security bypass. Use Core for
independent price/task questions; do not claim pre-final timings as deployment.

## Current evidence and decisions

- Interrupted root scans now retain their best completed child without more
  work or weakened cancellation. This is a fallback-contract repair, not a
  tactical gain:24fixed64node games include one introduced/one avoided local
  immediate-loss hole. Guard/effect reencoding preserves1124one-step Position
  pairs; the cheap compiled predicate probe is retained as a scoped input
  premise, not a learned utility. Two new hand-law rules/10games/275plies plus
  full selected-reply audits do not support adopting hand=board. At a common
  loss parent Unit completesD2 and avoids loss while both v3 arms stopD1;
  a five-child top-tie audit shows v3 uniquely favors the losing move.
  Existing hanging counts miss silent mating drops; q1 keeps all15old choices
  and losses, with six D2-to-D1 regressions. Root TT-priority omission has no
  opening choice gain and mixed later completion; retain the installed orderer.
  A completion-aware full-state research prototype avoids some exposed holes,
  but32one-second games including a fixed repeat do not establish an economical
  advantage. Three repeated trajectories change and one draw becomes mate.
  Existing Core successor handles retain24fixed-work signatures and503complete
  child states; they remove substantial redundant semantic transitions.48paired
  inverse-bool signatures also preserve full history on the scoped controls.
  Fresh2168-2171 common-time handle games give5frontier wins/1true repetition/
  10ongoing64, with wins confined to2168/2169 and no default adoption.232rectangle
  child pairs/six fixed-work signatures retain this interface's scoped transfer.
  Terminal-preserving32game ON/OFF ablation reverses win counts with1/2sec;
  fixed-work choices agree at the sole timed opening difference. Fresh16game
  coldD2 route comparison gives Core5/frontier3 wins,3rule draws/5ongoing,
  with frontier caller cost about twice Core on unlike trajectories. Defer the
  unmodified frontier default. Three nonterminal winning resolutions remain
  absent from CoreD2/D3-completed-only-D2; fixed-work completion finds two cheaply.
  Fresh2180-2183 fixed small prepass+residual Core gives16games645plies:
  combined5/Core4 wins,3true draws/4ongoing64, only11distinct trajectories.
  Its8resolutions are5direct winning terminals and3nonterminal current-side
  losses, with zero nonterminal winning resolution;4saved identical-history
  Core roots already have the same mate-range sign. No default adoption.
  Separate source-derived maxD6/q0 sensitivity on2184-2187 finishes16games/
  753plies:5combined/4Core wins,7ongoing64,10distinct paths; its8resolutions
  again contain no nonterminal winning result,6saved Core matches already
  have the same mate sign. All745Core calls stop on time, actualD1-D4 only.
  Common-parent diagnostics keep both directions/opportunity costs visible;
  different cohorts/unlike paths do not establish depth causality or strength.
  All47predeclaredD2common-parent actions/exposures agree, oneD2-to-D1
  residual retreat, caller50.330/52.461sec; defer fixed allocation adoption.
  All56D6common-parent actions/exposures also agree;54unknown deferrals
  cost109.542/110.003sec, saving comes from two already-known mate shortcuts.
  Both whole-cohort reply audits retain all adverse rows (D2 9/7unique;
  D6 9/6unique), not avoidable-error rates. All four solved paired shortcuts
  keep Core actions/mate signs with shipped root scanningON; the two instant
  wins already early-return. Next response-support placement/reuse, not
  per-leaf rescanning/cap growth.
  Full-root prepass coverage still leaves tied reply-unexpanded branches in
  214/315unknown calls; this motivates a new premise, not automatic cap growth.
  No fit or extra budget from exposed labels. Checking-drop counts alias safe/unsafe
  children; conditional response utility remains a scoped alternative.
  COMPLETION_SEARCH_FEASIBILITY.md owns that scoped alternative and cost limits.
  FINITE_SEARCH_COMPRESSION.md owns
  price/input evidence; UNFAMILIAR_RULE_SEARCH.md owns product behavior.

- Prospective2118/2119 capability transfer has32complete fronts and no common-
  action label conflict; the old61conflicts remain scoped. An untrained264axis
  probe separates those old aliases but pools distinct drop zones. No expanded
  model or refit follows.510actual leaf/scale/q calls retain caps/adverse results;
  q1improves completion without removing errors. Selected D3targets keep one
  gap and turn another into a tie.12fresh terminal-signal games yield3duplicate
  one-ply mates,4real repetition draws,5unknown external cuts with policy-
  dependent censoring. A broader prospective24game pilot yields15terminals;
  matched higher resource changes9event classes and yields13terminals. Two
  further prospective16game four-event studies retain ongoing as its own class.
  All three frozen small affine fits lose to constant priors on their report
  rules; unsigned context removes a balanced-inventory alias but worsens transfer.
  No model/default adopted. Fixed512node static-v3 crosses now retain449old
  and587prospective plies; v3 has4wins/3losses/1ongoing against Unit in the
  fresh owner-imbalanced cohort, not a strength estimate. Full selected-child
  reply audits separate immediate loss from zero immediate witnesses. Dormant
  declarations rescale prices but preserve837child orders and51call choices.
  Next distinguish local forced exposure, price/hand attribution and conditional
  rule-state support, rather than automatic feature/fit expansion.
  FINITE_SEARCH_COMPRESSION.md owns the
  new finite-policy evidence/recovery. TASK_PREDICTION_DIAGNOSTIC.md
  owns targets/recovery; EVALUATION_ROUTES.md owns the return-signal decision.

- Frozen full predictor versus board proxy: original hand terms restore all34
  choices; fixed Unit-D2 all-tie optimal29 versus18. Conditional role projection
  improves55 to58 of68 paired targets but adds no gain on34 further roots.
  Persistent auxiliary rights expose61 equal-input child labels with changed
  continuation values, including an independently replayed mating drop. Next
  retain the scoped latent-capability result above, no automatic architecture expansion
  or exposed fitting. Full-state execution stays intact. TASK_PREDICTION_DIAGNOSTIC.md
  owns scoped evidence; UNFAMILIAR_RULE_SEARCH.md owns forward/caller costs.
  Ordering control and scoring-discard folding do not establish playing gain.

- Four new finite16 source-prior rules retain mixed physical signal, then no
  actual selected-net improvement: capture worsens5q0/1q2 choices versusv3.
  Separate36matched D2 calls all complete; five losses remain. Stop automatic
  source-law/horizon expansion or refits, keep the candidate conditional, and
  examine promotion/auxiliary decision targets or small state-feature ablation.
  TASK_PREDICTION_DIAGNOSTIC.md owns all caps, raw results and isolated recovery.
  Scalar owner-string conversion hoisting is the only product change;544cold
  calls preserve work/signatures,9344queries/438cancel pairs preserve callbacks,
  and1778active tests pass. Two larger helper proposals stay deferred/rejected.
  Local short-call ratios are descriptive, not universal speed or strength;
  UNFAMILIAR_RULE_SEARCH.md owns these cost controls and exact source pins.

- Fresh partial-preference coverage now retains64roots/3155children,3133complete
  child references and22UNKNOWNs. At8192nodes,56roots supply usable certified
  pairs in160.45seconds, versus1371.55seconds for full children. Three frozen
  same-input count fits share dev/report choices and substantial errors;
  504actual ranks plus63matched-time search calls keep all zeros/caps. Retain
  cheaper partial supervision as a scoped option, defer more Unit-compression
  fits, and test the frozen constants on existing independent physical-task
  rewards before claiming useful rule prices. Exact inventory-class ceilings
  explain only some errors. FINITE_SEARCH_COMPRESSION.md owns the full cohort,
  cost attribution, limitations and partial-preference recovery index.
  The existing886slot physical check shows no full/8192top gain and one2048
  regression. A separate two-new-rule fixed-predictor check keeps442slots/
  2210cells/5855Core-Native transitions: on2104static C loses799/5148while the
  unchanged2048model's B loses21/1870; all methods match on mostly-zero2105.
  This is scoped physical-task signal, not model selection or strength.
  Crossed count/any and source/occupancy controls now explain2104's sign reversal:
  source weighting alone OR occupancy alone reverses B/C; neither statistic
  alone identifies the cause. Initial-source capture/total candidates frozen
  before four new rules improve immediate top loss3/4,tie1/4 and one-reply2/4,
  tie2/4, but worsen2109 B/C pair loss despite an unchanged top choice.
  Full state carriers keep drop/transformation effects that this removal proxy
  omits. The408 fixed-order cold caller controls retain every cap; q2 reaches
  D3 on only1/68roots per arm. Changed choices are not gains. Keep source priors
  as scoped candidates, no fit/default. Original actual-action oracles complete
  22/68roots,46UNKNOWN; a cheaper selected-action net task covers all68roots for
  5997extra transitions/59.97sec. Capture improves only2108 and worsens one2109
  q0 choice; total ties throughout. Choose a new utility/support premise rather
  than refit or expanding costly whole fronts. TASK_PREDICTION_DIAGNOSTIC.md
  owns this attribution, prospective task evidence and actual caller limits.
  The first common-capped q2root's128node audit finds354/372legal cache hits,
  352first-action-only terminal probes,17subsequent expansions and no repeated
  full generation per visit episode. Retain lazy generation; advisor duplication
  hypothesis is not a demonstrated full-set defect. Profile hotspots do not
  justify weakening semantic/cancel checks. Recovery correction and exact scoped
  records are in TASK_PREDICTION_DIAGNOSTIC.md; numerical bytes stay unchanged.

- Full-sort Core TT priority is now structural; large evaluator capture values
  previously outranked its numeric-1000sentinel. All84jointly complete D3pairs
  agree; cost regressions and original teacher records remain.1774active tests
  pass. UNFAMILIAR_RULE_SEARCH.md owns this interface repair, not a price claim.
  A further public-player q0/q2 switch exposed incompatible old TT bounds in
  all six completed small controls, including a missed mate value. Changed
  soft/hard q depths now invalidate those bounds; unchanged-q reuse stays.
  Hard-depth-only switches preserve the cold abort boundary. Cold source-prior
  caller records are unaffected and retain the old source pin. Next test a
  concrete generic search/state mechanism, not more numeric ordering patches.

- Shared-state comparison now retains64fresh roots/3445children across two
  prospective cohorts,3375complete children and70UNKNOWNs. A concrete zero-anchor
  input alias is repaired before the second cohort. Spatial/anchored linear and
  ReLU16 have mixed report successes but no clear development increment; whole
  denominators expose additional zero-root errors. Keep counts/search baselines,
  no report refits/default promotion. A384call search-cost curve favors2048TT+
  ordering as a scoped comparator. An eight-root24.26second bound pilot retains
  325inferior/8optimal/145unknown preferences, avoiding false-negative unchosen
  labels. Next choose fresh partial-preference coverage or a rule-price-usefulness
  target by decision/cost, not another automatic architecture expansion.
  FINITE_SEARCH_COMPRESSION.md owns sources, limits, five recovered models and
  the immutable shared-state/bound-teacher archives.

- State-input feasibility now separates semantics, signal and cost: a real
  base-identity continuation aliases the old compact input; a separate offline
  sparse Position encoder repairs that scope and supports tested rectangles,
  without changing live models. History remains a consequential omission.
  One frozen exposed-rule batch retains135completeD2children and229different
  finite teacher scores among1710dependent same-material pairs. This motivates
  a compact-predictor target/split decision, not automatic training or true-value
  claims.80actual caller controls defer expensive per-leaf attack relations;
  sparse/material/coarse controls remain candidates. STATE_INPUT_FEASIBILITY.md
  owns the full denominator, adverse costs, caps and recovery package.

- Finite-search compression now has six new frozen trajectories/all228complete
  D2children and one fixed72sample small predictor, authorized2026-10-09.
  Stop the D4 arm after55caps and retain173unattempted UNKNOWNs. Existing
  ordering reduces complete-search cost but worsens one finite-budget tie
  choice; static table callers keep4caps where unit completes. These are
  compression/cost diagnostics, not price quality or strength. Greedy prediction
  fails to improve development/report regret; identical-budget learned-leaf search
  helps this finite teacher. Preserve that distinction and all incomplete references.
  Parameter preconversion removes major per-leaf overhead without changing weights.
  Small training is authorized; single runs expected above one hour first need
  dot's necessity assessment, as defined in LOCAL_AGENT.md Budget.
  FINITE_SEARCH_COMPRESSION.md owns the current target, splits and controls.
  Pure symbolic relabel is now verified; cached public prediction removes repeated
  parameter conversion with identical outputs/schema. A fixed12game continuation
  batch has1mate/11censored; longer Unit search avoids the observed threat, so no
  learned strength claim. The subsequent24root/1055child conditional comparison
  selects7disagreement roots before prediction. Position and Position+pairs
  rankers share202trainchildren and have identical adverse dev/report regrets;
  matched-cost Unit search has0on all3selected dev/report roots. Defer expanding
  pairs/default promotion; a fresh sharing/support premise must precede another
  fit, rather than report tuning. Keep all17zero roots and scope/unknown records.
  Fresh coarse sharing now has1037complete children: one development improvement,
  adverse report unchanged; defer expansion. A four-rule74axis constant-input
  prototype keeps22complete/2capped roots and has no development choice benefit.
  Redundant identical drop declarations change raw count inputs despite17matched
  physical successor sets; defer syntactic mechanism counts. A concrete Bdrop-mate
  alias is detected by existing CoreD1in39ms, far below a full successor feature
  scan. Static v2/v3search has both a train improvement and a report regression.
  Keep state/rule semantics, existing search and static baselines; next work must
  test a behavior-based shared input or one cost-effective state interaction,
  not repeat these report fits. FINITE_SEARCH_COMPRESSION.md owns exact evidence.

- Full existing common-slot task populations now test fixed price selection:
  immediate top choices help against blind8/8rules, but average pair ordering
  fails3/8; v2/v3rank identically. One-reply support is sparse/check-dependent,
  with one allzero rule and phase/influence failures. Descriptive best-fixed
  ceilings separate generator headroom from conditional information loss;
  neither implies new prices or strength. TASK_PREDICTION_DIAGNOSTIC.md owns
  the complete136background/1500slot evidence and next-decision boundary.

- Fixed-order internal-Xiangqi leaf pilots separate sensitivity from ordering;
  finite-source kernels retain different stationary laws and rare-bridge limits.
  Do not replace the source law or infer calibrated prices from q-horizon choices.
- The inert-custody pilot repairs legacy remove_from_game execution and removes
  ghost hand credit in a proved simple no-drop/no-declaration IR subset only.
  Optional hand-weighted declaration controls exclude broader zero-hand claims;
  keys/history and default evaluation stay intact. Next: find a discriminating
  supported price diagnostic beyond trivial openings, not a generic utility proof.
- Legacy target queries preserve actual callers/work with local43.63% median
  q2wall reduction;189prospective contexts pass attack equivalence. Frozen
  paired games are trivial/censored and opening strict-inversion selection is
  empty. The deferred Native candidate remains unaccepted; the restored baseline
  module is available. Route exact evidence via leaf_order_20261009.

- Generic-v2 replaces signature-seeded hybrid sampling with exact independent-
  occupancy endpoint-prefix counts for supported Leap/primitive Ray atoms.
  This fixes finite representation noise, not material utility. Standalone
  rectangle capability/cache work; default rectangle evaluation stays explicitly
  unsupported. Four matched old/exact board-only caller pairs keep first choices;
  one pair remains capped. See GEOMETRY_OCCUPANCY.md and its data/archive index.
- Explicit material-only and semantic-mobility-only supplied evaluators now
  cross the rectangle carrier boundary with disabled square-dependent terms;
  default rectangle generation remains unsupported. Duplicate diagnostic/cache
  and short-anchor owner-frame defects are corrected. Screen-count studies show
  that distinct prerequisites can disappear in large-board total opportunity;
  retain conditional structure, not another uncalibrated material claim. See
  the geometry consistency supplement; full-v2 leaf/order callers stay scoped.
- Opt-in semantic-opportunity-v3 projects exact emptiness guards and finite
  source/target zone membership; other state/zone effects stay explicit exclusions.
  Guarded-H exchange sensitivity is separate from price usefulness. Equal means
  can hide shared-prerequisite options; initial-source closure exposes source-law
  bias but a rare bridge falsifies unqualified uniform-support replacement.
  Keep these conditional diagnostics, not a fitted price. Inverse Core zone
  membership retains16actual q0/q2 caller signatures/work, with modest mixed
  local timing. GEOMETRY_OCCUPANCY.md and CROSS_GAME_PRICE_DIAGNOSTIC.md route it.
- Common-slot interventions remove type-presence mismatch but retain a declared
  context/task law.2456 cells/6602 Core-Native transitions agree. A finite
  physical-selector alias qualification and716-cell type-alias check pass.
  Fixed-rule rounded board-only ablation runs8 Core D2 calls; not a new default.
- Chess common-slot capture opportunity is Q>R>B>N>P on17 backgrounds. Two
  en-passant events explain P geometry/task differences. Initial short exchange
  task collapses all75 cells to0 after one opponent reply. These scoped averages
  are runnable diagnostics, not material truth; do not fit human ratios.
  Equal-context versus equal-slot reaggregation preserves all six orderings.
  Board-only caller comparison changes1/21 completed event choices; one pair
  stays capped. Dormant duplicate type rescales the proposed normalization,
  although raw old-type ratios stay fixed. Neither finding is a strength gain.
- Final Native first-legal correction cannot load under App Control. Product
  source is restored; exact candidate is archived/deferred, Core research works.
  Earlier31.64% timing belongs to earlier builds, not accepted deployment.

- The simple target-directed iterator is delivered.16 actual q2 calls retain exact
  choices/PV/nodes/work, with local wall reductions5-13%;1654 regressions pass.
  Four6x6 routes additionally agree on4896 attacks/306432 geometry queries.
  Their22 actual event frontiers now retain88 cold q0 caller signatures/work;
  local median wall reduction8.35% is descriptive (sub.12sec calls), not strength.
- PVS/ordered-q factorial: no cell uniformly wins. Keep defaults and separate
  leaf prices, ordering prices, attack authority, completion and execution cost.
  The modest inconsistent warm compiled-target index remains deferred.
- On22 frozen event roots, lexical q fusion retains exact decisions/main/qnodes,
  reducing pushes133480->63829.16 wide-root calls retain signatures and old caps;
  four cold product controls plus qualified warm/cancel recovery pass.1673 active
  regressions pass. First-latency/abort-cause reports corrected, old raw data kept.
  Eager Native full legal-set terminal probing regresses to time_limit; rejected.
- A tuple-membership miss guard preserves all16 cold q2 signatures/work and
 306432 transfer geometry queries. Local median reductions0.22-3.55% are modest;
 no cache/index or cancellation weakening follows. Constructor pattern filtering
 was rejected before execution because per-call engines invalidate amortization.
- Public rectangle support with a supplied evaluator now reaches Core execution:
 12 cannon q0 calls match two full-width D2 references;16 q2 calls complete.
 20 further temporal/compound calls preserve actual roots/PVs;12 q0 calls match
 four full-width references. These unit-evaluator controls test execution only.
 Explicitly requested Native uses Core when unsupported; no Native rectangle or
 rule-only rectangle price support is claimed. Default square cache reuse stays.
- Semantic qsupport uses actual enemy-board removal, board-current/hand-base
  inventory change, terminals and checks. Semantic promotion/target labels are
  not authority. Ordered q reuses classification pushes. Balanced type swaps,
  spatial/auxiliary/base-only changes can conserve inventory; qsupport is limited,
  not full tactical completeness. Do not add all quiet actions without evidence.
- Fixed-stock anonymous occupancy is a conditional diagnostic, not a replacement
  material table.378 subset and40 colored-layout controls pass; same fixed stock
  and square marginals still permit opposite ray/cannon endpoint orderings.
  Canonical B/N changes mostly reflect selected density, not finite correlations.
  On68 frozen6x6 contexts, finite-stock quiet-count prediction improves3/4 rules,
  capture-count error worsensall4. This does not justify a new default/profile.
- Initial-template aggregate capture accuracy improves4rules, but619/1256 local
  fact sets are unchanged; changed-nonzero errors worsen2/4. One fixed dual-
  transform rule gives identical material deltas with opposite conditional task
  contrasts; static averaging loses information, not necessarily usefulness.
  Cross-rule3/14 residual inference rejected; Native1618 transitions agree.
- Promotion-aware preparation tasks retain20640 exact Core/Native roots overall.
  Quiet same-entity promotion changes task scope/ratios; target law, near-layer
  mass and representative backgrounds remain influential. Keep the conditional
  component; do not extend samples/horizons to obtain preferred stock ratios.
- Conditional P/X transformation features distinguish actual effects but depend
  on contexts and physical-response laws. The short retention and hand-service
  tasks supply no stable positive material ratios. Their zero/negative/capped
  results remain evidence, not prohibitions on entire research directions.

## Working boundaries

Latest search-first checkpoint (2026-10-10): compile-owned incoming geometry is
installed with full old fallback.48 product/48 thin paired controls retain fixed
work/routes; product local fixed cost falls29-53% and three4second roots gain
one completed layer. Correct unordered traversal is str(action), not natural.
Finite static-sequence/replace/state/rectangle/q2/cancel controls pass; completion
is not strength. Owned metadata, construction and a24ms poll-gap outlier remain
explicit costs. Native Runtime PV migration is deferred after separate neutral/
adverse mean tail controls; existing immutable validator, C/terminal boundaries
and UI isolation remain. The newer actual-UI checkpoint above owns the next choice; this incoming-index
result is retained context, not a competing task. No extra algorithm or price
fitting follows.36 post-index legal-generation prefix reuse controls show no
timed depth gain and a slightly adverse root: defer that extra cache. Evidence:
SEARCH_BACKEND_ATTRIBUTION.md;
data/frontier_contract_20261010.json. This technical review changes no manual,
heartbeat, publication, stop or long-run rules.

Use existing frozen outputs/search entries; select one discriminating mechanism
or interface uncertainty. Development approximations may state limitations rather
than first prove exact WDL/all defenses/holdout status. Human agreement remains
only descriptive. Xiangqi human holdout stays closed; exposed data never regain
unexposed status. Preserve legality, user stops, fair conditions and prior caps.

Static generation must preserve supported equivalent encodings and finite-board
saturation. Quantity and actor splitting do not assume linear conservation.
State context/response assumptions; separate semantics, approximation and useful
independent deployment evidence. Advisor objections guide one next action, not a
branch backlog or publication gate. Exact operating rules remain in AGENTS.md.

## Evidence routing

|Purpose|Document and latest records|
|---|---|
|Actual frozen UI path, first-completion boundary and compiled trigger cost|UI_PRODUCT_DIAGNOSTIC.md; data/ui_product_20261010.json|
|Evaluation families, state-input signal and actual caller cost|EVALUATION_ROUTES.md; STATE_INPUT_FEASIBILITY.md; data/state_inputs_20261009.json|
|Finite search compression, prospective splits and existing search/table controls|FINITE_SEARCH_COMPRESSION.md; data/search_compression_20261009.json|
|Fixed price predictions, conditional information ceilings and reply support|TASK_PREDICTION_DIAGNOSTIC.md; data/qfrontier_20261009.json|
|Semantic opportunity, equivalence, context/task boundaries|SEMANTIC_CAPABILITY.md; data/tasklaw_20261009.json; task_compression_20261009.json; finite_law_20261009.json; preparation_transfer_20261008.json; retention_20261008.json|
|Descriptive price ratios and preparation/promotion bias|CROSS_GAME_PRICE_DIAGNOSTIC.md; data/pawn_bias_20261009.json|
|Exact primitive occupancy, representation and rectangle capability|GEOMETRY_OCCUPANCY.md; data/geometry_occupancy_20261009.json; leaf_order_20261009.json|
|Search interface, actual-effect qsupport, costs and caps|UNFAMILIAR_RULE_SEARCH.md; data/event_qsearch_20261009.json; rect_search_20261009.json; query_transfer_20261009.json; qfactorial_20261009.json; qeffects_20261008.json; generated6_20261008.json; generated8_20261008.json|
|Completion-aware search alternative, full-state scope and actual caller costs|COMPLETION_SEARCH_FEASIBILITY.md; data/completion_search_20261010.json; data/handle_time_20261010.json; data/completion_ablation_20261010.json; data/bounded_completion_20261010.json|
|Retained utility alternatives|TEMPORAL_HAND_SERVICE.md; GOAL_INTERACTION.md; CONTRIBUTION_MODEL.md; JOINT_SERVICE_DIAGNOSTIC.md; CUSTODY_CONTINUATION.md|

Each data index routes exact sources/failures/outputs to its purpose-specific
archive. The longer prior mainline is recoverable at Git af8ed2c62f4c87a17e7fe33d2e2df3a65fd3af2e;
its detailed results remain in the documents above. It is not active scheduling.
Publish reviewed/tested Agent code/results/evidence each completed segment,
exclude private/user inputs and raw Slack/account/credential records, and verify
full origin/sandbox SHA. A local commit or failed push is not publication.
