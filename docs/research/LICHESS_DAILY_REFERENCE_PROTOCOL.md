# One independently selected daily-puzzle reference

Frozen2026-10-06 BEFORE fetching daily JSON/solution. Existing two exact
Chess contact laws, unit baseline and100000 quantization are fixed; no values,
duration/depth/tie protocol will be selected from this reference. Official
daily puzzle endpoint chooses the ONE sample, not the Agent. No replacement
if unhelpful, unsupported, inaccessible or over budget. No bulk dataset or
Xiangqi human-value holdout. This is engine-reference compatibility on a
curated tactical item, NOT a game strength/WDL or natural-population estimate.

Official sources read before sample acquisition:
https://database.lichess.org/#puzzles (Stockfish-generated public reference,
solution scope, CC0 and CSV first-opponent-move convention);
https://raw.githubusercontent.com/lichess-org/api/master/doc/specs/tags/puzzles/api-puzzle-daily.yaml
and schemas/PuzzleAndGame.yaml, examples/puzzles-getDailyPuzzle.json.yaml
under the same doc/specs root. API game.pgn contains SAN history, puzzle
solution starts with player's answer; require history to selected root at
initialPly+1 and compare optional puzzle.fen first4 fields/lastMove. Do not
reuse CSV's first setup move as API player's first solution move. Unknown
schema/index disagreement closes ingestion instead of guessing a better root.

Acquisition: single unauthenticated GET https://lichess.org/api/puzzle/daily,
timeout20sec/64KiB, preserve exact response bytes/hash/status/time before
parsing; no personal token or plugin credential. Network failure saved; no
automatic retry. Source/parser preflight uses pinned python-chess1.11.2 only,
parses plain SAN tokens (reject tags/comments/variations/setup/unsupported
tokens rather than silently stripping a branch), starts standard Board,
pushes complete prefix at most128. Check every state valid/automatic outcome,
full selected FEN/EP/castling/promoted mask/history. Return advertised first
answer as REFERENCE, not independently proved unique/WDL. No new tables.

Before any Core events, report required history length L and complete root
branch count b. Minimal three-model depth1 comparison, with complete public
root children and two contact plus unit runtime searches, requires at least
L+4*b materializations; if >128, close proposed use attempt. Exact legal-list
cost depends on intermediate parents and must still pass5000 before each
list/membership/push. Independent author preview is charged separately128
pushes/5000 legal entries,15sec, no source future solution rollout. Old closed
exchange/search budgets are not reset. Do not generate/seek another puzzle.

This phase ONLY admits or rejects source/history/cost; no local search or
claim of puzzle success yet. A future Core/history/search producer must be
frozen before executing this SAME admitted source, with actual counters,
full ties, all unsupported/failed states retained. Ingestion may see labels,
so later results are not described as an unseen blind validation corpus;
formula/protocol fixation predates them and prohibits tuning.
