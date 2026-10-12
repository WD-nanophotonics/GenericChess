# Packed ordering, fixed-search correctness and backend attribution

Two actual fixed-depth search defects are repaired. The fixed/probe entry now propagates a required child identity failure instead of skipping it as an illegal action, and returns a genuinely optimal canonical action rather than replacing an exact incumbent with a later fail-low tie. Direct full checked children also remove unused local undo/copy work. This is the existing generic C executor, not a new game-specific engine, evaluator, UI policy or persistent-search algorithm.

## Observed defects and final change

Original source94aea9b3394ee6b416c1d840f24801a92e91f1a2 used Boolean make_trusted. A private serializer-false injection scoped to the actual fixed-depth child call returned an apparently normal result; the new regression did not raise on that source. The final recursion calls make_checked_status directly into its local child, distinguishes1/0/-1, sets its existing ok channel false on -1, and the public caller raises RuntimeError. Rule/input/capacity refusals remain0. Parent and post-fault retry are checked. There is no product fault switch, added global status, or new public trusted API.

A second normal-input failure was reproduced atD3:

|Existing root|Old reported root value|Old selected action|Selected action independent exact value|
|---|---:|---|---:|
|Chess tactic|1000000|g2g3|500|
|Chess EP|100|f1e2|0|

The old loop generated a different order, then allowed a smaller packed action to replace an incumbent on an equal returned bound. A fail-low bound is not an exact tie. Sorting candidates by ascending packed uint64 before the shared-window alpha-beta prevents a later action from replacing an earlier exact incumbent on a tie. An improvement above the incumbent must supply an exact value; canonical ties retain the earliest packed action. This sufficient condition relies on this fixed order and cannot simply be reused with future dynamic ordering.

Both new selected-action regressions actually fail the preserved old compiled source. Independent python-chess exhaustive fullD3 trees, without alpha-beta/TT/q, agree with all102 exact root-child values and the canonical argmax on four Chess cases. The old scalar scores were correct in these cases; the returned actions were not. That distinction matters for a playable AI.

The initial repair used a new trusted-status helper. Measurement then showed local pre-copy, undo-save, child assignment and unmake were unnecessary: the child never escapes its recursion frame and the parent is immutable. The final smaller change directly uses the existing full checked child/status. It retains all postconditions, effects, typed auxiliary state, history appends, digests and required errors. The helper and its header/runtime changes were removed. Eight reverse fixedD4 candidate/control calls retain the complete C result, including PV and nodes, while saving20.9–30.1% elapsed on these four roots. No arbitrary-corrupt-memory or universal OOM guarantee follows.

Final exact-source kernel:2280 tests, zero failures/errors/skips. The earlier intermediate kernel also passed2280; those are separate checks, not independent scientific samples. A later isolated test launcher initially omitted the project root and produced30 collection errors. That launcher failure is retained, corrected, and the final complete suite passes. It was not Smart App Control or an unresolved machine block.

## A finite matched-order comparison

Core/specialist and Core/Native audits each check433 states across eight existing played/sparse Chess/Shogi roots, including promotion, actual EP and drops.430 ongoing frontiers were inspected;418 have a different packed-numeric versus UCI/USI lexical order. Full parent/child state, material, terminal and supplied histories match in the audited trees. These are exposed finite controls, not the complete generated domain.

AtD4, the identical existing Python lexical alpha-beta gives24551 entries on Chess-middle and39087 on Shogi-middle. Reverse Native-state bridge/specialist elapsed ratios are3.13–3.21 and12.51–12.59 respectively; complete work, action, value and label traces agree. Changing only Native order to packed changes entries to13638 and78370 respectively. Chess changes a tied action; Shogi keeps the action. Same score or a changed tie does not imply a playing gain, and unlike work cannot identify primitive speed.

For four Chess roots, an immutable finite table records the actual packed frontier order of every visitedD4 path. Both existing Python adapters independently enumerate their own legal moves and only reorder by that table. No values, TT hints or legality answers are supplied. Each root has its own compiled root/full prefix and path; remaining depth is fixedD4 minus path length. Table coverage is100%, every enumerated set equals its table set, and there is no missing-entry fallback or cross-root/depth reuse. Table preparation is outside warm timing and is not a free deployable search mechanism.

The final C fixed executor and both same-order Python adapters have identical entries, root value and selected action. Separate private C instrumentation matches the independent specialized implementation's complete visited action/leaf/returned-score sequence by FNV64 plus word count; this is a sequence consistency check, not cryptographic authentication. Clean timing uses the uninstrumented kernel.

|Final source, pairedD4|Entries|C fixed elapsed|Specialized Python replay elapsed|C/specialized replay|
|---|---:|---:|---:|---:|
|Chess-middle|13638|.261/.261s|.347/.358s|.752/.730|
|Chess tactic|4070|.056/.056s|.077/.097s|.728/.575|
|Chess promotion|1528|.018/.018s|.020/.020s|.905/.907|
|Chess EP|22339|.424/.424s|.539/.546s|.787/.777|

These are warm end-to-end finite ratios, not pure C cost, pure Python overhead, mature-engine parity or strength. Specialized replay adds about1.2–29.7ms of path/lookup/mapping/reordering that C does not pay; measured clock instrumentation perturbs it. Do not subtract separately measured means as exact net cost. The .02s cases are particularly noisy. Ordinary concurrent computation was present: some earlier replay timing overlapped our full suite, and later ablations overlapped the separate node-budget experiment. Neither invalidates deterministic semantic/work checks or proves a machine-exclusive speedup. Original rows are preserved, not selectively replaced.

The public fixed/probe Shogi gate still rejects its continuous-check policy. No gate was bypassed or declaration/history semantics removed. The current supported persistent exact-root Native versus specialist interval remains missing. The finite Chess fixed-executor result fills a different, narrower comparison cell.

## Physical work, not just recursive entries

A private whole-search runtime counter records actual candidate, S3, digest, history and attack operations. On Chess-middle, guarded Python Native and C fixed visit the same13638 nodes, but guarded Python has123828 S3 trials and85000 child digests/appends, versus C31849 trials and13637 digests/appends. Its110191 generated candidates are the same. Chess EP gives195694/120065 versus52606/22338; tactic37953/18910 versus10124/4069; promotion6775/3979 versus3853/1527.

The existing guarded adapter materializes/validates the full frontier and makes visited children again. A private lazy candidate adapter performs full checked make only as candidates are consumed, retaining each successful immutable child for the immediately visited edge. Its trial/digest/history/attack counts exactly match C in these finite traces. No required validation is skipped. It is a diagnostic, not a new production player or public error-contract adoption.

Clean reverseD4 pairs give guarded/lazy ratios1.58–3.47. A cold per-compiled-rule cache of pure packed-action-to-label conversion adds1.12–1.22 relative speed on the lazy adapter;148–535 misses and1379–21874 hits are recorded. Both keep complete action/value/work. Consequently the original bridge gap includes full-frontier materialization and repeated checked make, not just language or board representation. C additionally evaluates material on every entered fixed node while the Python minimal implementation evaluates at nonterminal leaves; matching recursive traces does not equalize every primitive. No claim that generic rule execution alone is already as cheap as specialist rules follows.

Three of four predeclared new4x4 hybrid generated roots remain ongoing after eight legal moves. Their independent Core exhaustiveD3 oracles visit2904/608/951 states and match all root values and packed canonical choices; promotion and drops occur, and each root keeps history9. The fourth is already terminal and is retained as a predeclared skip, not replaced. Final C reuses these exact oracles rather than rerunning Core; full result matches. This expands finite semantic support without redefining the generic target.

## Separate node/time resource decisions

Sixteen new paired calls keep the previous two saved roots, q0, TT1MiB, explicitmin2/static material view, cacheFalse, maxD7, and set both arms to1M nodes with32/64s. Original unbounded and older node-cap curves stay immutable. This experiment compares the prior full-status kernel with the already adopted material-view/decimal/discarded-clear composition; today's fixed/probe repair is not the iterative cause.

|Root/time|Original full depth in reversed pairs|Combined view depth|Interpretation|
|---|---|---|---|
|Gen2,32s|D6/D5|D6/D6|Boundary variation retained; not uniform two-pair depth gain|
|Shogi0,32s|D5/D5|D6/D6|More complete finite output on this resource plane|
|Gen2,64s|D6/D6|D6/D6|Both hit1M; full60.5–61.8s, view31.6–31.7s|
|Shogi0,64s|D6/D6|D6/D6|Both hit1M; full57.8–58.6s, view35.1–35.3s|

Completed values/actions/PVs, attempted counters, stop causes and parent restoration are retained; attempted extraD7 work is not a completedD7. No enlarged old test, unique-node interpretation, strength or universal utility claim.

A further predeclared four-call check revisits only the prior Gen2 ordering counterexample with this changed cheap-execution premise: same final source,32s/1M, same leaf/q/TT/history. No explicit ordering reachesD4 in24.4s at1M; explicitmin2/scoped view reachesD6 near32s. Both reversed pairs agree; actual ordering counters confirm which arm ran. This is one exposed counterexample under a new premise, not grounds for uniform default/UI adoption or retroactive repair of old failures.

A final predeclared16-call private control evaluates material only at leaves/fallbacks, retaining the entire fixed result. Its tiny elapsed changes reverse sign across paired cases (roughly-1.6% to+2%); they do not change the next decision. Do not adopt or enlarge that control. The every-entry evaluation difference remains explicitly disclosed in the final comparison.

## Decision and evidence

Adopt the small fixed-depth correctness repair and direct checked child. Keep lazy/cached-label adapters private diagnostics; avoid manufacturing a new specialist engine. Next target an actual supported consumer cost or matched persistent scheduling condition, retaining evaluation/terminal/order/resource differences.

Dot's full reply supports the finite bridge,100% coverage, and physical work decomposition; adopt its asymmetric replay-cost and small-time noise caveats. It independently read94aea9 old runtime source, not the new patch or local tests. No approval gate, extra worker or routine reply loop was introduced. Auxiliary learning remains independently owned; its old-source deployment tests do not verify this repair.

Exact producers, declarations, immutable raw science, preserved baseline/candidates, final source and member hashes: data/packed_order_20261013.json and archive/packed_order_20261013/evidence.zip. Raw Slack/account records, private test logs, DLLs/toolchains, state/session/memo and user/UI inputs are excluded. Failures and scope refusals are explicitly retained in handling-failures.json.
