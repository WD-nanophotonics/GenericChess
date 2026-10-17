# Candidate-decision training interface pilot

This pilot uses new TRAIN-only171001 prefixes on all four already exposed rules, both candidate colors and a fixed uniform opponent. The baseline model is frozen for each game. TD observes only the candidate's own searches with that model, never the opponent's search values or gradients. Its clock is candidate decisions: gamma1, lambda.95 per observation. Actual white-oriented terminal reward closes the trace; H64/resource unknown omits the artificial final error. This is a new clock, not equivalent to segment91 halfply selfplay.

The prospective WDL control plays the same baseline and a predeclared P+0.25 proposal on matching prefixes/roles, paying both sides' searches and both games. The pilot reports conservative paired reward bounds and whether strict positive-bound acceptance would occur, but does not deploy any selected price. No grid step or seed is fitted to validation.

Reusing a physically recorded baseline trace for independent TD arithmetic here is a diagnostic only. In a full method comparison each arm must pay all its training work, including baseline/proposal/opponent/failed work; this pilot does not establish equal-budget learning superiority. All16slots, terminals, unknowns, and caps remain visible. Read the exact plan and source pins. Current fixed5/free6 study is unchanged.
