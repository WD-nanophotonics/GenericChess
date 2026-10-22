# Current GenericChess mainline

AGENTS.md owns authority, PUBLIC, roles, stops and research integrity;
LOCAL_AGENT.md owns operations. PRIMARY_SANDBOX owns sandbox here. DEV_AUX owns
its separate learning/solver lane. The existing 90-minute patrol and read-only
project Chat remain unchanged. No extra worker or outbound consultation.

This replaces the chronological daily entry, whose complete decisions/reasons
remain at [897a110d](https://github.com/WD-nanophotonics/GenericChess/blob/897a110db22483c8fa99b8156a6d4547a655ca0d/docs/research/LOCAL_MAINLINE.md).
Old dated next actions are evidence, not a backlog or a competing live policy.

## Current selection and reason — 2026-10-22

Continue rule-only generic prices/cross-game ratios and stable unfamiliar-rule
search. Static, Unit and learned candidates remain. New incoming theory advice
and actual mechanism evidence favor decision-equivalence/learnable-signal
questions over further caller audits or unchanged price panels. This does not
claim knowledge transfer, select MCTS/Elo or take over DEV_AUX's learner.

[PRICE_DECISION_REGIONS_20261021.md](PRICE_DECISION_REGIONS_20261021.md) records:

- Blocked-leg static ratios623:1377 versus728:1272 leave the selected D2/D3
  actions unchanged on three exposed roots. One score changes+131to-184 without
  an action change. All four subsequent capped games remain UNKNOWN; no refill.
- The existing promotion/drop/full-history fixture gives exact D2 boundary
  wTP+wHandR=2*wR. Hand BASE and board CURRENT are distinct;48public checks match.
- One explicitly finite3x3 rule has real wins that positive-price D2 misses;
  six actual depth-control games end3D2draws/3D3mates against a fixedD3foe, with
  more paid work atD3. Signed coefficients escape two of the three positive-cone
  traps; this is not an impossibility result for unconstrained TDLeaf.
- Six type-label controls verify the complete finite game tree/history mapping;
  a tied choice changes, but no selected-WDL gain. No generic isomorphism API.
- A new analysis reuses24saved histories:96planned slots,83ongoing,60D1
  price-sensitive. Eighteen root-zero states are sensitive;14nonzero states
  are invariant. A concrete exchange proves D1 invariance cannot filter D2
  learning. These are budget/model-specific diagnostics, not utility evidence.
- Fixed dynamics make absolute material scale matter despite unchanged ratios.
  No normalizer, evaluator default, sampler or frozen experiment changes.

An actual existing Gumbel defect is fixed: terminal values follow the rule's
winner, including stalemate loss and perpetual check. Seventy-one affected
regressions pass. It remains a Native learning backend without a Player adapter;
zero-valued uniform-prior leaves are not terminal random rollouts. The old UCT
stability screen supplies neither Gumbel strength evidence nor a refutation.

## Follow-up decision — 2026-10-21

[FINITE_GOAL_CONTEXT_AND_SIGNAL_20261021.md](FINITE_GOAL_CONTEXT_AND_SIGNAL_20261021.md)
completes the empty-row control. A natural saved full history is D1-price-invariant
but D2-sensitive, with exact boardP+handP boundary3800. Cheap dynamic terms help
conditional roots but every tested D2opening policy still draws in the finite
world; an equivalent DSL rewrite can reverse a tied conditional win. Actual rule
clocks change WDL under identical shallow feature trees. Nonzero/full-rank PV
signals are not training gates. Forty-eight new mixed-rule state/scale controls
retain all16UNKNOWN; D-A and interaction bounds establish no robust gain. Keep
candidates, semantics and costs separate; no default is selected.

## Closed findings to preserve

- [FINITE_ROSTER_AND_SEMANTIC_AUTHORITY_20261021.md](FINITE_ROSTER_AND_SEMANTIC_AUTHORITY_20261021.md):
  finite-count correction improves reachable MAE only0.2745%, failing5%.
  The separate64-slot authority panel retains37UNKNOWN and utility bounds
  [-1.0625,1.25]. No default or unchanged rerun. Uniform legacy rejection sampling
  passes choice-only speed screens but only1of6 complete-turn20%/1ms gates;
  defer it. Raw stability-only selection also fails; not Clune's full method.
- [STATIC_CAPTURE_ORDER_UTILITY_20261021.md](STATIC_CAPTURE_ORDER_UTILITY_20261021.md)
  and [STATIC_HAND_PRICE_UTILITY_20261021.md](STATIC_HAND_PRICE_UTILITY_20261021.md):
  robustness gates failed; hand-only finite bounds[-0.3125,-0.25]. Do not rerun
  these panels or choose favorable subsets. No universal hand-price conclusion.
- [SEARCH_WORK_CURVES_AND_CACHE_CONTRACT_20261018.md](SEARCH_WORK_CURVES_AND_CACHE_CONTRACT_20261018.md):
  budget can reverse table ordering; cached scores are not literal-PV/WDL proofs.
  Preserve all missing/UNKNOWN outcomes. Static and learned controls remain.
- [FULL_TYPE_STATIC_INPUT_AND_PRECISION_20261018.md](FULL_TYPE_STATIC_INPUT_AND_PRECISION_20261018.md)
  and [PLAYABILITY_FILTER_OPPORTUNITIES_20261018.md](PLAYABILITY_FILTER_OPPORTUNITIES_20261018.md):
  complete types/promotion/drop/history retained; optional opening filter changes
  accepted-rule distribution, not same-game learning utility. No activation.
- [HIGH_RESOLUTION_SEARCH_CLOCK_20261021.md](HIGH_RESOLUTION_SEARCH_CLOCK_20261021.md):
  actual Windows15.625ms clock distortion fixed with perf_counter/QPC across the
  search/measurement/MatchClock caller. Cooperative deadlines are not preemption.

## Incoming Chat disposition and cleanup

The two-part theory memo and Claude correction were privately saved in full,
including the complete reply and no remaining thread pages. Adopt separation
of rule execution/search/learning/knowledge transfer, parameter regions, actual
utility and cost. Do not turn root feature tests into training gates. Defer full
Clune-port, MCTS integration, Elo/SPRT and larger theory/solver campaigns.
Prospective no-progress rules define new games; never relabel old UNKNOWN.

PRIMARY's2674-file cleanup is fixed at62b2a02a7e9c1d867935104f95b3003401c350ad.
AUX independently published its13366 deletions atb53e0b51806aa44fdfd852ab6a1d0dadf1dfdb6f;
this was verified in its fetched public ancestry, not independently rerun or
written by PRIMARY. The once-only cleanup manifest now lives at that PRIMARY
Git revision, not in the current tree. Exact raw research/Chat remains ignored;
a compact technical evidence copy and source are published for current research.
Unrelated branch/history/unique private cleanup remains as scoped in
[the cleanup report](../operations/CLEANUP_20261021.md), not a research stop.

## Current follow-up and next executable question

[HAND_VALUE_CONTEXT_AND_SEARCH_COST_20261021.md](HAND_VALUE_CONTEXT_AND_SEARCH_COST_20261021.md)
closes the valid3ply no-drop contrast. Custody identities make coefficients
nonunique even with actual promotion; this does not imply stock has no reader.
Equivalent leaf values can still alter ordering and capped decisions. An exact
Position value alias does not yet prove disjoint optimal policies. Existing
sparse inference reduces overhead but72complete finite slots show zero paired
utility difference. No default/learner/AUX change is selected.

[NATIVE_SERVICE_COST_AND_HYBRID_ALIAS_20261021.md](NATIVE_SERVICE_COST_AND_HYBRID_ALIAS_20261021.md)
completes that continuation and compares actual consumer cost. Aligned physical
PVs separate execution speed from ordering work. Native services improve scoped
throughput;16 fixed-opponent games retain8UNKNOWN and no paired outcome gain.
Ordered q gives3 additional D2 completions under the common clock on16 exposed
roots, without a strength claim. Full hybrid aliases can change sampling mass;
same seeds do not ensure matched states. Existing keys retain auxiliary effects.
GameRecord recording now uses the strict public serializer after5 red regressions.
One reusable cost probe and compact full-input/outcome evidence replace new
ad-hoc script proliferation. Defaults, learners and AUX ownership are unchanged.

[Q_HORIZON_POLICY_AND_EARLY_WIN_20261021.md](Q_HORIZON_POLICY_AND_EARLY_WIN_20261021.md)
completes q1 follow-up: hybrid32-game utility remains unidentified across zero;
finite808 conditional policy runs eliminate q0 errors with q1/q4/D3 on one game
and equivalent encoding. No horizon/evaluator/learner default is selected.
Optional any-win stopping reuses completed root children, default OFF, with
truthful depth/source/control reasons. Six of64 new post-win1 samples have
independent Core mate3 certificates; two separate extra-budget flags never
refill that cohort. Hash/native-eval/staged-scheduler alternatives are deferred
on measured cost, not universal prohibitions. Full semantics/history remain.

[SEARCH_ALLOCATION_AND_ANYWIN_20261021.md](SEARCH_ALLOCATION_AND_ANYWIN_20261021.md)
completes that arm and the bounded allocation follow-up.592 new capped histories
and202finite policies retain all failures/UNKNOWN. D3q0 has positive observed
contrasts on5/6boards but8board bounds cross zero; postseal factorial and q2
negative results reject depth/action-stability shortcuts, not all qsearch.
All78 any-win positive claims pass independent Core proof. Selected cold proof
roots save work;96whole-game utility remains unidentified. Keep default OFF.
Capture-only is exposed in the maintained cost CLI; its known quiet-check misses
and full-rule scope remain explicit. No evaluator/learner/default/AUX change.

[AUXILIARY_STATE_AND_CALLER_COST_20261021.md](AUXILIARY_STATE_AND_CALLER_COST_20261021.md)
closes the explicit-effect/auxiliary continuation: the maintained cost CLI now
accepts complete DSL inputs and a Core service control.1,240retained queries,
full child/history qualification and promoted negative controls distinguish
current kernel support from the deliberately unchanged provider admission.
Blind type recoding changes legality; scoped explicit service is feasible without
it. Plain-rule history digest savings fail20% across all6fixtures. Long replay
can erase cold-call gains, but the maintained caller already retains its full
GameSession. No default, history compression, replay cache or AUX learner change.
The closed6.8MB allocation packet is a small index into its verified fixed PUBLIC
Git version; exact originals remain, no history rewrite or withdrawn evidence.

[DECISION_EQUIVALENCE_PRICE_ORDER_20261022.md](DECISION_EQUIVALENCE_PRICE_ORDER_20261022.md)
closes that continuation:1,452root queries plus422new common-continuation calls
retain every failure/UNKNOWN. Frozen D2completion gates fail; actual default
already uses Native legality on9of9generated rules, so pureCore gains are not
incremental default gains. One partial-iteration3ply win has independent full
Core reply witnesses; paired Core action stays unknown. No provider/default change.

A144query leaf/ordering factorial is independently verified by36complete Core
trees. Static/Unit D2argmax sets overlap17of18;one exact85/161interpolation
boundary survives integer lifting,while rounding changes its tied set. Overlap
is not policy equality. Signed full-child masses include leaf,ordering and
interaction effects;20new fixed-continuation trajectories plus1verbatim old
censored receipt retain9terminals/12UNKNOWN. No price winner or training gate.

[DYNAMIC_PRICE_CONTEXT_AND_CACHE_SCOPE_20261022.md](DYNAMIC_PRICE_CONTEXT_AND_CACHE_SCOPE_20261022.md)
closes that continuation. Existing dynamics increase disjoint Static/Unit D2 sets
from1 to8 of18; a complete D4 counterexample refutes tie-only refinement. Table
and whole-evaluator scaling differ there. Unreachable-declaration controls expose
normalization sensitivity while retaining full histories and the conservative
semantic boundary. A real representation cache collision is fixed without
changing profile values/defaults: eight new regressions and3,598 active checks
pass. Old ambiguous disk files are ignored, not deleted.

126 new fixed-opponent games execute2,763 paid queries.18 C role frames and54
first moves are exact reuses. The initial combined priceON bound[-1/18,11/18]
was valid but too loose: reused C self-play has exactly opposite utility across
roles, even for UNKNOWN. Applying that known constraint gives[1/18,1/2]. This
supports a finite UnitON leaf-price edge against fixed C on this exposed panel;
family1646 has a negative effect, so there is no generic winner or activation.
The earlier no-strict-priority inference is superseded, with unlinked bounds
retained. All UNKNOWN and14 incomplete deeper Core references remain. One failed
exploratory override assumption has up to two unretained partial returns, excluded
from retained counts. No learner, AUX or evaluation-default change.

[PRICE_TIES_TRANSFER_AND_REFERENCE_UNITS_20261022.md](PRICE_TIES_TRANSFER_AND_REFERENCE_UNITS_20261022.md)
closes the prepared check: 36 new D/A games and 649 paid queries retain five
UNKNOWN; D-C [-4/9,7/18] does not extend the fixed-C advantage. At 50 actual first
divergences, 45 full D2 argmax supports are disjoint; promotion removal leaves 45,
material alone five. Uniform tie diagnostics do not establish WDL or policy utility.

A new prospective cohort fixes 18 configurations before generation: 15 successes,
three failures, no replacement. Its 105 episodes and 1,819 paid queries retain one
batch UNKNOWN. On accepted rules, D-C against C is [-1/15,0], against A is 1/6,
and the opponent interaction is [1/6,7/30]. Do not prioritize a universal Unit
winner in this envelope. Planned-completion sensitivities include zero; missing
4x4 free-random coverage is explicit. All full Core replay/PV/history checks pass;
52 optional actual-depth checks remain budget-incomplete. No default or cap refill.

Complete linear prices using an instance reference are the next cheap candidate;
nonlinear relative material is not needed solely for declaration invariance.
A reference based on unique initial types fails a qualified file-locked split;
the instance reference passes. Invariance and limited search feasibility are
not utility evidence. Material-only composition works without a legacy handle
on six typed-IR fixtures and 11 queries. Preserve supplied proved-inert hand zero
and every excluded-pattern scope. No default admission or AUX learner change.

[INSTANCE_UNITS_AND_STATE_DENOMINATORS_20261022.md](INSTANCE_UNITS_AND_STATE_DENOMINATORS_20261022.md)
completes that continuation. Six empty and six fully translated ray-declaration
controls retain complete child/history/aux/promotion/drop semantics. Exact old-ID
replay still fails when compilation renumbers; no identity or admission claim.
A truly unreachable compound actor also changes the conservative hand proof,
so complete-evaluator invariance does not follow from reference-unit invariance.
Actual token creation/off-target capture/expiry is qualified on a declared board,
not inferred from an empty-pawn fixture label. No product default or API changes.

New finite policy evidence keeps every planned slot: E/R D5/node65536 executes
only13/72, no complete matched contexts, bound[-16/9,14/9]; do not repeat that
coverage-poor panel unchanged. F/R D3/node4096 completes36 games and gives[0,2/9],
with all16 resolved pairs equal. G/R on nine NEW remove-from-game rules completes
36 games and gives[-13/18,11/18], with two resolved negative R contrasts. Each G
query prepares a complete CURRENT-root table with actual cost and TT OFF. These
are finite censoring bounds, not sampling CIs or cross-envelope causal evidence.

A complete discard D3 witness proves R can differ from both initial-fixed and
root-fixed tables; its two fixed-S continuations draw. Removing table coefficient
quantization does not erase the two whole-policy negative examples: exact-root G
wins with the same full trajectories as Gtable where R draws/loses. Thus neither
strict preference nor scoped invariance justifies nonlinear utility priority.
Same415-state timing gives R/E1.08117 and R/F0.99749; simpler F is not measured
faster. Material-only normalization also changes relative dynamic weights11–55x.

E remains a conditional cheap baseline, not a universal normalization solution:
zero-initial/future-positive type effects break its fallback scaling property.
A potential-type reference fixes that example but fails an impossible-guard
negative control (B1000->620). Keep full fields and limits; do not build a generic
reachability/guard framework or manufacture new fitness for18 identical E profiles.

## Current next choice — 2026-10-22

[SEARCH_WINDOWS_COMPLETE_STATE_AND_POLICY_20261022.md](SEARCH_WINDOWS_COMPLETE_STATE_AND_POLICY_20261022.md)
closes the normalization followup selection and tests existing search controls.
The prepared two-negative-example decomposition is NOT executed and no longer
Main: regardless of its result it would not change present priority. Preserve
the actual negative examples and scope, not an assertion of no effects. The
latest incoming Claude advice supports this stop; no new approval or AUX task.

PVS/aspiration/staged median cost gates fail on the exposed curve. A NEW18-rule,
36-role staged-vs-fixed-B panel executes32games/1317queries at its900second cap.
After actual whole-runner eligibility correction,13W11L2D10UNKNOWN gives finite
[-2/9,1/3]; all11 resolved rule-pair contrasts0. Four unexecuted slots, five
ongoing games and one timing-invalid outcome remain UNKNOWN. No cap refill,
Elo/population inference, default order/evaluator/learner or AUX change.

Two real defects are corrected: post-proof cancellation/deadline reporting keeps
the complete winning payload AND the established last-node success contract;
the maintained cost caller now saves prepared full input and errors before
propagation. Explicit Unit control covers complete metadata types without legacy
price metadata; defaults and all rule/history/aux/promotion/drop semantics remain.
Full3616 regressions and24 later consumer controls pass; old expected values stay.

A new18-root evaluation-repeat trace fails actual-cost feasibility (predicted
0.66%/0.182ms), so do not engineer that cache. This is not a universal ban.
Ninety-six late-history service queries add one D2q4 completion, but grouped
process first-call bias and terminal-predecessor sampling prevent a generic
latency/default claim. All actual q-policy strata and original timings remain.

Main: use the already-prepared readable `balanced-service-next.json` controls
only if they decide an actual next existing-service consumer choice. Separate
short/95ply full-history roots, rotated process-first modes, within-process later
calls and matching q policy/value; queries are NOT executed. A20%/1ms scoped
result may guide that explicit caller, never default or game utility from two
exposed states. Otherwise choose a new discriminating question, not more timing
receipts or a gate before research.

Backup1: one unread primary source that yields a falsifiable cheap test for
rule-general search/prices; no old-Clune reread credit or AUX solver/learning
replication. Backup2: use the NEW actual family costs to predeclare allocation
for a genuinely new question, not to refill this closed panel. The15minute
forecast missed4slots; analytical B/B cancellation saved18redundant games.
Closed large evidence packets are fixed PUBLIC indexes with verified private
copies. No historical result, source or failure was withdrawn. Science OPEN.
