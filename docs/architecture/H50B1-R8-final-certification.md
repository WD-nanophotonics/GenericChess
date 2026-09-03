# H50B1-R8 immutable regression evidence and identity closure

R8 is record-only.  It keeps the R5 Native production implementation frozen
and closes the two evidence gaps identified in the R7 review.

The H50A baseline is bound to commit `7ff0039bcc469bdc6b0b3c5ade61558d72ccf681`.
The fixture records its worktree Git identity, compiler source SHA-256, Git
blob SHA-256, Git object ID, parsed `SEMANTIC_PAYLOAD_VERSION=2`, loaded module
location, and generated Native artifact classification.  The actual H50A and
current R7 JUnit, raw output, and runner metadata are retained under
`tests/fixtures/h50b1_r8_regression_evidence/`; the R8 test validates their
hashes and parses their JUnit totals without requiring machine-local paths.

The authoritative post-freeze full regression includes the R8 tests:
`1547 = 1542 passed + 3 skipped + 2 failed`.  The only failures are the two
registered residuals: the F24F Kiwipete depth-1 result and the unavailable
external AlphaSho evaluation corpus.  The accepted 24 Western / 21 Standard
Shogi semantic differential, declaration/spatial controls, history and 500-ply
checks, generic witness, ABI measurements, and F49 scientific-contract
equality remain preserved.  `generic_chess/` is byte-identical to R5, R6, and
R7.  `F50B2_status=NOT_STARTED`; promotion remains `HOLD` pending review.

Resource policy for the next boundary: keep one Worker, one repository writer,
and one top-level Heavy job.  Within those safety boundaries, independent
partitions may use measured CPU and memory in parallel, with isolated caches or
TTs, atomic outputs, and deterministic ordered merge.  Re-audit conservative
limits such as Below Normal priority, one global computation subprocess, F49
serial loops, Native single-threading, and tiny TT before F50B2.  R8 does not
change those limits or production code.
