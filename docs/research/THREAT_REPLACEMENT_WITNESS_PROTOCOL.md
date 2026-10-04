# Threat replacement witness: freeze before public replay

2026-10-04, adviser GC-SLACK-20261004-173922-e63d9cdd. Dot proposed a
manual four-ordinary-token intrinsic counterexample, not executed evidence.
Independently verify it using current compiled Western Chess capture cubes
and semantic pseudo-attacks, with an actual public capture transition.

White R d3, N d1; black B b3, R d8. Add white K a1 and black K h8 outside
the relevant paths to permit a full-rule public replay. No castling/en-passant;
synthetic reset history. FEN 3r3k/8/8/8/8/1b1R4/8/K2N4 w - - 0 1.
Control: remove black R d8; FEN 7k/8/8/8/8/1b1R4/8/K2N4 w - - 0 1.
These are hand-built semantic controls, not deployment roots/goal labels.

Before replay, query capture eligibility of N d1 in the same full occupancy:
B b3 attacks through c2; R d8 is blocked by own R d3. Enumerate the public
legal capture d3xb3 exactly once. Preserve full child state and protected N
at d1. After replay, the bishop is absent, but R d8 now attacks d1 in the
four-token case. In the control, N is no longer attacked. Compile captures
and promotion identities exactly; compare total cube-derived exposure with
SemanticEngine.is_square_attacked on both states. Neither intrinsic cubes nor
that pseudo-attack API includes attacker's own-anchor safety; this is explicit.
The chosen actual capture does obey full public legality. In the replacement
case verify one public R d8xd1 reply exists and removes N; this demonstrates
replacement exposure, not forced loss or WDL value.

Report original removed-edge motif1 in both cases; exposure delta T_before-
T_after is0 for replacement,1 for control. This refutes an exact 'one removed
attack edge gives one net-protected piece' interpretation, not statistical
usefulness of a predeclared feature. No static material coefficients follow.

One process,10 seconds including compilation,128 public choices per fixture,
at most3 public transitions total (two captures and one replacement reply).
No deeper search, alternative fixtures, values, old service labels or holdout.
Preserve actions, histories, boards, hashes and observed runtime.
