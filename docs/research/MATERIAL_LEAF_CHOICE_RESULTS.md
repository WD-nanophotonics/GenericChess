# Exact leaf-choice primitives, 2026-10-04

MATERIAL_LEAF_DECISION_DESIGN.md is a prospective DRAFT, not a frozen root
population or admission of a material formula. scripts/material_leaf_choice.py
implements signed current-board/held-base features, exact bounded material
scores, pairwise sensitivity and a depth1 complete-child-table choice operator.
It does not run production search, create roots or query outcome labels.

Seven focused tests passed. Independent controls establish both-owner terminal
dominance, canonical ties independent of enumeration order, rational units,
missing-mode rejection even when owner counts cancel, incomplete-choice failure,
and unresolved/censored terminal failure. A mixed-sign inventory pair can reverse
under two strictly positive vectors; a third componentwise-dominating child
shows why that filter alone does not guarantee global selection sensitivity.

Public Standard Shogi integration preserves current TP on board versus captured
base P in hand. An actual legal R capture demotes the enemy TP into an own held
P, with history advanced; the unit control changes0 to2/3 under the declared
two-ordinary-token bound. Separate full public choice tables for both owners
include Session declarations. The31-point WIN claim outranks every ongoing
zero-material child; the24-point RESTART claim makes selection incomplete,
never a draw score or silently omitted action. These are existing semantic
fixture controls, not fresh usefulness labels or a candidate-fitted corpus.

Construction remains missing. The design also exposes an independent-label
problem: shallow full-inventory probes may be unknown, while standard Chess
tablebase goals need an adjudication compatibility audit. See
CHESS_TABLEBASE_APPLICABILITY.md. No coefficients, proposals, new human-value
reads, tablebase downloads or external position probes were performed here.
