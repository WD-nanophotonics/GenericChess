# Generated evaluator symmetry screen — 2026-10-21

## Question and result

On fresh generated rules with bilateral movement/setup symmetry, do replayed
owner-swapped, 180-degree mirrored states produce the same side-to-move score
from the default rule-derived evaluator, while their legal action sets remain
exact mirrors?

The finite screen passed: eight generated 6x6 `classic_like` bilateral rules,
seeds 863201–863208, supplied 138 mirrored legal state pairs through at most 20
plies. The audit reports zero structural/action-set mismatches and zero score
mismatches. Runtime was 0.356 seconds. This is a static evaluator consistency
result for this sample; it is not a search, utility, strength, or population
claim.

## Frozen inputs and provenance

- Source checkout HEAD: `e009c4a531aebd21bf8d07cb2115b43786cc3d94`.
- Plan SHA-256: `F32D06C8F88213C6C92A07B25618E3ECF28B784D6A676473B238643CED38215D`.
- Audit script SHA-256: `5913BBEDAF08FD72A7FEAB4E04514F7DB538DF5274F311C5FE9CBA64D10D6FC4`.
- Result SHA-256: `7DCEA022EED1006C79A756E5E42086180446474BAEDFB71E9ADC9B7B5B6E345D`.
- Replay-exposure plan SHA-256: `07305203C88577D3A977FA4CC11C60330741F5A94947A55F9F023A82A0A53A14`.
- Replay-exposure script SHA-256: `1CE09A3CFB28CCA9697BF5B232543E1DA45771B6F48BED8F5380A86790F1E13A`.
- Replay-exposure result SHA-256: `041478BB85258180F2319B2521AD5AC05642E6F0168ADD5F19A36C712C33CFB5`.

The plan fixed eight prospective seeds, one deterministic legal history per
rule, a 20-ply maximum, exact mirrored legal-action comparison, and the default
`EvaluationConfig`. It explicitly excluded search, WDL, training, and outcome
selection. The independent replay-only exposure audit added no games, searches,
or training.

## Coverage limit

Per-rule replay counts sum exactly to the aggregate audit: 112 legacy board
moves, 38 captures, 23 legacy drops, and six promotions; 41 sampled states had
a promoted piece and 82 had an occupied hand. There were zero semantic board
moves, zero semantic drops, and zero states with nonempty auxiliary state.
Therefore promotions/hands/drops were exposed through legacy actions, but the
screen did not exercise semantic action or auxiliary-state execution. It closes
only this fixed legacy-generated symmetry sample.

The scope gap has a source-backed cause: `GeneratorConfig` builds ordinary
legacy `RuleSet` movement/promotion/drop masks and does not generate
`semantic_actions` or auxiliary slots. The general `RuleSet` schema and semantic
DSL support those mechanisms, but this generator path does not. Reusing its
seeds cannot widen the screen to the complete generated semantic domain.

## Preserved preflight failures

Two attempts before the successful screen remain in
`data/generated_evaluator_symmetry_20261021/preflight-failures.json`
(SHA-256 `E3E72264D189F32A0F7CE5883B5F3E6750CEC3A155DF06BEC05CCC8979757959`).
The first compared the standard owner-0 initial state with its owner-swapped
mirror without constructing the corresponding owner-1 side-to-move state. The
fixture was corrected by constructing that exact state and its repetition
identity; no expected score was changed. The second imported
`repetition_identity_key` from the wrong module; it was corrected to
`generic_chess.core.identity`. These were harness/setup errors, not evaluator
counterexamples.

A separate one-fixture feasibility probe then tried the default evaluator on an
existing guarded semantic-only ruleset. The first script launch lacked the
project root on `sys.path`; after fixing that setup, the profile builder
explicitly refused the representation with `default evaluation requires legacy
movement metadata; supply evaluator_override for semantic-only search`. Source
confirms this is a fail-closed precondition. `AlphaBetaPlayer` invokes it only
when no evaluator override is supplied, so semantic-only search can proceed with
a caller-owned evaluator. Focused tests for auxiliary-history TT and recombined
semantic lifecycle passed 5/5; pytest emitted a cache-permission warning but no
assertion failures. This is a supported boundary, not a confirmed defect or an
evaluator mismatch. The ignored local script/result preserve the exact bounded
probe details.

## Decision

Close this finite legacy-generated static-score symmetry screen. Do not change a default or generalize to semantic actions, auxiliary state, search or outcomes. The previously pending geometry-only profile feasibility check is complete and documented below; the current next research choice is maintained in `LOCAL_MAINLINE.md`.
## Semantic static-profile support boundary — 2026-10-21

The minimal owner-relative direct-move geometry pilot completed. On the existing guarded-capture fixture after explicitly removing guards/auxiliary effects and making its geometry owner-relative, the semantic profile projection added `RayAtom((0, 1))` to type A's legacy `LeapAtom((2, 0))`; B and K retained their legacy atoms. A's expected mobility changed from `[0.6,0.5625,0.525,0.4875,0.45]` to `[2.6,2.2174072265625,1.889453125,1.6088134765625,1.36875]`. The semantic support payload exactly matched its retained compiler baseline on fingerprint, board shape, initial board, type anchor/promotable/target metadata, drop masks, promotion allowed/forced masks and empty mobility for A/B/K. Public `compile_ruleset` intentionally rejects semantic actions; the comparison used the baseline embedded by `compile_semantic_ruleset`.

This demonstrates a bounded route to reconstruct the existing static-profile inputs for this simple geometry, not general semantic pricing. The default profile builder still rejects the semantic-only compiled object unless the caller supplies an evaluator. No default/API change follows. The earlier action-ID tie study already showed cross-fingerprint tied-action sensitivity and documented deterministic ordering only within a fixed ruleset; lexical root/orderer sorting confirms the naive action-enumeration-order candidate is not a new gap.

The scoped static-v2 promotion-bonus audit also closed: bonus-on/off did not pass either preregistered retention gate. The next decision-changing candidate is a board-leaf-only contrast with Unit hand values, promotion bonus off, and Unit capture/type ordering fixed in both arms. `AlphaBetaPlayer(evaluator_override=...)` plus separate evaluator score and ordering hooks makes this feasible without a product change. First preregister fresh generated roots and exact controls; do not reuse or refill the closed panels.
