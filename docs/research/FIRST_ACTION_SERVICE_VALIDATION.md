# Frozen first-action service validation: Chess failure, Shogi board pass

The post-freeze validator reproduced every source hash and exact
Chess/Shogi vector in
`data/first_action_service_chess_shogi_preref.json` before opening the
unchanged human-reference fixture. Its complete output is
`data/first_action_service_chess_shogi_validation.json`. The formula and
predeclared gates were unchanged; Xiangqi human references were not
read in this stage.

| Chess pawn-normalized ratio | Candidate | Frozen band | Pass |
| --- | ---: | ---: | :---: |
| N/P | 3.7421 | 2.5–3.5 | no |
| B/P | 2.2076 | 2.5–3.75 | no |
| R/P | 6.1245 | 4–6 | no |
| Q/P | 10.5396 | 7.5–11 | yes |

Chess positive-pawn/sensible-order gate passes, but three of four
ratio bands fail. Cosine is 0.9919 and pairwise ordering accuracy 0.9000;
those global similarities do not override the frozen ratio gate.

Standard Shogi *board-mode* values pass the unchanged thresholds:
cosine 0.9919 (minimum 0.95), Spearman 0.9012 (minimum 0.90), and
pairwise ordering 0.9103 (minimum 0.90). The pass has a visible local
error: candidate raw R 11.4018 exceeds TR 10.8458, whereas the
reference places R 1000 below TR 1150. The coarse held-mode vectors
were not compared with a human hand-value reference.

The joint candidate is **rejected** because the Chess gate fails. A
general rule-based explanation, still a hypothesis rather than a
proved cause, is that unbounded positive-path reachability credits a
slow knight for eventual access to every square without accounting for
time or enemy replies, while a single bishop loses half the target
board because of color binding. Optional promotion also counts
multiple first results and can invert Shogi R/TR. These effects come
from the declared service objective, not from coefficient fitting.
No reach discount, target distribution, promotion weight, or held-mode
scale is being changed on this evidence. Because the Chess gate failed,
the existing [ADR-131](../architecture/ADR-131-static-material-redeployment-throughput.md)
holdout sequence keeps Xiangqi *human values* sealed for a later viable
candidate. A rule-only Xiangqi transfer/cost audit may test semantic
coverage without spending that holdout. The mainline remains open and
needs a new independent comparison principle. The exact
`FIRST_ACTION_SERVICE_COMPONENT_DIAGNOSIS.md` comparison further shows
that the pilot equals V2C for all Shogi board types, while Chess B is
halved and N/R/Q are unchanged.
