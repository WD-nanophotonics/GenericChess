# StagedMovePicker order-only feasibility preflight — 2026-10-21

## Question and decision

On eight fresh generated 5x5 rules (seeds 622123–622130), do static-v2
`capture_order_value` or promotion `type_value` values alter the opt-in Python
`StagedMovePicker` root order and selected candidate action when leaf evaluation,
opponent, picker, and search limits remain fixed? This was an outcome-free
feasibility check only. It did not authorize or run a utility panel. The
predeclared gate required at least one context with changed hook values, changed
root order, and a changed legal candidate action; zero qualified contexts means
close this route.

The route is already covered by earlier utility studies:
`STATIC_STAGED_CAPTURE_ORDER_UTILITY_20261021.md` exercised capture-order changes
and failed its utility and cost gates; `STATIC_STAGED_PROMOTION_ORDER_UTILITY_20261021.md`
exercised promotion-target order changes and failed both gates. This supplemental
cohort therefore cannot reopen either consumer or justify another panel.

## Method and integrity

The fixed schedule produced 16 full-history roots (two prefixes per rule) and 32
candidate-owner contexts. Both arms used the opt-in staged picker, TT off,
ordered qsearch off, identical D3/8192-node/0.5-second/qdepth-2/qnode-128 limits,
Unit material leaves and a fixed Unit opponent. Only the candidate ordering
hooks differed: Unit formulas versus the existing static-v2 profile's capture
and promotion-target values. Candidate search actions were observed but never
submitted; no game outcomes were collected. A non-moving candidate owner used
one fixed Unit reply to create its candidate-to-move state. Full histories were
replayed; every resulting search left its session snapshot unchanged.

Eight of 32 owner contexts were already checkmate before candidate search, so
24 contexts yielded 48 paired-arm searches rather than the planned maximum 64.
Among those calls, 44 reached a root picker; four returned the same
`root_immediate_win` in both arms before ordering. Across all 48 calls, candidate
actions were legal, evaluator accounting matched, and complete session snapshots
were unchanged.

The producer had three pre-result harness aborts: an incorrectly transcribed
producer hash, then an attempt to serialize the internal non-serializable
`SearchPathRuntime` for root detection, then a stale local variable in the
result record. Their exact exception types/messages are preserved in the
ignored `.local_agent/staged-picker-preflight-failures-20261021.json`; the final
abort and successful invocation also have private console records. The plan was
corrected only for the exact producer hash, and root identification now follows
the source call order (the first `StagedMovePicker` invocation is the root). No
expected values, gates, or search settings were changed. The final preflight
completed and is bound to the plan, producer and search source hashes in
`data/staged_move_picker_order_feasibility_20261021/`.

## Result and scope

There were zero contexts with changed visited capture/promotion hook values,
zero changed root orders, and zero changed candidate actions. The required gate
therefore failed. The observed sample supplied no additional ordering exposure;
it does not contradict the earlier disjoint cohorts, which did exercise capture
and promotion ordering and found no retained utility. Do not run another staged
capture/promotion ordering panel, reuse this result as a population claim, or
change defaults. `StagedMovePicker` remains opt-in.

Exact plan, producer and 32-context output are alongside the report. This
conclusion is limited to the prespecified generated 5x5 roots and budget; it
does not refute static-v2 leaf evaluation or all-domain rule-price transfer.
