"""Build readable reports only from closed audited experiments; no selection."""
from pathlib import Path
import json
O=Path('results/dev_aux');D=O/'task2536'
def load(p):return json.loads(Path(p).read_text())
def fmt(v):return '['+', '.join(f'{x:.6f}'for x in v)+']'
def run():
 tr=load(O/'task2534/result.json');ev=load(O/'task2535/result.json');ta=load(D/'training-audit.json');a=load(D/'evaluation-audit.json');diag=load(D/'diagnostics.json');root=load(D/'roots.json');res=load(D/'resources.json');pilot=load(O/'task2538/result.json');pa=load(O/'task2538/audit.json');sv=load(D/'search-verification.json');assert a['status'].startswith('PASS')and ta['status'].startswith('PASS')
 table='| Opponent | Contrast | Actual W-L gain bounds | Descriptive envelope |\n|---|---|---:|---:|\n'+''.join(f"| {x['foe']} | {x['treatment']} minus {x['base']} | {fmt(x['bounds'])} | {fmt(x['descriptive_95'])} |\n"for x in a['contrasts'])
 perrule='| Opponent | Contrast | Rule | Gain bounds |\n|---|---|---|---:|\n'+''.join(f"| {x['foe']} | {x['treatment']} minus {x['base']} | {r['rule']} | {fmt(r['bounds'])} |\n"for x in a['contrasts']for r in x['per_rule'])
 pp=[m for m in diag['models']if m['method']=='free6'];pmin=min(m['P_min']for m in pp);pmax=max(m['P_max']for m in pp);cross=sum(m['P_sign_crossings']for m in pp)
 direct=[x for x in a['contrasts']if x['treatment']=='free6'and x['base']=='fixed5'];interpret=' '.join(x['foe']+': '+('positive finite-panel direct bounds'if x['bounds'][0]>0 else'negative finite-panel direct bounds'if x['bounds'][1]<0 else'no resolved direct advantage from censor bounds')+'.'for x in direct)
 text=f'''# Segment91: fixed anchor versus six learnable material coefficients

The paired study completed {tr['expected_arms']} training arms and {ev['actual']}/{ev['expected']} registered validation games. Actual rule outcomes remain the strength criterion. The table gives conservative bounds for unknown or missing outcomes, not rewards based on material counts. All initializations, rules, roles and both fixed opponents are retained.

{table}
{interpret}

The primary comparison is **free6 minus fixed5**, separately under each opponent. The grey/descriptive envelope resamples four rules, four initial seeds and eight family labels. It is a small-panel diagnostic, not a population confidence guarantee, an equivalence test or evidence for a universal algorithm winner. Per-seed and per-role contrasts, including adverse results, are in [the complete outcome audit](task2536/evaluation-audit.json).

## What changed

Both arms use the same NEW TRAIN prefix recipe141000+game, full initial vectors, selected-PV episode-frozen TD(.05,.95), raw material D2 search, path-seeded coefficient-independent ordering, tanh scale10 and200000 visited nodes per arm. Fixed5 holds arbitrary generated boardP at+1; free6 learns all six signed coefficients. GeneratedP is not a Chess pawn. There is no clipping, per-step normalization, solver intervention, material-quantity reward or best-model selection. This is a new paired experiment, not new free6 training compared with old90 results.

All {tr['nodes']:,} TRAIN nodes completed in {tr['seconds']:.3f}s: {tr['episodes']} episodes, {tr['actual_terminal']} actual terminals, {tr['unknown']} unknowns and {tr['nonzero_updates']} nonzero updates. Independent reverse-credit audit verified {ta['counts']['queries']} queries, all64 closed-episode checkpoints, full typed histories, {ta['counts']['valid_TD_terms']} valid TD errors and {ta['counts']['nonzero_TD_errors']} nonzero errors. All32 models were checked as16 matched first-episode pairs: same initial searches/actions/PVs/nodes/outcomes and same other-five updates, only the P mask differs.

The complete validation returned {ev['actual_terminal']} actual terminals, {ev['unknown']} unknowns and {ev['missing']} missing slots, using {ev['nodes']:,} nodes/{ev['seconds']:.3f}s. Prices and the full validation plan were hash-bound before any fitness query. The baseline is paid once per rule/initialization/family/role/opponent; both learned policies face the same fixed opponent configuration. The random99031 opponent was already specified in earlier work and is not claimed stronger or previously unseen.

## Price interpretation and data coverage

Across all free6 closed-episode trajectories P ranged from {pmin:.9f} to {pmax:.9f}, with {cross} sign crossings. Thus any observed free6 benefit cannot be attributed to entering negative-P directions. Releasing P also changes credit and amplitude dynamics at the common fixed tanh scale; scale10 is a parameterization, not validated probability calibration. Posthoc L2 directions are descriptive only and were never deployed or used to normalize training.

All16 fixed5 models have observed active-feature span5 and all16 free6 models span6, using actual nonzero PV gradients and exact rational feature elimination. Full observed span does not prove TD identifiability, unique prices or stable convergence. All raw trajectories, endpoint norms, inter-initialization dispersion and update magnitudes remain in [diagnostics](task2536/diagnostics.json). The four per-rule weight figures show every seed and both methods. See [actual-strength intervals](task2536/actual-strength.png) and [rule271001](task2536/weights-271001.png), [rule271002](task2536/weights-271002.png), [rule271003](task2536/weights-271003.png), [rule271004](task2536/weights-271004.png). Plotted segments are interval bounds, not imputed point rewards.

The32 new PRNG validation roots include {root['overlap_current_TRAIN']} roots also observed in current TRAIN and {root['already_terminal']} already-terminal roots; all were retained. New random draws are not a strict unseen-state guarantee. Older exposure was not excluded. These are four previously TRAIN-exposed generated4x4 rules with promotion, drops and full histories, not sparse endgames, unseen-rule transfer or the full auxiliary/custom-DSL rule domain.

A first H128-censored TRAIN record was publicly replayed:133 visited positions,125 distinct full-Position representations, maximum repeat count3 against declared repeat limit4 and rule maxply512. It correctly remained unknown. Position equality here omits Session history and is not a draw/cycle proof. No old game was continued or relabelled.

## Next method comparison: working interface, not a winner claim

The separately registered TRAIN-only candidate-decision pilot completed16 games,12 actual terminals and4 H64 unknowns, paying23094 nodes in6.722s. TD observed105 candidate searches and excluded105 opponent queries. Independent replay verified three actual black-candidate cases where the white opponent subsequently ended the game: TD received white-oriented z, WDL candidate utility received -z, and earlier eligibility retained its terminal credit. No extra learner search was made on opponent turns.

The paid P+0.25 proposal produced finite TRAIN bounds+1 on two rules,[-2,+2] on one and0 on one. Those proposals were not deployed. This diagnostic is neither a comparative learning experiment nor held-out strength evidence; physically reusing a baseline trace for arithmetic is not free compute in the next full comparison. Dot's reply1792231880 reviewed inline mathematics only, not91 code or execution.

The next main experiment is SAME-engine, SAME-total-node candidate-turn TD versus a predeclared signed-coordinate WDL proposal/strict-bound selector, with new TRAIN and validation streams. Both must pay opponent, baseline, candidate and incomplete-query work. A negative grid result would apply only to that proposal/step/selection regime, not terminal feedback generally. Generic WIN Prover/TC/API work is not a prerequisite.

## Verification, cost and reproducibility

Related38 tests passed. Independently unpruned D2 verified all{sv['verified']} registered receipts/{sv['nodes']} nodes, including minimax values, committed full typed children and PV-leaf witnesses. This is not a replay of every search or an external rules engine. Full actual-game/credit audits use the same rule authority with independent arithmetic and public Session transitions.

Main TRAIN+EVAL producer cost is {res['producer_nodes']:,} nodes/{res['producer_seconds']:.3f}s; the separate pilot adds23094 nodes/6.722s. Engineering, audits, tests, serialization, transport and tokens are not all captured by that sum. TRAIN per-query and per-arm wall seconds were not journaled, so no per-arm wall-speed claim follows. Ordinary concurrent projects are an interpretation limit, not a quiet-window or automatic rerun requirement.

[Exact capsule manifest](ARCHIVE_MANIFEST_20261017_91.json) and [raw journal routing](JOURNAL_ROUTES_20261017_91.json) preserve source/data byte pins. Large raw queries are public inside the ZIP. Previous35 capsules remain separate. The [fresh consumer](task2537/fresh.py) parks sealed derived files and recomputes38 controls plus11 audit outputs; its actual execution status is recorded separately in [fresh-receipt.json](task2537/fresh-receipt.json). Direct Git LF/EOF-only text projections and post-seal delivery records are separate from immutable ZIP bytes.

Science remains OPEN. No product/default/UI or learned-price Native evaluation activation, PRIMARY writes, sandbox/master push or automatic merge occurred. Official duration and final remote/anonymous-Public receipts are issued separately in DELIVERY_20261017_91.json; inclusion of a report alone does not establish delivery or partner reading/execution.

## All rule contrasts

{perrule}
'''
 (O/'SEGMENT_20261017_91.md').write_text(text,encoding='utf8')
 method='''# Segment91 method and fixed conditions

The learner uses six rule-conditioned current-board/base-hand count differences, always player0 minus player1. Royal anchors are excluded. Search uses raw theta dot phi; transformed TD predictions use tanh(raw/10). Actual rule-terminal search nodes use fixed +/-1000000 or0 and have zero selected-PV derivative. Earlier eligibility is retained. This is a scoped TDLeaf-style variant, not a literal Beal-Smith/TreeStrap reproduction.

Within an episode theta is frozen. For complete queries, g_i=(1-v_i^2)*phi(PV_i)/10, except terminal PV constants have g_i=0. Fixed5 also masks coordinateP. Eligibility e_i=.95e_(i-1)+g_i; delta_i=v_(i+1)-v_i, or actual white-oriented terminal z-v_last at a real ending. Apply .05*sum(delta_i*e_i) after the episode. For unknown endings omit only the invented final delta, retaining valid preceding differences. Failed queries supply no action, target or derivative, but all consumed nodes count.

The main study observes both players' selfplay searches with that same frozen theta. Plain complete full-width D2 Alpha-Beta has no qsearch, TT, SEE, human material ordering or selective pruning. Ordering is sha256(seed, full action path), coefficient independent. Incomplete queries never become shallow labels. New TRAIN and both methods share the prefix recipe, initial vectors, ordering seeds, query limits and200000-node arm budgets; all4x4 rule/initialization combinations remain.

For both arms, each query must restore exact state and record after search. Each played episode/game is publicly replayed. Independent audit advances every selected action through public submit, compares the complete typed record and replays each final record. This preserves base/current identity, hands, promotions, drops, auxiliary fields and relevant history in the runtime; learned features remain only the six declared counts. Current data scope is the four saved ordinary generated rules, not all auxiliary/custom-DSL rules.

Final1536-game validation has eight new family numbers, both roles, initial/fixed5/free6 and two fixed opponents. Initial is paid once per panel cell. All models and plan were bound before fitness. Unknown/missing reward is interval[-1,1], not0; paired gains subtract intervals. Rule/seed/family resampling is descriptive, not formal coverage or equivalence. No outcome-directed price/root/seed/checkpoint choice, H extension or old-cap reset is allowed.

Releasing arbitraryP is not merely changing units at fixed tanh scale10. No training/deployment normalization or positive clipping is used. Posthoc L2 direction and exact observed feature span are diagnostics, not unique-price or all-domain proofs. All source/configuration/budgets are in task2534/registration.json and task2535/plan.json.

The separate candidate-decision pilot uses a fixed opponent and observes only candidate searches under its own theta. Its gamma1/lambda.95 clock is per candidate decision, not the main halfply clock. TD stays in white coordinates; candidate-black WDL utility is -z. It pays both proposal/current games and opponent nodes. Shared-trace arithmetic in the pilot is not an equal-cost method comparison. See task2538/plan.json, result.json and audit.json.
'''
 (O/'METHOD_20261017_91.md').write_text(method,encoding='utf8')
 print('REPORTS_FROM_CLOSED_AUDITED_DATA',len(text))
if __name__=='__main__':run()
