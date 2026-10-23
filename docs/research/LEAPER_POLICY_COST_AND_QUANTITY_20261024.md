# Leaper policy cost and quantity coordinates — 2026-10-24

This continuation corrects the executed Q0 contract, separates algorithm counters
from distinct positions and hashing, and tests how the finite cost screen depends
on its leaf policy. It also gives quantity-dependent two-action path polynomials
and an exact static configuration-count classification in the five-orbit toy
vocabulary. None selects a search/evaluator/learner default or a game-quality
scalar. Full generated promotion/drop/auxiliary/history semantics remain the
long-term target; these theorems have narrower stated domains.

## Source correction and paid-event contracts

The earlier fixed report b66566c3647918b4c2f40993869ff0c46fb75e9b described its
1152 calls as Q0/forced-check8. Actual executed SearchTuning left check-only OFF;
all1152 qnode counts are zero. The configured hard limit does not enable
extensions. Original registrations, source bytes, return data, caps and missing
old outcomes are retained; the current report corrects interpretation.

nodes increments at negamax entry and tactical-root child inspection. qnodes
increments at a qsearch entry. A main leaf entering qsearch counts the same
physical position twice. Their sum is the actual node-budget currency, including
repeats/unfinished iterations/aborted entry attempts, not unique states or
uniform-cost operations. The sealed runtime/static-Q0 compatibility field
position_keys_computed equals successors_searched+tt_probes on every return;
it is not a SHA count. Explicit legal requests include cached frontiers and
aborted attempts; list-length totals can count the same actions repeatedly.
Completed Native-provider successes are neither every attempt nor an exact cache
miss count. Query/setup/rule setup and the outer residual are separate clocks.

On this old runtime/static/nonstaged route the three legal/evaluation/ordering
wrappers are mutually nonnested, but omit much of the query. They cover only
14.7–17.7% of time-limit strata. Root-scan and profiler cumulative times overlap
other work. Do not label the unassigned269.93s outer residual serialization,
transition or hashing time. The old32-derived-packet writer measurement remains
a scoped diagnostic; no normalized-writer bypass is installed.

One selected same-root one-bit diagnostic uses5x5 K0flat15,Aflat21,K1flat5,
mask8 versus9, widths14 versus23. Four normal calls, in both orders, and two
profiled calls all terminate at exactly8192 budget events. The higher-width
mask9 also has higher prior action-output/event burden, yet is faster in both
normal orders: mask8=.9864/1.1695s, mask9=.8238/.8257s. This refutes that simple
burden-only explanation for this pair, not a universal cost law.

Profiled RuntimeCountsSnapshot.items accounts for1.2226/0.7793s cumulative,
with25,530/17,516 recursive calls. Cumulative terms must not be added. These are
ordinary exact equal-history guards as well as possible collision checks, not
proof of a collision defect. Each profile has one Python-visible openssl_sha256
call; Native internal hashing is not measured by this observation. Profiling
perturbs clocks and does not establish a production speedup. No runtime/history
identity was weakened or changed; AUX's runtime lane remains independent.

## Registered leaf-policy comparison

The same576 complete exposed inputs (24 masks,3 boards,8 common roots) are used.
OLD staticQ0/N32768 is a576-call reference, not another execution. NEW check-only
Q0 and ordinary Q4 each register576 calls at N32768/requested depth64/3s, unit
A1000/King0/dynamics OFF, Native all, fresh Player/TT per query. Each arm uses one
warm process. Four pre-panel pilot calls on two of these same roots are excluded from panel
counts; the later planned same-condition calls are physical repeats, not
independent rule evidence. Forecast includes preparation/recording/validation/analysis:87.6min<120.
Frozen per-arm2050s and whole4200s execution caps are not enlarged.

Chat1792780376 recommended counter audit before more budget points; that audit
and one matched-event pair were executed. This additional PRIMARY-selected
comparison addresses the newly discovered leaf-policy premise, not a larger
node-budget curve or a partner-approved experiment. No new authority is inferred
from peer comments. Old references and new sequential batches have different
load/cache histories; no isolated causal wall-speed claim follows. All signed
root/rule-mean correlations and stop strata are retained, without selecting a
posthoc signed/absolute winner. Runtime-push rates are explicitly post-registration
counter diagnostics. They include root probes/q classification, not distinct
positions or equal-cost transitions.

All576 inputs per policy are retained; both new arms have zero missing slots.

| Policy | NEW calls | Root shortcuts | Time limits | Node limits | Whole batch s |
|---|---:|---:|---:|---:|---:|
| staticQ0 | 0 (576 OLD references) | 65 | 505 | 6 | 1809.40 |
| checkQ0 | 576 | 65 | 486 | 25 | 1800.81 |
| ordinaryQ4 | 576 | 65 | 510 | 1 | 1816.93 |

All root-shortcut memberships agree with the old literal one-ply facts.

| Board | Policy | Budget events | Runtime pushes | Median completed MAIN depth | W2 rho ALL root/rule mean |
|---|---|---:|---:|---:|---:|
| 4 | staticQ0 | 3175949 | 3174570 | 8 | 0.415 / 0.920 |
| 5 | staticQ0 | 4436579 | 4435153 | 7 | 0.370 / 0.468 |
| 6 | staticQ0 | 4867344 | 4865998 | 6 | 0.295 / 0.324 |
| 4 | checkQ0 | 3401155 | 3194952 | 8 | 0.410 / 0.898 |
| 5 | checkQ0 | 4721319 | 4390063 | 7 | 0.352 / 0.541 |
| 6 | checkQ0 | 5015698 | 4756342 | 6 | 0.304 / 0.353 |
| 4 | ordinaryQ4 | 3270616 | 5026408 | 6 | 0.295 / 0.791 |
| 5 | ordinaryQ4 | 3496526 | 6441874 | 5 | 0.216 / 0.139 |
| 6 | ordinaryQ4 | 3516621 | 6652699 | 5 | 0.039 / -0.184 |

The overall6x6 rule-mean sign reversal is not a stable conditional sign reversal.
The preplanned per-policy time-limit strata give W2 rule-mean rho .910/.803/.168
for static/check/Q4; root rho .356/.363/.068. These strata have179/172/181 roots.
A separate POST-REGISTRATION same-input intersection diagnostic retains169 roots
and24 rules: rule-mean rho .897/.806/.168, root rho .354/.356/.075. The weakening
persists on the same selected roots, while the sign reversal disappears. This
conditions on post-treatment stopping, so it is still not a population/causal
effect. Independent pairwise average-rank/exact-integer covariance arithmetic
agrees with the existing implementation to1e-12; no SciPy/package install is used.
The full feature/target/stop matrices and exact intersection membership remain
available; no new scalar or best signed/absolute criterion is fitted.

Q4 is the ordinary q-depth setting with this explicit experimental unit evaluator,
not the complete product-default policy. It changes31 chosen actions and27 scores
relative to the old fixed-clock reference, and lowers completed MAIN depth on451
inputs. Those observations are not a utility or WDL comparison. Its runtime
pushes can increase while the budget-event sum decreases; neither count alone
measures equal-cost work or distinct states.

A separate four-call diagnostic selects exactly the two action differences after
checkQ0 closes. Each policy actually completes the same requested MAIN depth:
mask2 at D8 still changes A19->23 to K20->21, both score1000; mask23 at D6 gives
the same A21->17 and1000, unlike the old D7-versus-D6 clock comparison. All28 PV
plies replay. This separates a persistent finite leaf-policy effect from one
completion-depth explanation. It does not establish disjoint argmax supports,
WDL, equal uniform leaf horizons or utility. These are selected mechanism cases.

The maintained semantic cost CLI now explicitly exposes --check-only-qsearch;
omission preserves static Q0. A separate observed forward-registration defect
silently ignored q/check-only/hard-limit requests. Three red regressions precede
the repair: the current leaper_design caller now rejects unimplemented policies
and documents check-only=False. Legacy defaults and actual algorithms remain;
closed or running experiments are not rewritten or rerun to repair metadata.

## Quantity changes the path polynomial, including fixed averages

W2 means the number of paths of exactly two legal actions, K+ordinary actors
moving first. First-action terminal paths contribute0; terminal second-action
paths still count1. It is not unique Position count, nonterminal frontier size,
mean branching or policy sampling probability. Assume fixed square board,
fresh H64/repeat4 common-safe/ongoing root, identical plain A actors sharing the
five disjoint offset bits, King8 against a bare King, no other effects.

With k ordinary actors, an outer A move contributes x_i; a defender destination
must avoid each remaining actor, contributing a product of unique (1-x_j).
King moves have no outer gate. Capturing one A removes that attack source.
Boolean idempotence gives degree<=min(k+1,5). For k<5 every degree-(k+1) term has
sign (-1)^k: to reach that degree all k guard bits and the outer bit must differ.
Lower-degree signs need not match the singleton's nonpositive pair law.

The existing two-A5x5 root K0=0,A={7,11},K1=24 has cubic coefficient x0*x1*x3=4.
New three-A root K0=0,A={6,7,11},K1=24 has quartic x0*x1*x3*x4=-4 and
x0*x2*x3*x4=-4. All31 nonempty masks/826 second edges are actually Core checked
for the new root. A nonempty-base4 four-dimensional cube has fourth difference
-4; no zero-mask game is invented. This is a targeted algebra-boundary check,
not an independent-rule holdout or a solver.

Fixed nonnegative averaging cannot cancel these top-degree signs if a witness
has positive weight. In particular, uniform common-safe/ongoing5x5 two-A support
contains the old witness; its cardinality N<=25*24*C(23,2)=151800. Therefore that
mean cubic coefficient is at least4/N>=1/37950. This is a lower bound, not a
computed exact support size/mean or a useful effect-size estimate. Rule-dependent
supports or weights invalidate that averaging inference. Nothing here refutes
averaged prices or asserts quantity conservation.

## Minimum static mating quantity and the next input

For the five-orbit vocabulary and arbitrary static placements with King8 against
bare King,20 masks have minimum ordinary count1. The other11 need2 for n>=4.
On3x3,10 need2 and pure diag2 mask16 cannot mate with any number. Five explicit
two-actor corner constructions prove the upper bound and embed into larger
boards; the earlier singleton obstruction proves the lower bound. Adding A
attacks cannot restore a bare-King escape in this scope.

The3x3 exception attacks only opposite corner pairs. A checked corner's two
orthogonal edge-centres cannot be attacked by any A; a nonadjacent King cannot
cover both. One safe escape remains even if it captures an A on that square.
Actual Core checks cover123 positive minimum-count configurations and32 maximal
negative occupancies. Synthetic Position/fresh-history checks are explicitly
separate from legal opening admission, reachable cooperation and forced WDL.
The compiler's bare-King initial template does not license a claim that added
synthetic A actors are reachable.

Two actors alone also do not settle component allocation. For diag1 mask2, if
all A actors share one checkerboard color, every A move/attack preserves it.
A checked bare King has an opposite-color orthogonal escape outside King0's
cover. Captures only remove A actors, so this obstruction persists. Opposite
colors permit static mate but do not prove reachability from any chosen opening.

The next step has actually begun with two fully serialized, Core-admitted5x5
setups in ONE RuleSet fingerprint1988f7df02e58e0d48855e44a576e23b32e90ae5a0353c105615a1f33e946df1:
K0=0,K1=24,A={1,5} versus A={1,6}. Their A colors are[1,1] versus[1,0], initial
legal counts3/6, H64/repeat4. Both complete records round-trip. This is an explicit
setup-distribution counterfactual, not the same physical root. Zero Player or
fitness calls are made for these inputs; eight subsequently preserved legal
prefix moves provide four complete cost contexts. The mixed-color history remains UNKNOWN.
A new cost case must precede any subsequent forward fitness. No history solver,
AUX write, old1904 outcome fill, sampler activation or learning is performed.

## Evidence, validation and limits

The public data-only reader passes60 original/source byte hashes,1152 new policy
choices/6254 literal Core PV plies and130 root-immediate terminal checks,
plus six matched-event queries/39 PV plies, four common-main-depth queries/28
PV plies,31 new quantity trees/826 second edges,123 static mate configurations,
32 maximal negative configurations, and the two next complete inputs/eight
unique prepared prefix steps. Replay counts describe evidence units, not total
Core invocations across producer/tests/repeated replay. The packet is1,468,676
bytes, SHA256 e1cb29d6ad5fe10a09b93f5d5c1172baaa77c6730d1b85ab7c0eea2a12dadd94; source capsules are never executed.

135 relevant targeted tests pass before publication. The publication gate reruns
the required related targets. One new test initially used a Player Action field
on SemanticAction; source diagnosis fixed only the adapter, retaining the same
physical escape expectation. Three forward-registration regressions were red
before the caller rejection fix. An existing cross-layer helper import needed
the actual product qsearch module included first in the selected test command;
no test was removed, no expected numeric result weakened.

Scientific execution counts are1152 panel calls plus14 separate diagnostic calls
(6 matched-event,4 pre-panel pilots,4 common-depth), with0 new games or training.
Regression-test engine calls are separate, not experimental samples. OLD576
reference calls and the preceding1152-call source audit are not new executions.
The prepared next stage has zero Player/fitness calls; eight actual legal
prefix moves now provide four complete initial/4ply cost contexts. Their absolute
clock and initial-setup identity round-trip, and no whole-game feasibility is
inferred from that preparation.

See [README](data/leaper_policy_cost_20261024/README.md),
[summary](data/leaper_policy_cost_20261024/summary.json),
[plain quantity witnesses](data/leaper_policy_cost_20261024/quantity-witnesses.json),
[common-time diagnostic](data/leaper_policy_cost_20261024/common-time-diagnostic.json),
[next cost inputs](data/leaper_policy_cost_20261024/next-cost-inputs.json), and
[qualification](data/leaper_policy_cost_20261024/qualification.json).


Exact technical originals and actual executed-source capsules are in the data-only
packet. The private execution receipt's account-specific interpreter path is
normalized only in its publication copy; originals remain ignored. Capsules are
hash checked, never executed or unpacked by the reader. The fixed old screen is
a separately identified reference. Shared Core qualification is not a second
engine, and path replay is not an all-defense proof. The previous mate<=7
certificate remains at its fixed source, unchanged. Old E0/E1/1920 stay CLOSED
and1904 missing policy outcomes remain UNKNOWN.
