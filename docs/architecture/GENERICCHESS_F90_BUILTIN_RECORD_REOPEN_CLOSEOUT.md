# GenericChess F90 built-in record reopen

## Result

Production built-in records now reopen by canonical ruleset fingerprint. The
catalog resolver rebuilds each known built-in through the production builder
and `compile_ruleset_for_execution()`, returning a match only for the exact
compiled fingerprint. Unknown fingerprints never guess or resolve.

`UIController.open_record()` deserializes first, preserves the existing loaded
ruleset when its fingerprint matches, and otherwise resolves only a known
production built-in before replaying. The ruleset, compiled runtime, session,
history, and view state are switched only after successful replay. Unknown or
custom fingerprints fail closed without mutating the live game; custom
records retain the existing requirement that the matching RuleSet be loaded
first.

The bounded acceptance saves two production semantic actions from each built-in,
switches to the other built-in, reopens the record, and verifies exact action
history, final semantic state, side-to-move, position identity, and
`BoardViewModel`/rendered occupancy. It also verifies the unknown-fingerprint
failure path and state preservation.

## Verification

```text
.venv\\Scripts\\python.exe -m pytest -q tests/test_f90_builtin_record_reopen.py
```

The three F90 cases passed. No GameRecord schema change, Arena, training,
evaluator/search change, external engine, Heavy job, or F87A/F88/F89
requalification was run.
