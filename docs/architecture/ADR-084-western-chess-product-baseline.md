# ADR-084: Western Chess product boundary and AlphaBeta reference baseline

Status: accepted by F24H

## Decision

The perft-certified Western semantic RuleSet is now a production definition at
`generic_chess/rules/western_chess.py`.  The generic
`compile_ruleset_for_execution()` dispatcher selects legacy compilation for
legacy definitions and semantic compilation for non-empty semantic actions;
there is no semantic-to-legacy fallback.  `western_chess` is the sole built-in
catalog entry and is available through `--builtin-ruleset western_chess`.

The CLI also accepts generic visible coordinate aliases such as `e2-e4` and
`a7-a8=Q`.  It checks exact lossless action strings first and rejects an alias
when multiple semantic actions share it.  Semantic public actions retain their
pattern/geometry identity in GameRecord serialization and replay.

## Certification and identity

Production and F24F RuleSet canonical serialization are identical, including
the gameplay fingerprint:

`7bc6cf3179f4eaea30b205576b9032dca47a16803e9cc8b3e29405cb1e820b35`

The production builder reran all six F24G canonical perft positions exactly:

* Initial: 20 / 400 / 8902 / 197281
* Kiwipete: 48 / 2039 / 97862
* Position 3: 14 / 191 / 2812 / 43238
* Position 4: 6 / 264 / 9467
* Position 5: 44 / 1486 / 62379
* Position 6: 46 / 2079 / 89890

## Search baseline

The reproducible evidence is in
`tests/fixtures/f24h_western_search_baseline.json`, with manifest SHA-256
`55b4e4c5253fae932bf201675b93636c80b68b7335a581711d2d475d4c4aa55b`.
It records fresh-player fixed-node runs at 128, 512, and 2048 nodes (twice
each), plus three repetitions at 0.25 and 1.0 seconds for every canonical
position.  Fixed-node decisions were deterministic, roots remained unchanged,
and every returned action was legal.  The Native provider is expected to fail
closed for the certified `subject_ref` shape; the recorded mode is
`PYTHON_AUTHORITY_FALLBACK`.

This is a descriptive internal AlphaBeta/evaluator-v1 baseline.  It makes no
claim about playing strength, external-engine agreement, or Native support.
No evaluator coefficients, search policy, semantic schema/IR/executor, Core
transition, runtime, or master branch was changed.

## Result

`WESTERN_CHESS_PRODUCT_READY_BASELINE=true`

The next boundary is
`F25_STANDARD_SHOGI_PRODUCTIZATION_AND_DUAL_STANDARD_SEARCH_BASELINE`.
