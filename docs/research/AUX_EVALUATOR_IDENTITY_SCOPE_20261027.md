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

## Distinct actual cost consumer: timer boundaries

The next source question compared actual timer producers/consumers, not a new performance experiment. Initial naming of a diagnostic NPS was too broad: the located NPS producer is arena._play_one_game; no such field was found in diagnostics.py. The real arena can select either legacy or semantic Native via its _engine_for, depending on compiled rule type. The following distinctions are source facts, not measured overhead estimates:

| Actual field / producer | Included interval | Important exclusions / distinction |
| --- | --- | --- |
| NativeSearchEngine result.elapsed_seconds | C gc_iterative_search call, timed after search-context allocation | Python history packing, C context allocation, result construction and Python action/PV validation |
| SemanticSearchEngine result.elapsed_seconds | C iterative loop/fallback interval beginning at native_module.c:7105 | Earlier profile/setup/stack allocation, Python full-history packing, returned PV validation and leaf feature extraction |
| arena search_wall_seconds | wall_started before optional root-hint provider, through engine.search return | Earlier session legal enumeration, engine construction/reset and subsequent actual played move |
| arena elapsed_seconds / nps | _trusted_search_elapsed selects credible positive Native time, else wall fallback; nps uses result.nodes divided by that selected interval | The source can differ by row; a credible Native timer is not automatically full-call wall cost |
| own mainline receipt.seconds | adapter entry through receipt creation, including terminal checks, player construction, main search and literal PV replay/admission | Caller on_query logging, committed played move, episode TD update and earlier environment/rule construction |
| own EpisodeResult.seconds | episode entry through final terminal adjudication and learner.finish | Caller preparation/publication; this is broader than search receipts |

Semantic C sets its cooperative deadline before stack allocation/context seeding but starts its reported elapsed interval afterwards (native_module.c:7045-7105). Thus even the timer interval and budget interval need not have identical endpoints. Packing occurs still earlier, and PV checks later. This is not a claim that a new overhead was measured or that a particular run violated its contract. A deadline is cooperative, not a preemptive interruption of every primitive.

Arena already exports timing_mode='per_move_search_time', requested_time_seconds, wall_budget_overshoot_seconds and search_wall_seconds. Its move_time_seconds is passed to engine.search; it is not a full externally timed allowance for every preparation/validation step. The game wall timer starts after opening replay, engine creation and optional saved-prefix replay; the resumable stage timer starts after progress validation. Existing stage/game guards remain useful bounds on their declared portions but cannot recover all invocation startup cost. No change to those policies/defaults, archived results, validator or experimental design is made here.

The own mainline adapter deducts elapsed pre-search setup from its remaining time, then checks the same query deadline around PV replay. Its receipt includes those operations. The episode additionally pays actual opponent-policy moves/declarations/commit work and the final learner update in its wall field; query/node counts deliberately do not invent searches for such moves. Summed search nodes are therefore not a total Core-operation or total-time meter. The actual reference iterative consumer similarly records a broader outer elapsed interval than the sum of inner depth-search intervals. None of these boundaries should be silently equated with another backend's node counter.

Decision: retain the existing explicit elapsed_source/timing_mode and outer wall fields. A future claim about full-call acceleration must measure the same external boundary, comparable returned decision quality and the actual backend/options; kernel NPS alone cannot establish it. Conversely, no full-call slowdown or speedup is inferred here. No supported consumer was found requiring a new schema/guard/timer repair, so this seam ends with NO_NEW_SIGNAL for runtime modification. This source trace does not reopen PRIMARY's endpoint/profiling experiment or the closed initial Leaper cost audit. No benchmark, Native/Core/Player/game/training/solver execution or archived telemetry re-evaluation was performed.

## Own ordering contract: no direct price prior is not model independence

A separate actual-consumer check followed the cost seam: the own adapter's no-price-prior claim is about direct priority values. Material.capture_order_value always returns0, and the selected legacy MoveOrderer therefore gives every detected board capture the same direct price contribution. Promotion priority is the fixed category constant -60, not a learned promotion value. The staged picker does have an evaluator.type_value promotion path, but own tuning does not enable that picker; it is not a reached defect or a request to add that API. Earlier published tuning-default observations are reused, not counted as a new discovery. No SEE/LMR/lazy-evaluation switch is activated through this adapter.

There is nevertheless a real indirect dependence. run_root_search creates a fresh context/orderer for the call and deepens with the same TT. negamax passes a prior TT best_action to MoveOrderer; when model-dependent alpha-beta scores cause a cutoff, it records killer/history priorities used at subsequent nodes/iterations. Search source around489-611 establishes that control/data path. Thus changing leaf weights can change later search order even with equal direct capture prices and no human material prior. This is normal within-call search adaptation, not leaked cross-episode training or a fixed-tree equivalence. The existing fixed-tree derivative controls retain their explicit hypothetical-tree scope; they do not establish an unchanged visited tree under live search. No earlier quality result is recomputed or reinterpreted.

The adapter docstring now says 'no direct learned or human material price' and explicitly retains TT/history dependence. No numerical priority, search switch, trained weight or ordering implementation changes. Source inference only; no new Player/search/Native/Core/game/fixture run. Disposition NO_NEW_SIGNAL for a functional repair; stop this seam rather than adding ordering instrumentation or a new ablation campaign.

Final current source-only checkpoint:2739.610122confirmed seconds=45.6601687minutes in the SAME active segment, ordinary60-minute requirement still UNMET. The three changed Python files have identical executable AST to ef4ad7f8 after docstrings are stripped; no runtime imports/search calls. Followup1793052949.344609 was sent only after ac09bb7105c1618d638fd0baba34214b14d41ef9 push/full-SHA verification; its single delayed channel/full-thread check completed22:21:43UTC after due22:20:49.344609. No new Dot reply. This publication is an unfinished checkpoint, not an accepted ordinary segment finish or independent review endorsement.
