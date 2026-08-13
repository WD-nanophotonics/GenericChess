# F13 Evidence — Native `action_delivers_check`

F13 closes the one recorded native semantic capability gap for the certified Standard Shogi ruleset. H13A recorded fail-closed rejection of postcondition code `action_delivers_check`; H13B adds the frozen numeric code `2`, native parsing, and an operation-local actor-witness evaluator. E13 certifies the result without changing IR version 2, semantic payload version 2, native schema `native-0.5.0`, action layout, fingerprints, position keys, or production search.

The witness is deliberately narrower than generic child check: after make, the actor at `action.target` must itself attack the reply side's anchor through canonical target-enemy patterns, geometry, path predicates, state guards, and slot guards. It uses no S3 recursion and no S4 recursion. The direct Standard Shogi checking-drop witness and a non-checking drop both match Python exactly.

Evidence files are in `artifacts/f13_native_action_delivers_check/`. The four frozen Standard Shogi prefixes have exact candidate and guarded action identity/order parity; make/unmake, terminal/history, checking-drop, existing native corpus, focused tests, full pytest, and fresh Native build all pass. `FULL_NATIVE_SEARCH_READY` remains `false`: F13 closes capability certification only and does not migrate production search.

H13A commit: `d265c16`. H13B commit: `7314a60`. E13 evidence is finalized in the subsequent commit.
