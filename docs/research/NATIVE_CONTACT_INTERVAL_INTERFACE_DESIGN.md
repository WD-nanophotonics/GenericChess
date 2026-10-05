# Prospective native Chess interval constructor and complete-child interface

2026-10-05, before new construction-interface tests or broader use observations.
This is a research-only interval candidate; no point vector, production search
change, new root corpus/goal labels, generic-game admission or human holdout.

Use only the two ALREADY declared duration hypotheses, fixedg1/2 and density
2(1-g). Substitute exact moments into the current Q/R histograms, B1/B2 bounds,
N1/N2/N3 bounds/tour support, and Pawn rank-support/P1/P2 bounds. Before any
public use rows, PAWN_PREFIX_SUPPORT_OVERLAP_DESIGN.md merges the two Pawn
supports with exact overlap removed, not a sum of overlapping lower bounds.
No midpoint.
Q is exact and strictly larger than EVERY other upper for both hypotheses,
so dividing all intervals by its exact value fixes a COMMON native maximum1.
Do not normalize separately by uncertain mode maxima or tune either duration.

Provide a deterministic five-current-board-type rational interval mapping.
Native/P-origin Q/B/N and rights-disabled R use the existing source-qualified
origin relations; P is native unpromoted only. Current anchors are excluded
from material. Preserve Core piece/history identities and complete child states.
Do not add held modes or import Shogi/Xiangqi through matching type names.

The complete-child operator remains terminal-first, same canonical lossless
keys and common ordinary-token bound30, equivalent score raw/(30+1). Encode
authoritative terminal utilities as +/-31 or0 on an EXACT unit sentinel feature
when reusing material_margin_interval; nonterminal inventory raw is strictly
between-31 and31. This permits exact terminal/ongoing comparison without a
midpoint scorer or new core search. Reuse the existing conservative box-choice
certificate; box superset can be inconclusive, never silently choose a corner.

Scope checks on EVERY ongoing child: pinned Western ruleset fingerprint,8x8,
two native anchors (one each owner), no hands, all four rights explicitly0 and
EP explicitlyNone; valid native P/N/B/R/Q or promoted Pawn-origin N/B/R/Q,
at most30 ordinary tokens. Terminal states still need authoritative qualified
game results, not unsupported nominal piece geometry. Unresolved NO_CONTEST/
claims prevent selection. Complete=False never chooses from a partial table.
Do not remove unsupported children: mark the whole choice incomplete.

This NO-rights/EP use stratum deliberately does not admit an initial Pawn-double
child. A future structural root generator must keep EVERY action; if any child
falls outside scope it is an unsupported whole root, not a favorable action
filter. Static counts remain an approximate task-to-game transfer, not exact
position-dependent strategic material or WDL calibration.

Tests must verify behavior rather than just repeat coefficient formulas:
complete mixed-material choices for both owners, canonical tie equality,
terminal-versus-extreme inventory, simultaneous all-mode uncertainty, rejected
hands/rules/rights/origins, promotion-origin equivalence, unresolved terminal
and incomplete tables. No new public transitions/goals are needed for these
interface controls. Frozen evidence producers remain untouched.
