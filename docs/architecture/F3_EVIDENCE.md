# GenericChess F3 Safe History-Aware Transposition Reuse evidence

Status: IMPLEMENTED — focused correctness validation complete; final full
repository validation is recorded after the final push.

## Baseline

Required starting refs were verified before editing:

```text
origin/sandbox = 1b150cd024d68090238d2cde75834cd0e5a033e7
origin/master  = 4f1d03a308f5fd04a01bbd980c7411888ea1ed9d
origin/chat    = d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

## Gate B: current-key insufficiency

Two genuine legal paths in the generic `continuous_check_loss` 4x4-rook
fixture reach the same exact position, ply, and repetition map, while the
actor/check context differs.  The F2 key projection is equal; the F3 effective
keys are unequal.  The regression is
`test_f2_runtime_key_insufficiency_is_reproduced_by_legal_histories`.

## History context and eligibility

`RuntimeHistoryContext` is a persistent parent-pointer chain with exact
identity/actor/check records and a digest discriminator.  Equality walks the
chain after digest/length comparison.  Complete exact Session/replay history
is eligible; opaque or incomplete history skips all TT probes/stores.

## Focused results

```text
python -m pytest -q -p no:cacheprovider tests/test_search_path_runtime.py
23 passed
```

The focused suite proves forced context digest collision safety, opaque-history
ineligibility, session-witness eligibility, legal-path F2 insufficiency,
continuous-check TT-on/off parity, and exact runtime collision/rollback
behavior.

## Initial certified semantic Shogi result

Fixed depth 2, quiescence 0, ordering disabled, root tactical scan disabled:

```text
TT disabled: action legacy_112:g6:f1-g2, score 0
TT enabled:  action legacy_112:g6:f1-g2, score 0, eligible nodes 32,
             probes 32, hits 1, stores 32
```

The certified initial Session path therefore demonstrates nonzero safe reuse.

## Scope

No public serialization, external SHA, ruleset fingerprint, TT replacement,
bound, generation, mate normalization, evaluator, Native production search,
UI, AlphaSho, master, or chat changes are included.
