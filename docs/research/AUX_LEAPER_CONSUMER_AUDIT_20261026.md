# DEV_AUX pure-Leaper consumer source audit —2026-10-26

**Decision: DEFER further H6 syntax/bitmask prototype iterations; retain the
published candidate.** Actual consumers exist, but existing counters do not
establish the share of full-path time that a new fused kernel could remove.
No new search-quality design, Player, solver, game, build or benchmark was run.
This is the explicitly assigned15minute review, not a60minute research segment.

## Fixed sources and intake

Opening remote sandbox tip and task:
`264cfed3ced86d1c9ef8e3669667713a223542b5`,
`docs/operations/AUX_INITIAL_CONSUMER_AUDIT_20261026.md`.
Product/prototype/report/manifest inspected at
`66a41649c7a8da7e42491aba7f182b4b3e503aa1`.
Latest Patrol review at opening:
`87df8521a7f3826d209c81e5db566fba7746c4eb`,
`docs/reviews/chatgpt_patrol/2026-10-26_140342_JST_66a4164.md`;
its blob is also present unchanged at the opening tip. Exact22 file originals,
commit/path/blob/SHA256 records are retained privately; the publication
[source index](data/aux_consumer_audit_20261026/sources.json) binds them.
The27 entries of `executed-sources.json.gz` were decoded as SOURCE TEXT only,
with each UTF-8 SHA256 checked; no capsule was imported/executed. Query/record
archives were not decompressed/recomputed. Earlier nine Patrol documents were
preserved;14:03 and12:00 direction were read, earlier reviews deferred as
historical context rather than falsely declared all read.

Latest20 Slack roots plus three relevant complete threads were read; old channel
coverage remains incomplete and its prior complete boundary was not advanced.
Adopted the latest autonomous review's consumer/cost distinction; no old quality
campaign revived. PRIMARY's solicited Dot advice is lower-priority source-only
context. Exact originals, decisions and capture failures are retained privately.

## Actual caller and already-existing work

Paths below are relative to the fixed66a4164 source, unless labelled capsule.

| Consumer | Actual path / existing optimization | What this prototype changes |
|---|---|---|
| Search frontier | `ai/alphabeta/search.py` uses `runtime.legal_actions` / `runtime.pushed`; `core/search_runtime.py:1182–1279` checks capability, validates pairs, retains per-node frontier/binding map | Neither candidate removes runtime pair validation or the per-node map |
| Native handoff | `ai/alphabeta/native_legality.py:196–237,290–336`: state-only payload, one packed position, transient C call, direct packed64 decoder (no FFI call per decoded action), bounded immutable PUBLIC-action cache | Syntax hits additionally avoid SemanticAction decode/construction and exact binding/path construction |
| Generic transient S3 | capsule `native-source/native_module.c:3188–3230`: generates candidate buffer; each candidate calls `gc_semantic_runtime_make_checked_status` into a temporary child | H6 entry3123–3184 replaces these per-candidate trial children with enemy union/checker filtering; still generates candidates and allocates Python action integers/list/tuple |
| Existing attack dispatch | `rules/ir.py` incoming path/source/endpoint indices; `core/semantic_executor.py:650–798`; capsule `native_semantic_rules.c:1072–1120` prebuilds capture-authority membership bits | New union consumes existing Native bits. It is not a newly invented incoming index |
| Terminal check/availability | provider86–152: Native `in_check`, then one-use identical-Position packed-input handoff to Native `has_legal_action` | `FastBackend` in capsule `native_qualify.py:22–26` remaps ONLY `semantic_transient_legal_actions`; check/availability remain generic. S3 trials there are NOT eliminated by this experiment |
| Selected move application | `search_runtime.py:1507–1640` obtains cached binding, calls Python `engine._transition`, updates identity/hash/occurrences/snapshot/history/clock/terminal, restores frames on pop | This Python AlphaBeta path is NOT a persistent native make/unmake search just because legality uses Native. Syntax cache and S3 shortcut do not remove the selected move transition |
| TT and exit control | full `RuntimeSearchKey`1094–1117; push rollback1458–1505; context-managed pop1645 onward | Complete rule/position/history/ply identity, cancellation and exception safety remain necessary |
| Actual submit/replay | `session/session.py:119–139,197`; `core/transition.py:172–185` resolves Core legal action/binding again | Search-provider cache is not consumed by actual submit/replay |
| Outer data pipeline | capsule `syntax_query_run.py`: shared rule compile + full Session replay precede per-arm timer; return encoding/write and PV/source validation follow it | These costs remain outside reported constructor+choose reduction; no per-arm attribution exists |

The real syntax hit bypasses `_decode_action` and `_make_binding_from_action`;
that latter function875–974 checks exact actor/geometry and reconstructs the
compiled path through976–985. `_ActionBinding` is frozen and contains no victim
or Position reference: `_make_binding`843–872 stores pattern, actor owner/base/
current, geometry/source/target/promotion/path. Under this fixed admitted rule,
side+ENTIRE packed64 action and fresh successful C legality determine those
fields. The cache is per-provider/rule, bounded2048, and is not a legality,
terminal, history, score or TT cache. This supports the narrow reuse rationale;
it does not license Position-only bindings for arbitrary dynamic IR.

## Removable, retained and unknown cost

Potentially removable on cache HITS: decode/validation already implied by the
strict admitted C output, immutable SemanticAction/binding allocation, repeated
fixed geometry/path lookup. On MISSES the original work remains, plus lookup/
retention/clear overhead. The final cache already removes these hit costs; a
second cache cannot claim them again. Potential future representation work is
candidate/output materialization or a genuinely fused selected-move runtime,
not another Python incoming-attack traversal that Native bypasses.

Must retain the semantics of candidate authority/captures/own-anchor safety,
actual transition, Core terminal precedence, remaining clock, repetitions,
complete TT guard and cancellation/rollback. A new implementation may represent
these more cheaply, but this audit gives no permission to omit them. Inherited
check/availability and per-node binding validation are real remaining consumers.
A proof about ordinary nonanchor moves is not a proof about the whole runtime.

UNKNOWN: exclusive wall/CPU for each C trial, packing, decoding, transition,
terminal, evaluator, history/TT, per-arm replay/serialization, and peak RSS/native
heap. Candidate counts and cache hit counts are work counts, not time weights;
functions may nest, and terminal availability can stop early. No additive time
sum or invented removable percentage follows. The reported1.6975324→1.5768524s
saves0.1206800s in that measured section only. For an otherwise unchanged pipeline
with common nonnegative extra cost C, its fractional saving is
`0.1206800/(1.6975324+C)`, at most the reported7.11%; C is unmeasured by arm.
This is a conditional arithmetic bound, not a new timing measurement. Normal
Player passes `session._search_witnesses` (player.py:210); runtime history
reconstruction is conditional on missing witnesses, not every choose call.
Product per-step latency and total research/engineering cost are different
accounting quantities; do not add either twice. A proposed
larger kernel needs its own cost case; `1/(1-f)` with UNKNOWN f proves no speedup.
The isolated S3 result near parity already provides a negative practical control.

## Semantic and operational boundary

Source reasoning agrees with the admitted nonzero unblocked Leap theorem:
enemy attacks do not change when an ordinary own blocker moves; a nonanchor can
remove a check only by capturing its sole source; two distinct source squares
cannot be removed by one ordinary capture. An anchor tests its destination
against the pre-move enemy OR union: the victim cannot attack its own square,
and its removal uncovers no Ray. Overlapping attacks require OR/count-aware
updates; XOR-removing one attacker would erase another's identical target bit.
That is a concrete counterexample to a proposed incremental-XOR implementation,
not an observed defect in this OR-based prototype.

The actual rule guard (`native_semantic_rules.c:1125–1181`) excludes active
path/state/slot/post guards, triggers/aux/adjudication, promotion and executable
drops; fixes3×3/H6/repeat2/draw/three types, checks ordinary move/removal effects
and nonzero Leap endpoints. Position entry3123–3150 checks rule binding, ply<6,
side, empty hands, base=current/unpromoted, and exactly one anchor per side.
Inactive empty drop templates are deliberately skipped, not general drops admitted.
Ray blockers, move-again/type-changing/multisquare captures, self-attacking zero
Leap, dynamic guards and missing/multiple anchors defeat the reasoning and must
remain rejected. H128/repeat4 is not covered. Exact history truth never follows
from physical-position frontier parity.

**Confirmed production semantic defect: none established by this source audit.**
Confirmed operational difference: syntax provider uses strictTrue while the
comparison provider uses strictFalse. Runtime1182–1244 rethrows aborts/non-Exception
errors; ordinary provider failures rethrow in strict mode, otherwise disable the
provider and fall back to Core. Normal-return/cancel-recovery parity does not
establish equivalent operational-failure behavior. Also C has no Python checkpoint
inside its bounded frontier call; surrounding checks are retained, with no new
latency guarantee. Cache persistence after an abort is acceptable only for complete
immutable entries after real legality; runtime rollback alone does not validate
arbitrary mutable cache contents. No injected-failure or cancellation test was
newly run here; PRIMARY's published checks remain attributed evidence.

## Recommendation and stopping point

DEFER product activation, broader admission, another syntax-cache benchmark or
fused-native implementation. GO only for retaining the narrow published result
and this caller map. STOP using the saturated H6 set as evidence of improved
playing strength; PRIMARY owns the separate quality-design task.

Before any new related experiment, the smallest decision-changing evidence is
an existing-data table that distinguishes frontier-provider seconds and counts
from Native check/availability, selected Python transitions, Core terminal/TT
and outer costs, with inclusive/exclusive labels and missing shares UNKNOWN.
If current saved fields cannot attribute those costs, report that gap. A future
instrumented whole-call comparison would require a separate user assignment,
predefined complete-pipeline boundary and cumulative-cost necessity assessment;
this report grants no run or instrumentation budget. Do not rerun1520 returns
or pretend new counters alone supply a causal exclusive-time decomposition.

## Recovery, communication and cost

Own doctor verified DEV_AUX/sidemission; heartbeat file read ACTIVE/60min with
original binding. The old research session29cb5613 remains ENDED; no new60minute
research session or credit was created for this explicit bounded review. Old
Main/backups are deferred and the next action is WAIT_FOR_USER_ASSIGNMENT.

Own Dot opening initially failed on the stale chat_mailbox guard. Reviewed
published shared restoration was reused, preserving AUX receipt compatibility;
65transport regressions PASS. Initial default-temp permission errors and an
unsent frozen pre-publication request are retained. No engine tests/build ran.

Checkpoint `ff8f837850452089cc6469cb45bbe19ae0a436f6` was pushed/full remote SHA
verified before request `GC-SLACK-20261026-144033-9e243325`, root1792993268.610469.
Successful receipt and exact parent readback verified; the single delayed check
at05:46:10UTC received Dot1792993458.674609. Reply and complete parent were
privately preserved and reconciled. Adopted the source-only consumer distinctions
after reading submit/transition/terminal/player sources independently: availability
is Boolean/short-circuit (terminal.py:449–460), not an unbuilt full frontier to
cache. This correction was executed in this report; no runtime change follows.
Dot did not inspect all prototype sources or rerun measurements and granted no
new budget. Final actual all-inclusive bounded cost is
recorded in the accompanying completion receipt. No reply is a work gate.
H6 related prior99.204minutes is carried, not reset.15minute cap including ALL
recovery/intake/analysis/tool repair/tests/docs/publication bounds the related
sum by114.204minutes for this assignment; any other same-chain cost still adds.
AUX stays hourly/ACTIVE awaiting the user's next assignment after this delivery.
