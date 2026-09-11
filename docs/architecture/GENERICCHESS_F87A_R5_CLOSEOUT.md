# F87A-R5 search-budget and trajectory-independence closeout

This checkpoint records the signed R5 correction order, bound to baseline
`a42e38f9f8aeb6edacdb51c809fbdbe001a212d7`. It does not change ruleset
semantics, training, Arena, or the earlier R2/R3 evidence. The corrected
search control uses the production semantic runtime and the same two built-in
rulesets, with eight small role-swapped games, a depth-1 search prefix, a
128-ply horizon, and a strict 256-node cap per game.

## Explicit budget behavior

If the remaining node budget cannot evaluate the complete canonical root
action set, the implementation discards partial root scores, selects the first
canonical action, and records `BUDGET_FALLBACK`. Each trajectory records its
first budget-exhausted ply, searched-ply count, fallback-ply count, and
fallback fraction. This avoids treating a partial search result as a complete
search decision.

Terminal utility is explicit: winner utility is `+1`/`-1`, a terminal state
without a winner (including repetition) is `0.0`, and `CENSORED` has null
utility. CENSORED remains distinct from draw/repetition.

## Evidence

| Ruleset | Searched plies/game | First fallback ply | Fallback plies | Terminal viability | Sequence independence |
| --- | ---: | ---: | ---: | --- | --- |
| Western Chess | 12 | 13 | 116 | `DEFER` (all four censored) | `DEFER`, 1 unique sequence |
| Standard Shogi | 10 | 11 | 12 | `PASS` (four repetition terminals) | `DEFER`, 1 unique sequence |

The role-swapped deterministic trajectories are identical under this policy;
that fact is now recorded as evidence and is not promoted to an independence
PASS. Search budget usage is 2,048 total nodes, exactly 256 per game. No
abnormal recurrence or legal-action collapse predicate fired. Shogi terminal
utility is `0.0`; Western censored utility is null.

Ignored generated evidence SHA-256:

| Artifact | SHA-256 |
| --- | --- |
| `artifacts/f87a_r5_search_budget_evidence/manifest.json` | `b25432450185655831b4766b6630f63c460a0dc1a717d2b841bf2ecee3852614` |
| `artifacts/f87a_r5_search_budget_evidence/summary.json` | `5afe580d330c3af150d1a03949a6683bba8ca106137b04c86f3fe72c8b6153dc` |
| `artifacts/f87a_r5_search_budget_evidence/reports.json` | `4d90e48c132b14a97f12bf522c73a7f0c88127ffeae4aa893c423638ee88ad6a` |

No promotion is authorized by this closeout.
