# F2 Corrective R2 search-path call-site matrix

The immutable `GameState`/`legal_successors` path remains the public and
reference oracle.  F2 Corrective R1 changes only the private Core-owned
`SearchPathRuntime` data plane used by `run_root_search`.

## Data-plane ownership

| Boundary | Contract |
|---|---|
| Session, replay, serialization, UI, diagnostics | Immutable `GameState`, public SHA-256 position identity, and full public history remain unchanged. |
| Live Session/replay to AlphaBeta | A private exact position-witness tuple crosses the call boundary; it is not serialized or added to public state. |
| `reference_minimax` | Continues to use immutable transitions; it is not routed through the mutable runtime. |
| AlphaBeta candidate search | Imports one runtime at the root and uses `runtime.pushed(action)` for every child. |
| Runtime identity | Current exact in-memory `Position` plus process-local 128-bit `RuntimeHash`; no child external SHA. |
| Repetition authority | RuntimeHash buckets plus exact `Position` equality; imported opaque SHA identities are validated before search. |
| Semantic authority | Runtime delegates legal generation, checked transition, and terminal evidence to the Core semantic engine. |

## Child-creation paths

| Search path | Corrective R1 boundary |
|---|---|
| Main negamax | One exception-safe push/pop around every recursive child. |
| PVS null-window/full re-search | Each probe and re-search independently restores its parent frame. |
| Aspiration re-search | Root frame is unchanged between iterations. |
| In-check and ordinary qsearch | Evasions/noisy children use the same runtime boundary. |
| Root tactical scan | Root children use push/pop and cannot leak occurrence/history state. |
| Lazy/eager tuning | Both modes share runtime transitions; no public child tuple is retained. |
| Cancellation/exception | `push` restores frame, identity, hash, cache, history, occurrences, and snapshot before re-raising. |

## Identity and update matrix

| Transition | Runtime hash update | External key work |
|---|---|---|
| Legacy board move, including capture/promotion | XOR only side, touched source/destination cells, and changed hands | Root/import only; child count is zero |
| Legacy drop | XOR side, destination cell, and mover hand | Root/import only; child count is zero |
| Semantic action | Exact stable-address component-map delta, including aux add/remove | Root/import only; child count is zero |
| Forced hash collision | Same bucket, exact in-memory position comparison | No SHA fallback |

## History and repetition

| Concern | Corrective R1 rule |
|---|---|
| Imported history | Positive counts must equal the exact set and multiplicities derived from history; last history identity must be the imported root. |
| Pre-root non-root identity | Exact witnesses are used when available; otherwise only an unresolved imported key that a child externally matches is bridged. |
| Bridge rollback | Opaque-key aliases, occurrence buckets, snapshots, and history evidence restore on pop and exception. |
| History-bearing allocation | Bridge frames record only reversible mutations; no occurrence-table or history/repetition tuple copy is made per child. |
| Unknown/ghost key | Fail closed; never silently add it to runtime occurrences. |
| Runtime occurrence table | `RuntimeHash -> [exact identity, count]` buckets. |
| Repetition snapshot | Parent-pointer update with order-independent digest; exact map equality on digest collision. |
| Continuous check | Uses runtime actor/gave-check history evidence and exact identity occurrences; incomplete legacy history is not adjudicated as perpetual check. |
| Public SHA boundary | Still used for public state, imported records, and immutable APIs; never replaced by runtime hash. |
| Conditional fallback counters | Reconstruction, witness hit/miss, and opaque-history child-key work are reported separately from fresh-root child work. |

## Explicit exclusions

No board make/unmake changes, evaluator/search tuning, Native production
migration, Standard-Shogi TT policy change, Semantic TT reuse, UI/variant
changes, or AlphaSho work is included in F2 Corrective R1.
