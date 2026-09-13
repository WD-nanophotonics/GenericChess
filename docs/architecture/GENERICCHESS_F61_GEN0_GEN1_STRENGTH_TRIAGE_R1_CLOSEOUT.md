# F61 Gen0 to Gen1 strength triage R1 corrective closeout

## Immutable fix

- Sandbox commit: `49e44efa839bcadafbb8489bb7c1191f682d0ea1`
- Corrected driver: `scripts/f61_gen0_gen1_strength_triage.py`
- Regression: `tests/test_f61_gen0_gen1_strength_triage.py`
- Generated fixture: `gen_classic_like_4_101`

The generated arm now lowers the existing generator-produced `CompiledRuleSet`
through `lower_legacy_to_ir` into `CompiledSemanticRuleset`, preserving the
fixture's real ruleset fingerprint and using the same native semantic search,
F61 PAIRWISE_RANKING fitter, and equal-budget Arena path as Chess and Shogi.
It does not substitute a hand-written semantic fixture.

## Verification and boundary

The regression independently constructs generated D0 smoke roots, fits one
width-32 child with seed `59012`, and completes a two-pair role-swapped Arena;
the full focused publish set passed 22 tests. No full training seed or
multi-ruleset compute was started. The next permitted action is the already
specified first-seed mainline experiment: Shogi first, Chess second, generated
third only when Shogi is not directionally negative.
