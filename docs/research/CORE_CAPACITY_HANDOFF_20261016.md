# Core capacity handoff and long-rule admission —2026-10-16

Two concrete changes are qualified: preserve a completed Native result whose PV
ends at the last history slot, and distinguish the configured rule horizon from
fixed Native storage. No history or result fields are removed. Science is OPEN.

## Actual failure, correction and feature contract

The prior PUBLIC base was2d3e54105bae3e7e38a1543b4f98cdc7442e479e. The first memo
control used actual max_ply2048/repetition10000 records at prefix0 and1024.
Both are ONGOING; the old compiler refuses max2048 before import at both roots.
The existing explicit Core player executes the SAME declared material+3+9
callback, returning D1 score-71/root static value-80 with complete PV/history.
This was not an automatic full-search fallback or evidence of a compiler bug.

A subsequent admitted max1024 control exposed a caller failure: at prefix1022
D2 and prefix1023 D1/D2, q0/q1, the kernel finished a legitimate MAX_PLY draw and
checked a valid PV. Required post-search dynamic-feature extraction at leaf1024
then raised NotImplementedError, discarding the completed result. Six exact
failure receipts are retained. The32-query pre-fix panel has26 successful result
receipts plus those6 failures; all32 post-fix queries return matching Core scores.
Root1024 itself remains an actual rule terminal, not invented storage adjudication.

Only when root ply plus physical PV length equals1024, a plain rule-terminal
caller result can recover its three fields through complete Core PV replay.
It preserves Native's ACTUAL rule-ply trial gate and check pressure. No broad
Native fault is caught; ordinary calls keep the normal Native feature path.
Automatic/long-rule last-slot feature cases remain explicitly unsupported/Core,
rather than using an unqualified different feature definition. Root/history
remain unchanged and Core errors propagate through retry.

Dot's useful objection separated GameState's blanket terminal-empty actions from
Position-level S0-S4 actions. The initial draft used Position views and passed a
real asymmetric raw2/1 control. PRIMARY's deeper source review then found the
additional gate inside native_semantic_runtime.c: at/past rule max, trial moves
are accepted ONLY for automatic PENDING. Thus pure Position counts alone would
also change the existing Native definition. The initial draft was NOT published.

The corrected asymmetric control compares actual MAX512 and MAX1024 records:
both have raw Position counts2/1 and pure Position vector(1,0,0), but Native at
MAX512 is(0,0,0); corrected full-slot result matches that actual contract. A
separate actual e2e4,d7d5,f1b5/max3/noautomatic terminal retains Native/Core
feature(0,0,10), proving check pressure is computed rather than returning a zero
placeholder. Both distinctions are required: do not clear real terminal/history,
and do not assume 'ignores terminal status' means 'ignores the rule-ply gate'.
An actual depth0 long-rule query has no PV/empty result features; an individually
supplied legal last-slot edge is not mislabeled a Native PV or certified feature.

Source inventory matters: learning/selfplay.py consumes result.dynamic_features
as actual leaf input to its frozen checkpoint calculation. This field is not an
unused statistic that can simply be deleted. PRIMARY read this fixed-base source;
it did not run selfplay, training, arena or AUX programs. No new diagnostics API
or consumer migration is introduced. The Core evaluator callback's public search
view provides position/ply/terminal, not a promise of a public history attribute;
full history remains authoritative in the backing search runtime and terminal logic.

## Real PENDING history and the three independent bounds

A declared4board rook/king four-action cycle, automatic trigger1, rule max3 and
repetition10000 yields actual continuous-check events through1025. No edited
counts, synthetic event stream or private session-state injection was used.
The chosen line is not a forced continuation or optimal-WDL proof.

Core remains ONGOING, retains1026 history entries at1025 and executes the same
3+9 callback. Normal Native/Core D1 scores agree at prefixes1020/1021/1022:
165/-115/156. At1023/1024 Native explicitly refuses the requested search path;
at1025 import explicitly refuses. None is called MAX_PLY, a draw or no legal moves.

The new Native kernel advertises semantic_max_rule_ply=65535. Its uint16 rule
field now admits that range; GC_SEM_MAX_PLY remains1024 and position/undo sizes
remain53920 bytes EACH. No history/stack array grows. A rule can therefore have a
larger adjudication horizon while Native handles only bounded paths fitting its
storage. Requested main+enabled hard-q+feature allowance is checked before C
search when automatic continuation OR the rule horizon can outlive storage.
Actual records beyond storage still need the existing Core route. Rules outside
the uint16 horizon range also remain Core-only.

Python binds admission to the captured kernel's capability. Missing capability
means the old conservative1024 limit; unknown/bool/string capacities are refused.
The unbound pure payload builder retains its old default. Ordinary rules preserve
the existing default builder call path; a full regression caught a keyword-call
compatibility failure, which was fixed and followed by a fresh passing full run.
Rule ownership stays with the captured backend even if the default loader changes.

Core's optional Native legality provider now declines at min(rule limit, Native
storage), with the existing S4 reply margin. Actual20 Core calls on prefixes
512/1022/1023/1024/1025, q0/q1, provider off/on, retain all10 paired scores/actions/
PVs and zero operational failures. At1023 the provider executes one Native
frontier before Core continuation; at1024/1025 it performs zero Native frontiers
and records ordinary fallback. This is not an automatic replacement of a supplied
evaluation function or Native full-search fallback.

## Frozen cost and completion evidence

The first24-family protocol was frozen before new seeds: six families at each
4/8/12/16 board size, 32 generation attempts, same actual8-ply random walk,
paired horizons1024/2048, fixed shared rule-derived material+untrained3+9 values,
q0/TT0 D3/131072 visits,2/12seconds. One actual4board terminal tail retains its
six missing query slots;138/144 queries execute, no replacement. Batch clock
635.596seconds includes acquisition, setup, queries and recording, not engineering.

| Board | Actual families | Native1024 D3 at2s/12s | Pure Core1024 D3 | Pure Core2048 D3 |
|---|---:|---:|---:|---:|
|4|5|5/5|5/5|5/5|
|8|6|6/6|0/2|0/2|
|12|6|2/6|0/0|0/0|
|16|6|0/2|0/0|0/0|

All12 jointly completed Core horizon pairs have identical raw scores/actions/PVs.
In12 Native/Core joint pairs, six nonmate raw scores agree; six raw mate scores
differ by the existing1B versus100M conventions. Their exact public PVs end in
the same actual one/three-ply checkmate/winner. Preserve raw differences; do not
call this12 raw equalities, independent all-defense validation or learned prices.
Core and Native algorithms/order/work definitions differ; equal visit numbers are
not equal physical work. The callback separately enumerates its3 and9 inputs.

A PRIVATE two-C-file feasibility pilot then ran46 exposed-root Native2048 calls:
32 jointD3 comparisons with stored Native1024 results match ALL non-time fields;
actual1023/1024 search refusal and1025 import refusal stay explicit. It did not
increase arrays, silently truncate history or certify a final product alone.

The capability-gated final candidate received a NEW16-family protocol, four
families per board size, before its inputs: old-kernel1024 versus new-kernel2048,
same shared mechanics/actual record/profile, two counterbalanced repetitions,
D3/131072/4seconds. One actual terminal tail preserves four missing slots.
60/64 queries execute in122.872seconds:18 jointD3 pairs have all non-time fields
equal;12 pairs both retain shallower depth, no arm-only D3 completion. This is
scoped admission/semantic evidence, not a speed/strength claim. Conditional costs
and all censored raw receipts remain available; the older pilot is not relabeled
fresh transfer. The rule limit is far beyond every compared finite frontier.

## Validation, failures and source recovery

Final normal full regression:2817 tests pass in302.966seconds. The60 new tests cover
actual terminal/PENDING long records, features/S4/promotion/drop/aux mechanisms,
Core failure/retry, ordinary Native error propagation, old/unknown capabilities,
uint16 parser bounds and direct search-entry storage refusal. Existing PV,
declaration, cancellation, backend ownership and source-built injected-error
checks remain. No broader guarantee is inferred from this finite coverage.

The actual publication ZIP includes scoped normal source, exact retained records
and historical producer/prototype sources. Every member is hash/CRC verified in
a NEW source directory, Native rebuilt, affected checks run and all search entry
points disabled for receipt replay. Current reader validates337 successful query
receipts,1023 full Core states,978 Native states,679 PV edges and177 result feature
vectors. Forty-five states beyond Native capacity are explicitly Core-only;
six original caller failures and the original compile/capacity refusals remain.
It does not recompute old clocks, search objectives, WDL, games or training.
The publisher and actual restored-copy counts/manifest are separate receipts.

Retained operational failures: first capture placed compilation outside its error
handler; source/quoting preparations failed before queries; a raw GameRecord
dataclass dump was initially passed to the JSON transport decoder. The consumer
now reconstructs that EXACT immutable public record, checks round-trip dataclass
equality and replays it; no saved evidence is rewritten. Selective publication
copies first missed transitive test imports; original copied files/logs are kept,
and a new source dependency closure passed. These are not scientific censors.

Sandbox AccessDenied reading existing Python link libraries prevented a private
build and source-build regression fixtures. Normal supported escalation resolved
the actual failure. No Smart App Control diagnosis or security-setting change is
claimed. Private originals stay ignored; outgoing source/evidence copies are
checked for actual personal information/passwords/credentials, including metadata.

One proposed next optimization was closed BEFORE build/search: current fixed
2d3e source ALREADY has history_len<R-1 in q-history deferral. Its source assertion
invalidated the stale premise;0 new builds/queries. It is not a pending retry.

## Collaboration, current choice and limits

PRIMARY discovered/executed both boundary controls and owns these backend changes.
Dot's complete new reply1792155826.211089 read fixed2d3e movegen, semantic executor,
Native three-feature and reference-test source; it did not execute the unpublished
patch. Its Position-versus-GameState objection improved the asymmetric regression.
The complete35-reply thread was read as exact20+15 pages and reconciled only after
private raw saves. Legacy original payload binding remains false. Advice, source
review, delivery and independent execution remain distinct; no routine approval.

AUX76 fixedda6b0043 two complete reports are now read-only; AUX77 complete
request is inline-only, not implementation/execution. No other checkout/process was changed
or delayed, and no solver/verifier/cursor/learner was imported or run. Ordinary
concurrent load is an interpretation limit, not a stop or rerun requirement.

Keep the current search-first choice and cheap static baselines. Do not revive
unadopted3+9 fusion, filters/q shortcuts or expand Native arrays from these data.
Current LOCAL_MAINLINE.md replaces its growing diary with decisions/reasons and
fixed historical evidence; the preceding complete text remains at PUBLIC2d3e.
The goal remains complete generated rules, including promotion/drop/aux/history,
with useful decisions per total cost. This delivery is not the final scientific AI.

Closing peer update: AUX76 owner reports1924 outcome games and15 independent
saved proof/path checks; these remain owner execution. PRIMARY read fixedda6b0043
SEGMENT/REPLAY, checked the W-L table arithmetic only and did not run its code.
The fixed ACTION guide is not a generic WIN certificate. AUX77's new price-order
cell and D4 tie-order question is inline-only. The third CHAT Leaper-parameter
memorandum is retained as a future reference with its explicit no-work-now scope.
No new price experiment or reassignment follows. Checked details/hashes are in
data/capacity_peer_update_20261016.json.

Final actual publication copy:364 ZIP members,277 source files,172 affected
checks; archive SHA25611e6026e64a4521f3bf70236f44d5378430ee25e1aaf902b9b66f63b23732cd6.
All337 receipts replayed from the rebuilt sanitized source copy.
