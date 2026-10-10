# Protected reserve and residual backend diagnostics — 2026-10-10

A cheap completed D1 can survive an interrupted tactical refresh under the same
live budget. This addresses the earlier first-q1 D0 starvation, but does not
make replacement monotonically better. The implementation is a research-only
source clone in `scripts/reserve_refresh_diagnostic.py`; product search and the
frozen UI branch are unchanged. Exact producers, failures and raw observations
are routed through `data/reserve_refresh_20261010.json`.

## Completed reserve versus tactical coverage

The prototype completes ordinary-q0 D1, then recomputes D1 with ordinary-q1
and hard8. It reuses the context, cumulative node count and original deadline.
Only successful RHS completion replaces the reserve; interruption retains the
completed result. The refresh clears and disables TT, then restores configured
q4/TT with an empty table before deeper iterations. Those costs belong to the
call. Explicit q0 has no extra phase. This is a deliberately isolated policy,
not a proposed general cache framework or a verified UI submission contract.

On two existing queen-loss parents, naive same-table refresh adds only one main
node, zero qnodes and one hit, reproducing q0 scores1043/-925. Isolated refresh
adds44main/107q and42main/91q, scores-992/-2955 and avoids both immediate queen
captures.32 reversed25/50/100ms/1second calls retain completedD1; short refreshes
abort to the cheap reserve, while one-second refreshes complete. Four injected
begin/complete cancellations retain the appropriate result and restore internal
position/ply/terminal/stack; node-quota fixtures verify one cumulative budget.
Progress-callback cancellation and precompletion node4/32 controls preserve
the original completed reserve or exact incomplete fallback, respectively.
Earlier event fields marked runtime restoration as None: keep them as unknown,
with the later deterministic assertion controls stored separately.

Thirty old cold UI parents, alternating arm order at the same one-second/q4/
hard8/1M fuse, have7 finiteD2-material regret improvements,1 worsening by1000
and22 ties. Mean regret is900→166.7, without observed completed-depth loss.
The exposed finite material reference is reused unchanged; four old q4D2 caps
remain UNKNOWN. This is a development diagnostic, not a chess-strength estimate.
Eight Shogi/generated transfer calls retain completion; generated hardq limits
persist. Four explicit-q0 controls retain exact D2 action/score/work.

The retained white-ply17 regression is informative. Immutable full-window q1
values for exd4/Ke1 are-14014/-13075; independent specialized material q1 gives
-14000/-13000, agreeing on Ke1. After ...Qc1, Ra1xc1 is legal in both children,
but is a mandatory check evasion only after Ke1. Thus q1 extends it there while
its ordinary-depth boundary stops after exd4. The original materialD2 regret1000
stays intact: its horizon differs from the q1 contract. Neither result supplies
a strategic oracle, and no horizon/evaluation tuning is performed to erase it.

## Warm cache is a different experiment

Two original q4D2 primes complete within the predeclared5second fuse. Warm
baseline revisits retainD2, whereas protected refresh retainsD1 with the cold
q1 values. The follow-on entry-clear ablation starts each arm from independent
copies of the same prime, charging4.9–5.2ms copy/clear setup to the one-second
budget. A sidecar records actual accepted TT producer and request conditions.
Warm cheap A uses EXACTD2/ordinaryq4/hard8 entries for requestedD1/ordinaryq0;
entry-cleared B produces genuine q0 scores1043/-925. Both refresh to q1, but
cheap provenance differs. Unknown producer fields must remain UNKNOWN.

A smaller alternative bypasses TT reads/writes only in cheap-q0 and q1 phases,
retaining the original table for configured-q4 deeper iterations. This also
avoids fresh-generation cheap stores replacing old deeper entries. Two further
same-prime copies with charged setup preserve genuine cheap scores1043/-925
and q1 scores-992/-2955, then completeD2 with original warm-q4 scores21/-1946;
clear-on-refresh remainsD1. Actual sidecar hits verify q4 producer/request reuse.
This is a declared selective warm contract, not exact finite-horizon equivalence
or a quality gain. Two roots justify testing cold/transfer/interruption seams,
not deployment or a new namespace framework. Prototype source is archived.

Dot's complete review is adopted: preserve diagnostic isolation, separate these
contracts, and make the small same-prime ablation before considering cache
eligibility changes. It read supplied evidence/code excerpts, did not execute
or inspect unpublished source independently. No workflow/default/UI change.
Slack code-fence rendering changed exact request bytes; private native receipts
and actual arguments retain association, without claiming byte-verified payload.

## Residual execution cost

Forty-eight reversed identical lexicalD2 Core-indexOFF/Core-indexON/specialized
calls on the existing eight roots retain exact move/score/work. Chess trigger
index savings are11.4–15.1%; Shogi has no fixed triggers and retains jitter,
including an adverse millisecond promotion control. Current Core costs are
about9.6–15.0× specialized Chess and29.0–157.0× specialized Shogi in this small
fixed-work assay. These are neither strength ratios nor a parity requirement.
Profiling overhead is about2.9×/3.4× on Chess-middle/Shogi-drop; cumulative
hotspot times overlap. Guard/drop/check work motivated two smaller probes.

Target-directed actor-check paths preserve eight fixed signatures but save
only1.2% on Shogi-drop; defer. Eager line-guard filtering saves6.6% there with
an adverse3.6% Chess mean. Its first resolution order changed an absent-source
short-circuit exception; the corrected fallback matches7200 typed outcomes,
including153 paired exceptions and12 cancellation probes. These synthetic
bindings do not establish public-rule reachability.32 one/four-second product
controls retain all action/depth results: defer rather than install a new path.

A different parent-local drop-guard memo reuses the full original predicate for
same-file/rank target guards across one pattern/type/generator. It retains
predicate order, resolves no reference early, polls every guard/hit and never
shares results across parents/types. The initial fixed assay saves about10%
on Shogi-drop;45120 guard comparisons over8×8/9×9/9×10 and576 cached-cancel
probes agree. Thirty-two q4 common-time calls retain all choices/depths. A separately
predeclared explicit-q0 resource curve on the same Shogi-drop parent,
.5/1/2/4seconds with two reversed pairs each, also retains choices and
completedD1/2/2/2. More recursive work fits, but no complete layer changes.
Defer integration on these scoped results; this does not reject local caching
under other demonstrated bottlenecks. No WDL or universal parity gate is added.

The generated4seed21 hard8 abort path contains nine distinct ongoing positions.
A full11ply public legal replay matches their board/hands/aux/terminal states;
last five qnodes are checked. The old similar trace remains evidence; the new
contribution is authoritative full-path replay. No repetition patch, hard-limit
increase or stand-pat in check follows. The completedD2 result is retained.

Additional dynamic auxiliary dispatch controls compare216 typed configurations
between the installed index and original fallback. Per-owner/global square
references read the pretransition Position even when the working aux map differs;
fixed and dynamic clear events preserve owner filters, None/outside handling and
all original state. Independent expected outputs include dynamic-only events,
so fixed clears cannot mask a missed dynamic trigger. These are direct typed
fixtures, not full public execution with a substituted castling slot schema.
The initial fixture assumed a nonexistent second slot; failure is retained.

## Reproduction and limits

Use the exact source versions bound to each output, not the final runner for
all historical rows. `--games` accepts the Agent-generated frozen UI game record
in the prior UI evidence archive; no user game or UI-source export is required.
Root positions are exposed development controls, with fixed material/evaluator
and historical rule boundaries preserved. All timed calls are serial. Budget
and cancellation are cooperative, not strict wall-clock guarantees.

The initial runner import, test-fixture premise, source-transform indentation,
invalid SearchLimits keywords, missing GameSession undo and producer quoting
and UTF-8 document transport failures are retained. Corrections do not turn those failures into observations.
No new human labels, Xiangqi holdout, training, worker, fee or mature-engine
strength comparison is introduced by these experiments.
