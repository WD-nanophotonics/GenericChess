# GenericChess F3 Safe History-Aware Transposition Reuse evidence

Status: COMPLETE — focused and repository-wide validation passed; the final
receipt is recorded below.

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
is eligible; opaque or incomplete history skips all TT probes/stores.  A direct
search call without an exact runtime witness also fails closed for
`continuous_check_loss`.

## Focused results

```text
python -m pytest -q -p no:cacheprovider tests/test_search_path_runtime.py
26 passed
```

The focused suite proves forced context digest collision safety, opaque-history
ineligibility, session-witness eligibility, legal-path F2 insufficiency,
continuous-check TT-on/off parity, and exact runtime collision/rollback
behavior.

## TT-enabled versus TT-disabled parity

The legal-history pair is searched with TT disabled and enabled at the same
depth and receives identical `(action, score)` results for both histories.
The PVS plus aspiration case also matches.  Distinct legal histories produce
distinct effective keys and both keys can be stored/probed in one table; no
cross-history hit is possible through the F2 projection.

For opaque history, the conservative result is explicit: TT probes and stores
are skipped and `tt_skipped_ineligible_nodes` is nonzero.

## Initial certified semantic Shogi result

Fixed depth 2, quiescence 0, ordering disabled, root tactical scan disabled:

```text
TT disabled: action legacy_112:g6:f1-g2, score 0
TT enabled:  action legacy_112:g6:f1-g2, score 0, eligible nodes 32,
             probes 32, hits 1, stores 32
```

The certified initial Session path therefore demonstrates nonzero safe reuse.

## Reuse and cost observations

The generic continuous-check fixture records nonzero reuse at depth 3
(`eligible=36`, `probes=36`, `hits=9`, `stores=36`).  The certified semantic
Shogi path records `eligible=32`, `probes=32`, `hits=1`, and `stores=32`.
These are correctness/usefulness witnesses, not performance claims.

Each child appends one persistent `RuntimeHistoryContext` node and restores
the parent pointer on pop.  Key construction does not copy the public history
tuple, repetition map, or serialize a full history per child; the
digest/length discriminator is carried in the key and exact chain comparison
is reserved for equal discriminator candidates.

## Final validation record

```text
python -m pytest -q -p no:cacheprovider
876 tests collected; all passed

python scripts/build_native_zig.py
fresh Zig build passed from current F3 source
output: _native_core_f3_final.cp312-win_amd64.pyd (333312 bytes)
```

The temporary native output and Zig cache were removed after verification.
The required baseline refs above remain unchanged; only the sandbox branch is
modified.

## Scope

No public serialization, external SHA, ruleset fingerprint, TT replacement,
bound, generation, mate normalization, evaluator, Native production search,
UI, AlphaSho, master, or chat changes are included.
