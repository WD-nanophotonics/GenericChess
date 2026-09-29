# Frozen first-action service outputs before human-value checks

The preregistered [pilot protocol](FIRST_ACTION_SERVICE_PILOT_PROTOCOL.md)
was implemented and published at sandbox commit
`bd4d8410b06687628796b24c07284210afcb14b9`. The exact Chess and
Standard Shogi outputs, input SHA-256 values, RuleSet fingerprints,
coverage exclusions, and positive-event counts are in
`data/first_action_service_chess_shogi_preref.json`. The freeze test
recomputes both exact outputs and verifies every listed source hash.
This artifact imports no human reference and contains no Xiangqi
material score or reference.

| RuleSet | Raw board service by current type, approximate | Raw held service |
| --- | --- | --- |
| Chess | P 1.2248; B 2.7039; N 4.5833; R 7.5013; Q 12.9091 | none |
| Shogi ordinary | P 0.9688; N 1.3778; L 2.6639; G 4.4778; S 4.8545; B 8.6178; R 11.4018 | P/L 53.7778; N 47.0556; S/G/B/R 60.5 |
| Shogi promoted | TP/TN/TL/TS 4.4778; TB 9.0456; TR 10.8458 | none |

These numbers are exact fractions in the JSON; decimals here only aid
reading. The reporting gauge is Chess Q and Shogi ordinary R. All 13,448
Chess and 35,872 Shogi board event keys have positive V2C probability;
exchangeability normalization reduces them to 130 and 248 distinct
probability evaluations respectively. The full audit finished within
the 60-second cap for each game (under two seconds in this local run).
The evaluator itself needs only a type/mode table lookup per token.

Two strong structural consequences are visible before human-value
validation. Shogi's coarse held-mode service is several times its
board-mode service because most hand drops are available from one hand
state. Also unpromoted R scores above promoted TR: optional promotion
creates additional distinct first-action results for R, even though TR
has expanded movement geometry. These are predictions of the frozen
route-count objective and possible reasons it may fail as a material
proxy. They must be reported in validation, not corrected after the
fact. Shogi pawn nifu/drop-mate and dynamic safety remain exclusions.
