# GenericChess F87A Phase-Gate Reconciliation

- Charter baseline: `a33ff404d33aef1d6717fc62e05337ae92691540`
- Historical R3 PREP manifest SHA-256: `11dddf4855f61b7b32a323268acdbd7f4b40ab6f8deec03dfa73c0c6968e7ef5`
- Current PREP contract: schema `4`, `GENERICCHESS-F87A-R3.1-PLAYABILITY-SCOPE-RECONCILIATION`
- Current PREP manifest SHA-256: `daa1702aefb0ad34bbdab23d2764d148b5ad0f8d5a6c42c28b11ded51833e24a`
- Current qualification reports SHA-256: `d6098ff12c8e7faad91c2ebf1f25fddd1d2a652db6adc00c38892b24241dc1cf`
- Reconciled R9 checkpoint: `d4fa4c239dbccbc0889d891927adde8117d7a499`
- Published contract-correction checkpoint: `d2230cf293f080ac106e1b7b60a68447ad15f5da`
- Authority: `GENERICCHESS_F87A_RULESET_QUALIFICATION_TOOLBOX_FOUNDATION`
- Reconciliation result SHA-256: `bc9d7a621e2affca9ffdcaa5835791991ee8f660f0413fbcb3c455bbec3ea03a`

## Frozen scope

The charter declares `PLAYABILITY` as the target and requires Layers A--C.
Layer B is explicitly diagnostic and does not impose a universal lattice
rank/index admission gate. Layers D (paired strength response) and E
(learning/evaluator adapter) are explicitly `DEFERRED_IN_F87A`.

The target population for this reconciliation is the two built-in semantic
controls: Western Chess and Standard Shogi. The negative and boundary controls
remain calibration diagnostics; they are not silently reclassified as playable
positive controls.

## Decision

R9 supplies the missing Western termination evidence under the existing R6
gate: one generic-policy checkmate, five `HORIZON_ONLY` censored trajectories,
and zero search-budget censorship. Together with the existing semantic runtime
contract and positive-control tests, the declared A--C playability scope is
reconciled as `PLAYABILITY_SCOPE_SATISFIED`.

This is a scope decision, not a promotion approval. Layers D and E remain
follow-on work under their frozen `DEFERRED_IN_F87A` status. No additional
Western termination seeds, Arena, training, or Heavy job is authorized by this
reconciliation. A future decision to make D/E mandatory before promotion must
first supersede the frozen charter with an explicit approved contract.

The earlier R9 `HOLD` wording is therefore retained only as a promotion guard,
not as an unresolved Western termination blocker.
