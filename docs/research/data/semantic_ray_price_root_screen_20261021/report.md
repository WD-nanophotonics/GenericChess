# Semantic-ray static board-price action and outcome screens — 2026-10-21

## Root action sensitivity

The frozen 8-root depth-1/q0 screen in data/semantic_ray_price_root_screen_20261021/plan.json completed on all eight accepted synthetic three-rank RuleSets. Static-v2 board prices changed the selected root action in 5/8 compared with Unit board prices, with hand prices, promotion gains, evaluation config and search limits held fixed. All actions were legal, caller state/history remained unchanged, and node counts matched. No root-selected action was a semantic-ray move: the changed choices were legacy actions. This establishes sensitivity of the existing broad board-price profile on these rules, not ray-action valuation or utility.

## Bounded outcome follow-up

Because the action changed on five fixed roots, a separate outcome panel was preregistered before its run in data/semantic_ray_price_root_screen_20261021/outcome_plan.json. It used the same eight RuleSets, one static-v2 board-only candidate against one fixed Unit opponent, and two games per RuleSet with candidate colors swapped. Hand and promotion channels remained Unit; AlphaBeta D2 used a 20,000-node per-move ceiling, q0, no TT/order/native legality/root tactical scan, and a 48-ply game horizon. No training or default change was allowed.

The exact 16-game output and every move event are preserved in outcome_result.json. Fourteen games resolved (9 candidate wins, 5 losses); two remained UNKNOWN at the 48-ply cap. No game failed, and all 371 searched moves completed D2 without fallback. Resolved score was 0.643, but outcomes were strongly color-asymmetric: as color 0 the candidate scored 7 wins/1 loss; as color 1 it scored 2 wins/4 losses with two further UNKNOWN. The predeclared follow-up gate required all slots to resolve, so it failed. The panel is exploratory and too small to estimate general strength.

The semantic ray itself was rarely used: the candidate selected it once across the panel, while the fixed Unit opponents selected it three times. Candidate and opponent move-node medians were 346 and 479 respectively, but these descriptive totals neither repair the UNKNOWN slots nor establish a fair strength/cost advantage. The intervention changed board prices across the complete roster, not only the type carrying the new ray; most observed outcomes cannot be attributed to that ray.

The run required two harness corrections before any game was played: RuleSet is a project dataclass, so identity uses the compiled ruleset_fingerprint; the player map must retain the actor label alongside its AlphaBetaPlayer. The exact failed-attempt diagnostics are retained privately in ignored .local_agent. Neither correction changed the fixed rules, seeds, profiles, gates or search settings.

## Decision and limits

Close this sampled ray-profile outcome screen. Do not repeat these seeds, extend the horizon, change evaluator/defaults, or claim ray-price utility. The only supported conclusions are that the broad static-v2 board profile can alter some D1 actions on this fixed synthetic cohort, and this small color-swapped outcome panel did not satisfy its all-slots-resolved follow-up gate. Future work should select a distinct current unfamiliar-rule search contract and state its exact caller and budget.