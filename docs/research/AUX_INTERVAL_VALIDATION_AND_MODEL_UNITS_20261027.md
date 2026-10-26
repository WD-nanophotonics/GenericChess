# Partial WDL intervals, prediction diagnostics and fixed-scale model identity

Status: ENDED DEV_AUX segment1e5f0dfd-3761-49e6-a6b3-22226fdb916e. Origin2026-10-26T17:56:08.506075Z; accepted safe-checkpoint finish2026-10-26T19:14:34.514224Z. Confirmed effective work3752.021972seconds=62.53370minutes across9closed intervals; duration gate passed and memo synchronized. [Accepted ledger](data/aux_interval_validation_20261027/session-finish.json). The previous segment contributes no credit to this round.

The useful outcome is a bounded validation contract and three concrete learner fixes. Interval compatibility does not establish accuracy. A shared-truth paired error contrast can be informative even when two separate error intervals overlap. The actual TDLeaf consumer also needs literal terminal targets independent of material scale and an episode guard covering scale/fixed-unit index as well as weights. Neither result is policy-strength evidence.

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

## Censored final-target completion is a correlated sensitivity calculation

For m observed frozen predictions p_i and gradients g_i, let e_i=lambda*e_(i-1)+g_i, starting at zero. Let D_known=sum over i<m-1 of(p_(i+1)-p_i)*e_i. Replacing ONLY the missing last scalar target by z would give D(z)=D_known+(z-p_last)*e_last and weights w(z)=w_before+eta*D(z), before floating-point realization and the unchanged fixed-coordinate projection. There is one COMMON z for the entire vector. It is not a coordinate-wise collection of independent targets.

The actual None path omits that last TD error and retains D_known. Algebraically it agrees with a hypothetical real endpoint z=p_last, not generally z=0. That equality does not label the unknown final game result with a fractional WDL value. For lambda1 the interior sum telescopes to the last bootstrap prediction minus each earlier prediction, not a made-up Monte Carlo DRAW. Final-target uncertainty can also vanish when e_last=0 even though interior updates are nonzero; this says nothing about model accuracy or no future useful signal.

Synthetic source-consistent receipt example uses fixed weights[1,1,1], scale10, features[0,1,-1]then[0,2,-1], with raw scores0then1. Existing independent arithmetic gives:

| Hypothetical final target | Second weight | Third weight |
|---|---:|---:|
|-1|.984387474873|1.010168804064|
|0|.999038137781|1.000468472610|
|+1|1.013688800690|.990768141156|
|None: omit final term|1.000498339973|.999501660027|

The coordinate-wise maximum box corner combining the largest second and largest third weight requires BOTH z=+1and z=-1and is impossible. Under deterministic WDL there are only three hypothetical endpoint vectors, not the entire continuous segment. They are arithmetic alternatives, not a claim that all outcomes are reachable under the actual complete rule and future policies. Even a valid minimax state bound does not automatically restrict the realized return of arbitrary continuation play. Such narrowing needs actual continuation-policy/strategy evidence and is not implemented here.

This affine expression assumes the same frozen receipts, gradients, lambda, eta and trace logic, with only one final target varied. Changing targets/weights and recomputing search, adaptive steps, clipping TD errors, or updating between observations can invalidate it. It is not a method for selecting an oracle completion or a new training algorithm.

## Actual-update reporting: a third narrow consumer fix

The current incremental_learning summary counts training_updates from the learner's changed flag. A further source-backed control showed that changed=any(unscaled_delta) could report true when eta=0, or when a nonzero eta*delta rounds away at the actual parameter magnitude. Example weights[1,20], feature[0,9], scale10, target+1, eta.05 produces a tiny nonzero analytical direction but identical representable weights. The learner and independent arithmetic reader now compare actual before/after weights for changed. Two failing-before controls are retained;165related tests pass after this additional fix. No historical run count is rewritten or asserted wrong without a matching recorded case. Nonzero eligibility/error, proposed numerical direction and actual parameter movement are separate measurements.

## Primary-source check: what TDLeaf does and does not establish

Read the original [KnightCap paper introducing TDLeaf(lambda)](https://arxiv.org/abs/cs/9901002), arXivcs/9901002v1, especially sections2–3/figure3 and4.1–4.2. Exact145722-byte PDF is preserved privately, SHA2564ef51a94b47991cf4e27b4d12adbfd433f4d9b2aaf4dbfcd15a23001e27aa150; extracted text is separately hashed87ae71230250a85bcd6c35533550cfc38aa128dd400d467b386d83a95ea70c97. Python TLS initially lacked its local CA chain; a normal certificate-validating system client succeeded. Existing bundled text extraction was used after the local environment lacked a PDF extractor. No security setting was disabled; raw author-contact text stays private.

The paper's J* is an EXPECTED reward under a declared agent/opponent transition policy, not automatically deterministic optimal-play WDL. Figure3 freezes parameter-dependent principal leaves for the update, permits depth varying between positions, and takes the final reward as literal W/L/D. Our complete-history admission remains necessary even though the paper abbreviates game positions. Current play_episode observes completed learner-side searches, so lambda is per observation, not per Core ply or wall second. None/incomplete work cannot be converted into an actual terminal target.

The paper's root-gradient argument is local to a fixed minimax tree with a unique principal leaf; it discusses tied-PV nondifferentiability and arbitrarily selecting a leaf. Its empirical implementation also used hand-informed material initialization, online opponents, a tanh scale convention and selective suppression of some positive TD errors. Those are different from this project's uniform/random initialization, no human-price-prior requirement and unclipped fixed-scale learner. Its historical chess performance and convergence discussion supply no GenericChess strength guarantee, generic price law, or authority to import those modifications. No lambda/scale/initialization sweep or teacher campaign follows from reading it.

Unit initialization can lie ON tie surfaces rather than being a generic random parameter vector, so the paper's almost-everywhere differentiability is not evidence that ties are negligible here. A synthetic two-leaf arithmetic control uses material features[-1,+1]and[+1,-1], A=1,B=1,scale10. Both bounded leaf values are0but their free-B gradients are+.1and-.1. For a MIN root, f(B)=-abs(tanh((B-1)/10)); taking the first selected PV gradient toward a hypothetical+1target moves B to1.005and INCREASES actual restricted-root squared error. A MAX root has the opposite behavior. The non-tied fixed-tree derivative is separately checked by finite differences. This is a counterexample to a guaranteed-descent interpretation, not an actual legal Leaper position, actual WDL label or evidence that current experiments suffered it. We do not change tie policy or generate a rule to fit the example.

The actual mainline learner adapter verifies a literal material PV leaf and uses SearchTuning with root tactical off/require_full_pv on. Current shared tuning defaults leave PVS, aspiration and staged picker OFF; its exposed use_ordering switch is not an activation of every available search optimization. Existing PRIMARY PVS timings therefore do not establish acceleration for this learner. This is a source/caller qualification, with no new Player benchmark and no PRIMARY algorithm intervention.

A stronger synthetic tie control separates that effect from mere unrepresentability. With fixed A and free B/C initially[1,1,1], use leaf features[-1,1,0]and[-1,-1,2]. Both predictions are0. A selected-first-leaf update toward hypothetical+1raises only B, lowers the other branch and worsens the MIN-root squared loss. A joint positive B/C direction instead raises BOTH leaf values and improves it. This is a representation-level counterexample with an available improving direction. The two feature vectors are synthetic; no legal Generic/Leaper reachability, new state truth or observed current-run failure is claimed. A deterministic unit initialization can meet such tie surfaces exactly, so a future method claim must separate literal-PV receipt correctness from unique-root derivative or useful-decision improvement. No tie-policy experiment is launched here.

## Does the new changed-stat defect affect recorded learning evidence?

This is a new, bounded question prompted by the newly reproduced flag defect, not a rerun of an old experiment or rechecking old WDL. The fixed89e1274d publication contains the [earlier404-episode learning packet](data/leaper_ab_learning_and_rank_20261024/README.md), compressed hash ef6f0e954d3fd07f6ea688c5355b0f1da183d329a428639b34497a9c6410a9f1 and manifest blob08edefe3a3920979691c83fd065af97ea02dea5a. Read all404full game documents and verify their individual original byte hashes. Compare ONLY each stored changed boolean to exact stored before/after vector equality. No Core trajectory, TD return, parameter update, solver or old1520return is recomputed; raw historical payloads stay unchanged.

| Published cohort | TRAIN records | Flagged changed | Actual distinct before/after | Frozen EVAL records |
|---|---:|---:|---:|---:|
| Unit|8|0|0|32|
| Initialization|8|2|2|32|
| Near-boundary|4|1|1|0|
| Uniform|256|179|179|64|

All276TRAIN flags agree with stored vectors; all128EVALrecords have no update and equal weights. Thus no historical activation-count correction is supported for THIS packet:182actual parameter-changing episodes remain real. The newly found eta0/rounding defect remains a valid consumer bug, but it must not be promoted into an allegation that these past results were false. This does not establish all other archives unaffected, revalidate game truth, reproduce the numerical TD equations or turn the old zero observed terminal gain into a positive result. The [compact check result](data/aux_interval_validation_20261027/historical-parameter-change-check.json) records exact coverage and zero mismatches; the per-document private worklist remains available without creating another public registration framework.

## Prospective use and what is already closed

The policy-return/minimax distinction is not a new observation from the old Uniform study; it is retained context, not another work item or permission to refill its slots. A minimal conceptual tree makes the target contract clear: a safe immediate DRAW and a branch whose opponent can choose DRAW or our WIN both have minimax value0, while the latter has positive expected return against an opponent that sometimes chooses WIN. The opposite case, a branch offering our LOSS/WIN, can look attractive against a weak fixed opponent while having worse minimax security. These are conceptual examples only, not newly generated Generic rules or observations.

For a future compatible learning question, first state whether the quantity is actual terminal payoff against a declared opponent/distribution, conditional minimax action regret, scalar state-value calibration, or representation/gradient support. Then bind actual complete rules/history, constructor/unit/scale/channels and the relevant resource/exposure conditions. Evidence for one quantity does not silently establish another. Actual limited payoff tests do not require a universal WDL solver or perfect label coverage; conversely, label availability or gradient motion alone does not justify another paid experiment. The current saturated source panel remains closed. The new historical flag check was useful precisely because it could falsify a concrete interpretation of existing activation evidence at negligible data-only cost; it found no such correction in its covered packet.

Beal/Smith's1997Learning Piece Values Using Temporal Differences was located by primary-publication metadata (DOI10.3233/icg-1997-20302), but its publisher full-text endpoint returned403. Its initialization, execution and detailed outcomes were NOT independently read. KnightCap's summary of it is a secondary statement, not substituted primary experimental evidence or a parameter recommendation. This coverage gap is retained; no access bypass or repeated lookup follows.

## When partial targets can still make a comparison decision

For any two bounded predictions a,b and a completely UNKNOWN WDL target[-1,1], their paired squared-error difference interval contains0. Its width is4*abs(a-b). Thus that row alone cannot strictly order the predictors, but its possible effect is controlled by their prediction difference. For a narrower interval the width is2*(U-L)*abs(a-b). These are shared-target arithmetic limits, not sampling uncertainty.

Missing full truth is therefore not an automatic evaluation gate. Synthetic example:1%of predeclared row weight has target[0,1], with predictions a=-.1,b=-.9; the other99%has unknown target but IDENTICAL predictions a=b=.4. The unknown contribution cancels exactly, so total paired error difference is[-.024,-.008] despite overlapping separate error ranges. Partial certificates can decide this narrow scalar comparison. If predictions change on unknown rows, their measured differences must be included; no zero-error imputation or unmeasured cancellation is permitted.

For same-channel fixed-scale static material models, tanh is1-Lipschitz, giving abs(p_A-p_B) <= abs((w_A-w_B) dot phi)/scale. A valid feature bound can therefore bound the contribution of unlabelled rows; such a bound must match actual promotion/drop/stock/auxiliary scope and unit convention. A zero gradient at one returned PV is NOT proof that a different model leaves all possible search leaves or chosen actions unchanged. This is a prospective diagnostic criterion, not a new model fit, rule experiment, source-wide prediction measurement or proof that the current global price changes have small unknown impact.

A separate data-field compatibility check reads14598recorded receipts from the same404documents:13626material leaves and972literal terminal leaves. All972terminal leaves areDRAWwith value0and no feature; there are no nonzero terminal receipts in this covered packet. All recorded fields satisfy the new terminal/shape contract. These events span both actors and phases and can include uncommitted tails; they are not14598training observations. No PV replay, state-feature regeneration, actual terminal truth admission or TD-return recomputation is performed. In particular this old packet cannot independently test nonzero terminal normalization; the new actual Core WIN/LOSS integration controls do that with Player construction forbidden. Scale/fixed epoch immutability also cannot be proved from old arrays that did not record those fields.

## Numerical authority of diagnostic comparisons

A real supported Model(scale=1e200) returns p=1e-200for a unit material feature. Ordinary binary multiplication rounds p squared to0. The initial diagnostic consequently reported exact DRAW error upper0and EQUAL_SCALAR_ERROR when comparing p to a literal zero predictor. This was a false numerical equality, not evidence that the predictions were equally accurate. A failing-before control is retained.

The diagnostic now treats its finite binary floating INPUT values as exact rationals for endpoint/sign arithmetic, rounds displayed lower bounds down and upper bounds up, and derives paired verdicts from exact endpoint signs. Weighted paired sums likewise retain their common-target rational endpoints; they do not sum rounded-nearest products. Derivative displays remain floats. A subnormal displayed bound may contain0while an exact rational endpoint still proves a strict sign; the exact endpoint strings and numeric_scope state that distinction. This is numerical honesty for the scalar diagnostic, not a practically meaningful1e-400policy improvement, high-precision truth about real-valued tanh, or a change to search/training precision.

The existing real-data negative controls are regenerated only through this corrected arithmetic. Inputs, WDL bounds, model coefficients and source identities do not change. The approximate18-context scalar mean is accompanied by an outward-rounded interval. No data fitting, new truth, new source-state expansion or rerun of a closed experiment follows.

Historical closing-science checkpoint before the final control:178relatedtestsPASS and 58.01789confirmed effective minutes; sessionACTIVEduringpublication, no normalfinishyet. Full final ledger will follow after the minimum and final semantic-control checkpoint. No uncredited transport/publication/offline time is added.

## Final semantic control: lower scalar error can worsen the chosen action

Even pointwise scalar-error improvements are not a controller-quality theorem. In a synthetic complete two-action table with true fixed-seat0values[0,1], baseline predictions[-.9,.1]choose the winning action. Candidate predictions[.4,.3]are CLOSER to BOTH true values, but choose the DRAW action. The exact paired scalar diagnostic correctly prefers the candidate at each action; the action-regret diagnostic correctly gives candidate-minus-baseline regret+1. This is an algebraic control, not new rule reachability or evidence that these estimates occur in current runs.

A sufficient link needs additional conditions. If estimates for every actual choice satisfy a common sup error epsilon, a greedy action has minimax regret at most2epsilon. If a true unique-action gap exceeds2epsilon, it selects that best action. This derivation requires the same action-value target/perspective and the ACTUAL selection rule; a single returned PV or static root feature is not that complete estimate table. Missing legal declarations or different policy-continuation values can break the premise. Existing direct action-coverage bounds can sometimes prove optimality with less information; this is not a universal oracle/solver gate.

Consequently the new partial-risk criterion is useful for its declared scalar diagnostic and for falsifying exaggerated accuracy claims. Actual action/regret/payoff and same-resource execution evidence must remain separate. This final control closes the method interpretation without another training or policy-control campaign.

## Executable continuation after this safe checkpoint

The completed interval/gauge/censored/flag checks are not a new run queue. Next intake must use current GitHub Pro and the pending Dot method reply. One distinct AUX question, if no new assigned task supersedes it, is whether a uniformly bounded same-unit material perturbation can qualify action stability on an ALREADY complete fixed-depth tree. Max/min are nonexpansive in the sup norm, but a reported PV alone does not supply the required leaf-domain bound, and time-cancelled or selectively changed trees do not automatically share that guarantee. The first action is source/caller admission of the existing tree/profile and feature domain, not generating a tree or launching a solver. The deliverable is a precise applicable bound or an explicit source gap.

A second independent backup is to inspect the original fixed-policy TD function-approximation theorem and identify which assumptions the current nonlinear, search-controlled learner does not meet. This is a new primary-source question, not rereading the completed KnightCap report, implementing another learner, claiming convergence or starting training. The choice follows the next Pro/user plan; neither missing input nor a silent Dot reply becomes a permission gate. Existing H6/PVS/Uniform closures, limits, role boundaries and all actual cumulative costs remain intact.

## Accepted final closure

179relatedregressionsPASS. Accepted effective research62.53370minutes; actual origin-to-finish window78.433469minutes plus actual final delivery, with prior cumulative costs retained and no admin/transport credit. No open work interval, new writer, research campaign, PRIMARY change or cadence change. Final control separates pointwise value-error improvement from chosen-action regret.

Milestone1493969465166b44772d8e604fab63ada1684711was pushed/fullremoteverified before closing followup1793041659.871849at19:07:39.871849UTC. Its one delayed complete-thread check19:13:50UTC found3replies(priorDotanswer and twoownfollowups), no new method answer and no pagination gap. InitialDot1793037889mathematical cautions remain adopted, not numerical execution endorsement. The unanswered affine-target question remains for the next meaningful intake, not a gate, expired request or reason to poll again. Executable continuation is in the own memo/temporary plan; completed controls are not repeated.
