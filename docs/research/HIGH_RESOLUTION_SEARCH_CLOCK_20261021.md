# Precise elapsed budgets on the actual Windows runtime

The observed runtime uses `GetTickCount64` for `time.monotonic` with15.625ms
resolution, and `QueryPerformanceCounter` for `time.perf_counter` with100ns
reported resolution. The former quantizes sub-tick AI deadlines and reported
elapsed time. This is a live clock-source defect, not evidence of search strength.

Search deadlines, cancellation/deadline checkpoints, elapsed/first-iteration
telemetry, benchmark caller timing and profile/benchmark CLI timing now use
`perf_counter`. MatchClock and the controller's default injected source use it
as well; explicit fake clocks remain supported. No time-control parameters,
search budget defaults, rule/history semantics or Native kernel changed.

Four actual1s Fischer clock comparisons expired at988.75–1002.12ms with the old
source, versus1000.00–1000.01ms with QPC. At a QPC-targeted656ms elapsed sample,
QPC consistently reports344ms remaining, yielding44ms AI time after the300ms
reserve; coarse readings yield44–60ms. Actual44/60ms four-pair searches consumed
532–563 versus718–771 nodes while keeping the same action and depth4. Changed
work is a budget consequence, not a measured decision-quality gain.

Short-budget and semantic-rule controls preserve actual caller work and elapsed
measurements separately. Cold mandatory work can still exceed tiny budgets;
deadlines are cooperative, not a hard preemptive promise. Explicit first-legal,
terminal, declaration, partial-iteration and cancellation provenance remains.

[Python's timing contract](https://docs.python.org/3.12/library/time.html#time.perf_counter)
specifies a high-resolution elapsed counter including sleep.
[Microsoft's QPC contract](https://learn.microsoft.com/en-us/windows/win32/sysinfo/acquiring-high-resolution-time-stamps)
also includes system sleep/standby/hibernate. All changed deadlines and comparisons
stay in the same clock domain; no QPC value is compared to UTC or an old monotonic
epoch. Host suspend was not induced or tested.

Regression tests exercise the observed sub-tick expiry, public terminal telemetry,
benchmark timing classification and actual controller-to-AI budget path. Existing
fake-deadline tests change their injected clock target while retaining their
original behavioral assertions. The complete active suite and permission retry
are accounted for in `FINITE_ROSTER_AND_SEMANTIC_AUTHORITY_20261021.md`.
Actual timing rows and executed probes are in
[`data/search_clock_20261021/`](data/search_clock_20261021/). The four-pair search
effect is diagnostic only; it is not a strength benchmark.
