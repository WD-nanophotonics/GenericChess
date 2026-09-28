# Search deployment contract audit

**Unknown.** Do the actual Chess and Standard Shogi evaluator entry points and budgets define one fixed search horizon and one rule-given set of leaf states for a static material prior?

**Smallest observation.** Trace the UI decision path and the alternative native semantic search boundary in code. No game search, material table, Xiangqi value, or coefficient fitting was needed. Five focused budget/search tests passed on 2026-09-29: `tests/test_ai_budget.py` and `tests/test_ai_search.py` with the fixed-node, fixed-time, auto-time, depth-passthrough, and depth/node-limit selection.

## Observed contracts

| Path | Budget and evaluation point | Consequence |
| --- | --- | --- |
| UI Chess and Shogi | `ui/main_window.py` constructs the rule-generic `AlphaBetaPlayer`; `ui/controller.py` calls `allocate_search_limits` per move. `ai/budget.py` selects fixed nodes (5k/50k/200k presets), fixed time, or clock-derived time; `max_depth` is optional. | The same player implementation can serve both RuleSets, but the configured cap and achieved depth are deployment choices and depend on position, clock, and budget. |
| Python alpha-beta | `ai/alphabeta/search.py` deepens from 1 to the configured cap (64 when absent) until a budget abort, retaining the last completed iteration or a legal fallback. At nominal depth zero it enters quiescence when enabled; default `SearchLimits` has quiescence depth 4 and hard cap 8. `quiescence` calls the evaluator for stand-pat at non-check nodes before deciding whether to expand noisy actions. | Evaluator calls are not confined to one nominal-depth frontier or only to final quiet leaves. Different iterations and tactical continuations contribute calls. |
| Native semantic search | `native/semantic_engine.py` requires explicit `max_depth` and rejects nonzero quiescence. `_native/native_module.c` calls `gc_semantic_probe_material` when remaining depth reaches zero and deepens iteratively under node/time budgets. | This is a different evaluation boundary. It is an available research/engine path, not the UI path shown above. |

The tests establish budget mapping and a fixed-depth versus node-limited Python search on a small fixture. They do not enumerate all evaluator calls or measure actual Chess/Shogi frontier frequencies. The code path itself establishes that a single fixed horizon is not an existing universal deployment contract. Even a fixed `max_depth` is a cap, not a guarantee that its iteration completes.

The 2026-09-29 Tokyo-day Chat advisory independently pointed to bounded-search evaluation and quiescence as algorithm-dependent. Its literal primary links include [Shannon's *Programming a Computer for Playing Chess*](https://www.computerhistory.org/chess/doc-431614f453dde/) and the [Stockfish search implementation](https://github.com/official-stockfish/Stockfish/blob/master/src/search.cpp); the latter also describes iterative deepening under stopping limits. These sources are background, while the GenericChess claims above rest on inspected local code and tests. The advisory is not a rule for selecting a formula.

**Decision.** Do not call a depth-`d` uniform leaf ensemble the deployment distribution of the existing engine. A search-use validation contract must name the backend, search limits, quiescence policy, root set, and root-decision loss before observing material-value references. A prior intended to be game-independent should also report sensitivity across at least the Python and native semantic evaluation boundaries, rather than letting either backend define its coefficients silently.

**Next bounded step.** Specify a tiny, frozen Chess-first decision test with two predeclared search operators: Python alpha-beta at an explicit depth and quiescence setting, and native semantic search at an explicit depth with quiescence zero. Check whether the same candidate prior changes root choices under the two operators on a small exact-outcome fixture. Keep Standard Shogi as a control and Xiangqi material values sealed. If the comparison requires inventing or fitting a prior, state that boundary before running it.
