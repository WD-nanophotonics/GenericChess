# Profile rounding ties and movement-signature similarity — evidence copy

Public copy of the evidence behind
`docs/research/PROFILE_TIE_SIMILARITY_20261018.md`.

Provenance: **DEEPSEEK_AUX**, branch `codex/deepseek-aux`, session
`4615243a-f2b9-40ce-a634-266bb0b2e3b7`, 2026-10-18. Auxiliary result; no other
role has rerun it. No strength, playing-quality, utility, human-price or
game-outcome claim.

The study reads only the already published tie-risk result
`docs/research/data/profile_tie_risk_20261018/results_tie_risk.json` and the
private per-pair gap detail `.local_agent/profile-tie-risk-20261018/results_gap_headroom.json`.
It generates no rule, adds no seed, runs no search and changes no threshold.
The full per-pair array (about 6,800 rows) stays private; the 31 tied pairs are
published in `tied_pairs.json`.

## Files

| file | bytes | SHA-256 |
|---|---|---|
| `plan.json` | 2585 | `30d5fc3a74d73c97fa3d1f63ed7327129eb773d318a788817e3fcea35dce5309` |
| `plan-log.json` | 196 | `6a4399fe88cacefeb22a98ba29c51f68d1dfa045ee9b598734cf479421cac7a9` |
| `analyze_signature_similarity.py` | 3886 | `421ff63a1dd146872c392bc4f456fd130f64bb5eee39e65e4634007afa6b1ee3` |
| `posthoc_matched_reference.py` | 8003 | `f04b8d2b6479418fdb7664169390e3c3b7876196a50b5c1caa62c1276332992e` |
| `results_signature_similarity.json` | 5275 | `3c09e980e430d99849e783afba1bf35110bdaf9d035a55ce6832153c3408116e` |
| `tied_pairs.json` | 11950 | `1f19aea8c1f262d7c2d5a2abd617e7377688482a319c5d0be6a11c062f22e1a4` |
| `check_report_consistency.py` | 11233 | `c9186d8a6d6788cfbafde763e3069b98af91dd0d622997f690958cdef16ce9c6` |

`plan.json` carries the pre-written decision rule; its hash is recorded in
`plan-log.json` with `status: written_before_run` at `2026-10-18T13:17:30Z`,
before the analysis ran. The result embeds that plan hash.

## Method

A movement signature is the stored JSON list of movement entries; one token is
one entry (for example `["L",-3,3]`). Similarity is the set Jaccard index
`|A intersect B| / |A union B|` over the two token sets. The tied set is the 31
distinct-score tied pairs from the closed tie-risk study (raw scores differ,
exact normalized gap < 1, stored board integer equal). The reference set is
every distinct-capability pair in the same nine cells: 6,811 pairs, of which
6,499 pass the tie scan's raw-ratio >= 1.05 screen, 295 lie between 1.0 and
1.05, and 17 are exactly equal-scored.

The pre-written rule compares the tied median with the reference 90th and 75th
percentiles. It fires `benign_concentration` if the tied median is at or above
p90, `dissimilar_ties` at or below p75, and `inconclusive_similarity`
otherwise.

## Pre-registered versus post-hoc

`analyze_signature_similarity.py` and the `pooled`/`by_board_size`/`decision`
fields of the result are the pre-registered part. `post_hoc_exactness`,
`post_hoc_robustness` and `post_hoc_matched_reference` are descriptive
additions, not new decisions. The matched-reference block matches each
reference pair on its unordered pair of token-set sizes, so the contrast is not
driven by token-count composition. Tied pairs are removed from the matched
reference before the Fisher comparison.

## Validation performed

- Re-running `analyze_signature_similarity.py` and then
  `posthoc_matched_reference.py` reproduces this result and `tied_pairs.json`
  byte-identically (hashes above).
- The result's exactness block reconciles with `tied_pairs.json`: 25 same token
  set, 15 same move multiset, 0 same signature string, over 31 pairs.
- The Fisher value was recomputed independently with exact rational
  hypergeometric arithmetic in log space, agreeing to displayed precision
  (`6.56875e-18`). It compares tied pairs with non-tied matched-reference
  pairs; shared types and rules mean it is descriptive, not an
  independent-sample test.
- `check_report_consistency.py` recomputes the report's headline numbers,
  the exactness decomposition, the matched-reference counts and every file
  hash in this README: 67 checks, 0 failures.
- The input tie-risk result was itself replayed and audited earlier (105/105
  consistency checks, published `01b4dc98`).

No human evaluation, solver, search or strength measurement is involved.
