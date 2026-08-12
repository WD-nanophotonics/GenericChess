# GenericChess F3 Safe History-Aware Transposition Reuse evidence

Status: COMPLETE — Corrective R1 closure validation passed; final repository
validation is recorded below.

## Baseline

Required starting refs were verified before editing:

```text
origin/sandbox = 9938d04543645c057a829f7132e0206d1fa1d3bd
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

python -m pytest -q -p no:cacheprovider tests/test_f3_corrective_r1.py
12 passed
```

The focused suite proves forced context digest collision safety, opaque-history
ineligibility, session-witness eligibility, legal-path F2 insufficiency,
continuous-check TT-on/off parity, and exact runtime collision/rollback
behavior.

## Corrective R1 Closure

### Persistent TT across moves

`tests/test_f3_corrective_r1.py::test_f3_persistent_player_tt_survives_successive_session_moves`
uses one real `AlphaBetaPlayer` and one `GameSession` with a persistent TT.
Two successive `choose_action()` calls are compared to a TT-disabled player at
the same fixed depth. Both action/score pairs agree; the persistent table
advances generation 1 → 2, the second call has probes and hits, and entries
for the same position/runtime/ply all carry the exact current history context.
The table is not cleared between moves.

### Deterministic differential corpus

```text
generic draw policy:              4 prefixes × depth 2
continuous_check_loss:            4 prefixes × depths 1/2/3
Semantic Standard Shogi:          4 deterministic legal prefixes × depth 1
opaque/custom root:               1 case, TT probes/stores = 0
ordinary repetition:              plies 0/3/7 × depth 2
```

Every corpus row compares TT OFF vs TT ON action, score, completed depth, PV
legality, terminal input, and runtime balance. The continuous corpus includes
pre-root repetition/check evidence and the existing legal F2-insufficiency
pair. The exact tests are in `tests/test_f3_corrective_r1.py`.

### Explicit collision and research-context checks

The closure tests cover equal independently reconstructed contexts, forced
RuntimeHash collision with exact snapshot separation, forced history-context
digest collision, exception rollback, sibling isolation, PVS/aspiration pop
restoration, and qsearch remaining free of TT probes.

### Runtime key-cost audit

The command below measures snapshot digest calls, exact-position token/sort
calls, history-context digest updates, and effective search-key time
separately from TT table work:

```text
python scripts/audit_f3_runtime_key_cost.py
```

Post-optimization child-only results over six pushes:

```text
legacy-4x4-rooks: snapshot_entry_digest_calls=7,
  exact_position_token_calls=0, exact_position_sort_calls=0,
  history_context_digest_updates=6, search_key_calls=6, search_key_us=25.1
legacy-8x8-mate: snapshot_entry_digest_calls=6,
  exact_position_token_calls=0, exact_position_sort_calls=0,
  history_context_digest_updates=6, search_key_calls=6, search_key_us=19.9
```

The pre-change audit observed 8/7 snapshot entry calls and 8/7 exact-position
token calls respectively over the same six-child paths (root import included),
with position representations of 534/822 bytes. The important structural
change is that child updates no longer format those full representations;
wall-clock totals are intentionally not presented as a speed claim.

The complete effective path is therefore described honestly: context append is
O(1), child snapshot discriminator update is O(1) with exact-map equality as a
collision guard, effective key construction is separately instrumented, and
TT probe/store cost is separate.

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
888 tests collected; all passed

python scripts/build_native_zig.py
fresh Zig build passed from current F3 source
output: _native_core_f3_r1_final.cp312-win_amd64.pyd (333312 bytes)
```

The temporary native output and Zig cache were removed after verification.
The required baseline refs above remain unchanged; only the sandbox branch is
modified.

## Scope

No public serialization, external SHA, ruleset fingerprint, TT replacement,
bound, generation, mate normalization, evaluator, Native production search,
UI, AlphaSho, master, or chat changes are included.
