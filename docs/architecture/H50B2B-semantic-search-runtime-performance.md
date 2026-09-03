# H50B2B semantic Native search runtime performance

## Scope

This checkpoint measures the no-TT, iterative semantic Native search from
H50B2A.  It deliberately uses the canonical Western rule set, Standard Shogi
with declarations removed (the supported semantic-search subset), and a
compiler-produced mixed-mechanic rule set.  Each rule set is measured from
three deterministic legal midgames rather than from setup alone.

Raw measurements are caller-selected files outside Git.  The reproducible
driver is `scripts/benchmark_f50b2b_semantic_runtime.py`.

## State and transition cost

Native instrumentation reports a `GCSemanticPosition` size of 53,920 bytes;
the current compatibility `GCSemanticUndo` is also 53,920 bytes.  The payload
is dominated by the authoritative full history arrays.  A separately timed
checked public transition (including its immutable child capsule) measured:

| Ruleset | latency | transitions/s | full-state byte-equivalent bandwidth |
| --- | ---: | ---: | ---: |
| Western | 11.53 us | 86.7k | 4.68 GB/s |
| Shogi, no declarations | 16.24 us | 61.6k | 3.32 GB/s |
| Generated mixed | 4.08 us | 245.0k | 13.21 GB/s |

The bandwidth column is intentionally an approximate copy-pressure indicator,
not a claim that all bytes are physically copied by the CPU on every path.

## Independent search partitions

The Native entrypoint releases the GIL while it owns all mutable recursive
state.  The benchmark therefore schedules independent top-level searches with
isolated position capsules and no shared TT.  Determinism is checked per
midgame against `fixed_depth_search` at identical depth, evaluator, rule set,
and position: score, action, and full PV all matched.

At depth four, 24 partitioned searches across the three midgames yielded the
following sustained scaling results for the two CPU-heavy reference rule sets.
CPU is process CPU seconds divided by elapsed seconds; RSS is sampled Windows
working set and the delta is relative to the same process before the run.

| Ruleset | workers | NPS | speedup | CPU cores | RSS delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| Western | 1 | 25.1k | 1.00x | 1.00 | baseline |
| Western | 4 | 91.0k | 3.66x | 3.73 | 1.80 MB |
| Western | 8 | 156.6k | 6.27x | 6.50 | 3.95 MB |
| Western | 16 | 243.1k | 9.67x | 10.63 | 8.29 MB |
| Shogi, no declarations | 1 | 17.9k | 1.00x | 1.00 | baseline |
| Shogi, no declarations | 4 | 60.5k | 3.43x | 3.41 | 1.80 MB |
| Shogi, no declarations | 8 | 108.9k | 6.06x | 6.18 | 3.97 MB |
| Shogi, no declarations | 16 | 160.8k | 9.01x | 9.72 | 7.95 MB |

The generated mixed-mechanic rule set was also run across three midgames at
depth four: it kept strict parity and improved from 78.6k serial NPS to 219.4k
NPS with 16 partitions (2.79x).  It is too small for stable process-CPU timing,
so it is not used as the CPU-scaling reference.  A saturated single-midgame
16-job baseline reached 14.52 Western CPU cores and 15.12 Shogi CPU cores,
with 318.7k and 240.7k NPS respectively.

## Retained design and next optimization

Retain deterministic, isolated top-level search partitioning as the current
throughput mechanism.  It produces a measured multi-core gain without shared
TT state, without altering the search result, and with single-digit-MB
incremental working-set cost at depth four.

Do not land a compact mutable make/unmake implementation in this checkpoint.
The measurement proves that full-state copying is a meaningful pressure, but a
correct compact delta must separately own board squares, hands, aux changes,
side, ply, and a history append while preserving exact terminal/repetition
semantics.  Replacing it speculatively would be a larger semantic-risk change
than the measured partitioning gain.  The next runtime optimization target is
that compact history-aware delta representation; TT remains deferred until its
cost and identity semantics are measured independently.
