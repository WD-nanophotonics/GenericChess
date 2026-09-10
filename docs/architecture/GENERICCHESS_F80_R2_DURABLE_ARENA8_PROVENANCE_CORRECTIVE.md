# GenericChess F80-R2: durable Arena8 provenance corrective

Status: `PARENT_ANCHORED_FULL_RESIDUAL_ARENA8_EVIDENCE_DURABLE`.

This is a zero-game, zero-training metadata correction. The accepted F80-R1
Arena8 scientific result is unchanged, and no games, Heavy benchmark, model or
alpha mutation, opening generation, teacher/deep evaluation, self-play,
external engine, or production semantics were used.

## Corrected identity separation

The tracked artifact
`artifacts/f80_parent_anchored_full_residual/arena8_strength_evidence.json`
now uses schema `generic-chess-f80-arena8-strength-evidence-v2` and explicitly
separates:

Its corrected content SHA-256 is
`438ddec64d1225488900f3a823fa0fd8a52a9dd60942b39d1f9f32dcb3b0ead0`.

- work-order baseline: `f4fc8411079e25fe1cfeab1c9be79535881e4274`;
- execution harness checkpoint:
  `0fd011f9f34799fc087209a73538aacb61019e7b`;
- result/report checkpoint:
  `fe1f395224df199fd0244dcf2da297032953c1c7`.

The compatibility `source_checkpoint` field now points to the result/report
checkpoint, not the work-order baseline. The artifact continues to bind F79
evidence SHA `888864459718cbc1d81cd0e4d1f9e3cae5e1eb116b9c3d05ca2f559e35fb9477`
and report SHA
`e992fb9f7804d48878b3eb71a309d95f3979f8b55a775ecded9e6bff6ffcfd4b`.

## Retained science and validation

All strength content remains exact: parent
`d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`, child
`f0ca40ce5aaad97fb6437cb3a8a22d97791f9fe5939f48089becb27dbff82ec4`, model
`b4372d087d0e7760857efefd69413c97c8cf10b5b188dd704f5d1e308a4d32b6`, corpus
`2923f457e56454520f89c682614b3b10d07da974f03040bfc6c3a831ab41da48`, combined
pair scores `[0.5, 1.0, 0.5, 0.5, 0.25, 0.5, 1.0, 0.5]`, mean `0.59375`,
better/tied/worse `2/5/1`, W/D/L `9/1/6`, and 16 games/8 pairs. The retained
classification is `PARENT_ANCHORED_FULL_RESIDUAL_ARENA8_SURVIVES`; promotion
remains HOLD.

The contract tests recompute these statistics from tracked evidence, verify the
F79 artifact linkage and source report hash, and assert the three Git identities
are distinct and correctly bound. No ignored runtime result is required.
