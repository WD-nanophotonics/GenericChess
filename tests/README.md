# Test layers

Default `python -m pytest` collects only these directories:

- `product/`: Core, RuleSet, session, search, native, learning and UI behavior.
- `development/`: the current comparison entry, candidate helpers and recording.
- `workflow/`: local session, delivery and Slack stop/association behavior.
- `specification/`: retained native/semantic public contracts.

Shared fixture helpers remain at `tests/`; fixture data is in `tests/fixtures/`.
`pythonpath = ["tests"]` keeps their imports explicit after the directory move.
Historical corpus/results assertions and prototype experiments are not default
regressions. Original tests and fixtures are byte-preserved in the cleanup
snapshot; see `docs/archive/repository_cleanup_20261007/README.md` for isolated
recovery. Never restore historical workflow instructions as active policy.
