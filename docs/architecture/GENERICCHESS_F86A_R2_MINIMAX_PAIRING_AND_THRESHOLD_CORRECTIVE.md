# GenericChess F86A-R2 minimax, pairing, and threshold corrective

Status: corrective closure candidate. F85 remains HOLD; no Heavy, C2 fitting,
large scan, or formal ladder tournament was run.

Baseline: `0d16daf4e0dd671327a9c2dfb8317eeb0ca7b522`.

## Corrective changes

The terminal-only probe now uses a root-perspective MAX/MIN node combiner:

- root-player nodes maximize W/D/L values;
- opponent nodes minimize them;
- a decisive partial proof is retained only when MAX has a known win child or
  MIN has a known loss child;
- any unresolved child that could change the conclusion keeps the result
  unresolved;
- cutoffs are never converted to draws;
- depth remains capped at 4 and nodes at 256.

Focused tests cover known MAX/MIN child sets, unresolved-child propagation,
and the actual bounded probe's node cap.

Side-bias measurement now uses deterministic policy-paired games on the same
ruleset and opening. For each pair, Game 1 assigns policy A to player 0 and B
to player 1; Game 2 swaps those policy streams. The profile reports
`paired_game_count` as the number of pairs, `played_game_count` as twice that
number, first/second-player scores, and
`side_bias_magnitude = abs(first_player_score - 0.5) * 2`. The 180-degree
owner/color transform is retained only as an opening/action symmetry
diagnostic; it is not counted as a paired game or outcome evidence.

The Agent Ladder API now distinguishes `evaluate_ordered_scores` (a global
score pre-check) from `evaluate_adjacent_matchups`, which accepts actual
`(weaker, stronger) -> paired stronger score` observations. Disordered or
negative adjacent advantages yield zero skill discrimination; incomplete
paired evidence yields `None`.

Classification keeps provisional diagnostics separate from authority. Raw
diagnostic flags use conservative defaults for visibility, but a flag can
affect returned classification only when its own threshold key is explicitly
provided. With no explicit threshold, classification is `UNRESOLVED`.

## Bounded accounting for this checkpoint

For the focused profile test: generated rulesets = 1; policy-paired game
count = 3; actual played games = 6; tactical probe positions = 1; total
tactical probe nodes are hard-capped at 256 (the smaller direct probe test is
capped at 32). F85 actual compute = 0. The focused test command covers the
F86A/R2 test module plus retained F85 lane/acquisition contract tests and the
benchmark smoke suite; its exact pass count is recorded by the publish gate.
No benchmark-scale wall-time claim is made.

The next approved direction is F86B cheap quality calibration using a few
fixed-seed 4--4 and 5--5 games, followed by population calibration of explicit
admission thresholds and real adjacent ladder matchups. F85 Standard Shogi
teacher acquisition stays HOLD.
