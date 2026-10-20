# Generated-search repeat signature for declarations — 2026-10-20

## Question and finding

Does `scripts.unfamiliar_search.run_rule` measure whether repeated searches made
the same full root choice when a supported supplied ruleset can select a
declaration instead of an `Action`?

The ruleset runner accepts declarative `RuleSet` input and records the complete
`PlayerDecision`. Its `repeat_equal` summary previously compared only
`(action, score, completed_depth)`. On a declaration-capable root, `action` is
`None`; two distinct declaration IDs with the same outcome, score and depth
could therefore be summarized as equal. The per-run records retained the
declaration, so the defect was confined to the repeated-choice summary, not
lost raw results or search behavior.

An actual supplied-rule probe using the existing `opaque_claim` fixture returned
`choice_kind=DECLARATION`, `action=None`, declaration `opaque_claim/WIN`, and
`result_source=root_declaration` in both search controls. The exact probe output
is privately retained at `.local_agent/unfamiliar-declaration-probe.json`; it is
ignored by Git. This was a supplied semantic ruleset; today's generator does
not create declarations in its emitted `RuleSet`, so the probe is a product
boundary case rather than a generated-cohort observation. All four search
calls selected the same declaration before searching actions; this yields no
same-rule price/action outcome contrast. A focused aggregation regression
alternates two real `DeclarationAssessment` values with the same score/depth
and confirms that the summary distinguishes them.

## Change and validation

The signature now includes `choice_kind`, serialized `action`, serialized full
declaration assessment, score, and completed depth. No product search, session,
rules, price, evaluator, budget, training or historical result changed.

`tests/development/test_unfamiliar_search.py`: 11 passed using a new
Git-ignored project-local `--basetemp`. The initial default temporary-directory
setup was denied by the sandbox; the documented ignored project-local temp
path resolved it without changing OS permissions. Pytest cache was disabled.

## Limits and consequence

The probe verifies the existing declaration-capable supplied-rule caller path,
not a declaration emitted by the current generator, real nondeterminism or a
search-policy defect. The alternating regression validates
the summary's sensitivity to a changed declaration; it does not claim that the
engine selected different declarations on the same root. Existing published
search conclusions and frozen experiments remain unchanged. No backend/API,
search-policy, price or default choice follows. Future repeat summaries now
compare the full root decision before being used as a parity gate.
