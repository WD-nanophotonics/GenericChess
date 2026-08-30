# ADR-066 — Evaluator supervision strategy reassessment

- Status: Proposed F23V boundary; F23U diagnostic overlay only
- Date: 2026-08-30
- Work order: `GENERICCHESS-F23U-EVALUATOR-SUPERVISION-STRATEGY-REASSESSMENT`

## Decision

Stop automatic synthetic preference-corpus expansion after F23T/R10. The
diagnostic overlay in `tests/fixtures/f23u_supervision_strategy_assessment.json`
records the V5–V12 attrition ledger, a strict R10 re-audit, and a deterministic
comparison of four evaluator-development strategies. The selected boundary is
`F23V_MINIMAL_ANALYTIC_EVALUATOR_SIGNAL_PROBE`.

The recommended philosophy is a small analytic evaluator whose feature scales
are derived from RuleSet structure. It uses one common form, approximately
five generic feature families, five bounded coefficients, no game-name or
piece-name branches, and no Shogi/Chess-specific coefficient table. Synthetic
exact fitting remains rejected as the default because solver cost, all-equal
outcomes, horizon dependence, duplication, and mechanic undercoverage consume
the corpus before generic transfer is demonstrated. External engines remain
future validation axes, not training targets.

## R10 correction

The overlay re-audits the eight V12 strict-witness candidates without rewriting
V12. Each must have an actual designated mechanic, a W/D/L value different
from an alternative legal root action, and for anchor/check an actual check,
terminal, or anchor-safety transition. All eight survive. A metadata-free
semantic fingerprint uses compiled RuleSet fingerprint, exact initial
state/history, legal root-action signatures, complete W/D/L partition, optimal
actions, proof shape, and causal evidence while excluding IDs, lineage,
planned split, family labels, structural prefilter, solver tier/budget, and
evaluator information. It produces 8 raw strict roots and 8 orbits with no
cross-split collision; the abstraction-certified effective subset is 7 roots
and 7 metadata-free orbits. The declared short structural scan visibly reaches
10 non-MAX natural-terminal roots: ordinary 5, drop 2, semantic 2, leaper 1.

## Retrospective and feature basis

The V5–V12 table and attrition counts are evidence summaries, not a new
training corpus. Five coherent generic feature families are retained for the
future probe: material/inventory, safe mobility/control,
attack/defense/anchor safety, forcing capture/recapture, and capability-gated
promotion/drop potential. Semantic legality suppression/additions is not a
direct evaluator feature: the evaluator consumes the legal action boundary;
recomputing the full semantic legality delta as a feature is too expensive and
insufficiently justified.

## Genericity checkpoint

No missing semantic primitive was found for the requested mixed-mechanic
target. The semantic IR already exposes per-effect `capture_to_hand` versus
`remove_from_game`, drop action geometry, explicit promotion modes, path
constraints, and typed effects. The legacy path remains capture-to-hand
oriented; this is an architectural boundary, not a license for a production
extension in F23U. A future mixed RuleSet should combine Shogi-like
capture-to-hand/drop, Chess-like remove-from-game/promotion, and a
Xiangqi-like non-promotable special-movement piece and verify Core legality,
search runtime, identity/repetition, terminal handling, and evaluator behavior
without game-name branches.

## Pre-registered next experiment

`MINIMAL_ANALYTIC_EVALUATOR_SIGNAL_PROBE` has five fixed feature families,
five fixed rule-derived scales, one common score form, and no fitted
coefficients. It uses a frozen exact W/D/L DEVELOPMENT slice and grouped
transfer checks on Shogi-like, Western-Chess-like, and mixed-mechanic
RuleSets. Success requires at least 0.70 top-choice agreement on DEVELOPMENT,
at least 0.60 grouped-transfer agreement in each family, no group below 0.50,
and zero game-name branches. Stop on any miss, contradictory direction in at
least half of a group, a request to expand the feature/parameter budget, or a
game-specific production branch. Failure retains no production evaluator
change. F23U does not implement F23V.

## Benchmark matrix

Future validation is staged across Standard Shogi (rules/perft/legality,
AlphaSho ranking, fixed-node/time search, later strength), Western Chess
(equivalent legality/perft, a verified mature reference when available,
fixed-node/time move/PV/evaluation, later strength), and optional Xiangqi,
Janggi, Chaturanga/Indian-family, or other genuinely mechanic-expanding games.
These are future targets, not F23U implementation requirements.

No production evaluator/search/Native/rule semantics, workflow, or governance
file changed.
