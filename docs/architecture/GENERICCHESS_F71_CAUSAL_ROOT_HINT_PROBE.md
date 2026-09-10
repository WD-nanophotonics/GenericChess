# GenericChess F71 causal root-hint probe

This checkpoint defines the bounded experiment for
`GENERICCHESS-F71-CAUSAL-ROOT-HINT-PROBE`. It asks one causal search-control
question: with the frozen Gen1 D0 evaluator and the same 2,000-node Gen1
search, does a seed-59011 policy action used only as a root move-ordering hint
increase agreement with the already cached deep consensus?

## Frozen scope

- Baseline repository: `a180486b6a709a456d4a55a44a35ef716d4e4e20`.
- Ruleset and evaluator: F62 Standard Shogi semantic rules and accepted Gen1
  D0 checkpoint `d0e6a02482bb316e657ec6ef5c4f9379e6e7946d2da1a9a38647175567aecab4`.
- Roots: exactly the 20 F62 development roots with `root_40k == root_80k`.
  Fit and final-holdout roots are excluded.
- Arms: fresh runtime and fresh 8 MiB TT for each baseline/hinted arm,
  `max_nodes=2000`, `max_depth=12`, no qsearch, and no learned ordering below
  the root.
- Hint: seed 59011 scorer's top legal root action. The experiment-local
  capsule bridge writes only a matching root TT key with `depth=0`, `score=0`,
  `bound=NONE`, and `has_action=true`; it cannot provide an exact/bound
  cutoff or a score. Native position and TT layouts are checked against the
  runtime before the write.
- Repeatability: the first hinted root is run twice with the same fresh-arm
  contract and the action, score, node count, depth, and termination mode must
  match.

## Classification

`ROOT_HINT_CAUSAL_SUPPORTED` requires every baseline to reproduce F62's cached
2k action, every contract check to pass, and hinted/deep agreement to be
strictly greater than baseline/deep agreement. Equal agreement is
`ROOT_HINT_CAUSAL_NEUTRAL`; lower agreement is
`ROOT_HINT_CAUSAL_NEGATIVE`. Any baseline mismatch, illegal hint, budget
mismatch, layout mismatch, or failed repeatability check is
`HARNESS_MISMATCH`.

The machine-readable result is kept in the ignored F71 runtime namespace at
`.generic_chess_flow/f71-causal-root-hint-probe/f71_results.json`; each root
has an atomic progress record in its `progress/` subdirectory. F71 does not
authorize Heavy, Arena, self-play, retraining, production refactors, or
promotion. A positive result requires a later, independently approved
final-holdout confirmation.

## Formal result

The formal run completed on the 20 stable development roots with classification
`ROOT_HINT_CAUSAL_NEUTRAL`.

| Measure | Result |
|---|---:|
| Baseline cached F62 root_2k reproductions | 20/20 |
| Baseline/deep-consensus agreement | 1/20 |
| Hinted/deep-consensus agreement | 1/20 |
| Root decisions changed | 0/20 |
| Toward-deep / away-from-deep / lateral | 0 / 0 / 0 |
| Contract failures | 0 |
| Arm node counts | 2,000 for every arm |
| qnodes | 0 for every arm |
| Hinted TT cutoffs | 0 for every hinted arm |
| Hinted TT hits | 1,368 aggregate |

The one-root repeatability check matched on action, score, node count,
completed depth, and termination mode. The raw result is
`.generic_chess_flow/f71-causal-root-hint-probe/f71_results.json` with SHA-256
`f2fa37a0452a63a6d40efa40122804f8b72d468885b1a523e0ec6389eca7cb38`; it is
runtime evidence and remains outside Git. This neutral result does not
authorize final-holdout confirmation, Arena, or promotion.
