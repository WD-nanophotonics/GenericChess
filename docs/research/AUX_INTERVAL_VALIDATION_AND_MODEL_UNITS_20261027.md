# Partial WDL intervals, prediction diagnostics and fixed-scale model identity

Status: ACTIVE DEV_AUX segment1e5f0dfd-3761-49e6-a6b3-22226fdb916e, origin2026-10-26T17:56:08.506075Z. This is a new effective-work ledger; the previous64.78964-minute segment is ENDED and earns no credit here. Formal finish is pending.

The useful outcome is a bounded validation contract and two concrete learner fixes. Interval compatibility does not establish accuracy. A shared-truth paired error contrast can be informative even when two separate error intervals overlap. The actual TDLeaf consumer also needs literal terminal targets independent of material scale and an episode guard covering scale/fixed-unit index as well as weights. Neither result is policy-strength evidence.

## Sources and role boundary

Opening sandbox376cb684519c420c8ebd295e18e23f5a5c9b616d was explicitly fetched after inspecting current remote heads/default(master3d9eaaaad78166177bdb331fa79314b77c225374). The observed Pro path remains docs/reviews/chatgpt_patrol/2026-10-27_020414_JST_ec5fc26.md, blob8eafba5353ed18e7bdf3fece499e9049cbd357cb, SHA256bbc8c7038c3c305f2e1748bdec30ba593850743b748013900b1182e431b2ab0e. Its directory and production generic_chess/tests/tools have no delta from the last covered4a688eb3 revision. Exact Pro bytes were preserved privately before full assessment. Adopted its stop on further frontier/depth/closure expansion after zero strict signal; the prior terminal-frontier task is complete and is not repeated. PRIMARY's check-hint design, state and budget remain PRIMARY-owned.

Previous qualified bounds/features are fixed at own a5dbe90d90faf39ab33910f13c3cf317f9aa6d32, [terminal-frontier report](AUX_TERMINAL_FRONTIER_CERTIFICATES_20261027.md). This round reads those saved outputs, not a new state expansion, proof propagation or label-discovery pass. Rules/search/history/terminal authority is reused; only the AUX incremental learner contract changes.

The opening channel12roots and complete prior own thread1793032035.037579 were saved/read. Followup1793036639 still had no reply. Latest PRIMARY root1793036588 is its method question, not an AUX assignment. Older unpaged channel content is outside this opening delta, not asserted globally clear. GitHub Pro is the plan source; Slack Dot is separate consultation. Fresh requestGC-SLACK-20261027-025840-42cc317e used already published/fullremote-verifieda5dbe90d. Root1793037535.769729 was sent17:58:55.769729UTC; due18:03:55.769729. One about-five-minute complete-thread check found0replies; no wait or repeat poll. Request payload was exactly reconciled after correcting missing wrapper fields; the failed wrappers and original returns remain private, no send retry.

## The semantic prerequisite

Let v be the deterministic, complete-history, fixed-seat0 minimax WDL value, in{-1,0,1}. Let [L,U] be an already qualified outer bound containing it. A scalar p in[-1,1] is evaluated **under an explicit hypothesis that it approximates that value**. A bounded material tanh output is not automatically calibrated WDL; a raw PVS/search score is not such a prediction merely because its numeric value lies in this range. This pure arithmetic consumer cannot prove caller semantics or certificate authority.

An expected return against Uniform or another fixed policy is a different target, potentially continuous. A minimax non-loss strategy does not imply zero expected return or guarantee that an arbitrary continuation policy follows the strategy. History identity, value seat, target meaning and actual consumer remain required. None of these intervals chooses experiential training starts or supplies an oracle training target.

## Continuous relaxation, discrete error and upper risk

For a fixed prediction, the continuous optimistic error is distance(p,[L,U]) squared. Its derivative in p is2(p-proj_[L,U](p)). Deterministic WDL permits only S={-1,0,1} intersect[L,U], so the actual discrete optimistic error is min over v in S of(p-v)^2. The upper error is max((p-L)^2,(p-U)^2). The continuous floor is a relaxation of the discrete floor. Neither minimum selects the true value.

| Qualified interval | p | Continuous lower | WDL-discrete lower | Upper squared error |
|---|---:|---:|---:|---:|
| UNKNOWN[-1,1] |.4|0|.16|1.96|
| One-sided[0,1] |.4|0|.16|.36|
| Exact[0,0] |.4|.16|.16|.16|
| One-sided[-1,0] |.4|.16|.16|1.96|

UNKNOWN supplies no continuous constraint gradient. This does not mean that its true prediction error is zero. The discrete lower envelope's nearest-WDL choice would prefer zero at p=.4 without evidence identifying zero. It is not a justified label. Minimizing the upper envelope instead imposes a declared minimax-risk preference: UNKNOWN favors p=0, while[0,1] favors p=.5, which is not deterministic WDL. These are mathematical decision criteria, not additional truth.

The possible point-target derivatives lie in[2(p-U),2(p-L)]. Outside the interval they share a scalar direction. Inside it their sign need not agree. Composing the continuous constraint derivative with the existing Model.gradient gives a diagnostic chain rule, not TDLeaf's observed search-to-search objective.

Even a valid per-row constraint descent need not reduce actual aggregate error when contexts share representation. Synthetic example: two histories share prediction p; their intervals are[0,1] and[-1,0], with compatible actual values1and0. At p=.5, true mean squared error is minimal at.25. Moving to.49 reduces mean continuous constraint loss from.125to.12005, but increases true mean error to.2501. No model update is performed in this control. The hidden contribution from an already compatible row matters.

## Compare models at the same unknown value

At the SAME complete-history target, error(A)-error(B) equals(a-b)(a+b-2v). The v-squared term cancels, so endpoints give a sharper paired interval than subtracting two independent risk ranges. Synthetic example a=-.1,b=-.9,v in[0,1]: A error[.01,1.21] overlaps B error[.81,3.61], yet their shared-truth difference is[-2.4,-.8]. A has strictly smaller scalar error for either allowed WDL. This is a valid local scalar comparison, not evidence that a controller chooses better moves.

Seat conversion must transform both p and endpoints: seat1uses(-p,[-U,-L]). All squared-error and paired-difference results are invariant under this conversion. Child side-to-move alone never chooses value orientation.

Nonnegative explicit-weight averages of rowwise lower/upper bounds remain outer bounds without an independence assumption. Repeated occurrences may receive occurrence weights but are not independent samples or confidence intervals. Full-history values can also be coupled by the actual game tree. For a forced parent-child pair with the SAME unknown value, predictions-1and+1have separate optimistic errors0, but their jointly realizable mean error is at least1. We do not rerun a solver to tighten these coupled bounds. A lower/upper result does not claim all endpoints can be jointly realized.

## A real-data negative control against false validation success

The prior packet already showed that every one of1775qualified query-context intervals contains zero. Reusing that fact, constant p=0has continuous and discrete optimistic mean error0. Its distinct-context upper error is1757/1775=0.9898591549; occurrence weighting over2115queries gives2095/2115=0.9905437352. Zero lower error therefore cannot certify accuracy. This is a new consumer diagnostic of old evidence, not a new all-zero full-game solution or a new closure pass.

The18saved exact ply95DRAW contexts provide a precise but horizon-conditioned scalar check. The fixed A=1/all-channel-unit-weight/scale10 material output has mean squared scalar error0.008743539294 there. Constant zero matches those18targets exactly. This neither selects a material model nor proves a learned price/strength improvement. The sample was already exposed and uniformly final-horizon; the12initial opening values remain UNKNOWN. No new raw search score is interpreted as WDL.

## Actual model handoff and two learner contract fixes

The relevant implementation is generic_chess/learning/incremental.py, not the separate LearnableMaterialCheckpoint or compact-checkpoint pipeline. Model stores an ordered weight vector, fixed index and positive scale. FixedScaleSessionEnv.compile_channels places the declared physical board unit first, then other board/hand channels. Model's constructor overwrites its fixed coefficient with1. The fixed index therefore has physical meaning only with channel names, unit identity, rule semantics and caller binding.

Existing leaper_ab_uniform_learning and deeper-target callers intentionally construct fixedA/scale10 models. Their frozen-models.json arrays rely on the adjacent plan's unit/scale, complete world rules and the producer source, rather than being self-describing cross-rule checkpoints. incremental_learning.unchanged_model likewise constructs fixed0/scale10; it is not a generic clone of an arbitrary Model(scale=20). No historical source is rewritten or old study rerun.

The previous positive-unit gauge law remains a REAL-arithmetic prediction identity when channels, weights and scale are transformed consistently. Actual Model admission adds conditions. With old weights[A=1,B=1e-8],scale10 and feature[A=1,B=0], the prediction is valid. Changing unit toB produces weights[B=1,A=1e8],scale1e9: the mathematical ratio is unchanged, but Model.raw rejects the feature because the raw score crosses its existing MATE/2 safety margin. Floating finiteness and raw-score admission must therefore hold; the mate guard is preserved. Pure name permutation retaining the same physical unit is distinct and does preserve the tested prediction.

Two actual consumer defects were reproduced before repair using synthetic receipts, without a new search or fit:

1. TDLeafEpisode.observe transformed even a literal terminal MATE*WDL through tanh(score/scale). At scale1e12, WIN became0.0000009999999999996666. Now terminal receipts require exactly MATE*{-1,0,1} with no material feature, and supply literal-1/0/+1 with zero material gradient regardless of scale. The existing two search adapters already normalize actual terminal receipts to that contract. Historicalscale10returns saturate to the same values, so this is not evidence of a past training failure.
2. The frozen-episode guard compared only weights. With identical weights, changing scale10to20was accepted and mixed predictions0.1973753202and0.0996679946; changing the fixed index was also undetected. Both observe and finish now compare(weights,fixed,scale). An invalid terminal receipt leaves no partial observation/snapshot. Equivalent separate Model objects with the same parameters remain accepted. No production search, ordering, default, PRIMARY checkout or terminal authority changes.

These fixes preserve valid constant-config arithmetic and the fixed unit; they do not establish useful learning on the partial certificates or authorize a training campaign.

## Validation and next decision

Before-fix synthetic regression failures are retained privately. New controls enumerate allowed true WDL values rather than reproducing the bound formula, check all sign conversions, common-target cancellation, coupled-state counterexamples and a numerical derivative against the existing Model. Learner tests cover literal terminal targets across five positive scales, all WDL outcomes, scale/fixed mutation at observe/finish, malformed receipts, admission and intentional scale10 constructor semantics. Existing incremental/mainline learner regressions pass after the narrow fix; final counts and accepted session ledger will be appended at closure.

Research diagnostic batches make no new Core successors, Player calls, proof propagation, fitting or played-game experiment. Relevant EXISTING semantic regression tests do construct test Core/search/game cases and synthetic TD updates; their uninstrumented Core/Player/update counts are UNKNOWN, not zero. Their cost is retained and is not experimental strength evidence. All prior cumulative whole-window costs209.50498295+105.402+99.084+88.865and actual closing deliveries remain carried; this round's actual cost is added, never reset. Token totals UNKNOWN. Communication/publication/idle/offline time earns no effective-work credit.

The downstream decision is to use intervals for honest conditional-error validation with both optimistic and pessimistic limits, not a midpoint label, zero-loss success claim or singleton-witness action score. A real new compatible quality endpoint or a specifically evidence-changing learning question is still needed before another research experiment. The latest user authorizes continued scoped analysis without repeated approval; closed campaigns and Pro's stop on expansion stay closed.

## Published active milestone

163 related regressions PASS; the pre-fix receipt-only suite had15 failures among26 controls. Current confirmed effective work is 18.75485 minutes; the session is ACTIVE, with closed intervals during publication. [Static data and source hashes](data/aux_interval_validation_20261027/sources.json) preserve scope. No normal finish or new strength result is claimed.

For two legal choices A/B at the SAME complete-history root, minimax actor-regret(A)-regret(B) equals Q_actor(B)-Q_actor(A), because the common optimal root value cancels. Two partial action certificates can therefore bound a relative regret contrast without a complete root WDL/frontier. Identical selected action means exact contrast0, not two independent unknowns. Seat1reverses fixed-seat0 signs. The diagnostic is tested by exhaustive discrete completions including a third unknown option. It is not a comparison across different histories or of different continuation-policy values, and creates no new source action truth.
