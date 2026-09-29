# Safe R5 state identity does not rescue exact random continuation

**Unknown.** The previous exact uniform-action computation used the
entire `GameState` as a memo key and aborted at 10,000 states. Could
removing irrelevant path-history fields make the same computation cheap
without changing its value?

The frozen R5 exact solver reports
`history_key_mode=REPETITION_COUNTS_SUFFICIENT`, and this RuleSet has
`repetition_policy="draw"`. Core's `search_state_identity` contains the
position, ply count, and repetition counts while omitting the raw
history for this policy. That is the existing authoritative safe key;
it preserves the repetition and six-ply adjudication inputs.

`scripts/audit_r5_random_safe_key.py` computes the exact random-policy
terminal distribution for the frozen root's sole exact-LOSS action,
using this key and the *same* 10,000-state and five-second bounds. It
checks the fixture SHA, DEVELOPMENT split, action label, and repetition
policy before expansion. It returns a structured cost abort rather than
an incomplete probability.

| Observation | Result |
| --- | ---: |
| Distinct safe identities reached | 10,000 |
| Memo hits before abort | 0 |
| Abort cause | State limit, before time limit |
| Exact random outcome distribution | Unavailable |

The first 10,000 encountered states therefore offered no reuse under
the safe key. This is an observation about this depth-first traversal,
not proof that the complete graph has no transpositions. It explains
why simply dropping raw history does not repair the previous cost
abort. Raising the cap without a new algorithmic argument would repeat
the unsuccessful path. The seeded 100-sample-per-action pilot remains
descriptive; no static material coefficient or Xiangqi human value was
computed.
