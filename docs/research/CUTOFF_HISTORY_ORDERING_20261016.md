# Exact-action history ordering —2026-10-16 JST

Science remains OPEN. This study follows the failed unconditional reserve route
with a different question: can previous sufficient actions reduce search work
without changing the completed finite objective? It does not retune q, prices,
models or the auxiliary solver. The starting PUBLIC source is
`ef9d4a39b69f96da0d25ae70ad44a5edeb966d5d`.

## Mechanism and scope

A4096-slot table belongs to ONE search call. Each slot stores the entire packed
semantic action AND actor, with exact comparison before reuse; collisions replace
ordering information, never a score or terminal result. Noncanonical main cutoffs
receive a saturating16-bit remaining-depth-squared reward. The existing target-
enemy capture group stays first; history ranks within groups, then canonical
packed action breaks ties. All generated candidates still use complete checked
execution. Canonical selected-PV reconstruction, rule/auxiliary state, promotion,
drops, relevant histories, evaluator and cancellation/budget authority remain.

[Schaeffer, section3 and interactions](https://webdocs.cs.ualberta.ca/~jonathan/publications/ai_publications/pami.pdf)
motivates reusing sufficient operators, which need not be optimal. Its chess
results do not establish GenericChess gains; interacting ordering schemes and
overloaded histories can regress. Our cutoff-only, depth-squared, full-action
variant differs from its exponential weight and best-on-no-cutoff updates.
No paper experiment is reproduced.

The final delivery candidate moves the same48KiB/49152-byte table outside the
always-zeroed context. It is initialized/used only for existing
`root_window_pruning=True` with neither learned nor policy ordering. DefaultFalse,
learned/policy ordering, q ordering, APIs and UI selection stay unchanged. Storage
is local and bounded, with no heap allocation or persistent trained model.
The stack still reserves local storage; this is not a zero-overhead/peak-memory
claim. Native must be rebuilt to receive the implementation.

## Feasibility, then counter-free comparisons

The original8-root protocol is preserved, not edited retrospectively.32counter
queries give16pairs identical in every non-time result field and80complete-history
PV edges. The8distinct roots have1549non-replay cutoffs,1372exact repeats and2
replacements. Flagged canonical replay is excluded; scalar descents beneath its
reconstruction may still contribute. This is a lower bound on repetition, not
predictive accuracy. The old baseline binary in this counter stage means its
clock ratios are not clean adoption evidence.

A separate same-Zig/O2 counter-free pilot executes32queries.14jointly completeD3
pairs preserve score/action/PV;2baseline node-censored receipts at4323becomeD3.
The policy is frozen before the larger comparisons, with no per-position tuning.

|Cohort / objective|Actual queries / planned|Jointly complete pairs / all|Family-weighted caller ratio [descriptive95% interval]|
|---|---:|---:|---:|
|Paid20families, q0D3|144 /160|72 /72|.922 [.860,.971]|
|Paid20families, q4D2|144 /160|63 /72|.812 [.736,.887]|
|Prospective24families, q0D4|184 /192|74 /92|.776 [.671,.871]|
|Prospective24families, q4D3|184 /192|40 /92|.745 [.599,.886]|

Paid transfer closes432/480queries on36/40roots in586.370s;48missing slots are
actual terminal tails. Prospective transfer closes552/576queries on46/48roots
in1209.850s, plus6.613s input preparation;24missing slots are actual terminal
tails. All generation succeeds. Inputs/walks are frozen before any new search
outcomes; this is prospective for this declaration, not universal untouched
holdout. Complete generated movement mixtures retain promotion/drop/history;
this distribution does not cover every semantic-DSL mechanism or wide32domain.

The remaining third condition is equal-time enabled-q, not another fixed-depth
sample:72paid pairs at2s yield16deeper/54same/2shallower and64same actions;
92prospective pairs at4s yield24deeper/68same/0shallower and90same actions.
Requested-q coverage gains are2and4receipts, respectively, with0losses here.
These repeats are not independent wins. Q-hard aborts can finish far before the
wall budget, and a later attempted depth can fail after a retained requested
policy completes. Wall cost/depth/coverage are not fixed-work speed or strength.

All jointly completed finite scores/actions/PVs match. Paid/fresh returned
lines independently reconstruct1067/1383full-state/history edges during execution.
The table reports only the completion intersection; all censors are published.
In particular, no16-board prospective q4D3pair completes. Resampling is by family,
keeping dependent played roots/orders together; intervals are descriptive, not
an execution guarantee. Normal concurrent load applies. The6.6s input preparation
also overlaps a small part of the paid timing batch.

Negative evidence stays: at4323/8q0D3, work increases12420to35351(2.846x), with
same score/action/PV. Root first moves remain identical in all iterations; this
rules out only changed-first-root-action as a sufficient explanation. New-family
completed q0work regresses up to1.584x; completed q4up to1.083x. No board/position
patch or suppression of adverse cells. Totalwork is API main nodes PLUS qnodes.

## Compatibility and actual decisions

A48-call persistent1MiBTT/checked-root-hint control exercises cold/warm q0,
q4and q0again.22of24pairs jointly complete the finite objective with exact
score/action/PV;128complete-history edges pass. Two q4pairs remain censored.
This does not establish every TT size or all-domain performance.

Eighty existing concrete PV-oracle, q, budget, cancellation, terminal and PENDING
checks pass with the private source image. A separate existing pure-Core minimal
AB control uses the same integer board/current and hand/base prices, full history,
no Native legal provider and explicit terminal-scale normalization.18of20planned
roots run;2are actual tails.13completeD4, all26Native-arm score comparisons match;
5hit the original20000-node cap and stayUNKNOWN. This is independent algorithm/
primitive execution, not WDL, canonical tied-action equivalence or a new solver.

Twelve actual fixed-opponent games use4index-selected prospective roots, both
history actor roles,1ssearch-caller budget/.02sreserve and64additional-ply cap.
The baseline-baseline trajectory is physically executed once, then reused as
control for both role payoffs.258physical edges agree in both Native images and
Core. Three roots have the same actual winner under all three modes; the8-board
root remainsUNKNOWN under all modes. Six known role comparisons have0gain/0loss;
two comparisons remainUNKNOWN. Only the unknown history-role0trajectory changes.
All other physical paths match. No demonstrated strategy gain or Elo claim.

D1alone does not identify an unused-time problem: the closed8-board baseline
game has55time-censored D1turns and4q-hard D1turns. The latter leave about.031to
.468s, not a blanket free budget. No new fallback policy is implemented from
that observation. A separately frozen2-root literal-reply screen checks all
6/4/127/7replies in four selected children, with complete Core/Native histories;
no immediate opponent win is found. Native screen cost.000136-.003595s is only
local feasibility, not WDL or a cohort-wide safe budget.

## Final-source qualification and delivery decision

Final nullable-storage refinement:248queries,216active across ALL paid roots
and32inactive/default-mode controls.92non-time pairs preserve EVERY non-time
result field/work, with0errors/mismatches;572returned PV edges pass. Time-censored
pairs remain in the data. This qualifies changed storage activation against the
frozen active policy, rather than silently assigning its timings to a new build.
The final product source receives this scoped cost optimization only after these
checks. The supported rebuilt final product passes2687full default tests in270.50s
(271.087s caller). Separate public-copy replay receipts follow actual execution. No q/evaluator/model/default flag or auxiliary
checkout changes. The conclusion is conditional finite-analysis cost reduction,
with local regressions and no observed game-payoff gain.

All exact technical plans, complete results, failed launches, original slots,
source variants and replay scripts are in the companion source/evidence archive.
Raw Slack/account originals stay privately ignored. Zero-query seed-enumeration,
import-name collision and runtime-snapshot serialization errors were corrected;
the old summary accidentally re-evaluated on import is byte-identical to its
sealed prior archive. An analysis-only syntax error and oversized memo draft
never changed frozen search results. No OS/SAC block or user intervention was
needed, and no unchanged launch loop occurred.

Collaboration: complete10reply primary and20reply prior AUX threads are saved before
reconcile; no new advice at recovery. Closing channel coverage discovers a new
AUX62root and its full2reply thread, saved before evaluation. Dot's prior retained-policy/clock objections
remain adopted, not an approval gate. Latest AUX62owner delivery1c5bc8be5ce16ca3f3baf66468850574d1164308reports313tests,
496games/10435moves, a scoped inventory-absence filter and empirical2vs4tie.
PRIMARY reads the messages, not final source/tests/games. Dot read397c789asource/
report, did not run those tests/games/census; its zero empirical-regret and
common-prefix conditioning objections are useful for later price interpretation,
not a Native result or an implementation request for PRIMARY. No AUXcheckout
write, merge, solver/model duplication or pooled cost denominator.
Current work is Native AB ordering, not AUX Session solver/verifier/cursor/model.
Communication limits and fixed-version delivery are recorded in COLLABORATION_LOG.

Actual final normal-product consumers close29.081s/1344query receipts/3324PV
edges and2.284s/12games/258physical edges, with search disabled. These137root
receipts include repeated cohorts, not137distinct independent roots. Exact
extracted publication-copy replay rebuilds Native from source under Python-S,
asserts restored module origins and passes all620member hashes/CRC, then the
same1344query/3324edge and258physical-edge consumers in36.871s. Existing Windows/
Python3.12/Zig libraries remain host dependencies, not a fresh-machine claim.

The first source-only replay failed because a broad retained diagnostic import
required unused python-chess. Direct Core compiler import plus the same tiny
metadata adapter fixes this; the failed capsule stays private, no product source
or frozen search changed. Full2687test evidence still applies. Companion:
`../archive/cutoff_history_ordering_20261016/evidence.zip`, manifest and actual
publication-replay receipt; compact results: `data/cutoff_history_ordering_20261016.json`.
