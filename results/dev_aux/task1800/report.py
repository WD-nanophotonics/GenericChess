"""Render concise evidence-first segment report after actual audits close."""
import json
from pathlib import Path
R=Path("results/dev_aux")
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def contrast(task,name,role="BALANCED",op="MIXED"):
    r=read(R/f"task{task}/role_report.json")
    return next(x for x in r["DEV_contrasts"] if x["contrast"]==name and x["role"]==role and x["opponent"]==op)
cost=read(R/"COST_20261015_56.json");meta=read(R/"task1800/balanced_meta.json")
old=[]
for task in (1788,1791,1792):
    s=read(R/f"task{task}/selection.json");g=contrast(task,"price_with_solver");d=read(R/f"task{task}/role_diagnostic.json")
    old.append(f"|{task}|{list(s['integer_scores'].values())}|{s['selected'][0]/720:g}|{g['event_delta']:.7f}|{g['family95']}|{d['flat_families']}/{d['TRAIN_families']}|")
new=[]
for task,label in ((1797,"standard"),(1798,"two-sided conflict")):
    a=contrast(task,"candidate_solver_policy");b=contrast(task,"price_with_solver");d=read(R/f"task{task}/role_diagnostic.json");s=read(R/f"task{task}/selection.json")
    new.append(f"|{task} {label}|{list(s['integer_scores'].values())}|{a['event_delta']:.5f} {a['family95']}|{b['event_delta']:.5f} {b['family95']}|{d['actual_result_density']['nonflat_family_vectors']}/{d['TRAIN_families']}|{d['actual_result_density']['full_paid_study_seconds']:.2f}s|")
pooled=next(x for x in meta["contrasts"] if x["key"]==str(("BALANCED","MIXED","price_with_solver")))
text=f"""# DEV_AUX segment56 â€” balanced price learning and fixed-opponent correction

Science remains **OPEN**. Own90-minute patrol is restored ACTIVE by explicit user request. Independent checkout/`sidemission` only; no primary/Core/product/default/UI edits, new Agents or workers. Base `c299879d863eb53119b9eb732b3c4f03fbdbfa9d`. Actual session duration/end reason are in `SESSION_20261015_56.json`.

## What changed

The learner now has an explicit, fixed `candidate_side`, independently of who initially moves. All TRAIN and DEV families include both candidate roles, colors and unit64/unit4096 opponents with equal predeclared weights. Candidate prices and budgets follow that identity on every move. Full public history and turn are unchanged. Every actual Native price/ACK/budget, public action, terminal winner and role-specific reward is replayed independently.

A scientific interpretation error was diagnosed and corrected: legacy A-to-B enabled the proof/tail policy for BOTH players. The segment55 description does not isolate candidate solver contribution against a fixed opponent. Its numeric joint-policy contrast and raw records are retained; B-to-D still compares prices against the same opponent and remains valid. New1796/1797/1798 explicitly fix `opponent_proof=True` in all four cells. Candidate A/C are plain, B/D proof-equipped; A/B baseline prices, C/D TRAIN-selected prices. Opponent proofs and physical tails are counted even with a plain candidate. No old reward, cap or missing slot was relabeled.

## Balanced learning

Modified material-only Fairy-Stockfish, NNUEoff/one thread/cold policy; aligned leaf/native/capture prices. Closed4x4 KRN game, R360/720/1440 with N720, candidate4096, opponent64/4096, .25second step. H16 plus only an ALREADY verified rank<=64 certificate may physically finish; no new proof afterH16, no quantity reward or theoretical-win adjudication. UNKNOWN remains distinct. This is a finite actual W-L-event objective, not infinite win probability.

1791/1792 were jointly frozen before either result and before the pilot's DEV sign was known; both ran regardless sign. Their exact original loaded sources remain archived separately from the later fixed-opponent repair. Each large cohort has independent TRAIN32/DEV32 families; the pilot has8/8. Selection is TRAIN-only on the three-point grid with lex ties; coordinate paths share those actual grid games, not independent online training runs.

|Study|TRAIN net scores, low/unit/high R|Selected R/N|DEV B-to-D net event gain|Conditional family95|Flat TRAIN families|
|---|---|---|---|---|---|
{chr(10).join(old)}

Across the two large cohorts, conditional stratified family gain is **{pooled['event_delta']:.7f}**, interval **{pooled['family95']}**. Resampling keeps roles/colors/opponents paired and stratifies by cohort, conditional on each frozen TRAIN choice. It does not cover arbitrary retraining, opponent distributions, continuous optimum or full human price recovery. Opponent/role strata remain exploratory; cancellation is preserved without changing weights. See each role report and full planned finite/infinite-outcome bounds.

Actual outcome decomposition also matters: over512 paired DEV games, B has142wins/72losses/160draws/138unknowns, D has155wins/58losses/156draws/143unknowns. Win-only event gain is13/512=.025390625, conditional family95[.001953125,.048828125]. Twelve losses becomeUNKNOWN and four wins becomeUNKNOWN; those are displayed explicitly, not treated as proven infinite-WDL improvements. Next guarded1803 freezes16fresh families for H16/H24 fixed-hybrid price comparisons,512max actual games,0go; it is not yet implemented or executed and never extends oldcaps.

## Truly fixed opponent and information per cost

1796 is an8game actual mapping/entry check on a TRAIN root, not learning. New1797/1798 are jointly frozen8TRAIN/8DEV pilots. The latter reuses the exact guarded1794 inputs: both possible turns valid/uncheck,>=4legal choices, capture+quiet+checking option, no immediately terminal successor. Root generation never reads prices or WDL. The tactical filter changes the conditional distribution and may favor particular capabilities; it cannot establish universal or standard-Chess values.

|Study/root law|TRAIN scores|Candidate solver A-to-B gain/95|Price B-to-D gain/95|Nonflat TRAIN objective vectors|Whole paid study wall|
|---|---|---|---|---|---|
{chr(10).join(new)}

In these small pilots the richer filter does not improve the paid TRAIN information diagnostic:2/8nonflat vectors versus4/8standard at similar286/294second cost. Its greater terminal coverage is not sufficient grounds to adopt it; independent DEV price gain is still uncertain. Both candidate-solver A-to-B net effects are zero in these samples, so no added-strength claim follows from this corrected ablation.

Only actual paired price-result vectors and their full measured cost inform the next choice. More terminal games or changed moves alone are not learning signal. Dot supplied that concrete counterexample/control; adopted. Neither8-family pilot alone establishes stable direction. No pooling across the two different root laws or DEV-based root/price selection is done. Their TRAIN diagnostics preserve opposite-role cancellation.

## Generic proof and cost engineering

Separate opt-in immutable-public-state AND/OR proof and independent public verifier now handle authoritative no-progress history that the mutable runtime declines. `PublicStrategyCursor` executes the verified finite tree; the player accepts an explicit matching `cursor_factory`. A wrong unsupported verifier fails closed and continues the normal player. **96 focused tests pass**, including actual multi-step physical completion without evaluating material, drops, promotion, pass, history/aux binding, cancellation and same-board/sameply histories with different real no-progress outcomes. Declarations remain session-level unsupported choices; no full generated-domain completion claim.

72 declared no-progress finite maxply4 games give144target calls,18402reference visits:7proofs independently verify and physically win, no false win. The public oracle validates solver logic against Core rules, not an independent rule implementation. On96paired supported-rule calls, work and certificate trees match, but public execution costs1.62â€“1.67x runtime; it remains an optional unsupported-history fallback. Atomic public transitions/history replay can overrun cooperative deadlines; actual elapsed is charged.

A separate300pair caller attribution kept all legal-set checks and replayed only the chosen child. Microcost ratio0.309 saves only0.49ms/callback on60paid full-history states; no whole-game gain is established. Defer that optimization instead of spending another game batch on it. The initial64state assertion failure and its actual-denominator successor are preserved. No current wrapper/default was changed.

## Actual cost, failures and delivery

{cost['actual_episode_records']}actual episode records, {cost['actual_new_native_go']}new Nativego, {cost['actual_native_perft']}Nativeperft. {cost['adopted_proof_games_physically_redeemed']}adopted proof games physically reach the certified win; {cost['admitted_tails_physically_won']}tails use{cost['physical_tail_moves']}extra moves/{cost['physical_tail_native_go']}go. Every planned DEV slot is present; no early incomplete TRAIN selection or unassigned Native receipt. Overshoots remain in actual node counts. Study walls are not summed CPU/Agent duration; ordinary concurrent work and timed proof/residual-node variation remain limitations.1791 has two same-budget baseline path differences, UNKNOWN versus repetitiondraw, both zero finite W-L event; no automatic rerun or deterministic-noise-free claim.

Known qualifier timing prose is preserved/corrected additively; future calls explicitly record BEFORE_STUDY. Failed hand-written test moves, syntax/assertion errors and live-tail inspection race are documented, not hidden as scientific success. `FAILURES/COST/QA_20261015_56.json` bind details and source hashes. All prior stops/caps, including532 and guarded1787/1794 plans, remain intact; executable successors use exact parent hashes.

Dot read this request/protocol and prior Slack summary; its attempted fixed55 report read returned404. It did not execute56 or independently verify unpublished code. Raw exact Slack/account originals remain ignored/private; reviewed project-only summaries and evidence are delivered under the continuing2026-10-15 grant. PRIMARY's lane remains read-only, no integration or publication on its behalf. Exact executed sources, checked project evidence and independent SHA restoration are indexed in `ARCHIVE_MANIFEST_20261015_56.json`.
"""
(R/"SEGMENT_20261015_56.md").write_text(text,encoding="utf-8")
print("Report built",len(text.encode("utf-8")))
