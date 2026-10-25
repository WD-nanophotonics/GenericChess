# Full-key hash memo: fresh-object feasibility, 2026-10-26

This is a zero-Player feasibility result, not a product implementation or a
whole-search speedup. The current pure-Leaper hash switches stay default OFF.
All rule, position, repetition, ply and full-history TT guards remain intact.
Evidence is in [the manifest](data/leaper_key_lifecycle_20261026/manifest.json).

## New evidence and decision

The main negamax path keeps the SAME local key from probe through store.
Actual TranspositionTable calls on 12 existing full-history keys verify three
hash calls for a cold probe/new insertion, one for a hit probe, and one for an
existing-entry store. An equal-but-distinct query key takes two hash calls for
probe/update; the resident key is not rehashed by that lookup. A capacity-two
fixture inserting three unique keys observes 4/3/3 hashes: the first key gets
one additional explicit eviction-pop hash. This qualifies the operation model,
not the frequency of these paths during a full search.

The new component timing creates a fresh base key for EVERY operation group.
Three alternating-order repeats, 200 loops x 12 keys, returned these aggregate
wrapper/base ratios: construction 1.353; first hash 1.175; one miss probe 1.166;
cold probe/get/set 0.533. Tiny millisecond aggregates are exploratory and include
Python allocation/loop overhead. They neither estimate a stable production
speedup nor justify another timing batch. The existing-entry group ratio0.868
includes creating/hashing the resident table key in both arms; it is NOT a
steady-hit query gain. Original values and that limitation are preserved.

The wrapper adds48 shallow bytes plus a36-byte example cached integer beyond
the original80-byte key:84 extra retained bytes/key, hypothetically20.03MiB at
250,000 occupied entries. A hypothetical inline slot would be8+36=44bytes/key
(10.49MiB), but is NOT implemented or measured. Allocator overhead, live temporary
recursion, actual occupancy and peak RSS remain UNKNOWN; borrowed history graphs
must not be repeatedly charged to each key. Twelve raw/cached bidirectional
equality and dictionary interoperability checks pass. The equal-distinct fixture
shares immutable component objects, so it does not measure arbitrary history
collision/equality traversal.

Existing33 local-hash nonterminal control returns contain238,761 TT probes,
73,761 hits and540 TT cutoffs. They do NOT export store/new-insert/eviction
counts. position_keys_computed also counts child materialization and cannot be
used as allocated-key count. Thus the mixture of one/two/three-hash lifetimes is
UNKNOWN. Terminal and Q/static leaves return before key allocation. Counts and
history hash use digests already; their exact equality checks remain expensive
when needed and do not disappear with a memo. No replacement profile was run.

Decision: fresh-use losses do not rule out the three-use benefit, but the old
repeated14-key micro does not establish net benefit. A bounded whole-call test
would be necessary before adopting a product memo; it has NOT_STARTED because
its cumulative expected cost reaches the user's120-minute confirmation boundary.

## Review, failures and budget

At opening, origin/sandbox was freshly fetched and verified at
9a9f080b71b89ccc5d43d5af90d4d668999ddac8; all three Patrol blobs were unchanged.
The default/master and listed heads were checked; this is not an all-GitHub-PR
review claim. New Slack roots since the covered opening root and the latest
Chat/active Dot full threads had no changes before the fresh AGENT_REQUEST.
Dot subsequently replied with source-only reasoning, not independent experiment
replication. Adopt the fresh-use, exact-equality and memory cautions. Reject its
suggestion that Dot may substitute for USER approval at>=120minutes: the direct
user instruction and active AGENTS policy control. The mandatory single delayed
check occurred18:28:40UTC against18:28:26UTC due, retaining that reply.

The first probe preflight passed a string to load(Path), failing before keys,
timings or Player calls. Original source/error are retained; the caller contract
was repaired before the sole completed timing. A ledger overlap refusal was
resolved by reading actual recorded intervals and excluding the automatic
validation interval; no duplicated time was credited. No frozen old factorial,
profile or diagnostic slots were refilled.

The prior related kernel chain used100.023201minutes including delivery. This
feasibility extension forecast18minutes including delivery, cumulative118.023201;
it is not a fresh allowance. The proposed next extension forecasts about180
cumulative minutes, cap200 including all prior costs: four existing board controls
x two repeats x two arms =16 calls, each30s/50k nodes, batch600s maximum. Base is
local-hash ON/position-memo OFF; candidate adds only an immutable complete-key
memo, default OFF. Preserve all guards, semantic/action/value/work parity,
cancellation/rollback, raw/cached TT interoperability and memory bounds. Any
contract failure stops; no missing-slot refill or game expansion. This concrete
proposal has been sent to the user for necessity assessment; Dot does not grant
it. No product memo, new search call or approval claim is included here.
