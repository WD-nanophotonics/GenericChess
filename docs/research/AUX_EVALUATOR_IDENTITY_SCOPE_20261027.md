# Actual evaluator identity and Native observability — 2026-10-27

The inspected legacy Native search consumes integer material tables, not a checkpoint ID. Different physical weights or training metadata can therefore describe the same numerical search input. Its TT isolation comes from a fixed-evaluator engine owning its table, not from a config hash in each TT key. Two misleading docstrings are corrected; no search, evaluator, learner update, cache key or default is changed.

This is source evidence about a named existing consumer, not a new teacher experiment, action-invariance measurement, speed result, strength result or formal verification of the C engine. The previously closed teacher admission, arena and material-projection questions remain closed. No old games, 404/1520 returns, H6, PVS or frontier campaign is reopened.

## Fixed sources and consumer

Inspected own source is sidemission@ef4ad7f8803e9413552c335cffee1ec7b2cbb3b9, before the documentation correction. Current fetched mainline is sandbox@7cbdbbb3aa21b8f0ca4c66e3e1cd7d5712bf91bd; its delta from the previously covered source is only the Pro review, with no shared rules/search/terminal/history/runtime delta to import. Latest Pro review blob fda5dfc2fb4d16ff285e39b56bf33f9ed91697c5 remains adopted: no general TD theory expansion or new teacher campaign, and PRIMARY retains endpoint qualification. Source file Git blob identities:

| Path | Git blob at the inspected own source |
| --- | --- |
| generic_chess/native/compiler.py | 174fdd5d235799d42d971eeabb1a8d66d77b9042 |
| generic_chess/native/engine.py | 5960f1fd0bc8416a2dfebe0779991a63c2ed340e |
| generic_chess/_native/native_module.c | bff85ff4cb17cc779d8b5a403cd00c72c33a344f |
| generic_chess/_native/native_eval.c | d76f24fec6c913e557a0e7a263b2b044a26774e7 |
| generic_chess/_native/native_search.c | 5376072c5bdba36ed9aa51632628a93876bac09b |
| generic_chess/_native/native_tt.c | 202f7904b9ffb51c320b89fa03518f33425f82bb |
| generic_chess/learning/material.py | 29a0b289bef5061ab342b84bb1b58206c28078a7 |
| generic_chess/learning/mainline_search.py | 9e2f1370922496e109125a56dd981ac78854d237 |

The actual legacy route is diagnostics._search_position -> _engine_for -> compile_native_evaluation -> NativeSearchEngine -> native_iterative_search -> gc_iterative_search. _search_position replays the corpus action_history into GameSession, creates a fresh engine per position, requests depth64/node budget/q0, and sets no time limit or external cancellation token. This is not the own incremental learner's mainline_search route.

The earlier checkpoint-units.json control already supplies A1/B1.4 and A1/B1.49 with different checkpoint identities but equal legacy board arrays [1,1]. That control is not rerun. The present work resolves a previously unexamined question: could the differing identity itself still alter the actual engine through TT, ordering or hidden state?

## What the legacy kernel reads

material.py quantized_board/quantized_hand apply int(round(weight * material_scale)) in native type order. checkpoint_id includes generation, parent, training hash, counts, seed and other provenance in addition to physical weights. config_hash includes that checkpoint identity. Consequently neither an ID difference nor raw weight L2 is an operational numeric difference.

compiler.py builds board_value, hand_value, promotion_gain, mate_score, mate_threshold, max_static_eval and the metadata strings. native_module.c:1542-1623 parses/copies them into GCEvalPayload; native_eval.c:6-24 copies them into separately allocated tables. Material evaluation (native_eval.c:31-63) reads current board types, base-hand counts, side to move, board/hand values and max_static_eval. Search terminals read mate_score; TT score distance conversion reads mate_threshold. The inspected legacy search has no promotion_gain read; retaining equality of that extra numeric field is a conservative sufficient input condition.

A bounded full search of _native C sources for config_hash/evaluator_version finds their construction/copy references, not a behavioral read in legacy evaluation, search, TT lookup or ordering. This does not establish safety for an arbitrary future implementation or every external/raw capsule user.

native_module.c:1810-1851 allocates GCSearchEngine, binds its rules/eval pointers and creates its own initially zeroed TT. The Python engine retains the rule/evaluation objects. The inspected public engine methods offer search, clear_tt and tt_info; no evaluator-rebinding method is present. Changing a Python checkpoint after construction does not recompile/rebind the already copied C evaluation table. The supported comparison creates another engine rather than trying to change that binding.

native_tt.c keys/indexes entries using position hashes, repetition context, ply and history length. Evaluator hash/version is absent. Fresh engines with equal capacity have equal empty TT contents/generation; equal warm-state reasoning would additionally require equal relevant prior query/TT state, not merely the same current root. TT replacement follows generation/depth/fixed-way order. Keeping old TT bounds while changing numeric evaluations would require a separate invalidation contract; a differing ID alone cannot enforce it.

## Conditional computational prediction, with explicit limits

For two successful executions with the same fixed binary/platform and valid inputs, hold constant:

- the complete rules and packed full-history root, including session-level terminal handling;
- every behaviorally consumed numeric evaluation field and native type mapping;
- fresh/equivalent engine TT contents, capacity and generation;
- depth/node limits and all search options;
- absence of wall-time cutoff, external cancellation, concurrent mutation and allocation/other execution failure.

Under those conditions, the inspected source predicts equal computational outputs despite metadata-only checkpoint differences. Context/counters are initialized, legal actions are canonically sorted by packed action, ties use that same numeric action order, recursive make/unmake and numeric evaluation see equal inputs, TT probes/replacements see equal state, and the exact node-stop branch sees equal node counters. By induction through these state transitions, the next branch, TT write and completed-iteration publication remain equal. The canonical fallback is also ID-independent. Relevant sites are native_search.c:12-15,88-115,117-267,275-396 and461 onward.

This predicts equal selected action, score, completed depth, PV and computational counters for this qualified comparison. It does not predict equal elapsed_seconds: native_module.c measures real kernel time. Time-limited or externally cancelled calls can stop at different points even with equal numeric payloads. The diagnostic caller avoids those cutoffs, but an arbitrary persistent/time-limited consumer need not. Full computational equivalence is a source inference, not an executed paired search or a theorem that the search itself is minimax-correct. Numeric table equality also says nothing about terminal WDL correctness, policy quality or the sufficiency of the material representation.

Conversely, different integer tables only establish the potential for a numeric effect. A changed coefficient can belong to an absent type, cancel in the visited features, be clipped, change an unselected score, or preserve the chosen ordering. No stronger action or utility effect is asserted. Same raw ranking/ratio alone neither establishes nor excludes that effect.

## Why this does not suppress the own floating learner

The own mainline_search.Material.evaluate calls Model.raw on the declared material feature vector and supplies that object as AlphaBetaPlayer.evaluator_override. AlphaBetaPlayer passes it into run_root_search. The Python _bounded_static_score uses min/max clipping; its int annotation is not an int conversion. The Python TT stores the returned score without integer coercion. Model.raw returns the floating dot product and rejects nonfinite/terminal-band values. The adapter creates a new AlphaBetaPlayer for each call, avoiding stale learned-weight epochs across calls, and supplies equal capture-order values.

Native semantic legality/availability helpers do not replace that supplied evaluation with legacy integer tables. Therefore the legacy [1,1] quantization example cannot be used to claim that the own fixed-unit floating learner ignores a .09 coefficient update. An actual feature/decision effect still requires its own evidence. The own adapter also has a real wall deadline and literal PV admission, so the stronger node-only trace prediction above is not automatically its end-to-end guarantee.

SemanticSearchEngine is a third consumer: semantic_native_scale and dynamic/spatial/control/nonlinear/ordering profiles are additional inputs. A nonempty all-zero dynamic mapping selects the versioned scale256 path in the earlier example. Equal legacy board arrays are not equality of that whole semantic payload. No full semantic-engine equivalence or cache-correctness audit is attempted here.

## Decision and cost

The next interpretation should compare the actual consumer inputs before attributing an action difference or lack of difference to learning. Metadata-only distinctions remain provenance, not independent algorithm variants. This does not authorize deduplicating frozen paid comparisons, reusing a TT across changed evaluators, increasing alpha to cross rounding thresholds, switching learner/backend or launching a new campaign. Existing frozen originals and caps remain.

Disposition: the possible hidden-ID explanation is unsupported by the inspected legacy consumer; numeric/engine-state conditions, rather than checkpoint ID, delimit the source prediction. Correct the two documentation claims, retain the existing engines and terminate this seam. There is no measured speedup, strength gain or historical failure. No new Native/Player/teacher/search/game/training/solver call or build is made for this source analysis. No new test framework or hypothetical guard is added. A nonexecuting AST comparison can verify that the two edits only change docstrings; prior actual test counts and Native execution corrections remain in the existing teacher/arena reports and are not multiplied here.

Recovery Slack full thread capture after the current heartbeat contains the same parent and four replies through1793051362.612299, with no new Dot advice. This is a recovery intake, not a second delayed check or a duplicate request; exact original remains private. Reading/adoption is not independent execution. Same segment89c5ef59 remains authoritative until its real work ledger and finish allow closure; this report alone does not certify60 effective minutes.

Verification: both changed Python files parse successfully and their ASTs are identical to the fixed source after removing docstrings. The check imports neither file and executes no Native/Core/search. git diff --check passes. Explicit milestone fetch at22:13UTC still resolves sandbox7cbdbbb3aa21b8f0ca4c66e3e1cd7d5712bf91bd; no new mainline/review delta.
