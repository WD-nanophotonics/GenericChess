# GenericChess F94-R3 nonbinding depth-calibration runtime closeout

Status: the single authorized R3 calibration completed on published sandbox
checkpoint `569aa17aff89f30ba7d1fb8d5e40c4a084883f58`. This remains descriptive,
non-authoritative evidence: it does not pass Layer D, authorize tuning, Stage
1, the 216-game schedule, or any adjacent compute.

## Frozen run and retained evidence

The run used plan `f94-r3-depth-calibration-v1` (SHA-256
`aa482aa72eb69c9e6bb4b08a44877da16a782b36af18a49f1048421ea3ea864f`) and
canonical resource-envelope digest
`444556c0d1149b3fda76bd89506d84bfab3656f62f3d170d312d147f3e244f88`.
It ran exactly six single-worker Arena invocations and twelve games: one
role-swapped pair on each of three frozen tapes for each READY candidate.
Boundary V4-3 remained the frozen A/C-prerequisite short circuit and ran zero
games.

The complete ignored runtime result is
`.generic_chess_flow/f94-r3-nonbinding-depth-calibration-result.json`, raw-file
SHA-256 `5d254cde8539f0c305a0df0f44cfb7cc9de08c903394dfacccc1f17fd7f3ac82`.
It is deliberately outside Git because it contains raw run evidence. The
result schema records `r2_observations_pooled=false`.

## Descriptive outcome

| Candidate | Tape result | Pooled effect (descriptive CI) | Interpretation |
| --- | --- | --- | --- |
| Built-in Western Chess | `DEPTH_CENSORED`, `POSITIVE_DIRECTION`, `DEPTH_CENSORED` | 0.1667 (0.00, 0.25) | Two tapes reached the frozen depth-64 ceiling (max depths 64, 56, 64); censoring overrides the directional result. |
| Built-in Standard Shogi | `POSITIVE_DIRECTION` on all three tapes | 0.4167 (0.25, 0.50) | Directional evidence only; it is not Layer-D or tuning authority. |
| F86N-R1 boundary V4-3 | `PREREQUISITE_A_C_NOT_PASS` | n/a | Frozen zero-compute short circuit, unchanged. |

No invocation reported fallback. R3 removed the R2 depth-12 confound but did
not yield an uncensored Western measurement under the depth-64 protocol.

## Stop boundary

The registered stop rule applies: R3 stops after this result. A future route
must first separately audit why Western Chess remains depth-censored at 64; it
must not use more Arena samples to paper over that measurement issue. Any
future compute, Stage 1, schedule expansion, tuning, or promotion needs a new
explicit Chat and registered-Supervisor review.
