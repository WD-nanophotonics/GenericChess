# Unreachable declarations and static-price normalization — 2026-10-20

## Decision

Normalize legacy static piece prices over types reachable from any compiled
initial setup, adding enabled promotion targets only from reachable types that
can occur unpromoted. Do not recursively promote an already-promoted target.
Keep prices for every declaration in the returned profile for diagnostics, but
do not let an
unreachable declaration set the scale used by reachable pieces. Semantic
executables keep the all-declared denominator because their action effects can
change current piece types outside legacy promotion metadata. Bump the profile
version first to `generic-v4`, then to `generic-v5` for the follow-up closure
correction, so profiles cached by either previous implementation are rebuilt.

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

A second sample with the same strata and seed formula
`202610000000 + board_size*1000 + preset_offset + seed` (offset 0 for
`bilateral_random`, 500 for `free_random`, seed 0–39) found 56/320 such rules;
all 56 again preserved reachable profile values and initial legal actions after
declaration removal. These samples are bounded implementation checks, not
prevalence estimates. The current generator targets only nonpromotable types,
so these generated-rule samples do not exercise chained promotion metadata.

A later hand-authored, compiler-valid `P→Q→R` ruleset exposed a separate bug in
the initial closure: Q was included as P's promoted current type and then
incorrectly treated as an unpromoted promotion source for R. Core move
generation explicitly returns without promotion for `piece.promoted`. The
closure now adds targets in one pass from independently reachable unpromoted
base types; a promoted initial base type may be a source only when capture to
hand followed by an allowed drop could restore that unpromoted base. Added
tests establish both that `P→Q` does not imply `Q→R` when Q exists only as a
promoted target, and that `Q→R` remains included when Q is independently
present unpromoted. This is a follow-up correction to the already-published
`fa46c3e339fd7b0bbaba8e0a2f148a3953fb30db`; its `generic-v4` disk-cache key
would otherwise have reused profiles produced by the recursive helper, so this
follow-up also bumps the version to `generic-v5`. The earlier publication and
tests did not exercise hand-authored chained promotion metadata.

Earlier paired shallow-search checks found no selected-action mismatch in the
completed comparisons, but seven of twelve reachable-state roots hit their
8192-node caps. They do not establish policy equivalence or search utility; no
games or training were run for this correction.

## Scope and validation

The closure includes board and hand types from the default and alternate
initial positions. Promotion sources are independently reachable unpromoted
base types: initially unpromoted board pieces, droppable initial hand types,
and promoted initial pieces whose base type could be captured into hand and
dropped back unpromoted. One pass adds their declared targets when a
nonempty allowed-promotion relation exists. This conservatively over-approximates
square-level feasibility while avoiding impossible second-generation promotion
from an already promoted target. Semantic executables expose legacy metadata for compatibility, but
`set_current_type` and other effects can introduce types not visible through
that metadata, so the helper falls back to all declarations when semantic IR is
present. The legacy compiler rejects semantic actions; a focused regression
checks the executable semantic transform path separately.

The focused evaluator/cache/semantic-profile/rectangular suite passed 109 tests,
including the exact default-profile-version assertion. That assertion still
expected `generic-v3` and was updated after the cache-version bump. The broader
active AI evaluation/cache/search/match/budget plus semantic and rectangular
regression set passed 190 tests before the chain correction and 192 after it.
The initial failed assertion and exact
successful outputs are retained privately in ignored
`.local_agent/unreachable-scale-20261020/`.
