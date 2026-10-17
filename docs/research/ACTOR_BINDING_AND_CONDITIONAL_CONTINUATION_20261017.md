# Native actor binding and conditional continuation — 2026-10-17

Science remains OPEN. PRIMARY_SANDBOX owns this tested sandbox backend change.
The separate DEV_AUX checkout, solver/verifier/cursor/learning programs and data
were not edited or executed. No new Agent, worker, fee or machine security change.

## Product correction: original actor references

The earlier research admission repair prompted a concrete further source audit.
`set_current_type` also resolved `action_base/action_current` against the affected
piece. Unlike the earlier victim filters, the existing production Core-equivalent
provider admitted it. Two max2 invariant witnesses produce **Core4/Native6** legal
actions and different dynamic3/control9 vectors. For both references Core3 is
`(1,0,0)`, Native3 `(3,0,0)`; Core9 is
`(35,-1,-1,-1,-1,-1,-1,-1,-28)`, Native9
`(33,-3,-3,6,6,-3,-3,-3,-30)`. A more basic probe has equal counts/vectors yet
different frontiers: vector equality alone was insufficient. Full original
canonical rules, Positions and observations are preserved in the capsule.

**Adopt:** use the already passed original `action_base_type/action_current_type`
in the three Native `resolve_type` call sites for move/shift, remove and
set_current_type. This matches Core's existing binding semantics, even when the
affected piece differs from the actor or an earlier effect changed a piece.
No Core rule semantics, result fields, payload layout, search/evaluator/default
policy, storage, history representation or UI changes. Existing conservative
provider exclusions for move/shift/remove stay; this is not admission widening.

The rebuilt kernel advertises `semantic_actor_relative_effect_binding=True`.
Python refuses affected compilation on kernels missing/denying this capability,
with an explicit rebuild/Core-execution error. Ordinary unaffected rules still
compile; the existing Core provider fallback remains available. Actual default
v4/256 transport is qualified here, not DEV_AUX's separately built v5 backend.
Rebuild Native from the complete revision before using affected rules.

Qualification:

- **2939 normal full active-layer tests pass**, with a real normal Native rebuild.
  Thirty new tests compare full frontiers, every legal child Position, dynamic3,
  control9 and unchanged parents across both owners/references, promoted actors,
  invariants, affected filters, and missing/false old-kernel capabilities.
- Private whole-source build: **2938 pass, one skip**. The skipped generated
  console executable is absent in the source copy; it is not a Native skip.
  Focused private checks: **105 pass**. The normal full suite includes that
  console check and passes all2939.
- The **same six original** specification cases now match their original Core
  frontiers/vectors and all22 legal child Positions. Two further actual
  GameSession one-edge transformation controls verify complete history digests,
  events, terminal result, board/base/current/hands/aux and unchanged parents.
- First harness assumptions conflated equal counts with equal frontiers; raw
  RuleSet serialization then encountered frozensets. Canonical serialization and
  explicit observations preserve these failures. The first private test run
  reached correct frontiers/vectors but failed28 child comparisons on list/tuple
  transport containers (77 passed); existing lossless `record_value` comparison
  fixes the harness. No semantic fields or original observations were discarded.

The normal kernel SHA256 is
`9b6127f1dfdeaf8d0ed8b55e999ae3112049c71ee77368fc53f732101355cf64`.
The old binary is retained privately, not published. All normal source changes
were made **after** the frozen continuation producer closed; its source tier is
PUBLIC46293226dfa3da33430f0b27869a34aa915d7f83. Its generated rules contain none
of the affected actor-relative effects. A corrected-source replay is separately
qualified, not a relabelling of old execution or wall-clock evidence.

## Completed conditional continuation study

After the earlier one-ply filter delivery, a separate protocol declared eight new
family seeds across4/8/12/16 boards, both generator flags, and two fixed joint
policies: uniform repr-sorted semantic bindings, or existing Core AlphaBeta on
both sides. All16 generation invocations retain max32 attempts. All32 game slots
ran. The AlphaBeta limits are2s,1M total nodes,D12,q0/hard0, TT10k per player,
ordering on, no disk cache; default rule-derived profiles, no learned model.
Full promotion/drop/current/base/hands/aux and actual histories are retained.

| Flag | Joint policy | Actual terminal | 64-ply UNKNOWN | Terminal by ply1 | Terminal by ply32 | Mean observed min-length |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Off | Uniform | 1/8 | 7/8 | 0/8 | 0/8 | 62.125 |
| On | Uniform | 1/8 | 7/8 | 0/8 | 0/8 | 61.000 |
| Off | AlphaBeta | 4/8 | 4/8 | 2/8 | 4/8 | 39.125 |
| On | AlphaBeta | 4/8 | 4/8 | 0/8 | 3/8 | 46.375 |

Only the two four-board rule pairs changed; the other six pairs have identical
serialized rules. All six identical-rule uniform-policy record prefixes match.
These are eight correlated families, not32 independent samples. Wall-clock
AlphaBeta controls need not choose identical trajectories even on identical
rules; their actual depth/work is retained. No Elo, WDL, learned value or intrinsic
quality conclusion follows. Keep the optional preference **default False**;
do not add a stronger filter from these sparse conditional results.

Actual totals: **1669 physical edges, 684 search calls, 10 actual terminal games,
22 administrative UNKNOWN, zero errors, zero research fits**. Eight verified
root-child wins report completed_depth0; they are not completed D1 claims.
The other676 calls stop on time. Requested Native legality yields396700 actual
calls, zero fallback/operational failures in this cohort. Observed choose_action
latency reaches2.645s for a requested cooperative2s budget; it excludes external
root enumeration/submission. Whole1381.308s includes setup/recording and stays
below the frozen40min cap. Profiles cost1.145s total. Concurrent qualification
load is an interpretation limit, not evidence of a specific overrun cause.

Search-disabled frozen-source replay checks **2269 full Native/Core states,
1669 physical edges, 568 legal PV edges, 213 stored full snapshots and all684
decision receipts**. It does not re-search, reproduce clocks, authenticate old
internal future states, or prove independent optimal minimax truth. Administrative
caps are not DRAW. Earlier zero-game claims belong to the earlier interface
study; these32 trajectories are a separately declared later phase.

## Sampling measure and the actually begun next question

All16 new initial roots have zero total variation between uniform bindings and
uniform complete successor-Position/terminal observation groups. This is local:
three older count-discrepancy witnesses have equal observable frontiers but
semantic binding multiplicities5/10,120/126,96/102. The latter two induce TV
0.045238/0.055147. Complete action histories remain distinct and preserved;
there is **no** general state/action quotient or linear actor-conservation claim.

All32 declared actual ply8 slots were then inspected:30 prefixes exist, two
already ended. Six correlated slots have nonzero TV, up to19/780 (0.024359), from
4728 complete one-ply transitions. No sampler or frozen outcome was changed.
A next bounded question was actually executed on these six slots/three distinct
full parents: does the measure change even a cheap baseline statistic? Using
the same frozen normalized board-current/hand-base material component, the exact
binding-minus-observation-group mean child-minus-parent differences are
`96013/1560`, `-1655/2652`, `-8687/12224` in the existing profile's units (median
ordinary unit1000). This uses281 actual representative children, with full-state
hash checks and multiplicities retained. It is not a price fit, full evaluator,
clipped score, terminal utility or true-return estimate. Future rule-only averages
must name their distribution; count differences alone neither refute static
values nor establish a unique generic price.

## Primary literature and interpretation

Compilation properties and agent-dependent playout metrics are distinguished in
[General Board Game Concepts, IV-C](https://arxiv.org/html/2107.01078).
The author-uploaded [Evolutionary Game Design preprint](https://www.researchgate.net/publication/224111054_Evolutionary_Game_Design)
uses study-specific duration/decisive-completion preferences and human-ranking
calibration. We adopt the distinctions, not its preferred60 moves, human weights
or treatment of draws. Selected sections were read, not its entire final edition;
[publication metadata](https://cris.maastrichtuniversity.nl/en/publications/evolutionary-game-design/)
was checked separately. Two failed source URLs are recorded; no access control
was bypassed. No paper full text or human labels enter this project capsule.

[Data](data/actor_binding_continuation_20261017.json) and the two-tier
[source/evidence capsule](../archive/actor_binding_continuation_20261017_public_v2/README.md)
retain declared protocols, failures, original observations, complete rules/records,
all finite decisions, exact means, current source and frozen-source distinctions.
The generic scientific objective remains OPEN; no AUX program was executed.

Current relative archive links use the separately versioned personal-path-corrected publication copies. Historical source hashes/counts above retain their original execution tier; the new manifests identify only personal-directory substitutions. See [publication-copy qualification](PUBLICATION_COPIES_AND_SIGNED_PRICE_SERVING_20261017.md). Old Git history has not been purged.
