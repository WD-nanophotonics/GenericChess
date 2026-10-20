# Quiet semantic compound-action qsearch probe — 2026-10-20

## Question

Can a reachable nonterminal compound semantic action that changes board state
but preserves material inventory change AlphaBeta's fixed-budget root decision
when ordinary qsearch currently omits it?

## Frozen fixture and method

Reuse the public product fixture
`tests/product/test_recombined_semantic_lifecycle.py::test_alphabeta_preserves_compound_action_identity_and_replayable_pv`:
`weird_rulesets()[3]`, two kings, two owner-0 rooks and a submitted two-king-move
history. The legal `sem_00_move_and_shift_adjacent_friendly` child changes the
board, preserves material inventory, and is neither terminal nor an immediate
check. The baseline uses the current `noisy_child`; the counterfactual
monkeypatch includes only this compound action. Both use the same evaluator,
root, depth and node ceilings; TT, ordering and Native legality are disabled.
The exact runner and machine-readable outputs are beside this report.

The first public AlphaBeta comparison used a total-node ceiling of 3,000 and a
qsearch cap of 200. Both arms selected `legacy_020:g8:d4-g4`, score 2067,
depth 1; both stopped at `qsearch_budget` with 202 qnodes. Because that q cap
prevented depth 2, a second comparison kept the 3,000 total-node ceiling and
raised the q-specific cap to 3,000. Both arms then completed depth 2 and retained
the same action/PV and score 2072. The baseline used 118 main + 400 q nodes; the
forced-inclusion arm used 120 main + 443 q nodes. These are equal ceilings, not
equal realized work. The direct qsearch score shifted 2046 to 2062 under the
product default evaluator while qnodes shifted 13 to 14. A deliberately
constructed test evaluator shifted 0 to 10000; that confirms test sensitivity
only and is not utility evidence.

## Interpretation

This one existing fixture produced no root action or score change in the public
search at either q cap. Forced inclusion added qsearch work in the completed
D2 comparison. `SearchLimits` explicitly documents `quiescence_max_nodes` as a
soft q-expansion limit, with first-iteration q0 reserve leaves allowed to finish;
therefore 202 visits at a limit of 200 is documented behavior, not a defect.
The focused qsearch correctness, Native semantic qsearch and semantic-effects
modules pass (48 tests).

Do not broaden qsearch support or change its defaults from this result. The
sample is one action/state in one recombined fixture; it does not establish
utility, tactical coverage, cost over the generated domain, or behavior for
promotion, drops, guards, auxiliary-state mutations or arbitrary history. Reopen
only if a distinct reachable generated/recombined fixture shows a changed public
root decision at matched node ceilings and without relying on a fabricated
evaluator.
