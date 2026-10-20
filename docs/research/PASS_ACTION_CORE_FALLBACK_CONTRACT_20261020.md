# Pass-action fallback at the default AlphaBeta caller

## Question

When a semantic RuleSet enables coordinate-free `PassAction`, does the default
AlphaBeta caller preserve a usable search path even though the optional Native
semantic legality provider cannot encode that action?

## Evidence and result

`generic_chess/native/compiler.py` explicitly rejects pass-enabled rules during
Native compilation. `NativeSemanticLegalityProvider.try_create` treats that
unsupported compilation as provider unavailability; `AlphaBetaPlayer` then
keeps the Core legality/action path. The public generated-semantic regression
`test_public_alphabeta_root_selects_pass_and_generated_semantic_action` now
asserts both that Native legality was requested by the default player and that
the provider is absent for this fixture, before checking selection, legal
membership, PV identity, submission and serialized replay of `PassAction`.
The separate `PythonSearchBackend`/`SearchSnapshot` adapter regression also
returns the same pass action and PV without mutating the snapshotted session.
The UI completion source passes `decision.action` to the controller's generic
`submit_action(Action)` boundary, which directly calls `GameSession.submit`; no
action-kind filter appears there.

Focused validation: `python -m pytest tests/product/test_generic_pass_action.py
-q` — 17 passed; together with `tests/product/test_search_tuning.py`, 23 passed.
No runtime implementation or backend-selection behavior changed.

## Scope

This closes the tested default-AlphaBeta caller contract for the existing
pass-enabled semantic fixture. It does not make the experimental
`NativeSearchEngine` accept pass actions, establish all-domain support, or claim
that arbitrary provider construction errors should be silently ignored.
