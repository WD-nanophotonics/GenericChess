# ADR-079: F24C corrective runtime lifecycle and search certification

## Status

F24C corrective R1 passes. The first-pass F24C artifacts remain byte-identical,
production diff remains zero, and the next boundary is
`F24D_WESTERN_CHESS_RULESET_PERFT_CERTIFICATION`.

## Evidence

`tests/test_f24c_mixed_mechanic_certification_r1.py` reuses the frozen first-pass
RuleSet and adds public action round-trip for every simultaneous-root action,
RuleSet behavioral round-trip, complete opaque type-ID rename checks, and the
representative runtime matrix: hand capture, removal capture, promoted A1/B1
victims, A0 drop, A/B promotion, C path capture, and quiet move.

Each runtime case records and restores position, hands, auxiliary state, side,
ply, terminal status, repetition snapshot, history, identity, search key, and
legal-action digest. Nested sibling isolation, invalid/stale rollback, a
two-cycle repetition sequence at limit 3, and a max-ply boundary all agree
between runtime and pure transition authority.

The frozen eight-state smoke uses production AlphaBeta/evaluator-v1 routing,
fresh TT per run, 128/512 node budgets, two repeats, and a uniform qsearch
depth of zero so every bounded run reports node-limit or completed-depth rather
than an unbounded fallback. All selected actions are legal and repeated action,
score, and PV heads match. The exact mixed RuleSet Native provider is active;
historical F13/F14/F21 Native failures remain nonblocking and unchanged.

The compact durable evidence is
`tests/fixtures/f24c_mixed_mechanic_certification_r1.json`. No production
semantic, search, evaluator, runtime, Native, workflow, or governance file was
changed.

## Decision

F24C is final PASS. Proceed to
`F24D_WESTERN_CHESS_RULESET_PERFT_CERTIFICATION`; keep `master` locked and do
not promote.
