# F72 Root-Pruning Policy-Leverage Probe

Date: 2026-09-11  
Work order: `GENERICCHESS-F72-ROOT-PRUNING-POLICY-LEVERAGE-PROBE`  
Baseline: `f193983819f2b3842e18ea714a89ec2268b18b78`

## Implementation

Added an experiment-only `root_window_pruning` switch to Native semantic
iterative search. It defaults to `false`, preserving the existing full-window
root behavior. When enabled, the first successfully searched root child keeps
the full PV window and subsequent root children use normal negamax alpha-beta
windows. Deeper-node logic, evaluator, terminal/declaration semantics, node
accounting, qsearch, TT behavior, tie breaks, and selected-PV replay remain
unchanged outside this root control surface.

## Fixed-depth parity gate

The gate ran before any learned-policy probe at depths 1 and 2 with no node or
time limit, comparing full-window and root-pruning searches plus repeated runs.
It covered all 20 stable F62 development roots and one Western initial and one
Standard Shogi initial semantic regression position. There were 44 comparison
rows, with exact best action, score, PV, declaration/terminal result, and
repeatability agreement in every row.

Parity status: **PASS**.  
Parity contract failures: none.

## Three-arm bounded probe

The exact 20 stable development roots used the frozen Gen1 D0 evaluator, fresh
runtime and fresh 8 MiB TT per arm, `max_nodes=2000`, `max_depth=12`, and
`qsearch=0`.

| Arm | Configuration | Deep agreement | Nodes | Completed depth | Beta cutoffs |
| --- | --- | ---: | --- | --- | ---: |
| A | full-window, no hint | 1/20 | 2,000 each (40,000 total) | 1: 1, 2: 19 | 0 total |
| B | root pruning, no hint | 2/20 | 2,000 each (40,000 total) | 2: 20 | 1,254 total |
| C | root pruning + seed-59011 hint | 2/20 | 2,000 each (40,000 total) | 2: 20 | 784 total |

Additional causal results:

- A reproduced the cached F62 root_2k action on 20/20 roots.
- A→B decision changes: 1/20.
- B→C decision changes: 0/20.
- C root hints requested/legal: 20/20.
- C attempted iterations: 60; hint applications: 60/60.
- C first-root-action mismatches: 0.
- C repeatability, budget, legality, and qsearch contracts: all passed.
- TT cutoffs: 0 in each arm; full per-root TT probes/hits/cutoffs are retained
  in the ignored raw result.

Classification: **ROOT_POLICY_LEVERAGE_NEUTRAL**.

The primary comparison is C versus B, and both agree with the deep consensus on
2/20 roots. Root pruning itself changed one decision relative to the historical
full-window arm, but adding the 59011 root hint changed none relative to the
root-pruning control. This does not authorize final holdout, Arena, self-play,
external-engine comparison, or further work on this pure root-ordering branch;
the next Courier order controls continuation.

The ignored raw result is
`.generic_chess_flow/f72-root-pruning-policy-leverage-probe/f72_results.json`,
SHA-256
`e99e81ca4af788ed0427264da3aea35d69465dc358eb9217a04136eff3a4ed7e`.
