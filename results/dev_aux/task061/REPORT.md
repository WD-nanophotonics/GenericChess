# Task061: fixed-node opportunity cost of full-q4 refresh

The protected full-q4 `clear` prototype can displace completed main depth. In72 predeclared calls on two already public Chess roots, 10/36 paired node-budget cells lose one completed layer: one cold promotion cell and nine identical-warm-TT cells. This does not contradict primary's scoped no-loss observation on104 cold/time-limited calls at bebe3d98. No default/UI change or new unfamiliar-root cohort was made.

|Root / lineage|Node caps with layer loss|Baseline → refresh|Action difference at these caps|
|---|---|---|---|
|ChessEP / cold|none|same depth|—|
|ChessEP / same baselineD2 TT|128,256,512,1024|D2 → D1|none|
|ChessEP / same baselineD2 TT|8192|D3 → D2|none|
|Promotion / cold|1024|D2 → D1|none;score439 remains439|
|Promotion / same baselineD2 TT|128,256,512,1024|D2 → D1|none;score439 remains439|

Every cell used the same predeclared node cap, maxD4, configuredq4/hard8 and60s safety guard. All calls ended by node/depth; none was censored by time. Caps were128 through32768, fixed before execution. Baseline and refresh share the frozen weighted evaluator and Native-legality/Core-transition backend. Actual Native calls are positive and fallback/failure0 in all rows. Complete Runtime position/identity/hash/history/occurrence/alias snapshots and pushes/pops restore. Nodes+qnodes reach the exact cap on node-limit returns. Ordinary simultaneous projects were allowed; wall is descriptive and not an equal-time comparison.

The 265-file fixed-source export and two additional dependencies verify byte-for-byte against bebe3d98. Native SHA2f97cfb8 identifies the installed runtime, not its C-build source. Initial root construction lacked an exact research-data dependency and failed before searches; the original failure and exact source restoration are retained. No formula/profile was substituted.

Warm lineage was acquired once per root through baselineD2: ChessEP1505visits/32TT entries and promotion667visits/8entries. Both arms receive independent clones of identical keys, entries, scores/bounds/actions and generation. The seed never mutates; whole-table input hashes join exactly. Clone keys are shared immutable search identities, entry objects are copied. Setup and prewarm are excluded from the measured caller counts, but their two actual calls are recorded. The72 callers use488983visits and283.595s recorded wall; whole batch288.425s. Engineering/record-audit overhead is additional.

These are selective TT iteration labels, not fresh uniform-horizon value certificates. With the existing default require_full_pv=false, cached EXACT sufficient-depth entries can return an empty PV. The128-node warm reserve is labeled ordinaryq0 while its score came from a configured-q4 depth2 cached entry. q provenance describes the iteration policy, not the origin of every cache value. Nine warm layer losses therefore also expose discarded cache reuse; they do not prove worse fresh search values. The cold promotion loss is not a warm-cache artifact, but its action/score remain unchanged. No loss cell demonstrates worse decisions or strength.

Task062 separately began after this batch and tests the clearing/scheduling mechanism, without extending these frozen caps. `validate_q4_node_records.py` reproduces complete pair, cap, route, restoration and seed joins. No outcome-driven extra budget, unchanged repeat or label access occurred.
