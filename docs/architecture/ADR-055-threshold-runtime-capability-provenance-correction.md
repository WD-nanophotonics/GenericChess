# ADR-055: F23M capability provenance and key-contract correction

- Status: Accepted corrective evidence; F23N corpus work authorized
- Date: 2026-08-30
- Supersedes: first-pass evidence in ADR-054 only for capability provenance

## Decision

Treat `tests/fixtures/f23m_solver_capability_v4.json` and ADR-054 as immutable
historical first-pass evidence. The authoritative corrective evidence is the
full report `tests/fixtures/f23m_solver_capability_v4r1_full.json`; its compact
summary is `tests/fixtures/f23m_solver_capability_v4r1.json`. The benchmark
harness writes the full report from the actual worker results and computes the
summary with `summarize_report(full_report)`. A permanent test requires the
embedded and separately serialized summaries to be equal.

The corrective report is bound to baseline sandbox SHA
`d03e9fa6ca9d89cb22555393103d0eacaf9d762d`, solver version
`exact_generic_preference_solver_v3@F23M-CORRECTIVE-R1`, and benchmark-plan
digest `cf3d58a9ca5708df43b0f9328b9ce5d2538a6eefda8c496e0408f37e553bba4a`.
It retains the exact five representatives, 2,000/20,000/100,000 node ladder,
authoritative compiled horizon, and 8-second external wall cap.

## Correctness contracts

Threshold combination is tested behaviorally: existential TRUE and universal
FALSE short-circuit over an unresolved sibling, while existential FALSE and
universal TRUE require every child to be resolved. Unresolved results are never
stored, exact ties are preserved, and `strong=True` is possible only after all
root actions have exact W/D/L classifications.

For ordinary draw policy, two legal states with identical current position,
side, ply, and repetition counts but irrelevant reordered history produce the
same V3 future-relevant key and the same exact root/action classifications as
V3 without TT and V2's full-history solver where bounded. For
`continuous_check_loss`, the same legal-history pair has distinct complete
actor/check history evidence and distinct V3 keys; both runtime terminal
results agree with the public terminal oracle. The V3 key projection uses an
exact non-recursive occurrence snapshot to avoid deep persistent-snapshot
comparison recursion.

Completed V3 attempts report aggregate profile seconds and proportions for
terminal checks, legal-action generation, runtime push/transition, runtime
pop, threshold-key construction, TT lookup, TT store, and residual proof
bookkeeping. Runtime balance is derived from local and runtime push/pop counts
plus final depth; it is not a free-standing assertion. A subprocess killed by
the external wall cap is classified `UNCLASSIFIED_TIME_CAP` unless completed
profiling evidence supports a more specific blocker.

## Capability result

The corrective full report reproduces four of five fixed families: ordinary
anchor movement at SMALL, capture/recapture at SMALL, drop-hand tactics at
MEDIUM, and promotion race at SMALL. Each solved row has every legal root
action classified, proof depth 6, zero runtime imbalance, and nonzero profile
data. The semantic auxiliary representative remains unresolved under the
unchanged ladder and is recorded as `UNCLASSIFIED_TIME_CAP`. The drop-hand
SMALL node-cap attempt supplies measured combinatorial evidence; it does not
relabel the semantic wall timeout.

The derived gate is true: 4/5 total families, 3/4 among
capture/drop/promotion/semantic, 4 deep solved roots, complete root-action
certificates, and balanced runtime. The selected next boundary is exactly
`F23N_REFERENCE_PREFERENCE_CORPUS_R5`. This ADR does not implement F23N.
