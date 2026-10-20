# Benchmark fallback provenance — 2026-10-20

## Question

Do the public benchmark consumers censor a game when AlphaBeta returns a legal
fallback because its first search iteration did not finish?

## Reproducer and finding

Using the existing generated 4x4 `classic_like` fixture (seed 5, no opening)
with `max_nodes=1`, the public player returned
`result_source="root_scan_fallback"`, `termination_reason="node_limit"`, and
`completed_depth=0`. Before the fix, `ai.benchmark.runner.play_game` wrote an
event with `fallback=false`; its `GameOutcome` consequently had no fallback
flag and remained eligible for utility scoring. Thus the stop cause had been
mistaken for the source of the retained move.

`AlphaBetaPlayer` already reports these separately. A completed iteration is
`main_iteration`; an interrupted call that retains only a legal root action is
`legal_fallback` or `root_scan_fallback`. A proved root win from an interrupted
iteration is `completed_root_win`, not a fallback. A call with no legal action
uses `no_legal_fallback` and the benchmark marks the game failed. Preserve the
legacy `fallback` source/termination spelling for existing producers.

The benchmark and native-readiness audit now classify the retained result
source, while preserving `termination_reason` as the stop cause. A regression
drives the actual public benchmark caller under the same one-node cap for both
candidate colors and checks event ownership, per-side game flags, utility
eligibility, and aggregate count. A companion regression pre-cancels a real
player call to exercise the distinct `legal_fallback` source through that same
consumer.
A second regression parameterizes the Native-readiness budget-row path at node
budgets0 and1, covering an immediate `legal_fallback` and an interrupted root
scan. It checks both `fallback` and the aggregate `fallback_runs` count. The
`MoveEvent` schema is unchanged; old saved rows
remain immutable and this fix does not relabel or reinterpret prior reports.

## Existing public record audit

The only committed benchmark summaries exposing `fallback_games` are the two
2026-10-20 semantic-pawn reports. Both game tables contain16 games and report
zero fallback games. Their event files contain1,469 and1,670 rows respectively;
the as-built file has932 `node_limit` rows, all with completed depth2, and the
corrected file has870 such rows, also all at completed depth2. The remaining
events in each file completed depth3. The public search contract returns the
last completed iteration (`main_iteration`) after a later iteration aborts;
the fallback path is specifically used when no full iteration completed.
Neither archived event file has a zero-depth abort. Therefore this precise
false-negative (budget abort before the first completed iteration) is absent
from these two stored reports; their zero fallback totals need no correction.
This conclusion is bounded to the two committed summary datasets found by the
repository-wide search, not arbitrary private or external runs.

`MoveEvent` stores the binary fallback classification and stop cause, but not
the full `PlayerDecision.result_source` enum. That is enough for utility
eligibility and preserves the existing record schema; adding another public
field would be a separate auditability/API decision without a demonstrated
consumer need, so it is deferred.

The Native-readiness consumer uses the same three retained-action sources and
keeps terminal, declaration, immediate-win, completed-iteration and
`completed_root_win` results outside that set. `no_legal_fallback` is different:
it returns no action. The paired-game benchmark records that path as failed;
Native-readiness rows retain `best_action=null` and the explicit
`NO_LEGAL_FALLBACK_BEFORE_DEADLINE` stop reason, rather than calling it a legal
fallback. No saved repository report contains that source. There is no observed
reason to add a separate no-action aggregate or status field in this repair.

An end-to-end companion regression now covers the positive counterpart: the
existing prepared proof position produces an actual `completed_root_win` at
depth1 before a node-limit abort, then the benchmark continues the game to the
proved candidate win. It asserts the first event retains `termination_reason`
`node_limit` while `fallback=false`, and the completed game enters the eligible
summary. This protects the distinction between an interrupted later iteration
and a fallback retained without any completed iteration.

## Verification and scope

The focused modules
`test_benchmark.py`, `test_native_readiness_report.py`,
`test_no_contest_search.py`, `test_search_result_provenance.py`, and
`test_completed_root_win.py` pass (116 tests). A first direct focused invocation
did not place the project root on `PYTHONPATH`, so collection stopped at the
existing `scripts.full_q_refresh_comparison` test import; rerunning with the
repository root supplied passed. The first non-elevated run reached the tests but two existing
benchmark fixtures could not create their project-root temporary directories;
rerunning with the authorized project-local execution permission passed all
four modules. Pytest emitted only the existing cache-directory permission
warning.

This is benchmark eligibility/accounting correctness. It does not change
search, selected actions, prices, play strength, resource limits, or previous
frozen results. Raw command outputs and the original pre-fix reproduction are
kept privately under `.local_agent/research/benchmark-fallback-provenance-20261020/`.
