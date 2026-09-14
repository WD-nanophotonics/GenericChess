# F61 Standard-Shogi calibrated seed-59011 R27 — capped run stopped

R27 reconstructed the fixed calibrated child exactly:

- parent `2c98cdd7c9e7b878decb15c2baf91b9d0150c65953e22481ce607d926ae43362`
- child `eb3acd00eb74a268076301f58527b528b6befd500c037bddf5a44e2dab032368`
- calibrated model SHA `a31fe98618519e2cf905302540f071cce48e7a3f9ab04775d8e11e00373f69ee`
- alpha `0.041187666769104674`

The first approved attempt was stopped by Supervisor HOLD because the runner
omitted `ArenaExecutionCaps`; its manifest remains preserved under the original
uncapped runtime namespace as evidence and contains no completed game.

The minimal caps propagation fix was published at sandbox
`16c378c0412cd6f9e2892e843d92bd1e312cef78`, with a manifest regression test.
The capped v2 run used a fresh progress namespace and manifest-confirmed:

```text
per_game_wall_seconds=3600
per_game_nodes=400000
per_game_plies=200
max_stage_games=6
max_concurrent_games=1
stage_wall_seconds=18000
logical_cpu_count=2
```

It stopped at the first game's `per_game_wall_seconds` bound. No complete
game-v1 files were produced, so there are no new pair scores, W/D/L counts, or
combined four-pair decision. No games were added beyond the prescribed block,
and no strength conclusion is claimed.

Decision: `INCOMPLETE_BOUND_HIT_NO_STRENGTH_DECISION`.
