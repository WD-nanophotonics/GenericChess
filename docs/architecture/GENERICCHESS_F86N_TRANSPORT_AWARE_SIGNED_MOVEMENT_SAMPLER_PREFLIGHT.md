# F86N transport-aware signed movement sampler preflight

Status: completed static preflight. PREP commit:
`1c495972310ed2301c8e24c65633733c464e81f5`; PREP manifest blob:
`e28071134473bbf9a20fccb2e14da9fb12d2fcb1`. The candidate/result commit is
the direct successor of PREP.

F86N is independent of `generic_chess/benchmark/minimal_generator.py`; the
default generator is unchanged. It freezes the eight F86C samples, exact
initial placements/material, and all non-movement rules, and resamples only
ordinary movement atoms.

## Frozen sampler and predicate

The signed LEAP pool is the six legacy vectors and their exact reverses:
`(1,0),(0,1),(1,1),(2,1),(1,2),(-1,1),(-1,0),(0,-1),(-1,-1),(-2,-1),(-1,-2),(1,-1)`.
The signed RAY direction pool is
`(1,0),(0,1),(1,1),(-1,1),(-1,0),(0,-1),(-1,-1),(1,-1)` with max steps
`1,2,None`; reverses preserve max steps. Sampling uses two LEAP slots at
probability 0.70 each and one RAY slot at probability 0.55, deduplication,
one signed-LEAP fallback, and deterministic MT19937 `seed + attempt` retries,
bounded at 4,096 attempts per sample. No sampled candidate is automatically
reverse-closed.

Acceptance requires one ordinary type actually present in the owner-0 opening
material to have lattice rank 2, index 1, an opening source reaching both
higher and lower owner-relative rank, and a nontrivial SCC. Other types may be
rank-1, high-index, color-bound, or directional.

## All-eight sampling ledger

| Sample | Movement seed | Attempts | Status | Backbone | Candidate fingerprint |
| --- | ---: | ---: | --- | --- | --- |
| V4-2 | 8614019 | 2 | accepted | P0 | `1a5da4be0fe9bc92a369581200dc11d5e62731fc57144987bcc87fa49e9e89e4` |
| V4-3 | 8614029 | 15 | accepted | P0 | `692c0f22f4094406e7bc701908f513b27e65df551dfae4c0b718d1606c091b97` |
| V4-4 | 8614039 | 5 | accepted | P0 | `d14f57a2a99261e884853a03aa7de2232b0fcdf70de97fc0b893c5f669c4570a` |
| V4-5 | 8614049 | 42 | accepted | P0 | `f1c4c9e0dac8fe87ef65aa185be584cb7769c393764cf2e19903bdc22ccaee6e` |
| V5-2 | 8615019 | 4096 | predicate unavailable | — | — |
| V5-3 | 8615029 | 8 | accepted | P1 | `97d9ad77e3161d67a0fc6191b291986083e007cb9c3334a235d068410517fcdd` |
| V5-4 | 8615039 | 26 | accepted | P0 | `4d853026cf5c2d11bda7465223740c89447d3e3375e160562cd5e87023eb1097` |
| V5-5 | 8615049 | 32 | accepted | P1 | `8f131147b92c38ac10c88c111e5ad23a73f4d6b12d0d04e70092c94d41e301af` |

Seven samples accepted the structural backbone. V5-2 exhausted the frozen
4,096-attempt bound and is recorded fail-closed. Its sole ordinary type has
owner-0 opening sources on opposite rank edges, so no sampled type can make a
single opening source reach both higher and lower rank under this predicate.
This is a material/opening preflight failure, not a result-driven replacement.

The accepted profiles record per-type lattice rank/index/invariant, sink and
reverse-edge fractions, SCC fraction, source board reachability, and
higher/lower rank reachability. Material-level profiles record backbone type,
aggregate source coverage, same-type union coverage, component diversity, and
rank-1/high-index/index-1 opening-material fractions in the compact result.

## Targeted static gate

Execution-time caps were 2,048 checks per cell and 4,096 total. No dynamic
games were run.

| Cell | Checks | Validated positions | Templates | Truncated | Ordinary reachable | Joint reachable | Route |
| --- | ---: | ---: | ---: | --- | ---: | ---: | --- |
| V4-3 | 396 | 334 | 33 | no | 0 | 0 | `TRANSPORT_AWARE_SIGNED_SAMPLER_INSUFFICIENT_KINEMATICALLY` |
| V5-3 | 2048 | 1870 | 98 | yes | 16 | 16 | `TRANSPORT_AWARE_SIGNED_SAMPLER_STATIC_WITNESS_EXISTS` |

The V5-3 positive witness takes precedence over truncation, as required. F86N
therefore demonstrates a meaningful static advantage over the legacy/full-
reverse preflight on one targeted cell, while not claiming that all eight
samples pass or that gameplay is improved.

## Compute and verification

New real games: 0. Tactical nodes: 0. BFS expansions: 0.
Teacher/search/training: 0. F85 compute: 0. Default generator changed: false.

Exact verification command and result:

```text
.venv\Scripts\python.exe -m pytest tests/test_f86n_transport_aware_signed_sampler.py
5 passed
```

The compact durable result is in
`artifacts/f86n_transport_aware_signed_sampler/results.json`; raw transient
benchmark output is not tracked. This preflight does not authorize dynamic
games; any common-tape smoke must be a separate PREP work order.
