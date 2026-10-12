# Static ordering execution cost and disabled allocation

Current product change is narrow: ordering_cache_enabled=False skips the idle
ordering-cache allocation. True remains the default. The measured allocation is
11,108,360 bytes including the table header, not RSS. Older kernels report None
rather than a fabricated zero. Rebind/clear/cancel/retry are covered. The old
instrumented constructor fails the new zero-allocation assertion; 44 private
and 44 installed-production focused tests pass.

## Cost decisions

All controls use saved synthetic/full-rule states, q0 exact-root, unchanged leaf
and ordering profiles, cold 1MiB TT, minimum ordering depth2 and reversed arm
orders. Concurrent machine work is normal; these are finite exposed controls,
not exclusive/noise-free benchmarks or universal playing-strength evidence.

| Comparison | Complete calls | Result |
|---|---:|---|
| 4096 versus8192 cache entries, fixedD5 | 8 | Full tuples/work match; doubling11.1MB to22.2MB does not improve measured time. Reject capacity increase. |
| Existing cache on/off, fixedD5 | 8 | Full tuples/work match; off is only about1â€“2% cheaper on these static profiles. No default-off recommendation. |
| Full checked ordering child versus private static ordering view, fixedD5 | 8 | Full tuples/work match; gen2 about6.0â†’4.53s, Shogi9.26â†’7.72s, approximately25%/16.5% lower elapsed cost. |
| Private view finite7-root controls | 56 | 28 paired score/action/PV/depth/work outputs match. Whole batch22.87s. |
| Private view16s delivery plane, four roots/two orders | 16 | Every arm stillD5 with the same published tuple. More attemptedD6 work is not a completed-horizon/decision gain. |
| Complex ordering/cache guards and compact leaf | 24 | 12 output/work pairs match; complex ordering/cached cases fall back. Complex leaf with static ordering remains eligible. |
| Allcandidate fullchecked/view shadow | 4 searches | 26,312 paired candidate checks, zero mismatches of made boolean, live state/material and history prefix. Shadow overhead is not deployment timing. |
| Cancellation injected after fifth view trial | 9 | Three roots retainD1 cancellation; persistentTT retries match coldD4; parent/witnesses unchanged. |

The private view reuses make_mode with postconditions enabled and history
recording disabled. It skips only the discarded child digest/history append/
gave-check computation. Parent history, action binding, effects, promotion,
drops, typed auxiliary lifetime/triggers, invariants and postconditions remain.
Actual recursion and canonical selected output still use full checked children.
No global transient mode, TT/cache/terminal/trace consumer gets this view.
Eligibility is uncached static material ordering: no compact/policy, nonzero
dynamic, spatial or localized ordering profile. This does not shrink the generic
task definition or replace full histories with a reduced search state.

## Failure-set limitation and adoption

The first private view skipped the final history-capacity refusal. A synthetic
history_len1025/ply0 pair showed old checked=False/view=True; guarded=False/False.
That is an interface/source corner, not a demonstrated reachable game defect.
The guard preserves the refusal and normal pairs still pass.

Dot's independently read published-source reply identifies this same failure-set
issue and digest failure. Adopt that objection and describe the intended path
as equivalence for a restricted consumer, rather than merely an approximation.
The key serializer can reject invalid IDs/types/inputs and can fail realloc on
valid inputs. Normal-state field/material parity does not prove equal failure
handling under allocation failure. A private serializer-return-false injection on one actual legal action
confirms fullchecked=False/view=True while the parent remains unchanged. This
is not a machine OOM experiment; unconditional first injection was rejected at
adapter packing, then scoped to the paired call. One builder targeting error was
fixed before that query. No actual allocator failure was experimentally injected. Therefore the view remains PRIVATE, without product/UI/default
adoption; the public fix only removes an explicitly disabled cache allocation.
This is a concrete failure-contract decision, not a new general framework gate.

The approval reviewer initially rejected the combined finite/delivery command
as possibly exceeding the one-hour consultation threshold. Existing identical
finite measurements25.49s and per-call bounds were read first. New whole-batch
fuses240s/300s were declared before an approved short run; no long run was split,
no rejection bypassed, no pending user action or Smart App Control fault occurred.

A separately predeclared guarded/full64s D6 plane is recorded below after it
finishes; old16s measurements remain immutable. Evidence index:
data/q0_ordering_cost_20261012.json. Raw Slack/account, binaries, user UI and local
stop/session/memo files are excluded from the scientific archive.

## New D6 plane (all eight calls completed)

With64seconds per cell and no node cap, both arms reachD6 on both roots, with
identical full tuples and visited work. Gen2 uses500,519 visits andscore-2619:
full32.62/32.60s versusguarded25.71/25.77s. Shogi uses822,984 visits andscore-200:
full51.20/51.91s versusguarded41.34/41.65s. This confirms lower fixed-work cost at
a deeper horizon; it does not show an extra completed horizon or better decision.
The entire declared short plane stayed below its600s fuse. No old16s run was
extended or relabelled, and the serializer-failure limit still prevents adoption.
