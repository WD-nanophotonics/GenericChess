# Semantic promotion search-result closure

The prior many-target Native semantic test verified legality/child parity for
9 and 62 promotion targets, but did not ask AlphaBeta to select a target beyond
the legacy eight-entry boundary. A new nine-target fixture directs a fixed
child evaluator to `T08`; default AlphaBeta selects that exact
`SemanticBoardMove` with the target at the PV head, submits it, and round-trips
the complete record/state/result. The optional Native semantic legality
provider is active. `tests/product/test_native_semantic_many_promotions.py`
passes 5 tests.

The mixed F24C fixture also now searches for its opaque `A0→A1` semantic
promotion before the capture-to-hand/drop continuation, then searches for the
generated semantic drop with Native legality enabled and checks parity against
Core-only legality. The scoped mixed fixture passes. These checks establish
selected-action wiring for one ninth target and one mixed mechanism, not all 62
targets, all promotion/capture combinations, or Native iterative-search
coverage.
