# ADR-132: V2G Human-Validation Closeout

Status: frozen V2G candidate rejected by its unchanged validation gates; no score or formula adjustment made.

## Observation

The frozen V2G candidate has SHA-256 `b09c055fa5b29cddba6131ebe4de43f39be434b0e187950bce0a448bf8f5a6c9`; its pre-reference freeze has SHA-256 `59ebcdc8d2c264cbeafec7193cebd644aa0f92354c8fc1661862908364d8cb5e`. The reference comparison was run only after that freeze. Human material values were validation evidence, not a fitting objective.

Western Chess did not pass. Its pawn-normalized candidate ratios were N=0.6981, B=0.6204, R=1.6463, and Q=3.1660; all four miss their frozen bands, and the sensible-ordering condition also fails. The global-scale diagnostic gives cosine 0.9710, Pearson 0.9017, Spearman 0.6000, and pairwise ordering accuracy 0.7000. The scaled residuals (candidate minus reference) are P=+187.60, N=-119.23, B=-151.58, R=-26.53, Q=+10.54.

Standard Shogi also did not retain its frozen gate. Its cosine is 0.9483 against a 0.95 minimum; Spearman 0.9012 and pairwise ordering accuracy 0.9103 clear their respective 0.90 minima. Scaled residuals (candidate minus reference) are P=+7.08, L=-139.23, N=-192.02, S=-187.52, G=-281.14, B=+17.98, R=+262.45, TP/TL/TN/TS=-281.14 each, TB=-34.36, TR=+93.76.

These failures diagnose a mismatch in the frozen rule-derived components; they do not authorize fitting weights, discounts, or piece-specific corrections to these references. Any new hypothesis must first have an independent rule-semantic or game-theoretic rationale, then be frozen before validation. These inspected Chess and Shogi references are diagnostic evidence, not untouched holdouts.

## Validator provenance

The pre-reference validator SHA-256 recorded in the freeze is `93359e03ca5b7a0a3bf3e7c3c1c433e570fab221b48d8c8701970cba47f93a2f`. The first post-freeze attempt reached the human-reference fixture only after candidate preflight, then stopped on the validator's incorrect V2C key `v2c_u`; it emitted no metrics. The corrected validator reads `v2c_maxent_token_board_intrinsic`; its exact current SHA-256 is `266c5dadd135fcd19bcd22c96eb7625bdd3aa5e2085bb493c8b6998502919192`. A fail-closed helper requires both the recorded frozen SHA and this one reviewed current SHA; no arbitrary self-hash exclusion is accepted. Candidate bytes, formula, frozen bands, and human-comparison metrics were not changed by the validator correction.

The full machine-readable validation output remains under `.generic_chess_flow/` and is not published as a generated artifact.
