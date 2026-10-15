# Checked sibling replies and exact source lookup —2026-10-15

Adopt the combined checked-reply hint and guarded direct source lookup as a
measured development choice. Keep q policy/defaults, prices, result fields,
complete histories and fallback authority. This improves measured cost, not
established playing strength or all-domain optimality. Science remains OPEN.
[Summary data](data/reply_witness_20261015.json) and
[source/plans/full rows/failures/replay](../archive/reply_witness_20261015/README.md).

## Concrete changes and invariants

A q invocation keeps one local reply action plus a presence flag, learned only
from the existing checked generator visitor on the SAME immutable rules. On the
next quiet sibling, recheck that action through the original normalized full
S3/S4 availability probe. If illegal, enumerate normally; negative status fails
closed; no reply clears the hint. This carries no score, history, terminal
certificate or TT authority. Parent/child histories, deferred-history gate and
full checked reconstruction before recursive search stay unchanged. Hint
provenance is essential: this is not a general arbitrary packed-action cache.
Source review checks generator versus validator restrictions; it is separate
from execution and is not a whole-domain proof.

The existing geometry path lookup uses a lower-bound binary search on sorted
sources. Only when `entries[source].source == source`, within bounds, and either
source0 or the preceding entry is strictly lower, return that first entry directly.
All earlier entries are then lower by sortedness. Duplicates/gaps/unsorted inputs
retain the original binary/linear fallback. No new table, allocation, ABI field,
public diagnostics API, solver, price policy or GUI change.

A naive index is wrong on accepted entries0→3,2→4,2→5,4→6: source2 must select4,
not5.3456actual baseline/guarded lookups across108crafted/random sequences agree
with explicit first-match expectation. Four public checked-action tests cover
sorted duplicates, unsorted duplicates, dense and absent source paths and preserve
parent/full child history. These edited numeric payloads test Native's contract,
not a claim that the standard compiler emits duplicates or Core graph equivalence.

## Prospective hint-only transfer

Freeze24new development families4301–4306/4311–4316/4321–4326/4331–4336,
4/8/12/16boards, bilateral_random/hybrid32attempts/opening256,45s preparation,
roots0/8 via repr-sorted Random(seed+7000). Immutable source-built baseline versus
instrumented hint; D3/1024nodes/5s four orders and D12/1s,4s two orders, q4/hard8,
TT0. Original160s family/2400s batch fuse; actual814.218s. All48roots/768planned
queries recorded, no replacements or missing slots.

192fixed-work pairs have zero non-time mismatches or clock censors. Family-balanced
caller ratios at4/8/12/16: .9687/.9665/.9653/.8867; conditional family95% intervals
[.9350,.9935]/[.9439,.9880]/[.9418,.9849]/[.8177,.9520].192wall pairs:4deeper,
188same,0shallower, all192same actions and same-policy scores agree. This does
not demonstrate move-quality improvement. New development seeds are not an
independent whole-domain holdout; intervals condition on six families per board
and normal concurrent load. Hint counters are part of this instrumented variant;
its result is distinct from the following counter-free comparison.

## Counter-free four cells, including negative interaction

A=existing baseline, B=hint-only, C=exact source lookup, D=both. Freeze12already-paid
4201–4203/4211–4213/4221–4223/4231–4233 families, roots0/8, exact old rules/walks/
prices. D6/8192nodes/5s and D12/12s, q4/hard8, TT0, two orders, four immutable
source-built arms. Original290s family/3300s batch fuse. All24roots/384queries
close in1829.718s;48fixed quartets have identical non-time fields and zero clock
censors. Engine construction is inside the cold caller timer. Ratios are cheaper
below1; three paired families per board,4000fixed-seed family bootstrap samples.

|Board|B/A|C/A|D/A (conditional95%)|C→D = D/C|multiplicative interaction|
|---|---:|---:|---|---:|---:|
|4|.9634|.9879|.9747 [.9527,1.0115]|.9866|1.0241|
|8|.9578|.9815|.9279 [.9157,.9484]|.9454|.9870|
|12|.9181|.9722|.8917 [.8406,.9332]|.9171|.9989|
|16|.8960|.9762|.8790 [.8261,.9642]|.9004|1.0050|

Multiplicative interaction is `(D/C)/(B/A)`; do not add separate savings.
The actual seconds interaction `(D−C)−(B−A)` means by4/8/12/16 are
+.001277/−.001959/+.002121/+.004696 seconds per fixed quartet. Raw/cost ratio
interactions are different scales. D is about1.17% slower than B alone on4boards;
the D/A interval there includes1. This negative tradeoff is retained. D improves
on B's point estimate at8/12/16 and on the old baseline point estimate at all
four. Choose one simple global implementation on this balanced development set,
not an invented board-size patch or universal-workload optimum. Reconsider with
concrete cold-consumer regret or semantic/cost evidence.

All48wall quartets retain the same depth, actions and same-policy scores in all
four cells. Same retained depth may be a shared fallback; this does not claim all D12
requests completed. No depth/score/WDL/strength gain is claimed; physical work differs
although logical work/result counters agree. Existing hypotheses/negative studies
and frozen prices are not rewritten.

## Wide consumer and semantic qualification

On eight exposed old32rules from opening1024, change the NEW comparison to16knodes,
D3/q1 or q4/hard8/16s, both orders. Original160s family/1800s batch fuse,64planned
calls recorded,667.513s.24uncensored pairs have identical non-time fields; conditional
caller ratios q1=.8604, q4=.9223. Eight clock-censored pairs remain in denominator.
q1 has2deeper order pairs, q4none; all32pairs retain the same root action. Actual
hint hits total9.23million, but attempted q work is distinct from retained q policy.
Engine construction precedes the wide timer, so these ratios are not pooled with
cold-constructor narrow/four-cell costs. Optional historicalV2/no-automatic scope
only; no default wide activation. Original live SHA/field checks were expanded
AFTER closure by a separate full-history audit of all64recorded PVs/74edges;
no timing result was rerun/replaced. No universal gain or strength claim.

168supported small-board semantic queries preserve complete Core/Native board,
hands,aux,SHA,actor/check histories;14unsupported wider roots/112planned slots
stay explicitly unsupported. Prepared combined source repeats168with0mismatches.
197direct valid/absent/stale hints and10actual one-edge legal mate/stalemate
continuations preserve original availability/root state.24private negative-probe
injections at cached/enumerated sites fail as internal_error;24TT0/1 recoveries
restore complete roots/retained lines and match reference policy. These are
injected errors, not actual production memory failures or universal proofs.

Counter-free private hint full active suite:2664pass. Prepared combinedV1 and
optional replyV2 source-only rebuild:38focused plus35roots/4497legal actions,
full PV history, older private reads blocked. Final normally rebuilt installed product:2668full active tests pass with no
failures/skips; its C sources exactly match the qualified source export. Sanitized
public-copy replay is verified separately before delivery; existing Windows/
Python3.12/Zig toolchain, not a clean-machine installer.

One fixture initially tried an unplayable terminal initial RuleSet and correctly
failed INITIAL_NO_LEGAL_MOVE before queries. Preserve that source/log; actual
legal one-edge continuations replaced the invalid fixture. No OS/security/approval
blocker was hidden or attributed to Smart App Control.

## Next consumer question, already begun

Analyze recorded termination before changing policy: at4s, baseline12/16boards
both retain q0/D1 on10/24queries; all24in each group stop on time. Small boards
also show check-hard limits. qnodes includes reserve/depth0 visits, so it is not
measured wasted work. No default q-policy change follows from this histogram.

The next question is actual unfamiliar-rule admission versus amortized search,
not another unchanged q curve. A frozen small pilot ran16fresh processes/64queries,
one already-paid rule per4/8/12/16board, two orders, baseline versus combined,
four actual same-root persistent-engine queries. All non-time search fields agree;
actual13.317s batch,180s original fuse, no missing slots. Python imports and
independent diagnostic checks are separate from admission+search sums. This is
fresh process, not a cold OS/filesystem cache or a physical-game workload.

Baseline admission shares of first-call pipeline are .588/.585/.809/.868.
At16, median Python compilation.527s and rule-price construction.163s dwarf
native compilation.0105s; engine creation.000051s. Search-only first-call ratio
.779 becomes pipeline ratio.972 in this tiny sample. Board4 pipeline noise makes
its apparent benefit larger than search-only despite unchanged Python phases;
do NOT treat pipeline ratios as causal speed estimates or add confidence claims.
Actual N4reuse is recorded, not assumed linear amortization. Source inventory:
SemanticSearchEngine receives compiled rules; learning/selfplay and arena reuse
that ownership, so admission cost is not charged to every move. No training/
learning duplication or API redesign. Next profile actual Python compilation/
semantic admission once, then choose closure reuse versus search-policy work
from measured incremental cost; preserve complete rule/history semantics.

A bounded rule-price sanity control additionally compiles36profiles on12paid
complete rules: original roundtrip and two bijective type-label renamings preserve
mapped exposed board/hand values to1e-9. Promotion/drop data retained; no old price
replacement, formula fitting, label/holdout reads, graph-equivalence or price-quality
claim. This supports a narrow label-consistency check, not cross-game truth.


The next attribution actually ran: one complete4331rule, two fresh-process orders,
control versus cProfile. Mean control.4751s, profiled.8551s (1.80overhead), so do
not treat profile fractions as unbiased wall costs. Profiled semantic lowering
.4386s versus initial-playability validation.000399s points away from skipping
validation. Reverse attack paths/source partition dominate the sampled constructor;
cumulative times overlap. Raw source shows bounded65536path fallback and rank/
source/type/duplicate order are execution data that must be retained.

A private get-versus-eager-setdefault partition pilot then actually ran48calls on
four paid indices(316/3368/21132/60556rows). Mapping, key order, ranks and borrowed
row identities match; None fallback preserved. Cost ratios4/8/12/16 are
1.0459/.6471/1.3575/.7972. Mixed regressions reject immediate universal adoption;
no GC tuning, board patch or Core IR edit was made. Next inspect why derived
indices are constructed at multiple stages and whether their exact IR dependencies
match before proposing reuse; never assume equivalence or remove initial checks.
This is a new measured compiler question, not repeated q tuning or a second solver.

Outgoing-content review caught a machine-home path in the copied summary before
commit; only the publication copy was sanitized, exact private original retained.
No credential or raw-account record was published; no approval queue was added.
