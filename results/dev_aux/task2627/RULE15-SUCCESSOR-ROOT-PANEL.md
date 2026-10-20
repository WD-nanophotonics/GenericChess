# Rules15 successor root panel

Status: prepared and independently audited; no training registration, training,
or evaluation has started. This is a finite, feature-conditioned panel for one
generated 4x4 rules15 candidate, not a population or full-Generic result.

## Question and decision

Can the existing source-pinned exact-history inventory support a fresh 120-root
training pool and 16-root evaluation pool under the previously authorized
all-in budget, without reusing task2626 roots or outcomes? Yes. The new roots
were selected outcome-blind from separate seed-2433017 family ranges and pass
the independent source/hash/full-history audit. This completes preparation
only; it does not register or start a learner run.

## Evidence

- Candidate: `results/dev_aux/task2433/rules-15.json`, SHA256
  `28736c100941698a4218fb0532b0cc65017a4c9b820070faf1951f7bf523c284`,
  ruleset fingerprint `dfc95a6d4fc8bb14730a3163c71670822b88ee2f20ef6eaf1ea44b5b1c292020`.
- Dynamic source inventory: 9,986 plain and 21 compressed files enumerated;
  10 plain files matched. Reconstructed 118,884 complete-record occurrences
  and 55,385 unique canonical histories. There were no compressed matches.
  Inventory SHA256: `2bcc436be65dd2001df93295bb95ae3d788755b5fd83a653bdeb9ba7c4af528f`.
- The first preparation attempt failed before selecting or writing any roots:
  the preparer counted all rules in the multi-rule task2433 JSON while the
  inventory correctly counted only rules15. The exact failure and correction
  are retained in `preparation-attempt-001-failure.json`. The corrected
  preparer filters on the pinned ruleset fingerprint and carries the original
  0.633-second attempt into the cumulative 180-second preparation cap.
- The corrected preparation selected 120/120 training roots after testing
  2,738 family IDs in `[140000,260000)`, with 10 exact-history rejections and
  3 within-pool duplicates. It selected 16/16 evaluation roots after testing
  205 family IDs in `[280000,300000)`, with 2 exact-history rejections. The
  cumulative measured preparation time was 31.225 seconds. Pool SHA256:
  `03f7184d843bcd7c2f90ff84204516a739125ff26a538f2655078841bd98c17c`.
- Independent audit rehashed every inventoried source, reconstructed the
  exact-history set, replayed all 136 complete histories under the pinned rule,
  and recomputed fixed-scale features and same-owner counts. It found zero
  intersections with known exact histories and zero training/evaluation
  intersections. A legal hand-R unlock action is available in all 120 training
  and all 16 evaluation roots. Audit SHA256:
  `0c740bbda55b4ba55792543eebefec4c69889a088764987b9f283135dacd53d6`.
- Conservative all-in bound remains 5,677.12 seconds against the 6,600-second
  cap and 7,200-second Chat-assessment threshold. Actual preparation and audit
  consumed 31.225 and 23.008 seconds of their respective 180-second envelopes.
  The unspent envelope is not a new experiment budget.

## Limits and next point

Exact canonical records are excluded; descendants, transpositions and
distributional independence are not established. The family selector is
feature-conditioned, so later terminal outcomes describe this finite panel and
cannot be generalized to all rules15 states or the full Generic domain.
UNKNOWN remains censored; only actual rule terminals count as W/L/D. Search
targets train the unchanged fixed-scale TDLeaf learner. Do not register training
or evaluation from this preparation artifact alone; the next task is to review
and freeze a separate source-bound run plan if the same-learner strength
comparison remains the decision-changing question.
