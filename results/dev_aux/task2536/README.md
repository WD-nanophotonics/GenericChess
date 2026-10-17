# Paired anchor-release audit

This is a new learning experiment, not a rescore of segment90. The fixed5 and free6 arms share new training-prefix recipes, all four initial vectors, rule-conditioned features, path-seeded search ordering, episode-frozen TD(.05,.95), tanh scale10, H128 and200000 visited nodes per arm. The first coordinate is an arbitrary generated board type P, not a Chess pawn. All six coordinates are signed in free6; fixed5 retains P=+1. No normalization or positive clipping is applied during learning or play.

The direct endpoint contrast free6 minus fixed5 is primary, separately under each fixed opponent. Both learned-minus-initial contrasts remain visible. The shared initial baseline is paid once per initial/rule/family/role/opponent. New family numbers are new random draws, not a claim that every resulting full state is unseen. Rules were already exposed in earlier training. Every unknown or missing reward has interval[-1,1]; it is never silently replaced by a draw. Report all seeds, roles and rules. The descriptive crossed rule/seed/family envelope is not a population confidence guarantee.

Releasing P changes both the admissible model class and credit/amplitude dynamics at the common tanh scale. It is not a pure choice of units. Improvement with P remaining positive would not show that negative-P directions caused the improvement. Numerical convergence, L2-direction agreement, finite-board strength and universal rule-derived prices are distinct claims.

The old producer replayed the full prefix before and after each query. Both new arms instead retain exact push/pop state+record equality per query and a complete public replay per closed episode/game. Independent audit advances each actual transition with public submit, compares every complete typed record, then replays each final record. This reduces repeated verification work; it does not change training search, terminal authority, features, credit or budgets. Timing is descriptive under ordinary concurrent load, not a controlled speedup claim.

Run after the sole producer closes:

```
python -m results.dev_aux.task2536.training_audit
python -m results.dev_aux.task2536.search_verification
python -m results.dev_aux.task2536.diagnostics
python -m results.dev_aux.task2535.evaluate
python -m results.dev_aux.task2536.evaluation_audit
```

All source paths are repository relative. The complete runtime preserves typed promotion/drop actions and full GameSession state/history. This is scoped to four saved ordinary generated4x4 rules, not the full arbitrary auxiliary/custom-DSL domain. Fixed query limits, total caps, censored records and failures are retained. No main product, defaults, UI, Core or PRIMARY state changes follow automatically.
