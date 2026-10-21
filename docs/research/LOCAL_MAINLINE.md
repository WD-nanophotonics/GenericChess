# Current GenericChess mainline

AGENTS.md owns authority, PUBLIC, roles, stops and research integrity;
LOCAL_AGENT.md owns operations. PRIMARY_SANDBOX owns sandbox here. DEV_AUX owns
its separate learning/solver lane. The existing 90-minute patrol and read-only
project Chat remain unchanged. No extra worker or outbound consultation.

This replaces the chronological daily entry, whose complete decisions/reasons
remain at [897a110d](https://github.com/WD-nanophotonics/GenericChess/blob/897a110db22483c8fa99b8156a6d4547a655ca0d/docs/research/LOCAL_MAINLINE.md).
Old dated next actions are evidence, not a backlog or a competing live policy.

## Current selection and reason — 2026-10-21

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

Next: execute the prepared `artifacts/aux-deadline-20261021/price-third-foe-next.json`.
Run36 new D/A games against fixed A=StaticOFF. Reuse36 C/A baseline frames from
existing A/C matches by role transpose and utility negation; their interval is
[-2/9,1/3]. Zero new D/A queries have run. Keep all18 roots/both subject roles,
node512/q0/48-ply/180-second caps and common Static ordering. A contrary result
changes candidate priority; do not extend old UNKNOWN, select favorable families
or turn this diagnostic into Elo/default/training work.

Backup1: qualify `.local_agent/normalization_subset_probe.py` before any new
normalization candidate. It matches36 typed-support cases without a legacy
handle and rejects real type transforms. Initial-setup, stock and hand-conversion
controls remain pending. Keep every type field and conservative fallback outside
the proved scope; no current default change. Backup2: inspect new primary general-
game evaluation literature for one cheap decision-changing criterion, without a
model port or AUX learning duplication. Science OPEN.
