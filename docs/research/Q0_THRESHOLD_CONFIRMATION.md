# Integer root-tie threshold confirmation

The optional exact-root Native q0 route now confirms an apparent tie with an
integer threshold search instead of solving every losing candidate exactly.
Material root ordering, selected-branch canonical reconstruction, full history,
same-depth TT semantics and the final scalar check remain in place. Default
Core/UI q4 and legacy Native modes are unchanged. This is a search-cost repair,
not a piece-price, strength or whole-generated-domain claim.

Base: f1ea1d3870302777de6b56ae4cd62a17d7bf7bb0.
Exact sources, synthetic inputs, results and failed prototypes are bound by
[data/q0_threshold_confirmation_20261012.json](data/q0_threshold_confirmation_20261012.json)
and its 94-member archive. The previous 109-member archive remains unchanged.

## Decision and observed cost

Changing all root ordering to canonical encoding was rejected. In 16 paired
16-second/1M-node calls it raises the saved gen2 root from D4 to D5, but lowers
seed1202 root0 from D5/5405 to D4/3505. Fewer attempted visits do not imply a
better delivered result. No root-ID selector or uniform ordering change follows.

The narrower confirmation keeps the existing root ordering:

| Saved gen2 query | Previous visits | Threshold visits | Observed time |
|---|---:|---:|---|
| Fixed D4 | 281094 | 13794 | about 11.4 to 1.08 seconds |
| Fixed D5 | 347112 | 79801 | about 16.5 to 6.13 seconds |

All 12 fixed calls agree in full score/action/PV/depth. Both entry-PV variants
have the same visits; the retained variant preserves the existing PV-entry
TT-cutoff restriction. Fifty-six generated finite calls retain 28 full-tuple
pairs. Sixteen actual equal-budget delivery calls improve gen2 D4 to D5 and
preserve Shogi D5, seed1202 D5 and seed1204 D5. This is four exposed roots, not
independent playing utility or a universal speedup. Ordinary concurrent load
was allowed; timings are observations and attempted visits include incomplete
later iterations. The seed1204 candidate has more attempted work at equal time.

## Bound argument and direct checks

Let the exact root incumbent be b and T=-b. The first narrowed query gives the
later, encoding-smaller candidate a parent UPPER bound equal to b, hence child
value v>=T. A completed child query in [T,T+1] gives either v<=T, proving
v=T, or v>=T+1, excluding the candidate. Only confirmed equality can take the
existing equal-score preference. The fail-high return is only a parent upper
bound; it never supplies the final exact trace. A return below T contradicts
the earlier lower bound and causes internal_error rather than being clamped.

This argument requires deterministic integer finite q0, an exact incumbent,
matching history/evaluator/root offset and the existing exact-horizon TT mode.
Existing finite mate normalization and score bounds remain; it is not a
floating-point, selective aspiration or q4 result.

Twelve diagnostic calls independently remove TT and solve every actual
confirmation child in a full window: 314 classifications, six ties and
308 strict losses, zero disagreement. Shadow work is additional diagnostic
cost and excluded from deployment timings. Twelve existing Chess EP queries
with unit/zero/one-Knight profiles and TT0/1 cover 30 true ties and four
exact one-point losses; all 12 whole-root tuples match TT-free full searches.
These are actual guarded trigger paths, not merely hypothetical trees.

Two predeclared node limits stop inside root confirmation and final reconstruction.
Both retain the prior complete D3 result; four-node fields/PVs are not inferred
from a literal leaf. Retrying the same persistent TT reaches the cold full D4
tuple. These are node-budget phase controls, not an OS cancellation-latency test.

An injected contradictory bound triggers internal_error in the first iteration,
restores the root and returns the depth0 legal fallback; there was no prior
completed iteration in that fault query. Its saved field name
previous_complete_reference is imprecise: the comparison is a depth0 fallback,
not a completed minimax value. No naturally observed contradiction is claimed.

## Regression and separate caller policy

The guarded private candidate passes 40 relevant tests. Installed production
passes 41. The added saved-gen2 16000-node full-PV regression fails the previous
binary at D3 and passes this version at D4. An earlier unguarded private
40-test pass is retained separately, not counted as current production testing.

Actual terminal-proof stopping remains private and opt-in. Sixteen current-base
consumer calls cover three real winning submissions, pre-cancellation and
node-fallback submission. Twelve injected during-proof cancel/retry/cold calls
on the prior reconstruction base and another twelve on current threshold source
confirm four no-submit cancellations and four same-TT/cold full-tuple pairs per
version. A native flag is injected after the terminal probe, so this establishes
that boundary handling, not real-user callback latency. An actual D1 win is
never relabelled a requested D12 training value. No UI/default proof policy
or training enum has been adopted.

## Actual local UI handoff

[LOCAL_UI_SEARCH_TEST.md](LOCAL_UI_SEARCH_TEST.md) describes the separate local
test copy. It preserves the latest user UI revision 99c97bb87474c44af94c76571f326ef8a41eb898
and does not modify or push ui-test. The named local profile uses current
installed Native q0/material/maxdepth12 for Chess; declaration-enabled Shogi
and generated legacy rules retain explicitly labelled Core q4/hard8. It does
not silently downgrade a q4 request. Six real WebGame submit/cancel/restart
scenarios pass; a built page, health and three real HTTP PVE first moves pass.
A later real in-app browser check additionally verifies Chess setup, reload/continue,\nhuman e7-e5 and the Native reply with three-step history. Old CoreAI labels were\ncorrected in the isolated copy. All-rule browser coverage remains unclaimed.

Resolved integration failures remain local: missing explicit Native max_depth,
Windows CP1252 stdout, and a check incorrectly demanding next actions after the
declared hybrid seed42 actually checkmated on move1. The same existing games
were inspected; no resampling. Shadow compilation initially used an invalid TT
type and was corrected to GCSemanticTable; the failed source remains archived.
A stale extra Shogi input was rejected before any shadow query. Slack snapshot
path quoting and a missing reconcile request argument were fixed before the
successful saved read/reconcile. No unresolved user intervention is hidden.

Dot reviewed the published base source and supplied the contradiction/boundary
objection; it did not execute these new local tests. The full thread and new-root
coverage were saved and reconciled. DEV_AUX's segment20 is independently read at
1de362ef6c7ef9b5de3ec5ef236333469f1428f7: finite learning signal, depth/geometry
and encoding-cost findings remain its own lane, not q0 production validation.
Science is OPEN. Next separate remaining canonical cost from actual caller
usefulness, and extend the explicit local UI adapter only where a real complete
interface can be demonstrated.
