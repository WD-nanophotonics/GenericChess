# Preserve pass identity in recorded search results — 2026-10-20

## Observed contract gap

The complete public `Action` union is `BoardMove`, `DropMove`,
`SemanticBoardMove`, `SemanticDropMove`, and `PassAction`. Existing caller tests
select/submit/replay each form, including generated pass, compound castling
through a semantic board move, and the mixed semantic promotion/capture/drop
path. A separate current-source audit found no supported per-root-action score
field on `PlayerDecision`; that qfrontier diagnostic remains unsupported and
does not justify a new result API.

While auditing the search-result evidence consumer, a direct probe showed
`record_value(PassAction()) == {}` although canonical `action_to_dict` returns
`{"kind":"pass"}`. More importantly, `record_value(PlayerDecision(...))`
called `dataclasses.asdict` first, recursively reducing the action and PV pass
to empty objects before a nested special case could run. Generic search
research records therefore lost the selected action identity for pass-enabled
results.

## Narrow repair and validation

`record_value` now handles `PassAction` through `action_to_dict` and traverses
other dataclasses with `dataclasses.fields`, recursively converting original
field values instead of erasing nested action types with `asdict`. The recorded
pass is `{"kind":"pass"}`; the regression uses an actual `PlayerDecision` and
checks both its action and PV. A control asserts that the prior `BoardMove`
record shape stays unchanged. An in-memory shape check confirms all five
`Action` variants remain distinguishable.

The research-record module plus product pass, consecutive-action, F24C mixed
mechanic, and recombined semantic-lifecycle modules pass using a unique ignored
project-local pytest basetemp. The default Windows temp root denied access;
using `.local_agent/pytest-pass-record-20261020-0017` allowed the exact focused
suite without changing tests or user data. The second verification run after
the final nested-dataclass correction also passed. No existing archives were
rewritten, and other action record shapes are unchanged.

This fixes evidence identity only. It changes no search behavior, result API,
price, training route, or scientific claim.
