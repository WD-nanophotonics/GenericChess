# Reject non-finite AlphaBeta time budgets — 2026-10-20

## Contract and trigger

`SearchLimits` documents `None` as no limit and a time limit as the cooperative
deadline used by the public AlphaBeta search path. Before this change,
`SearchLimits(max_time_seconds=float("nan"))` was accepted; `_Budget` formed a
NaN deadline, for which `time.monotonic() >= deadline` is always false. Positive
infinity was also accepted and never expired. A negative duration was accepted
as an already-expired deadline. This made invalid time requests silently act
like no time bound or immediate fallback, depending on the value.

The bounded reproduction constructed `SearchLimits` and `_Budget` directly:
NaN and positive infinity were accepted and `check_iteration` did not abort.
No search tree or game was needed to establish the deadline comparison defect.

## Change and verification

`SearchLimits.__post_init__` now rejects negative, non-finite and nonnumeric
`max_time_seconds` values with a `ValueError` that points callers to `None` for
an unlimited budget. Zero remains valid and retains the existing immediate
time-limit fallback behavior. Other search fields, node accounting, and
runtime deadline polling are unchanged.

Focused regressions cover negative, NaN, positive/negative infinity, an
unrepresentably large integer, a string, and the accepted zero-duration case.
Validation command:

```text
python -m pytest -q -p no:cacheprovider tests/product/test_ai_search.py tests/product/test_native_search_budgets.py tests/product/test_finished_session_search.py
```

Result: 76 tests passed. This is input-contract/resource-bound correctness, not
a speed or playing-strength claim. It does not promise a hard wall-clock
deadline for finite values; existing cooperative polling semantics remain.
