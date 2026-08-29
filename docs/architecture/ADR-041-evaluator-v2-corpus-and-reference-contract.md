# ADR-041 — Evaluator-v2 Corpus and Reference Contract

Status: Accepted as an F23B corpus decision; evaluator-v2 implementation is
deferred to a separately authorized phase.

## Context

F23A recovered the exact ten-position F22 Standard-Shogi corpus and found
contradictory candidate-feature direction across its eight persistent
disagreements.  F23B was authorized to expand evidence without changing
production evaluation, search, Native runtime, or AlphaSho.

The local repository contains no additional independently identifiable
AlphaSho reference stratum beyond the ten preserved F22 positions.  F23B
therefore does not fabricate or resample Shogi labels.  It adds a compact
generic reference stratum generated from small GenericChess rulesets.

## Contract

`tests/fixtures/evaluator_v2_corpus_v1.json` is the versioned corpus manifest.
It contains:

- the unchanged F22 ten-position legacy stratum and its read-only provenance;
- eight non-Shogi diagnostic cases across five ruleset identities covering
  ray/checking, drops/hands, promotion, semantic suppression, and semantic S4;
- exact labels produced by bounded GenericChess legality/terminal solvers;
- a stable state identity hash and frozen DEVELOPMENT/HOLDOUT assignment.

Sampling is feature-blind.  Entry selection uses only provenance, generic
rule-family coverage, deterministic state definitions, and exact-solver
availability.  Candidate F23A feature values are not imported by the builder.
Labels are terminal mate-in-one action sets, forced-promotion action sets, or
exact semantic legality/suppression sets; no evaluator-v1 score is used.

The split is frozen before any future fitting:

`HOLDOUT` iff `int(state_identity_sha256[:8], 16) mod 4 == 0`; otherwise
`DEVELOPMENT`.

## Findings

Ten Shogi positions were safely available and zero additional Shogi positions
were added.  The generic stratum has eight positions, five ruleset identities,
seven DEVELOPMENT cases, and one HOLDOUT case.  It exercises four observed
generic families: checking/anchor pressure, drops/hands, promotion structure,
and semantic constraint effects.  The builder and fixture are deterministic;
the permanent tests re-run exact label generation and preserve the F22 stratum.

This is a reference/corpus foundation, not generic validation from Shogi alone.
The current compact stratum does not satisfy the later prototype gate requiring
at least five feature families observed across more than one source/ruleset.
The DEVELOPMENT probe has meaningful cross-ruleset observations for only three
families; attack/defense and capture/recapture remain unobserved in this exact
stratum.  In particular, the F22 Shogi features and the new generic exact
labels must remain separately visible in future audits.

## Decision

F23B provides the corpus/reference infrastructure needed for a later audit but
does not implement the selected F23C boundary.  Select exactly
`F23C_EVALUATOR_CORPUS_EXPANSION_R2`: expand generic exact/reference strata
until at least five feature families are meaningfully observed across more
than one source/ruleset.  Do not fit weights or implement an evaluator-v2
prototype in F23B.

## Consequences

Future work may add safely sourced cases only through the builder and must
preserve the F22 ten-position legacy stratum, exact-label authority, stable
split algorithm, type-name invariance, and bounded solver caps.  Raw AlphaSho
runs and bulky audit output remain outside the live tree.  No production
behavior changed in F23B.
