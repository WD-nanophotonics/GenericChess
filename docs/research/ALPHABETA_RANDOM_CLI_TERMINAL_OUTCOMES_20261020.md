# AlphaBeta vs-random CLI terminal outcome accounting — 2026-10-20

## Decision question

Does the existing `python -m generic_chess.ai.cli.benchmark_alphabeta --vs-random`
consumer preserve generic session-level declarations and distinguish an
external ply cutoff from a rule-defined draw?

## Reproduction

Using the existing `_claim_ruleset()` declaration fixture, one no-action root
WIN was selected by `AlphaBetaPlayer`. Before the change, the CLI stopped with
an ongoing `GameSession` and printed `AB wins: 0`, `draws: 1`, `avg plies: 0.0`.
The player result carries `choice_kind="DECLARATION"` and a declaration object;
it is not an ordinary action. Separately, the CLI's hardcoded 400-ply safety
cutoff can leave a session ongoing, which the old final `else` also counted as
a draw. Neither result is supported by the session's rule adjudicator.

## Scoped repair

The CLI now applies selected declarations through `GameSession.declare()`.
Final outcomes with a winner are attributed to AlphaBeta or Random by actual
color; explicit rule draws remain draws; `NO_CONTEST`, a failed declaration,
other no-result states and the external 400-ply ongoing cutoff are unresolved.
The result helper follows `SessionResult.winner` rather than duplicating a
winner table. The loop and 400-ply safety bound are unchanged.
The one-shot CLI report also renders a declaration as
`<declaration:<id>:<outcome>>` rather than misleadingly printing `action=None`.

The deterministic two-game control now reports one AlphaBeta declaration win,
one unresolved 400-ply game, zero draws and average 200 plies/game. The earlier
single-game pre-fix transcript is preserved above as the before case. Tests
cover winner/draw/unresolved categories and the real root declaration.

## Validation and claim boundary

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider tests/product/test_benchmark.py tests/product/test_generic_declaration_semantics.py tests/product/test_generic_no_progress_draw.py
```

Result: 68 passed. This repairs diagnostic accounting only. It changes no
search behavior, evaluation, price, budget, default or scientific conclusion;
the vs-random output remains a smoke diagnostic, not an Elo or strength claim.
