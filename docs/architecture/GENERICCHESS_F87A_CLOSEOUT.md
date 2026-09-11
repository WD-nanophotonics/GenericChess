# F87A closeout

Work order: `GENERICCHESS-F87A-RULESET-QUALIFICATION-TOOLBOX-FOUNDATION`

Published sandbox checkpoint: `991bc7e70e68a4f5c7242c9a6f138fe910ed0757`

Baseline: `a33ff404d33aef1d6717fc62e05337ae92691540`

## Delivered

- Shared `generic_chess.benchmark.qualification` contract for Layers A–E.
- F86M/F86N structural helper reuse through the shared probe.
- Explicit `CENSORED` max-ply handling and `UNRESOLVED` classification semantics.
- Deterministic PolicyTape role-swap calibration harness with branching, collapse, capture/check, terminal, and opening-identity diagnostics.
- Frozen six-control PREP schema and bounded result driver.
- Layer D Arena/strength-response and Layer E learning adapters represented and explicitly deferred.

## Evidence

The generated evidence remains ignored per repository policy and was not force-added to Git:

| Evidence | SHA-256 |
| --- | --- |
| `artifacts/f87a_ruleset_qualification/manifest.json` | `70c294eac433bc1f5c92b30cb4c09b837f09d89b4f5ff645d089b9698d516ab6` |
| `artifacts/f87a_ruleset_qualification/summary.json` | `cacc67e8a7fc299a182e9f7e68556fbe34dc5bdc7c504072af93ea6d060df9ed` |
| `artifacts/f87a_ruleset_qualification/reports.json` | `7cff20906bee2854984c9a84d4e88837c03ca42abf31ce8276a5bc4677caa17e` |

The bounded calibration covered F86C legacy V4-3, F86I full-reverse V4-3, F86N-R1 V4-3 and V5-3 boundaries, built-in Western Chess, and built-in Standard Shogi. All overall reports are `DEFER`; the semantic built-ins defer Layer C because the legacy `GameSession` is not their semantic-action runtime. Search nodes, Arena games, training steps, and Heavy jobs were all zero.

## Verification

Focused regression suite: `30 passed` across F87A, F86A, F86I, F86M, and F86N tests.

Courier publish verification: local and `origin/sandbox` both resolve to the full checkpoint SHA above.
