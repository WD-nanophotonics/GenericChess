# Allocation averages need a separate static-transfer assumption

2026-10-05. New derivation, no independent labels, coefficients or reruns.
Let a full context z have count N_m(z) of physical own resources in mode m,
total allocation A_m(z) in that mode, and task F(z). For a fully specified
coalition game with baseline0, efficiency gives F(z)=sum_m A_m(z).

Under a DECLARED context law mu, define the token-weighted prototype
w_m=E_mu A_m / E_mu N_m whenever E_mu N_m>0.
Do not substitute E_mu[A_m/N_m] over roots: variable counts change the sampling
law, and zero-count roots have no such per-token quantity. A prototype-query
replacement law is a different population, not automatically this expectation.

Then H(z)=sum_m N_m(z)w_m satisfies E_mu H=E_mu F. This is only a first-moment
identity, not a conditional prediction or smaller risk than a constant baseline.
For conditional mean transfer across inventories a sufficient assumption is
E[A_m|N]=N_m*w_m for each m. Summed conditional stability is weaker and enough
for total mean prediction, but neither follows from allocation efficiency.
For a different population nu, even the unconditional identity need not hold.

Write residual epsilon(z)=sum_m(A_m(z)-N_m(z)w_m). If a qualified simultaneous
mode deviation bound |A_m-N_m*w_m|<=N_m*eta_m holds, then
|epsilon(z)|<=sum_m N_m*eta_m. Without it, perfect average efficiency can hide
large cancelling individual errors. This is an approximation/transfer question,
not a demand for universal WDL calibration before construction research.

## Exposed matched-mode illustration: not independent validation

Use ONLY the two already observed Knight/Rook task roots, each with weight1/2,
and their source-derived singleton values. Both full task values are1.
Allocations are board-N1/R0 versus held-N1/2/R1/2. Thus token-weighted mode
prototypes are w_boardN=1,w_handN=1/2,w_boardR=1/4.
Static sums are5/4 and3/4. Average equals1 as efficiency predicts, yet squared
task risk is1/16. Constant1 has risk0; zero has risk1. The average identity
therefore does not imply useful static task prediction, even on its own law.

This does NOT reject every static vector: e.g. constant mode assignments could
represent these two FULL root values. Deprivation roots and individual
allocations ask additional, different questions. Do not turn the illustration
into a fitted rescue, a fresh independent benchmark, or prices for deployment.
The example diagnoses a concrete construction/transfer step; it does not
prove failure of the uncomputed112-frame law or forbid approximate priors.

For independent use, freeze actual mode-complete candidate/projection BEFORE
the new generator or goals. Compare full child selectors and both baselines,
retain ties/unknown quiet children. In particular, material feature intervals
can remain too wide to certify a unique selected action even while task mean
identities are exact. SMALL_SOURCE_USE_GENERATOR.md's no-midpoint requirement
continues to apply. No Xiangqi or human-price data is needed for this diagnosis.
