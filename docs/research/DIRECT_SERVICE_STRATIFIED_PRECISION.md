# Direct H2 service: integrate known rewards, sample relevant branches

2026-10-04. Analytic changed premise; no new game samples, coefficient vector,
context selection or larger experimental budget. The target remains the SAME
declared uniform complete-choice policy and fixed context law.

## Fixed-root identity

Let the root have A complete own choices a. The already qualified binding
reward gives the exact first-own mean g0 = sum_a R1(a)/A. Conditional on a,
let W_a be eligible next-own expected service after a uniformly chosen complete
opponent choice; terminal/ownership-loss branches give zero. Then

    v(root) = g0 + (1/A) sum_a E[W_a].

Integrate R1 at the root rather than sampling it again. Suppose a certified
pre-opponent bound b_a satisfies 0 <= W_a <= b_a. Define
U = sum_a b_a/A. If U=0, the future term is exactly zero. Otherwise sample the
first own choice with probability b_a/(A*U), sample the opponent under the
ORIGINAL conditional policy, and use T = U*W_a/b_a. Thus E[T] is the original
future term and 0 <= T <= U. Zero-bound actions are omitted by proof, not by
observed zero reward. Do not execute a renormalized policy and interpret its
unweighted service as the target; these are computational importance weights.

For a wholly held tag among n own same-base tokens, b_a=1/n on same-base drops
and zero otherwise, by HELD_H2_STRUCTURAL_BOUND.md. Therefore U=D/(A*n),
the relevant own choices are uniform among the D complete same-base drops,
and T=(D/A)*W_a. This does not require materializing all A own children to
learn their tag mass. The complete ROOT action set and exact drop/base mapping
must nevertheless be qualified. All opponent/next-own choices remain complete.
If D=0 the held H2 target is exactly zero at this root, not necessarily under
other contexts or a longer horizon. Board-mode b_a=1 is a conservative default;
tighter endpoint bounds require actual qualified transitions, not guessed IDs.

## Exact fixed-root variance saving for held tags

Write p=D/A and W for the conditional drop-then-opponent future service.
The original direct observation is Y=B*W, with B Bernoulli(p), and has

    Var(Y) = p Var(W) + p(1-p) (E W)^2.

The conditional-drop observation is T=p*W, with

    Var(T) = p^2 Var(W).

The saving is p(1-p) E[W^2] >= 0. For p=0 no sampling is needed; for p=1
the schemes agree. Anonymous label integration stays necessary: the dropped
piece carries only1/n tagged mass. Conditioning on a physical marked drop
without that factor would change the target. This argument assumes a public
policy independent of hidden physical labels, as in the qualified trace.

## What precision this actually buys

For a fixed root, m independent conditional-drop/opponent observations have
raw future halfwidth U*sqrt(log(2K/alpha)/(2m)) by the bounded-variable derivation
in DIRECT_SERVICE_PRECISION_BOUNDARY.md. Here K is the number of simultaneously
claimed root means, not automatically25 material components. Exact g0 adds no
path variance. If both first AND opponent branches can be completely integrated
within frozen caps, the finite-root target instead has no sampling uncertainty.

Illustration using structural data already recorded (not a new price estimate):
the frozen hand/P root has p=5/54,n=1,U=5/54. K=1,alpha=.05,m=6 gives a sufficient
halfwidth about0.0513, intersected with [0,5/54]. This is a conditional finite-root
claim. It does NOT turn six paths at one context into six independent contexts,
establish a population value, positive hand value, or justify rescoring a new
population selected after seeing these roots.

For variable roots X, total variance is Var(v(X))+E[conditional variance].
Stratification reduces the second term; it leaves context variation and context
bias intact. If roots are sampled, their exact g0 and U still vary. One cannot
plug a single root's U into a confidence bound for the full population unless
that bound holds throughout the independently declared support. Never normalize
different mode coefficients by their U: retain the common raw capture gauge.

The non-increasing variance claim above is SPECIFIC to wholly held tags, whose
R1 is identically zero. For a board tag, separating exact g0 from a newly sampled
future term need not reduce TOTAL variance relative to R1+W: negative covariance
can cancel the original noise. Two equiprobable branches (R1,W)=(1,0),(0,1)
give original total1 constantly, whereas g0+W is1/2 or3/2. Both are unbiased;
the latter has variance1/4. Importance weighting remains a valid identity and
range bound, but no universal efficiency assertion follows for board modes.

## Cost and next decision

Each selected branch needs at most two public transitions (own action/opponent),
then exact next-own enumeration; the fourth ply is unnecessary for H2 reward.
Terminal branches stop sooner. Complete root/conditional legal enumeration,
binding-set agreement, tag tracing and terminal qualification still cost work.
No claim that the existing24-transition diagnostic budget admits a25-mode vector.
This is a path-noise remedy, not a high-precision population or deployment result.

Before any new observations, choose a decision-changing claim with an independent
target law and frozen caps. Prefer a finite-root interval/use falsifier that can
retain unexamined branches as certified bounds. Do not increase paths until a
hand mean becomes positive, censor expensive branches, or silently replace the
original action policy with drop-only play. Pure independent hidden-label/branch
enumeration checks the weighting and variance below; engine adaptation remains
an explicit separate qualification step.
