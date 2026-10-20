# AlphaBeta semantic-only default-profile contract — 2026-10-21

## Question and finding

Does the public `AlphaBetaPlayer` support semantic-only compiled rulesets with
no `evaluator_override`, as its class summary could imply? No. The built-in
rule-derived profile is deliberately narrower; semantic-only search is
supported when the caller supplies a compatible evaluator.

`require_default_profile_metadata` rejects a non-square default profile first,
then rejects a compiled object without legacy `piece_types` with the actionable
`ValueError`: `default evaluation requires legacy movement metadata; supply
evaluator_override for semantic-only search`. `AlphaBetaPlayer.__init__` calls
this guard before profile-cache lookup/build. A supplied evaluator bypasses
default-profile construction/cache access and owns evaluation semantics; the
existing Core search still receives the compiled ruleset and complete session
history. The semantic-only override route is already exercised by
`tests/product/test_no_progress_search_context.py`; its default-refusal test
also verifies rejection occurs before an injected profile cache is called.
`docs/research/UNFAMILIAR_RULE_SEARCH.md` and `docs/operations/BACKEND_HANDOFF.md`
describe the override boundary.

The source audit found one misleading phrase in the `AlphaBetaPlayer` class
docstring (“for any GenericChess RuleSet”). It now states the actual default
metadata requirement and explicit override path. No search behavior, profile
values, cache, API, expectations, or defaults changed. The focused existing
selection `python -m pytest -q -p no:cacheprovider
tests/product/test_no_progress_search_context.py -k semantic_only` passed all
three selected cases.

## Scope

This is a caller-contract clarification, not a semantic-only price model or
complete-domain capability claim. The override path establishes search
execution support only; the caller remains responsible for meaningful and
finite evaluation. The current generator's lack of semantic-only action/aux
emission is a separate coverage boundary and cannot be resolved by adding more
seeds to that generator. No adapter/model work follows without a concrete
consumer and a decision-changing evidence need.
