# ADR-030 — Native `action_delivers_check` Capability Closure

## Decision

Support semantic postcondition code `action_delivers_check = 2` in the Native semantic compiler and runtime while retaining `opponent_checked = 0` and `no_legal_reply = 1`. The frozen versions remain IR `2`, semantic payload `2`, and native schema `native-0.5.0`.

## Semantics

The Python authority asks whether the action's own actor, now at `action.target`, attacks the reply side's anchor. Native follows the same canonical pattern/geometry order and evaluates exact path, state-guard, and slot-guard predicates on the child. A child being checked is insufficient: the check can be discovered or supplied by an unrelated friendly piece, while the moved actor itself remains non-checking.

The helper is private to the Native runtime make path. A private debug-only entrypoint exists solely for direct certification and is not exposed through `generic_chess/native/semantic.py` as a production semantic attack API.

## S4 and fail-closed behavior

S4 remains a forbidden-condition conjunction: a candidate is rejected only when every present postcondition is true. Unknown postcondition codes, malformed payloads, wrong fingerprints, invalid actions, and inexact-history restrictions continue to fail closed.

## Certification result

Before H13B, the certified Standard Shogi fingerprint `5b3d04eda31a342b729fc9af8a04cdde13c796646b2b37024891f8c99703c345` was not native-executable because code `action_delivers_check` was unsupported. After H13B it compiles as native-executable, and Python/Native differential certification passes for four frozen prefixes plus checking-drop/uchifuzume controls and the existing ten-case corpus.

No public semantic attack/check API, production search migration, evaluator, cache, version, payload structure, or fingerprint change is authorized by F13. Full Native search readiness remains deferred.
