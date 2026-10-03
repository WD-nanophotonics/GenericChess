# Frozen label implementation and input binding

The gate, formulas and costs were declared before generation in
`JOINT_CAPABILITY_CORPUS_PROTOCOL.md`; no criterion change here.
Bind the complete corpus SHA256
f7b027f681cb033b3f93cecc7ad4d49c153f11b6308c9cc5d5723c5c4cf41332.
Replay each deployment capture by public apply_action and require exact full
state_evidence equality; never reconstruct children by board-only reset.
Reference synthetic states also require exact evidence equality.

Compute all eight reference labels first with the existing complete actual
actor enumerator. Serialize the reference evidence, raw fractions and constants
to a separate file BEFORE calling any deployment label enumerator; bind that
file's hash in the result. If a game has all-zero reference signal, report its
failed usability gate and skip its deployment labels, as the original corpus
protocol permits. Other games may continue. Neither skip nor empty reply is
zero-labelled data. Per-game signal/baseline risks and both 10% inequalities
must all hold to qualify. Preserve all labels on a finite failed gate; no tuning.
One shared 30-second/60,000-materialization budget includes compilation, public
capture replays, references and deployment. No timeout retry or budget growth.
