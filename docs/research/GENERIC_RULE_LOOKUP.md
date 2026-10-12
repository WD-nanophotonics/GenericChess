# Generic rule lookup: retained semantics, different caller benefits

Science is OPEN. Adopt the immutable capture-pattern subsequence, ordered-source
lookup and small payload encoding change. These mechanically compile existing
rule properties; they add no game-specific search, state cache or evaluation
patch. Baseline is48f151ad960cf21415385ebf69ab964e0be9cfce.

## Changes and correctness

At successful C Rules construction, each current type receives the original
ascending pattern indices for target==enemy and Boolean selector membership.
Duplicate selector entries append that pattern once. uint16 counts/cursors
retain all256 patterns. Runtime uses current, not base type; source/geometry
order and first eligible witness stay unchanged. All path, state, slot and
base/current guards still run against current state. Empty/friendly target
pseudo-attacks retain their old semantics; target_ok is not inserted.

For each geometry/owner, parsing marks whether source entries are nondecreasing.
Sorted lists use lower_bound, including the FIRST duplicate. Unordered lists
retain the original linear first-match scan. Nothing is sorted, rejected or
removed from the numeric payload. Empty/missing sources still miss; uint32
bounds safely search the accepted65535-entry limit. These are immutable rule
properties, not cached dynamic guard answers.

The existing Native legality provider binds its ordinary type map once and
encodes promotion truth directly as0/1. Owner validation stays BEFORE integer
coercion; unknown board/hand types and negative hand counts retain errors and
causes. All3,456 synthetic encoding/error outcomes match the original, including
rejection of fractional owner0.5. Availability ply0 and actual-ply consumers
remain distinct; no history/SHA import or cache is added to this state-only entry.

Final clean-process installed Native plus current Python source passes2,314
active tests, zero failures/errors/skips. Earlier actual isolated index2,298
and installed index/payload2,302 checks are separate qualifications. Current
source fault kernels are rebuilt during final tests. Capture and path stages
each compare60 existing stress states/15,360 scalar queries against independent
Python semantics and complete attack sets. Original12 transformed-actor/guard/
pseudo-target regressions remain. New16 product cases cover256 patterns/255
duplicate selectors and sorted, unordered, duplicate-first, empty, missing and
65535 source entries; old implementations also pass their retained contracts.
Numeric synthetic boundaries are not claimed reachable game trajectories.

Four final ShogiD3 FNV64/word/node/value traces match independent cshogi replay
and prior complete sequences. FNV is a sequence diagnostic, not cryptographic
identity.32 index-stage Chess/Shogi finite cells retain full outputs/work;
board/drop-only reference scope does not establish declaration/persistent parity.

## Actual cost and completion

|Control|Baseline seconds|Candidate seconds|Interpretation|
|---|---:|---:|---|
|ShogiD5 capture index, both orders|2.662/2.692|1.735/1.732|About35percent local same-work saving|
|ShogiD5 path, both orders|1.736/1.735|1.540/1.538|About11percent additional local saving|
|Direct final combination versus48 baseline|2.714/2.733|1.551/1.563|About43percent local saving, directly measured|
|Actual Coreq4 D2 final, root1008 means|2.2496|2.1529|4.30percent; full non-time work identical|
|Actual Coreq4 D2 final, root1052 means|4.5342|4.3257|4.60percent; full non-time work identical|

Do not multiply staged ratios or transfer the persistent gain to Core. Core's
Native readonly availability/legality, Python state transition/history and
semantic attack evaluator are a different workload. Index-only CoreD2 saves
about1.7percent; path-only control is also smaller. Eight index-only and eight
final16s Coreq4 calls retain completedD2/-343 on1008 andD3/3880 on1052 in BOTH
orders: no completed-depth improvement. Actual work counters and durations are
preserved. Independent SemanticSearchEngine still supportsq0, notqsearch;
there is no hidden Nativeq4 fallback or new qkernel.

Index transfer separately declares eight new generated seeds2026101351..58,
8 sorted-uniform legal prefix plies, full history/hybrids/promotion/drops,
natural type-index board/hand leaves(K0), frozen ordering profile/min2/uncached,
1MiB cold TT, q0, maxD12, no node cap,16/64s, both orders.1357 is terminal/prefix
unavailable, kept without replacement.56 actual calls consume2,240.466 caller
seconds;28 pairs ALL retain the same completed depth/full choice/PV. Increased
throughput is not a completed-horizon gain here.

The subsequent path-only panel explicitly reuses those eight declared rules;
it is exposed development, not a new independent sample. Same16s conditions,
32 declared/28 actual calls,448.236 caller seconds.14 pairs:4 deeper,10 same,
0 lower.1353 advancesD6/-200 toD7/200 in both orders;1358 advancesD5/300 toD6/0.
All same-depth score/action/declaration/fullPV/decision-line tuples match.
Unavailable1357 remains. More completed search is not a WDL/strength proof;
no old cap/result is overwritten or extended. Each producer is below one hour.

Ordinary concurrent tests/other resource producers are disclosed; no exclusive
machine or noise-free speedup is claimed. Tiny fixed-promotion clocks are not
useful percentage evidence. Purpose/path-clock spans include instrumentation
and lost-inlining overhead; they locate a question, not clean CPU fractions.
Full non-time results/counters match the old sameD5 purpose experiment.

## Cold lifecycle, memory and ABI

Dot's concrete cold-lifecycle objection was read completely and adopted.
Existing ordinary and256-pattern descriptors use public C construction,
numeric roundtrip, pack and first attack, then20,000 same-capsule queries.
Normal construction adds21.6/24.2microseconds in the two observations;
max-pattern duplicate boundary adds325.4/72.1microseconds. Export/first-query
clocks are noisy; ordinary warm FFI queries show no reliable gain, while the
boundary warm batches improve. No universal amortization threshold is inferred
from these one-sample-per-order cold measurements. Python payload construction
is outside this C-only cold timer and inside whole Core caller measurements.

Actual x86_64-windows-gnu sizeof measurements: Rules271,360 to304,256bytes,
exactly32,896 extra bytes per LIVE Rules capsule. PathOwner remains16 and
Geometry48bytes; the sorted flag consumes existing padding. Memory is not
multiplied by search nodes, and this is not measured RSS. Python report's
estimated_bytes includes the fixed capture table. Runtime uses many queries
per capsule in persistent search; cold one-query consumers can pay extra cost.

The internal C layout changes. Compile allocation and EVERY consumer must use
one rebuilt source closure and a clean process. Restart after rebuilding;
external numeric payload/version/roundtrip are unchanged, which alone does not
prove mixed-object ABI compatibility. Final installed tests bind the actual
binary and source hashes. UI Test remains user-maintained; this is sandbox
backend delivery, not a frontend update or automatic branch integration.

## Rejected cheap alternatives and collaboration

Eight-round SHA keeps2,376 hashlib/digest/final-context cases but D5 changes
2.0percent forward and-0.43percent reverse: defer. Same-source O3 changes about
0.5percent forward/-0.38percent reverse: retain O2. A private immutable64hex
fingerprint encoding control keeps nonhex/UTF8 fallback and nine full-digest
cases but saves only0.1/0.7percent: defer cross-file flags/engineering. No full
identity/history removal, hardware dependency, large path array, new engine or
frame/global state cache follows these controls.

DEV_AUX independently publishes60f6d33b2d3ec4c350275acfee0fc24726482763/segment27.
PRIMARY reads the full report and independently checks66 exact rational gain/
component/family/leave-one-family/integer-displacement rows and96 diagnostic
profiles/terminal-only speed scores. This does not reproduce3,488 games,
70,592go, the binary, PVs or RNG journals. Random opposition is cheaper and
more terminal-responsive in that finite panel, but initialization and1024 versus
8192 search budgets reverse some transfer signs; one root family can carry a
gain. Adopt those interpretation limits, not auxiliary code/defaults or human
price recovery. Primary and auxiliary remain separate writers/checkouts.

Fresh PRIMARY consultation is a new AGENT_REQUEST root, not AGENT_FOLLOWUP.
Dot independently reads OLD48 code and gives conditional predicate/lifecycle
advice; our new results remain local execution evidence. No routine receipt
loop, duplicate Agent, boundary write or coordination conflict is observed.
See ../operations/COLLABORATION_LOG.md for reviewed shared work.

## Bound evidence and next useful question

[data index](data/generic_rule_lookup_20261013.json) binds298 archive members,
1,273,440 compressed bytes/25,037,253 raw bytes, SHA256
7a564436804d5199474c2e94a17e439c86cf51c821d391e0438a4e8bb65a14f8.
Every member and45 current source files are byte/hash verified. Raw Slack,
account/private inputs, credentials, binaries, toolchains, test hostnames/logs
and caches are excluded. Prior scalar archive supplies frozen Shogi replay
reference tables; baseline Native headers/source and all new scientific
producer records are retained here. No bit-identical compiler or machine speed
reproduction is promised.

Preparation label/quote errors, missing-file launch, list/tuple assertion and
Windows line-ending noise were diagnosed/corrected before delivery; detailed
handling evidence is retained. No hidden SAC/quota/runtime block or user action.
Next choose a remaining ACTUAL supported-caller/key cost or caller/backend
attribution whose opposite results change a concrete choice. Do not rerun the
unchanged SHA/O3/fingerprint microcontrols, add static tables from counts alone,
claim scientific completion, or use publication as an early segment ending.
