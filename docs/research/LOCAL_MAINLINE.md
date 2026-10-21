# Current GenericChess mainline

AGENTS.md owns authority, PUBLIC, roles, stops and research integrity;
LOCAL_AGENT.md owns operations. PRIMARY_SANDBOX owns sandbox here. DEV_AUX owns
its separate learning/solver lane. The existing hourly patrol and read-only
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

## Next executable question

The empty-row control is already begun: append one row to make the finite world
3x4, preserving pieces/coordinates/typed rules and actual max_ply6. All four
source-world event prefixes replay legally; opening actions change4to5 and the
old terminal prefix is ongoing in the NEW game. WDL/player comparison is pending.
Use existing reference_minimax, at most150000nodes/90seconds, retaining every
incomplete result. Compare these matched prefixes explicitly; they are not the
new game's natural opening distribution. No extra seeds, training or default.

If blocked, examine a different single rule axis or the actual fixed-node versus
complete-tree price-region distinction using existing data. Name a concrete
hypothesis/consumer and decision-changing result before new computation. Do not
recreate retired audits, fill old missing fitness slots or duplicate AUX work.
