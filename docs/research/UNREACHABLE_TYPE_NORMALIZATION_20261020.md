# Unreachable declarations and static-price normalization — 2026-10-20

## Decision

Normalize legacy static piece prices over types reachable from any compiled
initial setup, closing over enabled promotion targets. Keep prices for every
declaration in the returned profile for diagnostics, but do not let an
unreachable declaration set the scale used by reachable pieces. Semantic
executables keep the all-declared denominator because their action effects can
change current piece types outside legacy promotion metadata. Bump the profile
version to `generic-v4` so cached profiles are rebuilt.

This adopts an equivalent-rule consistency correction for the legacy generated
rule path. It does not claim that the resulting prices improve search utility,
transfer across games, or value every semantic rule.

## Evidence

`build_ruleset_profile` previously took the median raw mobility-capability score
over every declared non-anchor type. A bounded generated-rule census found
that unused declarations occur in this target. In generated seed `202610201023`
(6x6, `free_random`, bilateral/hybrid), ordinary type `B` is outside the
initial type closure and has no enabled reachable promotion path. Removing
`B` and its references preserves the same initial legal actions and the same
reachable state after a legal capture. Under the old all-declared normalizer,
the reachable values changed from `P=943, X=2149, A=1057` to `P=892, X=2033,
A=1000` when only `B` was removed. On that identical post-capture state, the
material-only score changed from -2008 to -1900; the nonmaterial residual was
-8 in both rules, and the full evaluator changed from -2016 to -1908.

After the repair, the same generated rule and its `B`-removed equivalent both
produce reachable values `P=892, X=2033, A=1000` and full score -1908 for the
same state. A fresh deterministic sample spanning board sizes 6, 8, 10 and 12,
both `bilateral_random` and `free_random` presets, and 40 seeds per stratum
contained 65/320 rules with unreachable ordinary declarations. In all 65,
removing unreachable declarations preserved every reachable profile value and
the initial legal-action set. The sample is a bounded implementation check,
not a prevalence estimate.

Earlier paired shallow-search checks found no selected-action mismatch in the
completed comparisons, but seven of twelve reachable-state roots hit their
8192-node caps. They do not establish policy equivalence or search utility; no
games or training were run for this correction.

## Scope and validation

The closure includes board and hand types from the default and alternate
initial positions, plus targets of reachable promotable types with a nonempty
allowed-promotion relation. Capture-to-hand/drop preserves a reachable base
type. Semantic executables expose legacy metadata for compatibility, but
`set_current_type` and other effects can introduce types not visible through
that metadata, so the helper falls back to all declarations when semantic IR is
present. The legacy compiler rejects semantic actions; a focused regression
checks the executable semantic transform path separately.

The focused evaluator/cache/semantic-profile/rectangular suite passed 109 tests,
including the exact default-profile-version assertion. That assertion still
expected `generic-v3` and was updated after the cache-version bump. The broader
active AI evaluation/cache/search/match/budget plus semantic and rectangular
regression set passed 190 tests. The initial failed assertion and exact
successful outputs are retained privately in ignored
`.local_agent/unreachable-scale-20261020/`.
