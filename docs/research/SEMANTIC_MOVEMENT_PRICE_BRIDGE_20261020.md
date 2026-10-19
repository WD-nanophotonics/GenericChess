# Semantic movement geometry and rule-only price inputs — 2026-10-20

## Decision question

Can the existing static movement-capability analysis consume canonical semantic
move geometry without changing prices for canonical types whose semantic
geometry already matches their legacy movement atoms? This is a price-input and
search-evaluation question, not evidence that a proposed value improves game
outcomes.

## Observed current boundary

`ExecutableSemanticRuleset` exposes legacy metadata as an inspection
compatibility view. That does not synthesize atoms for semantic-only moves;
`execution.py` explicitly warns that static evaluators may omit those moves.
`build_ruleset_profile` nevertheless accepts that metadata and analyzes its
movement atoms. On the canonical Western rules, pawn `P` has no legacy atoms,
but six IR patterns describe one-step, guarded double-step, two captures and
two guarded/auxiliary en-passant cases. The current default profile reports
`raw_capability_score=0`, board value `1`, hand value `1`. Its other non-anchor
board values are N=775, B=1000, R=1462 and Q=2439. Thus the supported default
search path does not fail loudly; its rule-derived price input silently sees no
pawn movement.

## Bounded canonical geometry census

For each non-anchor piece, the read-only census unioned geometries of IR
patterns containing a direct `move(source,target)` and compared normalized
leap/ray signatures with the declarative legacy atom set. It did not interpret
guards, occupancy, effects, action frequencies or historical state.

| Rule family | Non-anchor types | Exact geometry-set matches | Exceptions |
|---|---:|---:|---|
| Standard Shogi | 13 | 13 | none |
| Western Chess | 5 | 4 | P: 0 legacy atoms, 4 direct semantic geometries |
| Xiangqi diagnostic | 6 | 6 | none |

All 23 matching types therefore retain the existing geometry input exactly in
this finite canonical census. Western P's semantic patterns also include
guards and auxiliary effects. The two en-passant geometries duplicate ordinary
capture leaps; the guarded double step contributes the additional fourth
geometry. That distinction matters for a static potential-mobility feature.

## Candidate sensitivity, not a selected price

Reusing the current atom-only capability formula on a geometry projection gives
P raw capability 2.24518 when limited to its unguarded one-step and capture
geometries, or 2.77259 when the guarded double-step is included. Under the
unchanged median/scale normalization these become 361 and 446, respectively,
versus the current value 1. This is a sensitivity range from two projection
definitions, not an estimate of WDL, material exchange value, human price or a
recommended default. The feature ignores conditional availability and
auxiliary-state frequencies, just as the existing geometry-only analyzer
ignores board-state frequencies; that shared approximation does not establish
that either projection is useful.

## Controlled search sensitivity and cache boundary

The prototype changes the existing profile inputs, so it must not reuse a
persisted profile built under the previous algorithm. The profile disk key
contains `config_hash`, which includes `EvaluationConfig.evaluator_version`;
the default was advanced from `generic-v2` to `generic-v3`. A regression seeds
the exact old Western profile path with P board/hand values of 1 and confirms a
new default-cache lookup misses and rebuilds the semantic profile. This is
cache correctness, not evidence for the price choice.

The first three-root diagnostic is superseded: its hand-edited P=1 profile
changed the board/hand maps but retained the candidate's promotion-gain field,
so it was not an exact generic-v2 comparator. Its score/node outputs are
historical setup evidence and are not used in the current result. The later
12-root panel reconstructs generic-v2 through the original declared movement
atoms, including the corresponding promotion fields.

To check that sensitivity was not confined to those three roots, a separate
deterministic panel sampled twelve 12-ply legal prefixes using sorted legal
actions and `random.Random(seed)` for seeds 101–112. The identical saved
prefixes were searched by both profiles at depth 2, q0, with TT, move ordering
and root-tactical scan disabled and a 3000-total-node cap. All 24 searches
completed depth 2; the selected root action differed on 3/12 pairs. Exact
per-root output is in
[`data/semantic_pawn_decision_20261020.json`](data/semantic_pawn_decision_20261020.json).
These roots are a small deterministic sample, not a holdout or outcome test.
The first recorder tried to read a legacy `captured_type_id` from semantic
actions and reported zero captures. That metadata was not used in search; it
was corrected to count board pieces before and after each applied prefix
action, and the same seeds were rerun. The corrected panel contains one capture
across the twelve prefixes.

## Interpretation and next falsifiable step

The mismatch is concrete and localized. The bounded prototype passed exact
old-profile parity for all 23 matching canonical types, exercised Western P,
retained legacy fallback for guarded Xiangqi E/H, and reports unsupported
semantic-only movement visibly. Promotion, drops, guards, auxiliary state and
history remain in rule execution; this projection changes only a static feature
input. Do not promote it to a default or claim price quality from geometry
counts alone.
The small root panel confirms that the candidate can change selected actions,
so a separate finite-game utility question is now worth considering. It does
not select a default. Any follow-up must be frozen before play, keep both
candidates on the same full Western rules/history, pair root and candidate
color, retain every UNKNOWN and actual terminal, and compare equal per-move
resource limits. If a modest panel cannot distinguish the table, do not expand
an unchanged fitness campaign; revisit only with a changed distribution or a
concrete downstream price decision.

### Frozen finite-game follow-up

Before play, freeze eight fresh deterministic legal prefixes for seeds
201–208, each generated from canonical Western Chess by `random.Random(seed)`
choosing among sorted legal actions for 12 plies. For each prefix, play two
games with candidate color swapped: generic-v3 semantic P profile versus the
exact generic-v2 profile reconstructed from declared legacy movement atoms.
Both roles use the same Core/full-history rules, q0, depth at most 3, 4096
total nodes per move, no TT/order/root-tactical scan. Stop each game after 128
additional plies; only an actual Core terminal is W/D/L, otherwise UNKNOWN.
Keep the full paired seed/color structure, actual depths/nodes/causes and all
slots; no refill, changed budget, or claim beyond this canonical sample. The
estimated ceiling is 8×2×128×4096 ≈ 8.4 million search nodes, comfortably
under the two-hour experiment threshold even allowing for preparation and
recording. The 8-root scope is a bounded diagnostic, not an independent
population estimate or universal price/default test.

### Post-launch evaluator-scope correction

While this panel was running, an integration check found that the default
evaluator's dynamic promotion-potential term still read the compiler's legacy
`empty_forward_mobility` table. Canonical Western P has no legacy movement
atoms, so that table classified all 64 squares as the heuristic's
no-forward-mobility promotion-potential zone. This is a
separate consequence of the same semantic/legacy boundary: the candidate's
static price input was updated, but the dynamic promotion feature was not.
`Evaluator` now derives its cached forward map and zone from the same narrow
`profile_movement_atoms` projection used by the static profile; legacy inputs
retain their prior geometric zones. The refactor also fixes a type mismatch in
the old helper: it compared forward `Square` objects with integer-index zone
members, so its half-step bonus never matched. The cached forward map now uses
the same integer indices, activating that intended band for legacy as well as
semantic rules. Regressions verify legacy zone parity and the half-step bonus,
plus owner-mirrored no-forward terminal ranks and full/half/zero bands for
Western P (94 focused profile, evaluation and unfamiliar-search cases pass).

The frozen 16-game process had already imported the pre-fix evaluator when
this was found. It completed all slots with 0 candidate wins, 7 losses, no
draws, and 9 unresolved games; the conservative candidate reward interval is
[-1.000,+0.125]. There were no fallback or timing-invalid games and 4,727,809
recorded nodes across 1,469 search events (921.953 s total run time). The
candidate lost four games as color 0 and three as color 1. Preserve these
outputs as evidence for that as-built variant, but do not use them as a utility
test of the corrected generic-v3 evaluator. The interval includes zero, most
games are unresolved, and the dynamic promotion feature was mis-scoped. The
post-launch correction does not alter this frozen code or its records. Exact
runner, plan, games, events and summary are preserved in
[`data/semantic_pawn_utility_asbuilt_20261020/`](data/semantic_pawn_utility_asbuilt_20261020/).

## Corrected-evaluator utility test — preregistered

The changed premise is now concrete: the static candidate and the dynamic
promotion term had been reading incompatible geometry/index views. Test whether
the price-input candidate changes finite-game outcomes when both arms use the
corrected evaluator geometry. Use eight fresh canonical Western 12-ply legal
prefixes (seeds 301–308), two games per prefix with candidate color swapped,
and the same depth-3/4096-node/q0/no-TT/no-ordering/no-root-tactical settings,
128 additional plies, and UNKNOWN for any still-ongoing game. Candidate is the
generic-v3 profile (P board/hand 361/325); control is the exact generic-v2
legacy-atom profile (P 1/1). Both Evaluator instances use the corrected
semantic movement projection for the dynamic promotion-potential term, so the
contrast is the price profile plus its derived promotion gain, not the old
Square/index bug. Preserve all slots, color pairing, full history and actual
costs; no refill. The prior as-built run took 921.953 s, so budget this run at
about 20 minutes including setup/recording. Its 3,000 s elapsed-time check is
between games: once reached, it starts no further game, but lets an in-flight
game finish. Each game is separately bounded by the 128-additional-ply limit
and fixed per-move node budget, so this is a finite workload, not a hard
wall-clock kill. The expected run remains below the user-set 120-minute
Dot-assessment threshold. This small one-family diagnostic may inform
candidate retention under this budget; it cannot select a universal
price/default or establish broad population utility. Exact runner and pre-run
plan are preserved in
[`data/semantic_pawn_utility_corrected_20261020/`](data/semantic_pawn_utility_corrected_20261020/).

## Corrected panel outcome

All 16 planned keys completed exactly once: two color-swapped games on each of
the eight fresh prefixes, with no missing or extra slot. The independent check
also verified 1,670 recorded move events equal each game's additional plies,
all event node counts are at most 4,096, and there are no failed games,
fallbacks, invalid timings or rule draws. The outcome is 1 candidate win,
4 losses and 11 unresolved games. The conservative all-slot candidate-reward
interval, retaining each unresolved game as [-1,+1], is [-0.875,+0.500].
Only five games terminated, and their 1/5 score is a heavily censored subset;
it is not an estimate that overrides the all-slot interval. Owner 0 had 1 win,
3 losses and 4 unresolved; owner 1 had 0 wins, 1 loss and 7 unresolved.

The producer elapsed time was 985.625 s. The 1,670 search events total
4,918,610 nodes (2,416,831 candidate and 2,501,779 control); recorded search
time sums to 983.861 s (476.039 candidate, 507.822 control). These realized
totals are descriptive, not a matched latency or strength claim. Because the
wide interval includes both meaningful harm and benefit, this test does not
validate utility or promote the semantic 361/325 profile to a generally
validated price/default. Retain it as the explicit rule-derived candidate
needed to avoid silently treating semantic Western P as immobile; keep the
scope and lack of utility evidence visible, and do not tune or rerun this
unchanged panel. Exact completed `games.jsonl`, `events.jsonl` and
`summary.json` are in the public data folder above.

## Generated legacy-rule compatibility sample

After the utility panel, an eight-rule source-compatible sample checked sizes
4, 5, 6 and 8 (two fixed seeds per size). The rules were generated with the
existing bilateral-random/hybrid movement generator, then compiled through its
semantic execution adapter. Across 38 non-anchor piece types, the projected
static movement atom sets and every promotable type's forward-target map on
every square for both owners matched the original generated declarations
exactly. Profile construction completed for all eight rules; there were zero
mismatches. The saved exact output is
[`data/semantic_generated_profile_audit_20261020.json`](data/semantic_generated_profile_audit_20261020.json).

This supports compatibility for the sampled legacy atom-generated rules only.
It does not exercise arbitrary semantic-only guards, auxiliary mutations,
non-clear path predicates, drops-as-moves or recombined DSL rules, and it is not
utility evidence. It found no reason to change the current scoped projection or
to repeat the completed Western P panel.

The initial focused pytest attempt failed during fixture setup because the
OS-managed Temp directory was unwritable. Rerunning with an ignored
project-local basetemp and cache disabled passed; the targeted semantic-profile,
unfamiliar-search, evaluation, cache, default-version, search and Native
semantic-search suite passed 92 cases, including a regression that seeds a
stale generic-v2 P=1 disk profile and confirms a generic-v3 lookup misses and
rebuilds it. One ad-hoc launch first used a blocked WindowsApps Python alias,
and a setup attempt matched legacy `BoardMove` rather than semantic actions;
both were corrected without source edits or changed experiment conditions. The
first random-prefix recorder also used the wrong enum-case comparison and
emitted no rows; that status check was corrected and the same seeds rerun before
interpreting results.

## Mixed legacy plus eligible semantic mover projection

The existing `move_and_shift_adjacent_friendly` fixture supplies a useful
projection boundary: R has four legacy orthogonal rays plus an unguarded direct
semantic leap(+1,+1) pattern whose transition also shifts a companion. The
current `profile_movement_atoms` returns the union, so the eligible direct
geometry is not silently omitted when legacy atoms coexist. The projection is
still geometry-only and does not price the companion shift. On this ruleset's
only non-anchor type, raw capability rises from9.088 (legacy-only) to9.767
(union), but median normalization pins both normalized R prices to1000. Thus
the fixture verifies input inclusion but cannot establish a cross-piece price
effect. Exact compact output is in
`data/semantic_search_mechanism_probes_20261020.json`; next choose an existing
multi-non-anchor composition with the same eligible/excluded pattern mix before
claiming any relative-price consequence.
