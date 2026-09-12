# F94-R5-R1 horizon-aware PREP repair closeout

This result-free repair replaces the unsafe R5 v1 PREP as the only candidate
for a future Layer-D RESULT.  It does not run Arena or Heavy, change any
scientific parameter, tune search/evaluation, or reinterpret R3.

The protocol repair commit is
`2aaf9b3426e2b0d875424f5f88076872e384d140`.  The newly generated immutable
PREP is `GENERICCHESS_F94_R5_R1_HORIZON_AWARE_PREP.json`; both
`source_sandbox_sha` and `protocol_source_sha` bind to that exact published
commit.  The schema is bumped to v2, so its PREP fingerprint cannot be
confused with the defective v1 contract.

The adapter now flattens each real `ArenaSummary` into its two games per
seat-swapped pair before the horizon reducer reads it.  The R5 contract fails
closed unless every READY candidate has exactly:

- 12 games for every tape/matchup (`2 * pair_count`);
- 36 games for every tape;
- 108 action traces across 3 tapes and 3 matchups;
- 36 strongest-vs-weakest horizon games; and
- exactly one owner-0 and one owner-1 game for every
  `(tape, matchup, pair_index)`.

Termination status, actual plies, opening/final position identities, pair and
role identity, and trace hash are mandatory.  Missing data raises an error;
the reducer never substitutes a zero denominator or zero horizon fraction.

The generator no longer depends on the untracked
`artifacts/f87a_ruleset_qualification/reports.json`.  It binds its A/C
prerequisites to the committed R2 PREP authority manifest and records that
manifest's SHA-256.  A temporary clean clone of the published `sandbox` branch
generated this PREP successfully from the bound protocol SHA.

The 256/1024/4096 budgets, depth 12, 8 MiB TT, tapes, corpora, pair count,
candidate identities, boundary A/C short-circuit, and both `>= 0.5 => DEFER`
GenericChess-specific empirical gates remain unchanged.  Focused tests pass:
`tests/test_strength_response.py`, `tests/test_f94_r5_horizon_aware_prep.py`,
and `tests/test_f94_r2_stage0.py`.

No R5 RESULT may start until Chat approves the required compute plan and its
resource envelope for this repaired PREP.
