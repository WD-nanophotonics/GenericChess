# Static-profile normalization at board sizes 6 and 8 — evidence copy

Public copy of the evidence behind
`docs/research/PROFILE_NORMALIZATION_SCALE_20261018.md`.

Provenance: produced by **DEEPSEEK_AUX** in the isolated `codex/deepseek-aux`
worktree, session `4615243a-f2b9-40ce-a634-266bb0b2e3b7`, on Git HEAD
`8e6c56f3`. Auxiliary result; no other role has rerun it. No strength,
utility or game-outcome claim.

Copied byte-for-byte from the Git-ignored private directory
`.local_agent/profile-normalization-scale-20261018/`.

## Files

| file | bytes | SHA-256 |
|---|---|---|
| `plan.json` | 3388 | `1838ec9890069cbd3edde5e78a6f15f89d6d13327c112126c63dd3fd418508cb` |
| `plan-log.json` | 197 | `674a270df1c26c90814ab3be99fd0bb127528f743a189bfacdf2069305b25f1e` |
| `scan_profile_scale.py` | 9254 | `ccecaf2fa4ffbcd6aa9e3801b481ba46a169268058437bbe19186106a476e595` |
| `results_profile_scale.json` | 295317 | `a025f8e167e62128a1a45d6be76ee54a88b17c0ff51566e603ac068719e3f1c3` |
| `validation_report.json` | 492 | `1fd56cdfa012f06464b206b514a28828cd28c268050e0e07731789c3d5dc7a21` |

`plan.json` holds the endpoints and the pre-written decision rule, hashed as
`1838ec98...` in `plan-log.json` with `status: written_before_run` before the
scan executed. `results_profile_scale.json` stores that plan hash, the hash of
the imported 4x4 endpoint script, source hashes and the Git HEAD.

## Reproduction

```
python .local_agent/profile-normalization-scale-20261018/scan_profile_scale.py
```

Deterministic, zero-search, 1.3 s. It imports `scan_rule` from
`.local_agent/profile-normalization-20261018/scan_profile_normalization.py`
(published as `2a8f630d...`) and overrides its board-size constant, so the
endpoint definitions are the published ones rather than a re-implementation.
The scan must sit one directory below the repository root, because the script
resolves the checkout as `Path(__file__).parents[1]`.

## Validation performed

- Replayed from a copied script and plan in
  `.local_agent/profile-scale-replay-20261018/`: both size blocks, the plan
  hash, the imported-script hash and the source hashes were identical; only
  `generated_at_utc` differed. `validation_report.json` records this.
- The result and plan JSON parse and the scan script byte-compiles.
- A scan of the files for personal paths, account identifiers, tokens,
  passwords and API keys returned no hits.

## Scope limits

- 40 rules per size from one generator family, `classic_like`, zero search.
- The weakest normalized value observed was 101 (4x4 block), 178 (size 6) and
  158 (size 8); the near-zero regime where ratio error approaches 50% was not
  sampled.
- Zero ties reflects this generator's capability spread and the 1000-median
  integer scale; it is not a guarantee for other presets or families.
- No seeds, sizes, thresholds or endpoints were retuned after the result.

## Publication boundary

Project-relative paths, role/session identifiers, seed numbers and technical
measurements only; no personal information, credentials or keys.
