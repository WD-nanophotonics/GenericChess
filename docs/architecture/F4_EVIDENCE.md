# GenericChess F4 evidence

## Status

`COMPLETE` — `F4_RESULT = OPTIMIZATION_PASS`.

## Baseline and provenance

```text
starting sandbox = 47bad121fb07fef421583aa7198bf2887d985994
H4A              = 98ecd8c400157984df809f23a988120dfa5dca16
H4B              = 1cc19b4d0e92dfd36871a228cb628a906e4b1759
origin/sandbox   = 1cc19b4d0e92dfd36871a228cb628a906e4b1759
origin/master    = 4f1d03a308f5fd04a01bbd980c7411888ea1ed9d
origin/chat      = d6b0d5720efe23019a7a2b4cce72e05beee2e6c4
```

Machine: Python 3.12.0, Windows 11, ARM64.  H4A worktree was clean and only
`sandbox` was pushed.

## Corpus and profiles

Corpus contains legacy draw control, continuous-check control, and four
reachable nonterminal Semantic Standard Shogi prefixes (`plies=0,1,2,3`,
deterministic seeds `0,1,2,3`).  The certified semantic fingerprint remained
`5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345`.

Profile A: TT on, ordering off, quiescence depth 0, root tactical off, depth 2,
max nodes 512.  Profile B: default tuning, TT on, depth 2, max nodes 256,
quiescence depth 4, deterministic node budget.

Each case used one warm-up and five measured repetitions.

## Attribution

Profile A before optimization, representative semantic prefix 0:

```text
wall 6465.956 ms; nodes 331; qnodes 0; completed depth 2
MOVE_GEN inclusive 3074.957 ms
EVALUATION inclusive 231.470 ms
TT_PROBE_STORE inclusive 3.371 ms
runtime push 3222.522 ms; pop 7.473 ms; 329 pushes
TT probes/hits/stores 32/1/32
```

The cProfile top cumulative roots were `is_square_attacked` (32.834 s),
`iter_legal_action_bindings` (23.842 s), `_trial_child_if_s3_legal` (21.893 s),
`SearchPathRuntime.push` (17.700 s), and terminal legal-action processing
(11.778 s).  The top self-time root was checkpoint polling:
`search.py:147 checkpoint` 9.658 s plus `semantic_executor.py:42 _checkpoint`
9.500 s, followed by `is_square_attacked` self 7.628 s.  These cumulative
figures are nested and are not summed as wall-clock shares.

Profile B repeated whole-search attribution showed quiescence as the dominant
top-level timed category (about 28.5–36.0 s in the four semantic cases), with
move generation about 3.5–4.2 s, evaluator/order/TT much smaller.  A Profile B
cProfile attempt was bounded and recorded `RUNTIME_SAFETY_ABORT` at 60 s; the
non-profiler five-run corpus completed normally.

## Optimization gate and implementation

Candidate: fixed-node checkpoint dispatch fast path.

All seven gates passed: DOMINANT, MATERIAL, EXPLAINED, LOCAL,
SEMANTICS_PRESERVING, TESTABLE, and LIKELY_USEFUL.  The implementation is one
branch in `_Context.checkpoint`; interactive cancellation/deadline semantics
remain unchanged.  No Core, rules, evaluator, TT, history, or qsearch design
was changed.

## Before/after performance and parity

Five-run medians, same machine/corpus/profile:

```text
Profile A semantic aggregate: 6479.636 ms -> 4748.891 ms  (+26.7%)
Profile B semantic aggregate: 38329.638 ms -> 25295.268 ms (+34.0%)
```

Per-case semantic improvements were 23.6–33.6% in Profile A and 31.1–57.0%
in Profile B.  Every before/after row matched action, score, PV, nodes, qnodes,
completed depth, and termination reason.  No semantic representative case
had a stable >10% regression.  Generic controls also retained exact parity.

Instrumentation overhead was not material: timing-vs-null Profile A medians
varied from -12.6% to -2.6% on these noisy process-isolated runs; all logical
results remained deterministic.  Timing is therefore used for attribution,
while cProfile and repeated before/after medians support hotspot conclusions.

## Technical answers

1. Semantic wall time is dominated by repeated checkpoint polling combined with
   semantic attack/check and S3 legality trials; not TT or evaluator.
2. The checkpoint component is per-callback/per-node; attack and S3 costs are
   branching-dependent and recur across legal candidates.
3. Profile A and product-like Profile B agree that checkpoint/semantic legality
   dominates; Profile B additionally makes qsearch the largest top-level timer.
4. Move-generation cost is specifically S3 trial/legal binding and check
   safety, not simple candidate enumeration alone.
5. Runtime push is substantial because it contains semantic transition and
   terminal work, but the checkpoint dispatch was the only isolated F4 fix.
6. Evaluator, ordering, and TT are small relative to semantic legality and
   qsearch; TT probe/store was milliseconds in Profile A.
7. F3 history-aware TT key/context is not the bottleneck: only 32 probes in the
   representative Profile A case versus tens of seconds in semantic/check
   work.
8. The single next recommendation is F5 semantic attack/S3 legality
   optimization, with separate parity gates.  Deferred alternatives are
   transition/runtime reuse, then Native migration.

## Evidence tree

All required machine-readable and profiler outputs are under
`artifacts/f4_runtime_cost/`; `manifest.json` contains SHA-256 hashes for all
26 closure files.  Required files include baseline/corpus, Profile A/B before
and after JSONL, recorder overhead, cProfile cumulative/self reports,
hotspot ranking, optimization gate, parity, performance comparison,
`final_verdict.json`, and the Profile B cProfile safety-abort record.

## Final validation

```text
python -m pytest -q -p no:cacheprovider
892 tests collected; all passed

python scripts/build_native_zig.py
fresh supported Zig build passed; output 333312 bytes
```
