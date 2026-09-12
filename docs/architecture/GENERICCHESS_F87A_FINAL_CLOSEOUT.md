# GenericChess F87A Final Closeout

- Published checkpoint: `e726d7f163bae054e7d5b768d86aeadf723f29cd`
- Frozen charter baseline: `a33ff404d33aef1d6717fc62e05337ae92691540`
- Historical R3 PREP manifest SHA-256: `11dddf4855f61b7b32a323268acdbd7f4b40ab6f8deec03dfa73c0c6968e7ef5`
- Current PREP contract: schema `4`, `GENERICCHESS-F87A-R3.1-PLAYABILITY-SCOPE-RECONCILIATION`
- Current PREP manifest SHA-256: `daa1702aefb0ad34bbdab23d2764d148b5ad0f8d5a6c42c28b11ded51833e24a`
- Current qualification reports SHA-256: `d6098ff12c8e7faad91c2ebf1f25fddd1d2a652db6adc00c38892b24241dc1cf`
- R9 manifest SHA-256: `19abaf84ebe35f196004f7ad38f2e22d0047e8657cec2c869ddf826543226ecc`
- R9 results SHA-256: `fc9552f8177cc17d156fd5b311a56f4f243c21203313515c6c6910f41661516c`
- Phase reconciliation result SHA-256: `bc9d7a621e2affca9ffdcaa5835791991ee8f660f0413fbcb3c455bbec3ea03a`

## Final scope decision

F87A's frozen target is `PLAYABILITY`, requiring Layers A--C. For the two
built-in semantic controls, the authoritative QualificationReports now agree:

- Layer A: `PASS`;
- Layer B: diagnostic-only and non-blocking;
- Layer C: `PASS`;
- overall playability status: `PASS`.

R9 closed the Western termination subgate with one generic-policy checkmate,
five `HORIZON_ONLY` trajectories, and zero search-budget censorship. The
historical R3 evidence remains immutable; the schema-4 PREP is an explicit
superseding contract, and the loader rejects the historical identity as the
current PREP.

Therefore the F87A declared scope is `PLAYABILITY_SCOPE_SATISFIED`.
Layers D (paired strength response) and E (learning/evaluator adapter) remain
`DEFERRED_IN_F87A` follow-on work. This closeout does not grant promotion and
does not authorize additional Western seeds, Arena, training, or Heavy compute.
