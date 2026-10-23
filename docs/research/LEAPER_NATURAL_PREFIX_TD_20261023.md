# Natural-prefix free priors and bounded incremental TD

The owned segment608f6642-d2a8-4504-8016-0a3941ddc47d closes at a safe
checkpoint with3799.974 confirmed effective seconds (63.333 minutes), three
evidence-bearing intervals and a successful duration gate/memo synchronization.
Publication and message transport are outside that research credit.

DEV_AUX only; PRIMARY retains the rule generator, forward/inverse screens and
production defaults. Shared rules, Core, history and public search are pinned
to committed sandbox `1ac1f97a74b26015ffb73dcb612333923a6d61d0`. Their source
matches this checkout; the existing AUX learner remains separate. No measured
acceleration or default change is claimed.
Closing fetch also checks sandbox `8f1f9e5f977e1baba0e5a3cd14d74b7ea0351130`.
Its25 changed paths are research/operations documents and data only; shared
rules/Core/history/public search/runtime/helpers/tests have no new delta.
These experiments retain their actually executed1ac source. PRIMARY's new
inverse/forward controls are read as committed evidence, not adopted as AUX
tasks; their complete histories are available for the next learner comparison.

## Question and frozen comparison

The preceding eight exposed first-divergence histories showed a useful free
Mobility prior, but could not establish transfer to natural starts or an
incremental learning benefit. This study consumes PRIMARY's committed 6x6
ten-piece inputs, without generating or selecting new rules. Four source code
indices, 0/6/12/18, use alternating source layouts 0/1, giving worlds
0/30/12/42. Selection uses metadata only, without WDL, first-divergence,
material-imbalance or search labels. The rules and source have been exposed.

For each world the first pilot freezes four TRAIN starts, each obtained by
eight uniformly sampled legal moves from its source initial record. Seeds are
2026102300 + world-order*100 + episode-index. Early real terminals are retained,
without replacement. Roles alternate 0/1/0/1. EVAL uses INITIAL and another
uniform8 prefix, seed 2026102300 + world-order*100 + 51, each with both candidate
roles. The three arms are Unit, zero-trained Mobility and Mobility-initialized
TD. All post-training models are evaluated; there is no model selection.

All candidates use the maintained `learning.mainline_search.search`: pure
material, A fixed at 1, requested D4, 8192 counted nodes, two seconds including
10% reserved for literal PV replay, qmax/qhard 0, equal capture-order values
and a fresh player per query. Hand channels are zero because these source
remove-capture rules have no drops or reachable stock. The opponent is the
existing Static adapter, requested D3/8192 nodes/two seconds, qmax 0/qhard 8,
with TT retained within each game. Its dynamic profile and ordering policy
differ from the pure material candidate. Results are conditional on that foe;
they are not merged with PRIMARY's dynamic-policy quality screen.

The SAME maintained `TDLeafEpisode` has eta .05, lambda .95, scale 10. Model
weights freeze throughout an episode; only candidate-side completed literal
search returns are observed. Features and values use player-0 orientation even
when the candidate plays player 1. Actual rule outcomes supply the final
target. A censored episode withholds the final error; UNKNOWN is not a draw.

The first pilot has 16 TRAIN + 48 EVAL slots. Its original whole/train/eval
caps are 1800/600/1200 seconds, each game at most 90 seconds, 250000 counted
nodes and 128 added plies. No old proof or learning cohort is refilled.

## First pilot result

All 64 slots reach actual terminals, with no missing or UNKNOWN result, in
564.819 seconds. TRAIN costs 161.283 game-seconds. The 48 EVAL games have:

| Arm | W/D/L | Mean signed utility |
| --- | --- | --- |
| Unit | 5/4/7 | -1/8 |
| Mobility | 7/4/5 | +1/8 |
| Four-episode TD | 7/4/5 | +1/8 |

Mobility minus Unit is +1/4 over the 16 paired frames: +1/8 for role 0,
+3/8 for role 1; +1/2 on INITIAL and zero on uniform8. The four per-world
means are +3/4, 0, +1/4, 0. This is finite descriptive evidence for this
candidate/opponent family. It is not a population effect or a minimax value.

TD and Mobility have identical complete action trajectories in all 16 EVAL
frames, not merely identical terminal utilities. Eleven TRAIN episodes change
weights. The 390 observed targets include 360 literal nonterminal PVs and
30 terminal PVs; 193 nonterminal targets have a nonzero trainable gradient.
The observed B/C feature vectors have rank two in every world. Rank is not
identifiability of strategic values or an argument for intrinsic prices.

Every last actual-terminal TD error contributes zero to the update here.
Nonzero updates occur through earlier search-to-search transitions, including
transitions into searched rule terminals. This does not mean that terminal
information is absent. On the saved, frozen PV paths, recomputing the adjacent
TD-residual loss after the update decreases it in ten episodes, increases it
in one and leaves it equal in five. The semi-gradient update need not minimize
that recomputed objective; smaller old-path error is not better play.

Paid queries: TRAIN candidate 390/404678 nodes, opponent 388/231202 nodes;
EVAL candidate 1016/1141687 nodes, opponent 1017/497095 nodes. Three TRAIN
candidate decisions complete D3 rather than requested D4; the other 387 TRAIN
and all 1016 EVAL candidate decisions complete D4. Their lower achieved depth
is retained. There are 2811 actual added moves in total.

The reader replays every root, actual move and literal candidate PV and checks
TD updates using a backward lambda-error sum equivalent to, but separately
implemented from, the online eligibility sum. It passes 5428 candidate PV
edges, 4128 reference PV edges, all 390 TD terms and 64 terminal records. This
uses shared Core, not an independent game oracle. An initial reader assertion
mistook the opponent's dataclass action serialization for the candidate's
action-to-dict schema; complete-action matching fixes that reader error. No
engine, source result or experiment was repaired or rerun. The 88 relevant
learner/runtime/public-search tests pass.

## Separately frozen learning-budget check

Four episodes establish executable targets and small updates, not the value
of more training. Before examining this pilot's paired summary, a NEW TRAIN
stream was frozen with 64 episodes per world and the same fixed hyperparameters.
It restarts at Mobility; it does not continue the pilot's model or reset its
caps. Seeds are 202610230000 + world-order*1000 + episode-index, with uniform8
starts and alternating roles. Every episode is retained, including early
terminals. Only the fixed final model is evaluated; no checkpoint selection.

There are 256 new TRAIN slots and 16 new TD EVAL slots. EVAL reuses exactly
the old INITIAL/uniform8 records; its free baseline games are exact existing
controls, not new samples or new calls. These exposed frames cannot validate
new-rule generality. The new whole/train/eval caps are 3600/3000/600 seconds,
with the original per-game/query limits. At the measured first TRAIN cost,
256 episodes estimate about 2581 seconds before EVAL. The hard whole cap is
60 minutes, below the 120-minute assessment boundary; the two studies together
are not a split long experiment or an extension of a frozen test denominator.
The 256 new TRAIN starts have 252 distinct complete-history IDs, no overlap
with old TRAIN or EVAL history IDs, and 14 prefixes ending before eight moves.
All repeats and early terminals remain; distinct seeds are not assumed to
give independent or nonterminal trajectories.

All272 new slots reach actual terminals in2461.678 seconds, with no missing or
UNKNOWN. There are5655 TRAIN candidate queries/5905930 nodes and5643 opponent
queries/2942299 nodes; EVAL has357 candidate queries/399798 nodes and358
opponent queries/185019 nodes. Two TRAIN returns complete D3, the other5653
TRAIN and all357 EVAL returns complete D4. There are12013 actual added moves.
The final model weights are recorded in the packet, not promoted as prices.

The64-episode final models have6W5D5L on the same16 EVAL frames. Relative to
the exact existing Mobility controls, the paired mean is-1/16: role0-1/8,
role1zero; INITIAL-1/8, uniform8zero. Fifteen utilities are unchanged and
one changes WIN to DRAW. Fourteen complete trajectories are identical; one
changes trajectory but stays WIN, and the negative frame changes trajectory
and outcome. Two frames finish before the candidate can make any query; they
remain in the denominator and cannot be called learner decision failures.

Against Unit, the final mean difference is+3/16, smaller than the free prior's
+1/4. TD4 versus TD64 is not a pure episode-count causal comparison: the TRAIN
streams differ. There is no new independent EVAL sample, no checkpoint winner
selection and no positive incremental TD claim.166 episodes actually update
weights. Saved-path TD loss falls in162 episodes, rises in4 and is equal in90;
every world's observed trainable feature rank is two. These optimization
diagnostics do not supersede the negative actual-play control.

The full reader passes264 natural roots,23200 literal candidate PV edges,
17636 reference PV edges,5655 backward-summed TD terms and all272 terminal
histories. The two pilot packets have336 NEW physical games in total; reuse
of32 free control games and16 oldTD4 games adds no new game or query.

## Negative mechanism and next input readiness

The sole harmful frame is world12/INITIAL/role0. A separately declared NEW
first-action control forces the learned model's first action, then uses the
unchanged free Mobility tail against the same Static foe. It still draws by
the actual max-ply rule:127 new moves after the forced prefix,34.093 seconds,
63 candidate queries/87327 nodes and64 reference queries/70487 nodes. The
old free policy wins. This isolates a harmful first-action effect against that
foe; it does not label minimax WDL or establish the value of other actions.

Four additional public child-D3 queries compare the two first actions under
both frozen critics. All four complete and return0, matching the parent D4
best score0. Thus both served first actions are cooptimal under each completed
D4 critic. The changed learned parameters alter the executed selection within
that tie, rather than establishing a strict learned critic preference for the
harmful action. No default, move-ordering patch or universal price conclusion
follows. The one control game is additional physical computation, not an old
slot refill.

The preplanned16 directional queries complete in7.644 seconds/34044 nodes.
All16 finite slopes match the saved leaf coefficients at epsilon1e-4. There is
no observed directional counterexample on these four roots and no gradient
implementation change. The algebraic caution below remains a scope limit.

Next, AUX consumes the already committed5x5 typed inputs from sandbox1ac,
`analysis-and-next-proposal.json.gz`, SHA256
`33567703b6c57db1008dec8092b9a37b1dd0d374bcf466fcc156c59009e4f2b2`.
One source-order pass over ALL96 complete INITIAL/uniform8 records through the
same Mobility learner path costs27.009 seconds/123926 nodes:96 complete
returns,71 nonterminal literal targets,25 terminal returns,31 returns with
nonzero trainable B/C features.92 complete D4;4 already-terminal roots return
D0. Zero games and zero updates. Early terminals and zero gradients stay in
the denominator. This is target portability/exposure, not PRIMARY's fitness
screen, a useful-decision/WDL oracle or evidence of5x5 strength.

All supplemental histories/PVs replay, including652 target PV edges,190
reference PV edges and the127 new control moves. No new query is run by that
reader. Current choice: stop further unchanged6x6 TD budget escalation. The
next useful bounded check is free-prior conditional transfer on these committed
5x5 records, with prospective metadata selection and role/context reporting,
before considering another training run. Do not recreate a generator, mirror
screen or production default study.

## Gradient interpretation and next falsifiable mechanism

The original [Baxter/Tridgell/Weaver TDLeaf paper](https://arxiv.org/html/cs/9901001v1)
relates a unique minimax PV leaf derivative to the root derivative, discusses
non-unique PVs at ties, and highlights initialization and training-distribution
effects. These observations motivate diagnostics; they do not predict a
training count, guarantee convergence here or transfer its chess strength
results to this material-only Leaper setting. No running hyperparameter changes
follow from this reading.

Our own finite-tree caution is stronger than saying that every tied leaf gives
a unique valid local derivative. Let F(x)=max(x,min(-x,0)). At x=0 a nested
tie-breaking path may select the leaf -x, yet F(x)=max(x,0), whose one-sided
slopes are 0 and 1. Thus literal PV/value consistency alone cannot prove that
the served leaf derivative describes nearby root values. This is an algebraic
example, not an observed game defect or evidence that the present learner's
updates are invalid. It does not assume continuity of strategic piece prices
under rule changes.

A small next check is frozen before further queries: for each of the four
worlds, take the first complete nonterminal TRAIN candidate return with a
nonzero B/C leaf feature, by slot/query order. Reconstruct its full history and
perturb B and C separately by plus/minus 1e-4, leaving A fixed. Compare the
public D4 one-sided root-score differences with the saved leaf coefficients,
recording literal PVs, actual depths and costs. Any lower completed depth or
resource failure leaves that directional comparison UNKNOWN; it is not a
gradient counterexample. This uses exposed training targets for mechanism
diagnosis, never for oracle-selected experiential starts or a new strength
claim. At most 16 NEW queries, two seconds/8192 nodes each, whole120 seconds;
no retries, proof expansion, hyperparameter selection or additional worker.

## Reproduction and interpretation

Runnable producers and readers are ordinary scripts, not executable content
hidden in a capsule:

```
python scripts/leaper_prior_td_pilot.py plan --output artifacts/new-pilot
python scripts/leaper_prior_td_pilot.py run --output artifacts/new-pilot
python -m scripts.leaper_prior_td_budget --previous artifacts/new-pilot --output artifacts/new-budget
python scripts/leaper_prior_td_pilot.py run --output artifacts/new-budget
python scripts/verify_leaper_prior_td.py PATH_TO_PACKET.json.gz
python scripts/analyze_leaper_prior_td.py PATH_TO_PACKET.json.gz
python scripts/analyze_leaper_td_signals.py PATH_TO_PACKET.json.gz
```

Running producers incurs NEW computation; it must not overwrite or refill
these closed output directories. Readers replay saved evidence without search.
The source packet already exists at
`data/leaper_tie_truth_20261023/strongfoe-source.json.gz`; selected source world
records are retained in the new packets without duplicating that large source.

The PRIMARY-thread ChatGPT reply 1792742950.558489 was additionally read from
the channel's advertised reply thread after noticing it was absent from the
tracked AUX roots. Its legacy DOT_REPLY type is preserved, not treated as a
new Dot consultation. Adopt its target-distribution, role, exposed-prefix,
achieved-depth and full logical-cost qualifications. Its inverse/Pareto design
belongs to PRIMARY and is not executed by AUX. Exact raw return and the
revision-bound read/adopt/defer decision are retained privately in this probe.

Claude comment 1792745445.474859 is read and adopted for the foe-conditional
interpretation and ordinary runnable scripts. PRIMARY owns the proposed mirror
opponent screen; AUX does not duplicate it. The optional offline terminal fit
is deferred behind this learner feasibility check. Such observed labels would
also remain conditional on source policies; they would not automatically yield
an opponent-independent price axis. The last AUX question has no new reply at
this probe. No realtime wait, uncertain-send retry or Dot mention occurs.
