# Fixed-prior positional feedback, 2026-10-07

Generated Standard Chess development evidence. The current interpretation is in
`../../research/data/chess_positional_feedback_20261007.json` and
`../../research/CHESS_DEVELOPMENT.md`; this directory is immutable recovery data.
It is not active policy, a task backlog, independent holdout evidence or admission
of a generic evaluator. All adverse and unfinished cells remain in the raw data.

- `raw.zip`: exact diagnosis, both declared game cohorts and independent replays,
  plus the separate fixed-node root28 declaration/results.
- `sources.zip`: exact producers and existing shared adapter/serializer, frozen
  opening suite and material variant configuration. No private account/Slack data.
- `index.json`: per-entry byte counts and SHA256; each ZIP was actually extracted
  into a temporary directory and every recovered file rehashed before publication.

Recovery: extract raw/sources into a new isolated
`<repo>/.local_agent/positional-feedback-20261007` directory. Scripts refuse output
overwrite, so preserve recovered outputs separately before a deliberate new run.
Place the recovered suite at `.local_agent/see-opening-20261007/suite.json` and
configuration at `.local_agent/mature-search/material-variants.ini`. Restore the
qualified native exchange, activity and classical builds from the source/build
packages referenced by `chess_exchange_20261007.json`,
`chess_activity_games_20261007.json` and `chess_classical_20261007.json`. Their
GPL source/license and pinned upstream commit are retained there, not replaced by
this package. Binaries are not in this ZIP. Restore the pinned Stockfish17.1
reference and existing Python Chess/Core environment; verify every executable,
configuration and adapter hash against the relevant declaration before running.

The ordinary producers use full starting-position history, rather than importing
a bare midgame FEN. Run `games.py`, then `priors.py`, then `fixed-nodes.py`, without
another timed engine/test job. Afterwards `replay.py` and `replay.py priors`
independently check Core legal sets, full histories, selected PVs, final states and
actual draw witnesses. `collect.py` rebuilds the portable report and verified ZIPs
only in an empty destination. A new run remains a separate exposed development
attempt, never a replacement for these frozen results or a restored holdout.

Classical evaluation is a human-engineered diagnostic bundle. Changing prices
also affects its PSQT/material/SEE/pruning; this is not an isolated positional term
or pure prior effect. Reference2400 is an engine setting, not a measured rating.
