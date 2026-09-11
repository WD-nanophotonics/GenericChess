# F86N-R1 transport-aware signed movement sampler preflight

Status: completed fresh PREP-to-RESULT static preflight. PREP SHA:
`a95e6f5c554f0239af50dfbc23693778a68f6081`. PREP manifest blob:
`adba41fa02a6e44459d3692ba232bf564c4450c7`. RESULT is the direct successor
commit and uses only candidates frozen in that PREP manifest.

The default generator remains unchanged. F86N-R1 preserves the F86N signed
LEAP/RAY pool, two LEAP slots at p=0.70, one RAY slot at p=0.55,
`max_steps ∈ {1,2,None}`, dedupe, one signed-LEAP fallback, and a 4,096
attempt bound. Seeds are frozen as the first 64 bits, big-endian, of
`SHA256("F86N-R1|sample_id|source_ruleset_fingerprint")`.

## Boundary-safe backbone predicate

Candidate selection occurs entirely in PREP, before any mate census. An opening
ordinary type is a backbone when it is present in owner-0 opening material,
has integer movement-lattice rank 2 and index 1, and at least one actual
opening source lies in a nontrivial SCC whose members span at least two files
and at least two owner-relative ranks. This accepts edge-to-interior-to-edge
transport and does not require an opening source to move outside the board.
Other types may remain rank-1, high-index, color-bound, or directional.

## Frozen candidate ledger

| Sample | Movement seed | Accepted attempt | Backbone/source | SCC (size; file span; rank span) | Candidate fingerprint |
| --- | ---: | ---: | --- | --- | --- |
| V4-2 | 406439205195250778 | 69 | P0 / P0@o0#1 | 0 (14; 0–3; 0–3) | `02e4fdf733bffbf778a9b7f0fb8cd18abc8722dce9ad8632cea94b0d7e8a04b4` |
| V4-3 | 3070855626994714998 | 37 | P0 / P0@o0#1 | 4 (3; 0–2; 1–3) | `856a810d3a21eec779f9ba8300ce602cd24d3e8850ba895e39579603fd4ff3e2` |
| V4-4 | 10305839976894073876 | 17 | P0 / P0@o0#1 | 0 (14; 0–3; 0–3) | `f4b489db672ea91b86e9246c055a4bd3d5cf4d19772225ef8f4446f5f36e8149` |
| V4-5 | 15828931209065400409 | 8 | P0 / P0@o0#2 | 5 (2; 1–3; 1–2) | `8530ab797c3d5f7c306f2b7a998bec6c6dad7d392c7952b3ceccf58d135dd193` |
| V5-2 | 11978203786740654645 | 26 | P0 / P0@o0#1 | 1 (2; 0–1; 0–1) | `f428ac94c1539f79a572f656595de59c2e1ad48eb7b53aae2a5a84a98b2efb7b` |
| V5-3 | 14663260470151880405 | 2 | P0 / P0@o0#1 | 0 (25; 0–4; 0–4) | `e8528688a64bce3f39231d9e4f38d5d200ade57c6f517ae33ce9b71b9f75ebe5` |
| V5-4 | 12180817424716413829 | 20 | P0 / P0@o0#1 | 0 (25; 0–4; 0–4) | `8036d5b5c071f5373e3f4ba6aab5f5423b7e16d57e4b6e05cd834528e67c0777` |
| V5-5 | 15607937451917703870 | 36 | P0 / P0@o0#1 | 0 (25; 0–4; 0–4) | `1f33451daefc18b78df7b5d566f1453ed29b03c2e3e894df63e2e55ac5242873` |

All eight candidates were frozen successfully in PREP. Result code only
deserialized and compiled those candidate rulesets; it did not resample.

## Transitive material profile

Per-source reachable sets use full empty-board graph reachability, not one-ply
mobility. The compact result records each type’s union coverage, source
component diversity, pairwise overlap, lattice rank/index/invariant, sink and
reverse-edge fractions, SCC fraction, and source spans. Aggregate transitive
source-union board coverage is recorded for every sample; no opaque scalar
quality score is used.

## Targeted static gate

Execution-time caps were 2,048 checks per cell and 4,096 total. No dynamic
games were run.

| Cell | Checks | Validated positions | Templates | Truncated | Ordinary reachable | Joint reachable | Lower bound | Route |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | --- |
| V4-3 | 1296 | 1166 | 108 | no | 2 | 2 | 8 | `TRANSPORT_AWARE_SIGNED_SAMPLER_STATIC_WITNESS_EXISTS` |
| V5-3 | 2048 | 1592 | 90 | yes | 21 | 21 | 21 | `TRANSPORT_AWARE_SIGNED_SAMPLER_STATIC_WITNESS_EXISTS` |

The positive witness takes precedence over truncation. This is a static
preflight result only: it does not claim gameplay or terminal-outcome
improvement. It does establish that the boundary-safe signed sampler can
produce frozen candidates with transport backbones in all eight samples and
positive static witnesses in both targeted cells.

## Compute and verification

New real games: 0. Tactical nodes: 0. BFS expansions: 0.
Teacher/search/training: 0. F85 compute: 0. Default generator changed: false.

Exact verification command and result:

```text
.venv\Scripts\python.exe -m pytest tests/test_f86n_r1_transport_aware_signed_sampler.py
6 passed
```

The compact result is in
`artifacts/f86n_r1_transport_aware_signed_sampler/results.json`. Raw transient
benchmark output is not tracked. Any dynamic smoke requires a separate
authorized PREP work order.
