# H50B1 semantic Native canonical execution closure

- Checkpoint: `H50B1_F50_SEMANTIC_NATIVE_CANONICAL_EXECUTION`
- Work order: `GENERICCHESS-F50B1-SEMANTIC-NATIVE-CANONICAL-EXECUTION-CLOSURE`
- Parent: `7ff0039bcc469bdc6b0b3c5ade61558d72ccf681`
- Implementation commit: `455dc71b6e588597e60b2199939f0b8157121335`
- The final closeout artifact commit and its `origin/sandbox` SHA are supplied
  by the Courier envelope for this file.
- Promotion: HOLD; no master mutation

## Scope

The existing `CompiledSemanticRuleset.ir + .support` and `GCSemanticPosition`
remain the semantic authorities. No F49 restart, S49 regeneration, learner,
F50B2 iterative search, TT, budget, cancellation, or production search routing
was added.

Semantic payload version changed from 2 to 3. Semantic history capacity is
1025 entries (indices 0..1024), independent of legacy `GC_MAX_PLY=512`.
Western `max_ply=1000` compiles unchanged. The payload lowers generic
`subject_ref`, stores repetition policy and the first automatic adjudication
trigger, and preserves exact public action identity through
`generic_chess.native.semantic.public_action`.

Native semantic state capacity is board `GC_MAX_SQUARES=256`, hands
`2 x GC_MAX_TYPES`, auxiliary state `GC_SEM_MAX_AUX_SLOTS x 3`, and exact
history digest plus actor/`gave_check` metadata for each semantic history entry.
These path fields do not enter the public position key.

Standard Shogi declarations remain represented on the Native compiled wrapper
and are assessed through the generic declaration contract: owner, outcome,
weighted score, failure outcome, and outcome bands. Native terminal handling
certifies ordinary repetition, continuous-check loss, and the generic 500-ply
automatic adjudication trigger.

## Certification

- Fresh Native build: PASS; binary SHA-256
  `c7b4e31b6bff068bc868d6b53ee09d51c2767deec86f7ad3c60793aa6555630c`.
- Focused H50B1 and existing semantic Native suites: PASS.
- Western initial position: 20/20 exact guarded actions; packed action to
  `SemanticBoardMove` round-trip preserves pattern, geometry, actor type,
  coordinates, and promotion identity.
- Standard Shogi: Native compile, ordinary actions, declarations, continuous
  check, 500-ply no-contest, and exact history metadata: PASS.
- Generic compiler-produced witness: PASS; no H48B legacy fingerprint or
  second compiler/state representation was introduced.
- Post-publish full regression: `1473 passed, 3 skipped, 17 failed`.
  The two functional/environment residuals are the established F24F Kiwipete
  depth-1 mismatch (45 vs 48) and the missing external
  `C:\Users\icywo\PycharmProjects\alphasho\configs\training\evaluation_positions.jsonl`.
  The other 15 failures are historical F40/F41/F48/F49/H48/H49/H50A frozen
  evidence checks bound to pre-H50B1 source, binary, or audit artifacts; they
  require independent re-baselining rather than silent artifact rewriting.

## Production diff

Only semantic Native compiler/runtime/state files, the public semantic Native
adapter, contract updates, the H50B1 certification test, and ADR-120 addendum
changed. Legacy Native search/TT/evaluator, Python AlphaBeta, RuleSet schema,
canonical RuleSets, learning, F49, S49, and master were not modified.
