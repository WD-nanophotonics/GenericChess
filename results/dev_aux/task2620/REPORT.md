# Task2620 independent frozen-model Chess evaluation

Status: COMPLETE; full independent action/accounting audit PASS. Science OPEN.

## Closed result and decision

The original one-shot launcher exited0 at2026-10-20T09:19:26Z in3199.534s,
inside the unchanged4500s execution cap. All1536 registered slots are present:
1267 actual terminal results,269 UNKNOWN,0 missing. Paid evaluation cost is
24728530 candidate-plus-foe nodes and222704 queries. The independent auditor
replayed every recorded action/history, terminal result, actor/model identity,
per-search/per-slot cap and both-side accounting. All24 source pins match.
The48 first-eligible8-ply roots,6051-record exclusion pool and complete randomized
slot/cap schedule were independently reconstructed without outcome selection.

The six predeclared mean reward-difference bounds below retain the complete384
paired slots per contrast, including every UNKNOWN as[-1,+1]. These are exact
finite-panel bounds, **not confidence intervals** or population effects.

| Left minus right | Lower | Upper |
|---|---:|---:|
| initial - TreeStrap | -0.742188 | +0.023438 |
| initial - TDLeaf | -0.867188 | -0.075521 |
| initial - WDL | -0.638021 | +0.153646 |
| TreeStrap - TDLeaf | -0.416667 | +0.192708 |
| TreeStrap - WDL | -0.187500 | +0.421875 |
| TDLeaf - WDL | -0.088542 | +0.546875 |

Thus TDLeaf-minus-initial is[29/384,111/128]=[+0.075521,+0.867188], positive even
under worst-case UNKNOWN assignments. The other five full-panel intervals span0;
this panel does not select a winner among the three learning packages. TDLeaf's
per-seed gain is sign-resolved for two seeds and unresolved for two. No seed,
root, endpoint or weight vector was selected after inspecting these outcomes.

| Endpoint | Learner wins | Draws | Losses | UNKNOWN | Paid eval nodes |
|---|---:|---:|---:|---:|---:|
| initial | 153 | 38 | 102 | 91 | 6365291 |
| TreeStrap | 240 | 37 | 51 | 56 | 6069885 |
| TDLeaf | 267 | 21 | 35 | 61 | 6143961 |
| WDL | 220 | 27 | 76 | 61 | 6149393 |

257 of269 UNKNOWN are in the assigned20k-node stratum;12 are in40k. Most ended
at the remaining per-slot node allowance, not a mysterious missing process.
The40k stratum alone has sign-resolved TDLeaf>TreeStrap>WDL>initial comparisons,
but its roots differ from the20k stratum. This is a descriptive finite stratum,
not a causal estimate of extra nodes and not permission to choose a new overall
winner, extend an old cap or top up any slot. Both strata and all seed/root
breakdowns remain in `run-002/panel-description.json`.

Terminal authority is python-chess with the common predeclared available-draw-
claim policy, including legal intended-move claims:1144 checkmates,72 fifty-move
claims,48 threefold claims,2 insufficient-material draws and1 stalemate.
Search resource/horizon endings remain UNKNOWN. A different draw-claim policy
or search/opponent distribution is a different comparison.

## Source verification and corrections

The12 frozen training endpoints were independently reconstructed from all
113666 original training queries and709 started episodes, including every
search action/value/node/PV/bound receipt, learning update and59 complete WDL
proposal blocks. Final weights and1M-node budgets match every arm exactly.
This added **verification** cost is12M nodes and1656.978s, separately paid from
the original12M-node/1545.365s training. It adds no strength samples or training
labels, replaces no original row and establishes no convergence or population
claim. Per-method evidence is in the two `*-source-replay/result.json` files.

A real historical telemetry defect was reproduced: TreeStrap's
`weights_before_search` field was serialized after its update. Four first-change
witnesses and the full reconstruction confirm the post-update interpretation;
the frozen trainer/log/model were not rewritten. Future trainers must snapshot
actor weights before search/update. The audit itself initially could not import
its reward/training checks from the analysis module; its import was corrected
and actual-search/corruption/terminal/missing/closure regressions added.

Training AlphaBeta uses a traversal RNG; deployed TrainingSearch uses path-
hashed ordering.32 fixed complete-query witnesses agree with exhaustive D2
values and optimal-action sets, while22 choose different tied actions. This
checks finite semantic compatibility, not identical policies or a strength
gain from changed ties. The initial64 saved-query source replays also match.

Ordinary sandbox process visibility initially suggested the evaluator was
absent. Supported scoped process inspection confirmed the original process
chain was alive; its subsequent original exit receipt closes the question.
No interrupted-run story, replacement evaluator or retry was invented.

## Next direct-route task

Retain TDLeaf as a working candidate supported against initialization on this
finite Chess panel, without declaring it superior to TreeStrap/WDL. Prioritize
strict SAME fixed-scale learner Generic interface/cost feasibility over another
Chess resolution panel. Task2621 reuses the exact Model/TDLeafEpisode classes;
the older FreeModel Generic comparison is not strict fixed-scale transfer.
No engine/UI default or other role state changed. Broad Generic learning,
stable rule-independent prices and population strength remain OPEN.

## Original registration and qualifications (preserved)

Task2618 v4 completed all12 training arms (12M paid nodes,693 actual terminal
training episodes,16 UNKNOWN and2171 unstarted slots), exit0 in1545.365s.
Its20 original source pins match. Its original evaluation was never started:
registration/execution require the same active session, but that segment ended;
the pinned evaluator also references Model without importing it. Existing tests
only exercised helpers, missing the actual execution path. Neither old sources,
plan, session clock, cap nor missing evaluation slots were changed.

This is a separate evaluation-only experiment over all frozen endpoints, not a
training retry or completion of old slots. The new48 full-history eight-ply roots
are outcome-blind first eligible families in the920001 namespace. They are exact
record-disjoint from6051 known prior roots, including the complete prospective
training pool containing the v4 families and the original32 evaluation roots.
This is exact root disjointness, not descendant/transposition or population
independence. All four original seeds and all endpoints are retained; no weights,
seeds, roots or endpoint winners are selected from development outcomes.

The1536 slots cross four seeds,48 roots,two learner colors and four endpoints:
initial,TreeStrap,TDLeaf,WDL. All use the same fixed foe, D2 shared search receipt,
q_limit2, per-search8192-node cap,512-ply horizon and deterministic tie seeds.
Randomized blocks and endpoint orders are frozen before search. Half the roots
have20k and half40k candidate-plus-foe node caps, paired across every method/seed
and role. Terminal W/L/D alone is reward; incomplete/horizon/resource outcomes
remain UNKNOWN[-1,+1], with full finite-panel denominators and all six contrasts.
Missing slots are preserved. The arithmetic analysis is the already-pinned
source from task2618, not a selected post-result comparison.

The source-bound slower complete1024-slot cost receipt scales by1.5, adds25percent
runtime margin, actual preparation time and600s audit reserve:88.178minutes at
registration, under120. Execution is capped at4500s; the all-in6600s clock starts
at the preserved preparation origin, not registration or a resumed session.
Historical training costs remain paid12M nodes and are reported separately from
new evaluation cost. The experiment never tops up missing slots or increases caps.

A no-search first registration copied stale32-root provenance metadata while
setting the new48-root panel. Independent preflight rejected it; exact sources,
plan and rejection are preserved in run-001. Run-002 uses a minimal coherent
protocol, the same outcome-blind inputs and the same preparation origin/cap.
No search/outcome existed in run-001. The first execution-test fixture used an
invalid q_limit0; corrected to legal q_limit1. Real search execution, replay,
UNKNOWN, cross-session provenance, no-rerun and whole paired-panel preflight
regressions now pass. No immutable old source was patched to pass a gate.

The original launcher retains PID/command and exit receipts. Registration hashes
and original running status remain in CHECKPOINT.json as historical evidence;
the closed files and audit above supersede that operational status. No cap,
original session or missing old task2618 evaluation was reset or filled.
