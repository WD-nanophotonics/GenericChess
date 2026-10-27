# One pure-Leaper quiet-ordering proposal — 2026-10-27

Status: SOURCE GO TO NECESSITY ASSESSMENT; implementation and every empirical
stage NOT_STARTED. This is a falsifiable development pilot, not a qualified
optimizer, product activation, independent holdout or class-wide success.
The completed USER570 source audit supplies candidate inputs only. It supplies
no unspent grant for this proposal. No Player/Core/solver/game/build was run.

## Decision and changed premise

The new autonomous reviews at sandbox21d9e068 (09:43 and10:18 JST), plus the
09:48 Slack autonomous comment1793062136.747249, request one new algorithm
variable with real quality endpoints instead of further provenance campaigns.
Adopt that direction. Stop historical source hunting, old root scans, PVS/child
refills and the deferred Native16 games. Those are not competing live tasks.
The ten existing exposed full rules permit a current prospective development
comparison even though historical full executable provenance remains UNKNOWN.
Unknown current resolution permits an exploratory test; it does not prove
saturation or justify claiming that random-opponent wins validate this feature.

Question: does moving geometrically unexposed quiet destinations earlier improve
actual equal-service-time Core outcomes against the same current search without
that preference, enough to justify later independently held-out validation?
A negative answer, no feature exposure, excessive overhead or all-draw outcome
closes this candidate; none authorizes more seeds, prefixes, caps or thresholds.

## Exactly one algorithm variable

Use executable semantic IR geometry and capture patterns, not the inspection-only
legacy handle. `ExecutableSemanticRuleset.__getattr__` exposes compatibility
metadata which need not describe semantic overrides. Existing compile-owned paths
and incoming indexes are infrastructure, not a claimed new invention.

For each full-width main-search ordering call, first obtain exactly the existing
MoveOrderer result. Eligible slots contain board actions onto empty squares,
no promotion, and neither TT action, current-depth killer nor active countermove.
Skip when fewer than two eligible actions. Build one boolean destination set from
CURRENT enemy pieces and applicable IR capture-pattern leap paths; match current
type, owner, source and geometry atom_source. Ignore destination occupancy for
this geometric feature: an empty destination may become occupied after the quiet
move. Stable-partition only the eligible subsequence: destinations outside the
set first, inside second, retaining baseline order within each group. Write it
back into exactly those original slots. Preserve action objects/multiplicity,
including semantic pattern/geometry identity, and every excluded action's index.
No second complete action sort, per-child transition or per-action Native probe.

This is a heuristic geometric exposure flag, not legal attack, a legal recapture,
SEE, check prediction or WDL truth. Pins and sacrifices are concrete failure
mechanisms. It does not prune or reject any action. Parent occupancy is explicitly
used, not a claim to model the post-move legal reply position.

The default orderer only structurally prioritizes TT. Capture/history priorities
are scalar and evaluator scale is unbounded; do not replace them with invented
structural buckets. Subsequence partition avoids changing other slots. History
may differ downstream because the tree order differs; its UPDATE RULE stays
identical, not its arm-specific values. Q ordering/configuration bypasses the new
feature, though changed main trees may naturally change later TT/history access.
Existing staged picker remains OFF in both arms. One opt-in OFF-by-default hook,
experiment-only selection; no general attack cache or fused Native kernel.

Admission is structural and fail-closed, once per compiled product, not repeated
schema validation at every node. Review the narrow existing
`_plain_leaper_hash_patterns` IR certificate as a possible shared predicate;
its transition-footprint result is not an attack certificate. Require leap-only
board capture/move patterns with explicit remove-from-game/move effects, no path,
state/slot/zone guards, custom effects, promotions, enabled drops, aux/triggers,
declarations, pass or special adjudication; own-anchor-safety invariant may remain
because this feature deliberately ignores legal pin constraints. Unknown schema
or unsupported pattern returns the exact baseline. Final predicate tests precede
runtime use. Actual search.py _Context constructs a fresh MoveOrderer per root query, not
per Player. Proposed explicit constructor input supplies compiled IR only when
the OFF-by-default switch is enabled. Precompute type/owner/source unions once
per search context, reuse within that query, and charge this build on EVERY
query plus occupied-source unions at main ordering calls. No uncharged global
cache or mutation of compiled IR; unchanged Q calls explicitly bypass feature.
Record build bytes/time separately inside the charged query.
No executable implementation or certificate was constructed in this source task.

## Fixed staged execution, only after USER approval

1. Implement only this hook and its strict admission. Necessary tests exercise
   semantic atom/type/owner matching, duplicate actions, pinned enemy geometry,
   sacrificial quiet ordering, excluded-slot preservation, unsupported-rule
   fallback, Q bypass and cancellation/state preservation. Include fixtures with
   both exposure groups (positive feature control) and all-equal flags (negative
   feature control). These are behavior controls, not positive WDL examples.
   No broad framework, new solver or learning task.
2. Reuse all ten complete root RuleSets/GameRecords in the pinned old packet,
   in world order0..9. Runtime compile/replay compatibility is still unverified;
   reject a failure, never repair clocks to get admission. Complete H128/repeat4,
   captured-piece disposition, initial state/history/side are unchanged. No old
   terminal is used as a counterfactual move label. No selective winning prefixes.
3. At each root run two OFF/ON fixed-D3 repetitions, balanced ABBA/BAAB by world:
   40 calls maximum, each3s/500k total main+Q nodes, Q4/hard8. Fresh Player/TT per
   call, disk OFF; all requested Native legality/availability/check ON and actual
   binary/fallback recorded. Both arms use identical explicit PVS ON, aspiration
   OFF, root tactical ON, staged OFF, local-hash/child/clock-cap flags OFF and
   identical DEFAULT evaluator/profile/TT parameters. PVS ON is this experimental
   reference, not the product default (which remains OFF). Source snapshots and
   resulting binary identity must be frozen before dispatch.
4. Gate: all40 calls complete D3, same paired completed root values, legal action
   and returned PV, unchanged query state and balanced runtime depth; any mismatch
   stops for causal diagnosis, never rewrite expected output to match a result.
   Tied actions may differ. Paired wall/CPU must include all real overhead; median
   and aggregate candidate/reference ratios each <=1.05. Ratio is overhead screen,
   not a strength result. At least3 rule families must actually reorder eligible
   slots; otherwise NO_EXPOSURE and stop, no new prefixes or extra calls. Missing
   slot, provider fallback or timer violation yields incomplete/NO_GO, not refill.
5. Only if all preceding gates pass: 20 near-baseline games, one OFF/ON color pair
   on each of ten roots; then4 weak-control games on world0 andworld5 (one old
   responsive family and one old nonresponsive family), ON versus uniform legal
   policy with both colors. World selection frozen here; old labels merely
   motivate controls and are not current truth. These4 only check playability;
   they never substitute for the20 similar-strength games. Each actor's TT is
   fresh per game, retained across its own moves, never shared across arms/games.
   Fixed seed202610271143 +10000*world +100*comparison +10*seat +actor;
   uniform samples complete legal action enumeration; do not add root tactics.
   No new stochastic seeds after observing results.

## Timing, output and inference

Per service call, start an outer wall/CPU timer before packing the full record
and before first-call Player/feature construction. One-second deadline is anchored
there; pass remaining positive time plus the original cooperative cancellation
deadline into choose_action. No remaining time means a recorded failure, not a
fresh second. Common rule compilation/replay and game setup are separately charged
and reported per arm/game and in total; they are not hidden inside an allegedly
all-inclusive choose timer. Whole service time ends after the returned decision
is packed. Persistence and PV verification follow and are separately charged in
whole experiment cost. This corrects the existing PVS driver's timer boundary,
which starts after to_record/provider metrics and excludes Player construction.

Limits per game query D64/500k total main+Q nodes/Q4 hard8 with1s whole service;
cooperative overshoot is possible. Preserve actual wall/CPU and all overshoots,
use >1.10s as timing-ineligible, never retrospectively call it exactly1s. Do not
idle uniform to consume1s. Compare resource ceilings AND actual costs distinctly.
Raw original returns precede interpretation. Store full initial and final records,
action traces, Core terminal reason/utility, root score/bound/source, completed
iteration/depth, fallback, main/Q nodes, TT work, Native operational/fallback
counts, ordering exposures/reorders, setup/featurebuild and outer wall/CPU.

Game batch is bounded3900s including setup, calls and recording, with reserve for
an in-flight call and20min whole-chain delivery. Maximum24*128=3072 turns; nominal
service ceiling3072s=51.2min, not a prediction of exact elapsed time. No automatic
extension. Natural Core checkmate/stalemate/repetition/max-ply outcomes are distinct
from caller cancellation, exception, NOT_STARTED, NOT_RUN and ONGOING. A truncated
game stays missing/censored, never DRAW. Fixed denominators20 near+4 controls;
report every slot and both colors, and all per-family W/D/L and timing exclusions.

Pilot continuation signal requires all20 near-baseline games qualified/terminal,
positive candidate net wins overall, positive net result in >=3 of10 families
and negative net result in <=1 family. This arbitrary operational screen is
frozen before data and not a confidence statement. Otherwise close as negative
or inconclusive, including all draws. Report controls separately regardless of
success. No class-wide strength or Elo claim from this dependent exposed panel.
Even a pass only motivates a separately budgeted, independently held-out rule
study; no such study is included or automatically queued here.

## Cost, authority and stop

Prior conservative related-chain carry550.8653386167min plus this actual window
from01:43:43.995UTC, excluding offline gap. Preparation/delivery are counted in
whole cost, not automatically in effective research. Future estimate170min:
70 implementation/necessary validation,15 fixed-call/admission work,65 bounded
game batch,20 analysis/delivery. Expected cumulative roughly735–755min depending
on this preparation, proposed hard cumulative cap770min. This is a conservative
forecast, not an extra170min entitlement after any cap. Stop at earliest scoped
stop, failed gate, exhausted stage reserve or770 cumulative; retain partials.

AGENTS requires direct USER necessity assessment for related expected>=120min.
The old570 review is CLOSED, not borrowed. Dot and Patrol cannot grant this run.
Until USER decides, no implementation or empirical stages start. The question is
whether this uncertain exploratory signal is worth the additional cost, not
whether old provenance can be made perfect. No AUX assignment/checkout/state,
worker, scheduler, fee, product-default or UI change.

The10:18 review reports an AUX pause in its external prompt, conflicting with the
latest trusted direct USER direction here (both existing roles ACTIVE hourly).
Record that source uncertainty; do not change another role or automation. This
proposal affects only PRIMARY. The matching09:43 review/Slack comment recognizes
the explicit dual ACTIVE state. Authority/provenance is not inferred from TYPE.

Source bindings and exact rule identities: [plan.json](data/leaper_quiet_attack_proposal_20261027/plan.json).
Current interpretation remains conditional on unperformed admission/cost tests.

## Dot consultation and source correction

Opening requestGC-SLACK-20261027-105145-93b4cfa4 sent01:51:59.422929UTC;
one delayed read started about01:57:30UTC, roughly31seconds after +5minute due.
Exact channel/thread originals preserved before assessment. Dot1793066169.602979
was already present (sent01:56:09UTC). Adopt its source-only conditional approval
and caveats; it independently read fixed56a19a5 source but ran no tests/queries.
Strict quiet transition leaves enemy sources/types/state unchanged, so unconditional
leap geometric coverage is parent/child invariant; legal reply constraints need
not be invariant. Owner paths are already oriented: use path[0], never rotate
again. Actual SemanticExecutor.attacked_squares filtering was read as reference.
This is not a new measured speed or quality result. No Dot grant is attributed.
Source inspection additionally corrected construction lifetime: orderer is fresh
in _Context each query, so planned geometry preprocessing is charged per query.
