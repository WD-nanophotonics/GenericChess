# Shared-parameter cutoff contract from the actual scalar consumer

The saved joint-law/hand certificate is not a drop-in evaluator for production
negamax. Source inspection: ai/alphabeta/search.py stores int SearchResult.score,
updates scalar max(alpha,score), prunes alpha>=beta, negates child windows,
uses PVS[-alpha-1,-alpha], aspiration arithmetic and scalar mate TT offsets.
Transposition entries contain depth/int/bound/action, not evaluator or domain
identity. This is appropriate for a fixed scalar evaluator/search instance;
it does not qualify reuse across coefficient models or symbolic domains.
No production engine change or new game search is made here.

Let theta=(alpha,hP,hR) be ONE vector for the whole tree, and D(theta)>0 a
common denominator. Leaves have multiaffine numerator p(theta); internal
min/max envelopes are pointwise functions, generally not multiaffine. An
interval enclosure of an envelope is sound but can be loose; independently
choosing parameters at each leaf changes the game and cannot be called the
shared-domain exact value. The order test needed for a uniform cutoff is
forall theta, lower_child(theta)>=upper_beta(theta), after root/actor signs
and denominator have been aligned. A failed supplied certificate means
NO PROOF, not a negative order or permission to sample a midpoint.

For exact min envelopes A=min_i ai and B=min_j bj, a supplied per-i convex
combination of B leaves proves A-B>=c: for each i, max_j(ai-bj) is at least
ai-sum_j w_ij*bj; certify each resulting polynomial globally>=c by its8
vertices. Taking min_i retains this lower bound. This is the existing helper's
proved contract, not a claim that original envelopes extremize at vertices.
For max envelopes use max A-max B=min(-B)-min(-A), with proofs in THAT order.
For min A-max B, every pair ai-bj>=c suffices and is necessary pointwise;
global certificate must retain all pairs. For max A-min B, any one globally
dominating pair suffices but is incomplete; absence of such a pair is unknown.

Tie ownership matters. A>=B suffices for a scalar beta cutoff's VALUE bound;
to discard an alternative ACTION with an earlier canonical ID, equality is
insufficient. Require A>B everywhere or verify the retained ID wins equality.
Range and branch completeness must be bound into a certificate. Missing legal
responses, terminal/claim/history mismatch, different remaining depths or
different qsearch objectives cannot be repaired by a strong algebraic margin.

Before cache reuse bind full physical/rule/history state, remaining search and
qsearch horizon, payoff/terminal/declaration semantics, leaf evaluator version,
shared-variable order/domain, common denominator and subtree/proof identities.
Caller-local fresh scalar TT remains usable for each FIXED point, but old TT
entries are not universal certificates. Depth>= alone does not establish that
a different finite-depth static target is pointwise identical. If a proposed
adapter makes deeper-search bounds heuristic, mark that separate premise.

Mate scores are scalar constants only for the SAME authoritative goal. A
symbolic numerator must encode them as score*D(theta), not a raw numerator
constant; assert D positive before division/sign tests. Restart floors and
literal-mate-only unknowns have distinct goals. Fixed integer quantization
or rounding of mixture-dependent weights is generally piecewise, not the
saved exact rational polynomial; certify its error separately or keep this
contract research-only. PVS+1 also depends on an admitted integer score lattice.

The narrow useful next step is a pure order-certificate verifier for the
four envelope orientations and canonical ties, tested on switching functions
and common-denominator controls. It can qualify admissible algebraic cutoffs,
not production integration, avoided Core cost, WDL or independent strength.
Existing closed43-leaf and failed full-stock families must not be expanded.
