# Profile rounding-tie risk — evidence copy

Public copy of the evidence behind
`docs/research/PROFILE_TIE_RISK_20261018.md`.

Provenance: **DEEPSEEK_AUX**, branch `codex/deepseek-aux`, session
`4615243a-f2b9-40ce-a634-266bb0b2e3b7`, 2026-10-18, run against Git HEAD
`66681931`. Auxiliary result; no other role has rerun it. No strength,
playing-quality, utility or price claim.

Private originals remain in `.local_agent/profile-tie-risk-20261018/`; the
replay copy is in `.local_agent/profile-tie-risk-replay-20261018/` (identical
`blocks`, `design`, `predictions`, plan hash, source hashes and decision).

## Files

| file | bytes | SHA-256 |
|---|---|---|
| `plan.json` | 3878 | `659b509ad32b008421ecbb100784864e397c3b1cf9ddbb06a97864bd7a48ad21` |
| `plan-log.json` | 201 | `d381d103c0349447467f95a8fbadc8dee4297ad9131592c5489f5e7d7be85e3f` |
| `scan_tie_risk.py` | 7111 | `51daaf5529a695274a7b63eac3e34d0d1b2fbcdaba966b71e7eecba4a09b3f61` |
| `results_tie_risk.json` | 3338477 | `6091573d59134c9020f7ae3977cdc94adf286b4dd20efeb20b31959e7d88e85d` |
| `validation_report.json` | 737 | `dd9941cbec9e51bb7136b59ca7ae130aa76ef8446a708fc07f3189ba9cb3d91d` |
| `plan_posthoc.json` | 2785 | `59818a3a3bd347cc657a216e25860c1459815656af5cf53a6e86ff42c88a3eee` |
| `analyze_gap_headroom.py` | 14275 | `f57f23b715126284caf74c2ff2e2e62c7f6abd52d628b163bf98d99f58dfd9bb` |
| `results_gap_headroom.summary.json` | 19853 | `824e6b15707e8b46a4398f3096796eda9e484e8d5c61d165c2c7eddb4223df0c` |

`plan.json` carries the pre-written endpoints and decision rule. Its hash
`659b509a...` is recorded in `plan-log.json` with `status:
written_before_run` at `2026-10-18T13:02:35Z`, before the scan executed. The
stored result embeds that plan hash, the imported endpoint and aggregation
source hashes, the three generator/evaluator source hashes and Git HEAD
`666819310a008deb05a6444f70851fd6bcb6446d`.

## Pre-registered scan versus post-hoc gap analysis

`scan_tie_risk.py` and `results_tie_risk.json` are the pre-registered part:
three presets x board sizes 4/6/8 x 120 fresh seeds, 1,080 rules, 6,499 ratio
pairs, zero search, 14.19 s. The decision rule was fixed before execution and
fired as `tie_risk_increases_with_types_per_rule`.

`plan_posthoc.json`, `analyze_gap_headroom.py` and
`results_gap_headroom.summary.json` are **post-hoc and not pre-registered**.
They read only the stored result above; they generate no rule, add no seed and
retune no threshold. `plan_posthoc.json` is published as written before that
analysis ran.

The published summary omits the per-cell `pairs` array (about 10,000 rows) to
keep the repository small. Every aggregate, distribution and conversion figure
is retained. Running the script without `--summary-only` regenerates the
pairs; the private original has them.

## Validation performed

- Replay: `.local_agent/profile-tie-risk-replay-20261018/` reproduces
  `blocks`, `design`, `predictions`, `plan_sha256`, `source_sha256` and
  `overall_decision` identically. `validation_report.json` records 9 cells,
  1,080 rules, 6,499 ratio pairs, 30 tie groups, 0 material ties,
  `tie_detail` counts equal to `tie_groups`, JSON parses and the script
  byte-compiles.
- Tie-definition consistency: the summed `C(k,2)` over tie groups is 32 pairs
  across 30 groups. One pair inside a three-member group (`classic_like` seed
  294038) has bitwise-identical raw scores with a different movement
  signature, so 31 pairs compare distinct values and are recounted as tied;
  the equal-score pair is excluded as capability equality, not compression.
  No pair inside any tie group shares a movement signature.
- Gap analysis self-check: the exact reconstruction reproduces all 5,040
  stored board integers with 0 mismatches, and no tie falls outside
  `exact_gap < 1` in any cell. The summary also separates near pairs with
  exactly equal raw scores (zero gap, 17 across the scan, none a compression
  tie) from distinct-score near pairs, so the published conversion figures use
  the correct denominator. The same summary records the per-rule headroom
  counts below 1/2/5/10/20/50/100 grid units and the scaled ratio-excess check
  `(raw_ratio - 1) * smaller_exact_value`.
- Determinism: re-running the gap script produced a byte-identical file; the
  published summary was produced by running the published copy in place with
  `--summary-only` and matches the private full result minus the `pairs` field.

## Limits

- One seed block per preset, shared across the three board sizes, with repeated
  capability signatures: cells are paired, not independent. The Wilson
  intervals and the exploratory Fisher test are descriptive.
- Per-cell tie counts are 1-7; only the three-preset agreement supports the
  ordering.
- One generator family and one evaluator configuration (`hand_weight=0.9`).
- Ties are a normalization fact, not strategic equality, and nothing here is a
  game outcome.
