# ADR-064: Natural-terminal reference corpus R9

- Status: Accepted as F23S evidence; full and signal-probe gates not passed
- Date: 2026-08-30
- Work order: `GENERICCHESS-F23S-NATURAL-TERMINAL-REFERENCE-CORPUS-R9`
- R9 plan SHA-256: `f4f6029b30ec28025cf0a113f70dc11d438d95385821e8b6ca62f3a906211bcc`

## Decision

Freeze a new evaluator-blind R9 candidate plan with 48 candidates across six
families: ordinary anchor terminal, capture/recapture terminal, drop/hand
terminal, promotion terminal, semantic-guard terminal, and interposition
leaper terminal. Candidate lineage IDs and DEVELOPMENT/HOLDOUT splits are
derived from canonical payloads using the established F23N-V7 split contract.
V10 roots are historical controls only and cannot become V11 supervision.

Each candidate is first required to pass the authoritative V3 exact ladder,
with complete root-action W/D/L values, a nontrivial preference partition, and
a causal mechanic witness. Only then is the separate F23R abstraction v2 run;
V11 eligibility requires every root action and the complete optimal set to
match V3 under MAX_PLY-as-unknown semantics.

## R9/V11 result

The frozen plan contains 39 DEVELOPMENT and 9 HOLDOUT candidates. V3 solved 39
and left 9 unresolved; 19 were preference-bearing, 23 had a witness, 18 were
abstraction-refused, and 20 were all-equal diagnostics. One candidate was
eligible after exact and abstraction filtering, yielding 1 DEVELOPMENT and 0
HOLDOUT effective representatives. There were zero observed or residual
behavioral leakage groups, zero duplicate orbit groups, and zero V10 IDs in
V11 eligibility.

The one effective root is multiply dependent and has a DRAW/WIN partition, but
the clean corpus is below both the full gate and the signal-probe gate. The
selected next boundary is `F23T_NATURAL_TERMINAL_REFERENCE_CORPUS_R10`.
No evaluator prototype or fitting is authorized by this ADR.

## Integrity and scope

V1–V10, all F23N–F23Q plans and evidence, all F23R first-pass/R1/R2 artifacts,
F23F/F23K/F23L/F23M capability evidence, and prior ADRs remain byte-identical.
No production evaluator/search/Native/workflow/governance code changed. The
V11 fixture retains historical source hashes, complete candidate diagnostics,
abstraction certificates/refusals, witness data, orbit/leakage accounting,
split coverage, proof depth, and explicit full/signal gate calculations.

