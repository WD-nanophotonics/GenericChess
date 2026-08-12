# F3 history-aware TT context matrix

| Runtime condition | History context | TT policy | Reason |
|---|---|---|---|
| Legacy `draw` policy | Existing position/repetition/ply key | Existing TT behavior | Continuous-check evidence is not terminal input. |
| `continuous_check_loss`, complete Session/replay witnesses | Persistent exact actor/check chain | Probe/store enabled | Future perpetual-check evidence is represented exactly. |
| Complete public history replayed from authoritative initial state | Persistent exact actor/check chain | Probe/store enabled | Replay verifies each public record and final state. |
| Opaque/custom-root or incomplete history | No safe exact context | Skip probe/store | Current position/count equality cannot prove perpetual-check equivalence. |
| Forced runtime-hash collision | Exact identity in occurrence buckets/context | Safe | Hash is only a discriminator. |
| Forced history-context digest collision | Exact parent-chain comparison | Safe | Digest equality is not identity. |

## Terminal inputs

| Input | Source | Included in key/eligibility |
|---|---|---|
| Current position and ruleset | `RuntimePositionIdentity`, fingerprint | Yes |
| Absolute ply/max-ply | runtime `ply_count` | Yes |
| Repetition multiplicities | `RuntimeCountsSnapshot` exact guard | Yes |
| Occurrence boundary/order | persistent history context | Yes |
| Actor/check sequence | persistent history context | Yes for continuous check |
| Missing imported provenance | eligibility state | Forces TT skip |

TT probes and stores are performed only at the `negamax` boundary.  Qsearch is
not newly TT-enabled.  Generation, replacement, bound, and mate normalization
are unchanged.

## Corrective R1 Closure

`RuntimeHistoryContext.append()` remains persistent parent-pointer work. The
repetition snapshot discriminator now consumes the already-maintained
`RuntimeHash` and occurrence count on child updates, avoiding full
`repr(Position)` formatting on that hot path. Exact identity/count map
materialization and equality remain the collision guard. Effective
`runtime.search_key()` construction and TT probe/store work are measured and
reported independently; no blanket O(1) claim is made for the complete search
path.
