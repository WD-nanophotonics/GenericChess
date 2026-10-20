# Generated semantic-action and auxiliary-state generator coverage — 2026-10-21

## Question and result

Can the project's native stochastic game generator emit generated rules that
combine legacy movement with semantic actions and auxiliary state? No. The
current `GeneratorConfig` / `generate_game` path only emits the legacy
movement-atom, setup, promotion-mask, and drop-mask substrate. Adding seeds to
that path cannot introduce semantic actions or auxiliary slots.

This is a generator-support gap, not evidence of a transition, search, or
evaluation bug. It limits claims about the sampled rule population: legacy
generated studies are scoped to that generator's current support and do not
cover the complete generated semantic domain in the stated research target.

## Source-backed coverage

| Layer | Existing support | Coverage consequence |
|---|---|---|
| Configuration | `generic_chess/generation/config.py::GeneratorConfig` samples board size, setup, movement symmetry/atoms, promotion/drop-related requirements, and opening preferences. There are no semantic-template, action, auxiliary-slot, or DSL-profile fields. | No configured semantic generation distribution exists. |
| Producer | `generic_chess/generation/generator.py::_try_generate` creates the piece types, derives promotion/drop masks, constructs `RuleSet`, and calls the legacy `compile_ruleset`. It does not populate `RuleSet.semantic_actions`. | Produced rules retain the schema's empty semantic-action default. The legacy compiler deliberately refuses nonempty semantic actions rather than silently ignoring them. |
| Semantic schema | `RuleSet` can store `semantic_actions`; `RuleSemanticAction` has geometry, composition, guards, auxiliary declarations, effects, invariants, promotion mode, triggers, and other typed fields. The schema bounds effects at four and auxiliary slots at eight; auxiliary values/scopes/lifetimes are typed. | The representational/compiler layer is richer than the stochastic producer. A generator must sample mutually coherent typed structures and preserve slot references. |
| Filters | `generation/filters.py` can evaluate a `CompiledSemanticRuleset`; `tests/product/test_generation_semantic_opening_filter.py` constructs a semantic ruleset by hand, compiles it, and tests the filter. | This proves filter compatibility for a hand-built semantic fixture, not a semantic output path from `generate_game`. |
| Other semantic examples | Game definitions such as `generic_chess/learning/shogi_semantic_rules.py` construct fixed actions and replace/augment a ruleset. Research preparation scripts also manually compose actions into legacy generated bases. | These are authored or manually augmented examples, not a stochastic generic grammar. |

The prior finite symmetry screen provides corroboration, not a new experiment:
its eight generated legacy profiles had zero semantic board/drop actions and
zero nonempty auxiliary states. Its own report correctly warns that the screen
does not cover the complete semantic domain.

## Smallest defensible missing capability

The smallest useful addition is an **opt-in typed semantic-template profile**
over the existing legacy generated substrate, not an unrestricted mutator over
all possible rule trees:

1. Define a versioned catalogue/grammar of semantic action templates with typed
   parameters that bind to each generated board and available piece types.
2. Let the seeded local RNG select templates and any declared auxiliary slots;
   construct guards/effects/triggers from the same slot bindings so every
   reference is well-formed.
3. When the profile is absent, preserve the current generator and all seeded
   legacy outputs. When enabled, compile through the product execution boundary
   `compile_ruleset_for_execution` (which invokes semantic compilation without
   dropping into the legacy executor), then run semantic-aware validation and
   filters.
4. Record the grammar/profile version and per-family inclusion counts in the
   generation report. State the supported template families and sampling
   weights; do not call a finite subset the complete DSL.
5. Return semantic compiled games through an explicit result type/path instead
   of widening `GeneratedGame.compiled_ruleset` in place: that field and several
   existing consumers are statically legacy-typed. Qualify the intended
   `GameSession`/search consumer before broadening public annotations.
6. Add contract tests for deterministic reproduction, serialization/fingerprint
   stability, legacy-default identity, semantic-only and mixed outputs,
   auxiliary-slot reference validity, and fail-closed rejection of invalid
   templates.

This preserves a coherent support definition while making representational
coverage observable. A general sampler spanning every legal combination in the
DSL would first need an explicit grammar and probability measure; universal
description-language expressivity alone does not provide either. Ludii's
description system is organized around high-level ludemes and emphasizes
generality and extensibility; that is a useful design analogy, not evidence for
any particular GenericChess grammar or distribution ([Piette et al., 2019](https://arxiv.org/abs/1905.05013)).
Likewise, the universality result for Ludii concerns what can be represented,
not what a practical random generator should sample ([Soemers et al., 2022](https://arxiv.org/abs/2205.00451)).

## One-template feasibility screen

To distinguish a missing producer from a compiler/search impossibility, a
fixed eight-seed screen reused each generated non-promotable piece's own legacy
leap/ray family in one semantic `augment` action. The action performed the same
empty-target move plus a guarded persistent global-bool write. The seed set was
202610401–202610408 on 6x6 classic-like bases; no bases were removed, and no
search, games, outcomes, prices, or training were run.

On the corrected product execution boundary, all eight semantic rulesets
compiled and passed the existing filters. Each root exposed 1–6 candidate
semantic actions (counts `3,2,2,4,1,4,6,2`); submitting one legal candidate in
each session changed auxiliary state and produced one recorded history action.
This establishes that a generic schema-level template can create a legal
mixed legacy/semantic action with persistent state on these eight roots. It is
not evidence of utility, broad representativeness, general template coverage,
or full-domain generation.

The first harness attempt is preserved in
`result-attempt-01-harness-failure.json`: it passed the lower-level
`CompiledSemanticRuleset` directly to `run_soft_filters`, producing the same
missing-`piece_types` attribute error on every seed before action counting.
Source tracing showed product tests and filters use
`compile_ruleset_for_execution`, whose `ExecutableSemanticRuleset` adapter
retains the semantic compiled object while exposing its legacy geometry
metadata. The producer was corrected to use that existing boundary; seeds,
template, outputs, and decision rule were unchanged. This was a harness
contract error, not a changed expected value or a failed semantic transition.
The original attempt and correction record remain alongside the successful
`result.json`.

## Output-contract boundary

There is one additional integration surface. `GeneratedGame.compiled_ruleset`
is annotated as the legacy `CompiledRuleSet`, while `compile_semantic_ruleset`
returns the distinct `CompiledSemanticRuleset` type. `GameSession` and
`AlphaBetaPlayer` also retain legacy-only annotations in their public
constructors/properties, and generated results feed benchmark, CLI, learning,
demo, and UI consumers. This static type mismatch is not proof of runtime
incompatibility: the existing semantic-only `AlphaBetaPlayer` test demonstrates
that an explicit evaluator can execute a semantic compiled ruleset. It does
mean that returning this second compiled type through the existing
`GeneratedGame` field would silently widen its contract and should not be the
first integration step. A bounded prototype should expose an explicit semantic
generated-result type/path and audit the intended `GameSession`/search consumer,
leaving the current `generate_game` result type and callers unchanged until that
consumer is qualified.

## Orthogonal rule-history and executor coverage

The action-template screen does not measure the generated rule-history domain.
An AST/dataclass comparison of the producer and schemas found that none of the
nine ruleset-level history/terminal fields is configurable in `GeneratorConfig`.
`_try_generate` explicitly fixes `repetition_limit=4`, `max_ply=512`, and
`stalemate_result="draw"`; the other history fields inherit their schema
defaults (`repetition_policy="draw"`, no automatic or consecutive
adjudications, pass disabled, no repeated-cycle conditions, and no no-progress
draw). These are independent from semantic action templates and can affect
terminal outcomes and search histories, so seed expansion over current
`GeneratorConfig` cannot sample them.

The fixed-seed probe in
`data/semantic_generator_template_preflight_20261021/history_profile_probe.py`
held the persistent-bool action fixed and varied one history policy at a time.
All six variants compiled through `compile_ruleset_for_execution`, retained
their changed schema fingerprints and the expected Core support fields. In this
sample, repetition limit/policy and `max_ply` remained Native-capable;
automatic-ply adjudication, pass-class adjudication, repeated-cycle targeting,
and no-progress draw were Core-executable but marked Native-incompatible. A
first-ply automatic-adjudication transition through `GameSession` still
submitted the semantic action, changed its auxiliary slot, appended one history
record, and returned `NO_CONTEST`; this checks one Core composition, not the
correctness of every history policy or all executor combinations. Machine
readable output is in
`data/semantic_generator_template_preflight_20261021/history_profile_probe.json`.
No test expectation or product code changed.

This separates three coverage axes that must stay explicit in any future
profile report:

| Axis | Current evidence | Limit for the first profile |
| --- | --- | --- |
| Semantic action grammar | One augmenting legacy-motion move with empty target, persistent global bool, false slot guard, move+set effect, and own-anchor invariant passed on 8/8 roots. | Does not cover explicit leap/ray/drop geometry, replace-legacy, other guards/effects, square-or-none/per-owner/turn-lifetime slots, triggers, promotion modes, path/zone guards, or postconditions. |
| Ruleset history | Current generator covers one fixed stratum; probe compiles a fixed semantic action with six one-at-a-time policy variants. | A future distribution must explicitly pin or sample each supported family and report that choice; do not hide a fixed history stratum behind a broad generic claim. |
| Executor | Sampled simple action and three history variants are Native-capable; all seven configurations are Core-executable. | Four tested history variants require Core in this sample. Label per-result capability and route accordingly; do not infer all-template Native coverage from one rule. |

The immediate implementation decision is therefore not “enable all semantic
generation”. First identify a concrete unfamiliar-rule search or price
comparison, select only the action-family and history-policy support that its
hypothesis needs, and state the execution backend. Keep a versioned,
distribution-labelled opt-in profile over the full existing legacy substrate;
the finite catalogue is a scoped experimental distribution, not a replacement
definition of the complete generated-rule target. A future cross-family profile
must retain promotion, drops, auxiliary state and history rather than silently
freezing them out.

## Existing AlphaBeta consumer: search acceptance versus semantic pricing

A fixed-seed mixed legacy+semantic root also passed through the existing public
`AlphaBetaPlayer` without an evaluator override: its built-in profile constructed,
depth-1 search completed, and the returned action was legal among 3 generated
semantic candidates. This establishes a usable bounded search consumer without
changing `GeneratedGame` or AlphaBeta's constructor. It does **not** establish a
semantic price model. The base and mixed rulesets had different fingerprints,
but their static piece, board, hand, and promotion profile values were identical
because the tested action has a slot guard and `set_bool` effect. Source audit
confirms `profile_movement_atoms` intentionally excludes guarded and selected
state-writing patterns, falling back to legacy atoms when present. Dynamic
evaluation also uses Core attack maps; this probe did not test full score
equivalence or claim that those dynamic terms ignore semantic execution.

Therefore the default AlphaBeta path is a valid smoke target for mixed-action
legality/search integration, but not a valid measurement of the value of this
stateful semantic action. A price/utility comparison needs a separately declared
evaluator that models the action's relevant state/effects, or must narrow its
claim to search execution/cost. This is a documented evaluator scope limit, not
a newly demonstrated product defect and not a reason to widen the default
profile.

## Decision and limits

- Keep current generated-rule findings explicitly scoped to the legacy producer.
- Do not widen seed ranges to address absent mechanisms; do not infer semantic
  coverage from manually authored fixtures or post-generation injections.
- Carry forward an opt-in semantic-template profile as the smallest feasible
  generator extension. Do not change defaults or implement a broad grammar in
  this audit: first define the exact template support and distribution required
  by a decision-changing unfamiliar-rule search or price comparison.
- The tested movement-plus-persistent-bool template is a feasible first scoped
  profile element; its eight-root exposure is a construction check only.
- No product code changed. This does not claim all-domain generation, all-DSL
  search support, or utility of any semantic price model.

## Direct geometry: static price projection versus opening exposure

Two separate fresh-seed screens distinguish whether a geometry can be projected
from whether it contributes an action in the initial position. On seeds
202610421–202610428, one unguarded direct leap (offset (1,2), empty target,
move effect) was legal on all 8 roots; its geometry entered the static profile
on all 8, with a nonzero board-value change on 6. On seeds 202610431–202610438,
the preregistered owner-relative direct ray (direction (1,0), steps 1..3,
empty target) entered the profile and changed board value on all 8 roots, but
contributed zero opening actions on all 8.

The bounded follow-up traced compiled owner-relative paths: every selected
source's first ray square was occupied by a friendly unit in those frozen
initial setups. The existing `opening_legal_moves_in_range` filter passed on
each root because it counts all legal opening moves (8–25 here), not the
contribution of each semantic pattern. This matches its contract; it is not a
filter defect. A direction census over every absent direct-ray direction for
every eligible present type on the same roots found 51/127 type-direction pairs
with at least one initial semantic candidate, and all 8 roots had at least one
such pair. Candidate pairs occurred only in the opener's forward relative
directions `(0,1)`, `(1,1)` and `(-1,1)` (17 pairs each); this is an initial
setup/side-to-move observation, not an action-balance result.

The static movement profile is intentionally a potential-geometry projection:
it unions supported direct move geometries without occupancy, invariant,
frequency or path-state realization. Therefore profile sensitivity alone can
price a geometry with no legal opening action in the sampled position. Treat
the direct leap/ray evidence as scoped construction and profile-sensitivity
checks, not calibrated values or utility. If a future opt-in generator needs
opening exposure, its template/setup sampling must test semantic candidate
contribution explicitly; do not change current soft-filter semantics or
defaults on this screen. Reproducible scripts, plans, result JSON and harness
attempt receipts are in
`data/semantic_generator_template_preflight_20261021/`.

## Effect on the production evaluator's material term

Source tracing confirms `Evaluator.evaluate` always scores board pieces from
`profile.board_value_by_type`; when enabled, dynamic mobility and anchor terms
are added separately from current-state attack maps. To check whether the
blocked ray's profile effect was merely a report field, the same eight roots
were scored with the default production evaluator on legacy and ray arms and
each component was independently reconciled against `evaluate`.

The ray changed the selected type's raw capability on all 8 roots and its
normalized board price on all 8. Because normalization uses the median raw
capability across the non-anchor roster, other types' prices also moved; this is
the specified relative normalization behavior. On the symmetric initial
positions, each owner's material subtotal shifted identically (aggregate
−5148 for each side across the eight roots), so the side-to-move score delta
was 0 on all 8; dynamic mobility, anchor/check and promotion terms also had
zero delta. Thus the static price is consumed by the live evaluator even though
the sampled symmetric root score cancels. This does not estimate an asymmetric
position's score delta or establish whether the price shift is useful. The
reconciled component data and recorded harness attempts are in
`data/semantic_generator_template_preflight_20261021/ray_root_evaluation.py`,
`ray_root_evaluation_result.json`, and `ray_root_evaluation_attempts.json`.

## Capability-feature attribution

The raw capability increase was reconciled to its declared formula on all eight
roots. Summed across roots, the default weighted expected-mobility curve
contributed +10.7437 of +10.7691 total raw capability; coverage contributed
zero, reachability +0.0129 on one root, and path efficiency +0.0126. These are
empty-board graph/profile features, which explains how a ray can affect nominal
price while its path is blocked in the starting arrangement. It also shows the
price shift here is almost entirely a mobility-density term, not new board
coverage. Exact per-root feature contributions are in
`data/semantic_generator_template_preflight_20261021/ray_capability_decomposition_result.json`;
the probe and plan are adjacent. This remains model-mechanism attribution, not
calibration or utility evidence.

## Bounded-ray range sensitivity

With roots and selected types frozen, varying only `max_steps` from 1 to 3
left the horizontal ray with zero initial legal candidates on all 8 roots at
every range. Raw capability and normalized selected-type value were
non-decreasing in 8/8 roots. Some roots plateaued between lengths 1 and 2 or
across all lengths because the added geometric destinations were already
represented by other movement atoms; the longer range was not always a new
behavioral opportunity. This supports retaining explicit ray bounds in a
priceable template representation, but it does not justify linear scaling or
a value law. Full-precision values and per-type profile changes are generated
by `ray_range_sensitivity.py`; the fixed design and rounded summary are in the
adjacent plan and `ray_range_sensitivity_result.json`.

A geometry-edge follow-up on the two plateau roots confirms why: each raw-score
plateau has zero additional owner-relative source-target edges. Seed 202610432
adds 60 edges at range 1, none at range 2, then 36 at range 3; seed 202610435
adds 60 at range 1 and none at ranges 2 or 3 because its legacy atom union
already overlaps those extra destinations. This is evidence that distinct
schema atoms can encode the same finite-board movement opportunities; neither
atom identity nor a larger `max_steps` guarantees a marginal capability change.
The exact all-source/both-owner edge counts are in
`ray_plateau_overlap_result.json` and can be regenerated with the adjacent
probe and plan.

## Joint graph novelty, static price, and root exposure

The complete fixed universe of 127 absent type-direction pairs was then
measured on the same eight roots. Every pair added at least one owner-relative
empty-board movement edge, increased that type's raw capability, and increased
its normalized board price (deltas 56–914). Only 51/127 had an initial legal
semantic action; the remaining 76 still received a positive static price
change because those price features describe potential geometry, while their
opening paths were blocked or unavailable to the opener. The change also
redistributed other types' normalized values: 303 of 508 non-selected type
entries fell, 205 stayed equal, and none rose. These results combine graph
novelty, profile response and finite root exposure without conflating them;
they do not establish good calibration or utility. The raw exact run is
preserved under ignored `.local_agent/research_raw/`; its SHA-256 and the compact
per-direction summary are in
`data/semantic_generator_template_preflight_20261021/ray_pair_novelty_price_result.json`.

### Selected-price change: raw capability versus roster-median shift

To determine how much of the selected-type price response is due to the new
geometry versus renormalization, the exact same 8 roots and 127 absent-ray
pairs were decomposed using the production formula. The raw-only component holds
the baseline roster median fixed while substituting the ray-arm selected-type
raw capability; the residual is the median-shift component. Base profiles use
the currently reachable ordinary-type set, while semantic profiles use all
declared ordinary types, matching `_initially_reachable_type_ids` and
`build_ruleset_profile`.

Across equal-weight pairs, the raw-only component sums to +49,864 board-value
units; the median shift contributes −16,444, leaving the observed normalized
selected-type change +33,420. The roster median therefore attenuated 32.98% of
the aggregate fixed-median response. It attenuated 101/127 pairs, left 26
unchanged, and amplified none; rowwise actual/raw-only ratios ranged from
0.349 to 1.0. This is an exact algebraic attribution for the frozen sample, not
a calibrated alternative evaluator: summing pairs weights eligible
type-direction pairs equally, and no utility/outcomes/search/training were
measured. It explains the scale of roster coupling; it does not show whether
the resulting values are better. The script, plan and compact result are in
`data/semantic_generator_template_preflight_20261021/ray_median_attribution*`;
the exact original and identical repeat are privately retained in ignored
`.local_agent/research_raw/`.

The ordinary normalization roster was also checked directly: all eight base
roots use the same reachable non-anchor set `{A,B,P,X}` as the semantic
profiles' declared non-anchor set, so no type-membership change contributed in
this sample. The median raw capability increased in 29/41 A additions, 32/38 B
additions, and 40/48 X additions; it never decreased. All 303 negative
non-selected price entries occurred when the selected pair's median-shift
component was negative; there were no positive non-selected changes. The 205
zero entries include the fixed anchor and rounding plateaus. This ties the
relative-price redistribution to the moving denominator rather than to a
change in which ordinary types were normalized.

Stratifying those same pairs by the already-recorded initial-action flag gives
attenuation fractions 29.51% for exposed pairs (51 pairs) and 35.07% for pairs
with no initial candidate (76 pairs). This modest descriptive difference is
not an independent exposure/utility test and does not turn static price into
an opening-action proxy. The compact summary is in
`ray_median_attribution_result.json`.

### One-ply legal-action availability

The same 127 pair/seed combinations were followed through every legal root
action (2,186 transitions total). Among the 76 pairs with zero matching root
actions, 1,266 root actions produced 1,166 nonterminal reply states and 100
terminal states. None of those 1,166 live reply states exposed a legal action
for that same ray/type pair. Thus a one-ply reply-action screen did not change
the inclusion set on this frozen sample: 51 pairs were initially exposed and
76 remained unexposed. This is a finite one-step legality result, not a
probability of play, deeper reachability, outcome, search or utility estimate;
later plies and other setups remain untested. Exact root candidate counts
matched the earlier 127-pair capture, and an identical repeat reproduced the
full result. The plan, script and compact summary are in
`data/semantic_generator_template_preflight_20261021/ray_one_ply_exposure*`;
raw captures are retained in ignored `.local_agent/research_raw/`.

### Setup-layout sensitivity with rule genomes held fixed

To test whether that exposure pattern was unique to `classic_like`, the exact
same eight generated movement genomes and 127 ray templates were compiled over
accepted `bilateral_random` and `free_random` starting layouts. Layout
acceptance used the existing legacy anchor-safety and opening-move bounds and
did not inspect ray candidates: all 16 alternate layouts were accepted, with
nine deterministic anchor-attacked rejections before one bilateral layout was
accepted on its tenth attempt. No opening-count rejections occurred.

The root action direction support was unchanged across all three setup
families: candidates appeared only for owner-relative forward rays `(0,1)`,
`(1,1)` and `(-1,1)`; horizontal and backward rays had no candidates. The
bilateral layouts exposed 42/127 pairs because 24 template rows had no piece of
the selected type on board (8 A rows and 16 X rows); among the 103 present-type
rows, 42 were exposed. Classic-like and free-random each exposed 51/127, with
all selected types present. The three implemented presets all keep each side
within the outer two ranks, so this does not test broader placement domains.
It suggests that switching among current presets alone will not add new
direction support for root-exposure filtering; a future screen needing a
wider action spectrum must consider new setup structures, while retaining
type-presence and exposure as separate fields. This is not utility evidence or
a reason to change generator defaults. Full results and limitations are in
`data/semantic_generator_template_preflight_20261021/ray_setup_sensitivity*`;
exact repeated captures are privately saved in ignored `.local_agent`.

### Three-rank setup feasibility

To distinguish the current presets' two-rank structure from a general rule
limitation, a deterministic synthetic fixture placed the same generated
genomes' 24 pieces over the three ranks on each side (12 rotationally paired
slots per owner), included all four ordinary types, and retained the 180-degree
owner symmetry. Layouts were accepted only by legacy anchor-safety and opening
move bounds; no candidate-ray count was used for selection. All 8 roots passed,
with 8 rejected candidates due to legacy anchor attacks and none due to opening
move count. The semantic ray variants produced no initial check for either
owner in any of the 127 measured rows.

This changed root exposure from 51/127 in `classic_like` and `free_random`
(42/127 in `bilateral_random`) to 88/127. Unlike every current preset, the
three-rank fixture produced legal root ray candidates in all eight directions:
6–15 pairs per direction. This supports setup placement as an independent
coverage dimension for a future opt-in semantic generator; it does not establish
that these layouts are in a desired population, are strategically useful, or
justify changing defaults. It is a synthetic feasibility screen, not full
joint-generator output. Plan, script and result are in
`data/semantic_generator_template_preflight_20261021/ray_spread_setup*`; the
exact deterministic capture is in ignored `.local_agent/research_raw/`.

On the exact paired 127 rows, the spread fixture gained legal exposure for 47
previously unexposed pairs while losing it for 10 previously exposed pairs; 41
were exposed in both and 29 in neither. Thus the net +37 is a redistribution of
which ray/type pairs are available, not universal improvement. The direction
comparison is informative: of 30 previously unexposed horizontal pairs, 27
became exposed and 3 remained unavailable; backward
vertical gained 8/18, and the two backward diagonals gained 12/28. Six
forward-direction pairs lost exposure, so even the wider fixture is not a
superset. A future setup catalogue should preserve paired direction/type
coverage and report transitions, rather than select one layout by its raw
exposure count.

### Serialized-rule public search consumer — 2026-10-21

The concrete API consumer is the existing `benchmark_alphabeta --ruleset`
entrypoint: it deserializes a full `RuleSet`, compiles it for execution, then
constructs the ordinary public `AlphaBetaPlayer`. `GeneratorConfig`, by
contrast, only emits the three existing setup presets and the legacy atom
generator; the serialized `RuleSet` input is the supported way to supply an
authored setup plus semantic action for this probe.

One fixed 6x6 seed/layout (`202610431`, accepted spread-layout attempt 0) added
one X horizontal ray (`(1,0)`, max step 3). JSON round-trip and fingerprint
matched; the imported root had 18 legal actions, including two matching ray
actions. With the public player at D1/q0 and root tactical scan disabled, it
returned a legal legacy-action PV, left session state/history unchanged, and
reported 19 nodes: one root plus one child node for each of 18 legal actions.
The actual `benchmark_alphabeta --ruleset` CLI also completed D1 at its fixed
64-node budget (37 nodes, 18 qnodes) and returned a legal legacy action. Thus
the search/import boundary can execute this authored unfamiliar rule; neither
search selected the ray action, which is not evidence about its utility. No
game, outcome, strength, or price claim follows.

The first probe-harness attempt failed before measurement because it accessed
a nonexistent `RuleSet.fingerprint` convenience attribute; the harness now
uses canonical `compute_fingerprint`, with no fixture or expectation change.
Exact attempt and bounded result are in `ray_imported_search_probe_attempts.json`
and `ray_imported_search_probe_result.json`; two focused existing CLI/search
test files pass 56 tests. This closes the integration-smoke question only. It
does not justify a new `GeneratorConfig` option or default: automatic semantic
generation still lacks a concrete target population/consumer requirement.

The bounded current-entrypoint inventory found the same separation elsewhere:
`cli.play`, `cli.replay`, `ai.cli.analyze_ruleset` and
`ai.cli.benchmark_alphabeta` each accept serialized `RuleSet` input, while
`scripts/unfamiliar_search.py --rules` takes an authored declaration and its
generated-cohort path uses four fixed `(board_size in {4,6}, seed in {7,21})`
`bilateral_random` legacy-atom configs. No inspected public/search caller asks
`generate_game` to synthesize semantic actions or a new setup family. This is
not proof that no future caller will need that; it means automatic synthesis
has no current concrete consumer in the inspected surfaces. Reconsider only
against a named target caller with a required sampled mechanism/setup family.
