# GenericChess F94-R2 Stage-0 runtime closeout

Status: the one authorized F94-R2 Stage-0 calibration completed on the
published sandbox checkpoint `01898c68fcbf0cb4ecc1ee7b42d0377baad4faaf`.
This is a descriptive, non-authoritative evidence record; it does not pass
Layer D, authorize tuning, or authorize Stage 1.

## Frozen run and retained evidence

The run used plan `f94-r2-stage0-v1` (SHA-256
`bb035b45b084e895cd0cef6938b59848a3d64dc1de0271d65e28cc7e57fce968`) and
the canonical resource-envelope digest
`723d940f118f9ba5a3ab2fb4474b9221484ab620c004fa5c6a4076eb41ac5238`.
It ran exactly six single-worker Arena invocations and twelve games: one
role-swapped pair for each of three frozen tapes for each READY candidate.
The boundary candidate remained the frozen A/C-prerequisite short circuit and
ran zero games.

The complete ignored runtime result is
`.generic_chess_flow/f94-r2-stage0-result.json`, whose raw-file SHA-256 is
`51249bcefca625ae9e306654ca3ad076b6c6ad3ac015ad9a132c3ade62e0915f`.
It is deliberately not versioned because it includes raw run evidence.

## Descriptive outcome

| Candidate | Tape result | Pooled effect (descriptive CI) | Interpretation |
| --- | --- | --- | --- |
| Built-in Western Chess | `DEPTH_CENSORED` on all three tapes | 0.1667 (0.00, 0.25) | The frozen depth-censoring precedence overrides directional interpretation. |
| Built-in Standard Shogi | `POSITIVE_DIRECTION` on all three tapes | 0.4167 (0.25, 0.50) | Directional evidence only; it is not an authority to tune, pass Layer D, or continue the schedule. |
| F86N-R1 boundary V4-3 | `PREREQUISITE_A_C_NOT_PASS` | n/a | Zero-compute prerequisite short circuit, unchanged. |

No invocation reported fallback. Western Chess reached completed depth 12 on
every tape; Standard Shogi's maximum completed depths were 3, 4, and 3.

## Stop boundary

Stage 0 is complete and evaluation stops here. A new explicit Chat and
registered-Supervisor review must decide any Stage 1, full F94-R2 schedule,
tuning, or adjacent compute. This record makes no such request or decision.
