# Task003: retained work from an aborted iteration

Pinned source b4108a68; material-only frozen tables, q0/hard0, root scanOFF.
24 predeclared short calls completed. All Session/history objects restore and
all recorded runtime pushes/pops balance. Actual Native legality reports zero
fallback/operational failure in these calls. No wall benchmark was performed.

|Root|Cancel after64 iteration2 pushes?|Final interrupted depth|Retained aborted entries|Warm matching probes|Warm/cold D2 score|Warm/cold nodes|
|---|---|---|---|---|---|---|
|Chess middle|Yes|1|16|16|-100 / -100|56 /138|
|Chess EP|Yes|1|6|6|0 /0|58 /147|
|Chess tactic|Unreached|2|0|0|999999999 /999999999|2 /88|
|Chess promotion|Unreached|2|0|0|400 /400|2 /24|

Each row is reproduced in both warm/cold orders. The unreached cells completed
D2 before the declared cancellation condition; their warm work reuses completed
iteration entries, never evidence for reuse from an aborted iteration.
reuse.json preserves those completed-iteration entry/probe counts separately.

For middle/EP, TT stores made in eventually aborted iteration2 survive with the
exact same key/depth/score/bound/action metadata. Warm probes actually match
16/6 retained entries. Returned completedD2 scores agree with cold calls.
This falsifies the claim that all successful work in an aborted iteration is
necessarily unusable. It does not show every entry was sufficient for a bound
cutoff, that all work was reused, or that preserving more work improves play.

Node differences describe total warm-state reuse. They include earlier completed
iteration1 entries as well as entries from aborted iteration2, changed ordering
and ordinary iterative scheduling. They do not isolate an exclusive causal
saving from the aborted entries, and they are not a timing improvement.
No additional ablation is needed for the present narrow decision: label aborted
work as not part of the returned completed iteration, rather than automatically
wasted. It remains a candidate source of subsequent reuse.

A first report label called all iteration2 retained entries aborted, even in
the two unreached/fully completed cells. This was corrected directly from their
recorded trigger and completed_depth, with no search rerun or limit extension.
label_correction.json preserves the error and its scope. The producer now
classifies retained aborted entries only when actual completed_depth is below2.

## Semantics and provenance limits

Search keys include rule fingerprint, exact Position identity, repetition
snapshot, ply and eligible exact history context. A retained TT entry is written
only after its node reaches a normal return or valid bound cutoff; interruption
unwinds that node before its store, while already completed descendants retain
their entries. This source explanation matches observed retained work.

A probe hit by itself does not establish TT soundness in all rules. The finite
warm/cold score checks cover only four exposed Chess roots under material/q0;
they do not cover Shogi continuous check, generic action-history adjudication,
q4, changed evaluator, deeper horizon or all TT collision cases. The existing
player clears TT for changed q-depth semantics; current source intentionally
allows sufficient/deeper cached horizon reuse, so requested depth is not a
universal cold exact-horizon guarantee. No product, defaults or UI changed.

Use reuse_audit.py with own supported runtime. Fixed original source hash,
public decisions, full non-time stats, store summaries, actual cancellation
and probe-match metadata are in reuse.json. Raw key objects stay only in process
memory and were not published. Declaration was made before the run. Actual
timing-slot coordination and raw Slack receipts remain ignored local records.
