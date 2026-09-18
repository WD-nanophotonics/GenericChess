# F119 Shogi Gumbel completed-Q Arena4 confirmation

## Decision

`SHOGI_GUMBEL_COMPLETED_Q_ARENA4_REJECTED`

The exact F118 child policy was evaluated against its frozen parent in four
role-swapped opening pairs. All eight games satisfied the runner's validity
contract, but the child did not outperform the parent: pair scores were
`[0.0, 0.0, 0.0, 0.75]`, mean child score `0.1875`, with one child-better
pair and three child-worse pairs. No promotion or Arena8 follow-up is
authorized by this result.

## Frozen inputs

- Work order: F119 Arena4 confirmation.
- Frozen checkpoint: `f0ca40ce93b54d15ca5d72c9870a9d77977b82ec4f7380c294c08c6e1c6a82ec4`.
- Parent policy SHA-256: `2357472db2d8b131fce2b78b51b1bb7cdacfb84a34b6dcc4ab8ee2c2d7cc3b955`.
- F118 child policy SHA-256: `45281f8ccccf557fdbe2edd74fc0822dedbff209c2178125dafab3c883aefdb3`.
- Arena opening seed: `1190801`, selection offset `0`.
- Arena search seed contract: `1190901 + 10000 * game + ply`; the contract
  was valid for all eight games.
- Search budget: exactly 64 simulations per non-terminal search, with the
  F118 completed-Q policy and maximum game length of 512 plies.

## Game outcomes

| Game | Child side | Valid | Result | Winner | Plies |
| ---: | ---: | :---: | :--- | ---: | ---: |
| 0 | 0 | yes | checkmate | 1 | 160 |
| 1 | 1 | yes | checkmate | 0 | 143 |
| 2 | 0 | yes | checkmate | 1 | 196 |
| 3 | 1 | yes | checkmate | 0 | 223 |
| 4 | 0 | yes | checkmate | 1 | 140 |
| 5 | 1 | yes | checkmate | 0 | 219 |
| 6 | 0 | yes | checkmate | 0 | 410 |
| 7 | 1 | yes | no-contest/repetition | none | 497 |

The no-contest game remained protocol-valid: every executed search used the
required budget, selected a legal action, and passed the finite-support/Q
checks. Its half-point was included in the role-swapped pair score.

## Reproducibility and evidence

The runner also completed eight deterministic regression rows, each with 64
simulations and exact repeated-search agreement. The requested command was:

```text
generic-chess-flow.cmd heavy --resource-envelope .generic_chess_flow\f119-arena4-envelope.json -- .venv\Scripts\python.exe scripts\f119_shogi_gumbel_arena4_confirmation.py --checkpoint .generic_chess_flow\f109-inputs\standard_shogi.json --parent-report .generic_chess_flow\f111-offline.json --child-policy .generic_chess_flow\f118-shogi-gumbel-clean-replication-arena2\candidate_policy.json --output .generic_chess_flow\f119-shogi-gumbel-arena4\report.json
```

The raw report is retained under ignored workflow evidence at
`.generic_chess_flow/f119-shogi-gumbel-arena4/report.json`; this document is
the durable result.
