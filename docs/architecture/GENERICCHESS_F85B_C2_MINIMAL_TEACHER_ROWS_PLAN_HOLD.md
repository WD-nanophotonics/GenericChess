# GenericChess F85B minimal teacher rows plan hold

Status: `C2_MINIMAL_TEACHER_ROWS_PLAN_HOLD`.

The F85B minimal phase-resumable path is published at sandbox
`48b88b1b50a9e9d3d60e33011583e45d1a8c19fb`. Focused smoke equivalence tests
passed: the new path reproduces F59's selected action order, q1k values,
features, base-Q values, and q20 values while omitting only root40k,
duplicate observer2k, and selected q10k diagnostics. The minimal manifest is
`artifacts/f85_c2_train_teacher_evidence/minimal_train_manifest.json`, content
SHA `de9f6419e48bf4ce5e804cef070d9a9aaf36007996b135d85129e40e7600fa2e`,
with declared total ceiling `9,954,000` nodes.

The immutable v10 compute plan bound to that checkpoint was submitted through
Chat: plan SHA `23e5613aa7a60dd5850bf24bfe905aef51a45486d6abb17a4c0b191d6aba0253`,
envelope SHA `ae72febb48626be7c0fc6d70e3f96b2287ae1f85d921a7ccae6e9d4723487053`.
Chat returned `GENERICCHESS_COMPUTE_PLAN_APPROVAL=HOLD`; no Heavy, teacher
acquisition, C2 fit, or Arena work was launched. Further execution requires a
new explicit scientific route and approval.
