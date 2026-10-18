# Cross-rule scale of median normalization — evidence copy

Evidence for `docs/research/PROFILE_CROSS_RULE_SCALE_20261018.md`.

Provenance: **DEEPSEEK_AUX**, `codex/deepseek-aux`, session
`4615243a-f2b9-40ce-a634-266bb0b2e3b7`, 2026-10-18.

**Status: secondary, post-hoc analysis, not pre-registered.** It re-reads the
two already-published profile scans after seeing their results. No rules were
generated, nothing was searched, and no independent sample was added.

## Files

| file | bytes | SHA-256 |
|---|---|---|
| `cross_rule_scale.py` | 2793 | `435934fad90295991028a488678e6bc5b30df193715489eb651dddc474db4f43` |
| `results_cross_rule_scale.json` | 1840 | `bab1f2b8f91f0141b012d3ba979fff2319b8e56c7f1560d439b3187b383685c1` |

## Inputs

Both are already in this repository and their hashes are recorded inside the
result file:

- `docs/research/data/profile_normalization_20261018/results_profile_normalization.json`
  (`900f3127...`)
- `docs/research/data/profile_normalization_scale_20261018/results_profile_scale.json`
  (`a025f8e1...`)

## Reproduction

```
python docs/research/data/profile_cross_rule_scale_20261018/cross_rule_scale.py
```

Deterministic, under 0.2 s, writes `results_cross_rule_scale.json`.

## Limits

- Raw capability units are not semantically identical across rules, so the
  3-5x spread measures the discarded normalization factor, not a value
  comparison between rules.
- This does not test or extend the earlier null results.
- No strength, utility or human-price claim; the files contain
  project-relative paths, role/session identifiers and measurements only.
