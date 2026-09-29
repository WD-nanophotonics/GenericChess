# V2H historical evidence reconciliation

Question: does the frozen support-conditioned V2H prior supply an untried
Chess/Shogi candidate or an immediately reusable Xiangqi holdout? The smallest
observation is its existing freeze, validation closeout, and Xiangqi dependency
records; no candidate rerun or human-reference read is needed.

The pre-reference V2H candidate is already frozen at SHA-256
`ca906eb9d80841ad6f85d9c6f1a51ef3cf50c8a97490e32266cba4aa207d74b9`.
Its subsequent Chess/Shogi diagnostic validation reports passing the unchanged
Chess ratio bands and Shogi gates. This is **spent development evidence**, not
an untried candidate or independent holdout. ADR-133 explicitly assumes equal
mass on rule-reachable source squares; reachability alone does not establish
visitation frequency or a strategic material unit.

The Xiangqi route did not produce a valid unchanged-formula holdout score. Its
compiled General-facing capture has a typed opposing-General target that the
inherited three-label analytic occupancy measure cannot assign a probability.
The actor is an excluded anchor, so this unresolved probability does not enter
the retained non-anchor vector algebraically. It nevertheless fails the
candidate's **global** intrinsic-coverage gate. Separately, the inherited V2H
producer and U/C dependencies still contain square-board `board_size ** 2`
assumptions, so the frozen Chess/Shogi pipeline cannot consume a 9×10 ruleset
unchanged. These are distinct coverage and implementation limits. The older
phrase “falsified on Xiangqi holdout” refers to applicability at this gate,
not a measured disagreement with Xiangqi human material values.

Current-source reproduction also remains blocked: the V2H complete-candidate
test fails its pre-reference V2D source-hash check before reconstruction.
The recorded drift audit identifies later source changes and a non-provenance
V2H support-index change; the historical freeze must not be silently rebased.
The original Chess/Shogi validation is historical evidence, not a fresh run
against today's source tree.

This closes V2H as a fresh-candidate lead. Reusing its Chess/Shogi numbers to
select another formula would spend the same development references again.
The current mainline still needs a justified context/utility interpretation,
an inexpensive general construction, and an independently valid cross-game
test. Do not rerun V2H, waive its coverage gate, or inspect Xiangqi human
values merely because this historical candidate passed two development games.

Sources: `docs/architecture/ADR-133-rule-support-conditioned-source-prior.md`;
`.generic_chess_flow/static-material-v2h-closeout.md` and
`static-material-v2h-validation-closeout.md`;
`.generic_chess_flow/xiangqi-typed-target-algebraic-identifiability.md`;
`.generic_chess_flow/reports/v2h-shape-assumption-inventory-20260928.md`;
`.generic_chess_flow/reports/frozen-source-drift-lineage-20260928.md`;
`.generic_chess_flow/rule_only-hypothesis-family-discovery-closeout.md`.

Verification: `git diff --check` passed. Focused V2H/Xiangqi pytest run:
20 passed, one failed at the frozen V2D source-hash precondition above; no
candidate reconstruction occurred. No human-reference file, Xiangqi material
value, game, or heavy computation was accessed.
