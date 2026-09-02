# ADR-118: F48 learnable material recovery protocol

Status: accepted protocol checkpoint (H48A)

Date: 2026-09-02

## Context

F42-F47 established that repeatedly adding parameter-free static material
formulas is not the preferred primary route for arbitrary RuleSets. F48 tests a
different boundary: rule-derived material is a cold-start prior, while
RuleSet-specific learnable material is adaptable knowledge. This ADR records
the pre-registered audit/prototype protocol before any recovery experiment is
run.

H48A is frozen by
`tests/fixtures/h48a_learnable_material_recovery_manifest.json`, whose
canonical manifest SHA is
`684e33d261e08b89b74187e3b7fbcc02e514148869366dafcb155aa459214490`.
The checkpoint is anchored to sandbox baseline
`d4a0d8baf00f95dc9eef315183c59e394ed5928f`; it contains no observed learning
results.

## Decision

The protocol has six explicit ownership layers:

- L0 Rule semantics and L1 compiled RuleSet execution are immutable and are
  compiled once per RuleSet per run.
- L2 supplies a finite, sensibly scaled, rule-derived Generation-0 prior.
- L3 trains only current-type board material and base-type hand material,
  bound to one RuleSet fingerprint per checkpoint.
- L4 search algorithms and budgets remain fixed within each comparison.
- L5 runs learning outside the search tree; no learner callback or mutable
  update executes per node.

The primary benchmarks are canonical Western Chess, canonical Standard Shogi,
and one deterministic generated GenericChess evaluation-sensitive benchmark.
The generated benchmark is screened from 32 pre-frozen candidates using only
checkpoint-independent structural, terminal, Gen0, and artificial-perturbation
metrics. If that screening is needed, H48B is required before training.

Each benchmark has exactly four starting priors: rule-derived control, flat
material, deterministic positive perturbation, and cyclic permutation. The
learners are the unchanged existing TDLeaf control and an audit/prototype
search-aware material evolution driver over `LearnableMaterialCheckpoint`.
Both use generic self-generated/search-generated evidence, a disjoint
64-position teacher holdout, a fixed 20,000-node teacher versus 2,000-node
student comparison, and a 16-pair fresh-engine color-swapped arena.

Recovery requires holdout teacher agreement to reach 90% of the P48-0 reference
and improve at least 0.05 over the disturbed start, with no catastrophic arena
regression. Strength claims additionally require a paired score above 0.5 and
the pre-registered positive bootstrap criterion. Efficiency records compile,
engine, native-search, and non-native learning costs and enforces no compiler
or learner work inside the node loop.

The classification selector and all seven F49 boundaries are frozen in H48A.
Human material values are diagnostic-only and cannot be used by the learner or
benchmark selector. Production learning integration, static feature expansion,
search tuning, external AlphaSho teaching/data, F49 execution, and master
promotion remain prohibited.

## Consequences

The first F48 implementation must publish H48B if generated-benchmark
selection cannot be reconstructed from an already fingerprinted checkpoint-
independent artifact. It must then measure recovery and beyond-prior
improvement separately, report paired playing strength separately from teacher
agreement, and preserve RuleSet/checkpoint/TT identity boundaries. A failure of
the learner is not interpretable as a learning failure when material leverage
or teacher stability gates fail first.

No F48 result, production integration, or F49 work is authorized by this ADR;
the manifest and its validation test are the only H48A deliverables.
