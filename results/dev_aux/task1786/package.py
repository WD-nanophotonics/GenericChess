# Build reviewed segment55 cost, quality, failures and report.
import json,hashlib
from pathlib import Path
R=Path('results/dev_aux')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def put(p,x):Path(p).write_text(json.dumps(x,indent=2),encoding='utf-8')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
ids=[1773,1775,1776,1780,1781,1783,1784];studies=[];proofs=tails=moves=tailgo=0
for task in ids:
 p=R/f'task{task}';r=read(p/'result.json');a=read(p/'audit.json');t=read(p/'tail_audit.json')
 assert r['status']=='COMPLETE' and a['status']=='PASS_PUBLIC_REPLAY_AND_RECEIPTS'
 assert a['games']==r['games'] and a['unassigned_native_receipts']==0 and a['early_unknown_before_H']==0
 assert not any(x['early_incomplete'] or x['missing_games'] for x in a['cells_DEV_only'].values())
 proofs+=a['proof_calls'];tails+=t['counts'].get('actual_tail_wins',0);moves+=t['counts'].get('tail_steps',0);tailgo+=t['counts'].get('tail_native_go',0)
 studies.append(dict(task=task,**{k:r[k] for k in ('status','games','actual_native_go','actual_native_reported_nodes','seconds')},plan_sha256=sha(p/'plan.json'),game_sha256=a['raw_games_sha256'],native_node_overruns=a['native_node_overruns'],step_time_overruns=a['step_time_overruns'],max_step_seconds=a['max_step_seconds']))
smoke=read(R/'task1778/game_smoke/result.json');protocol=read(R/'task1778/protocol_smoke.json')
assert smoke['status']=='COMPLETE' and protocol['status']=='PASS_ALL_PROFILES_SIZED_ACTUAL_PROTOCOL'
perft=sum(read(R/f'task{i}/native_qualification.json')['actual_perft'] for i in [1773,1775,1776,1778,1780,1781,1783])
cost=dict(segment=55,studies=studies,actual_new_native_go=sum(x['actual_native_go'] for x in studies)+smoke['actual_native_go']+protocol['actual_new_native_go'],actual_native_reported_nodes=sum(x['actual_native_reported_nodes'] for x in studies)+smoke['actual_native_reported_nodes']+protocol['actual_nodes'],actual_episode_records=sum(x['games'] for x in studies)+smoke['games'],actual_native_perft=perft,adopted_proof_games_physically_redeemed=proofs,admitted_tails_physically_won=tails,physical_tail_moves=moves,physical_tail_native_go=tailgo,entry_smoke=smoke,protocol_smoke_calls=protocol['actual_new_native_go'],retention=read(R/'task1777/result.json'),measurement_limits='Study times exclude module/driver construction before local start; include main qualification/engine setup/games. Not summed CPU or Agent duration. Generic visits and Native nodes differ; Native overshoots retained. Trigger per-game costs include public observe/transition. Concurrent load, sequential policy order and fixed absolute scale remain. No independent task token counter.')
put(R/'COST_20261015_55.json',cost)
subjects=['scripts/generic_win_proof.py','scripts/generic_win_proof_pn.py','scripts/generic_proof_player.py','scripts/generic_proof_tail.py','scripts/generic_proof_native_study.py','scripts/generic_proof_scaled_study.py','scripts/generic_proof_native_driver.py','scripts/generic_royal_actor.py','scripts/generic_win_proof_retained.py']
quality=dict(segment=55,focused_pytest_passed=77,test_observation='Observed complete nine-module pytest after fallback/trigger changes; two real unsupported-runtime regressions failed before repair and passed afterward.',subject_sha256={p:sha(p) for p in subjects},all_studies_closed=True,all_actual_game_public_replay_and_protocol_audits_passed=True,all_planned_DEV_slots_present=True,adopted_proof_games_physically_redeemed=proofs,all_admitted_tails_won=tails,unassigned_native_receipts=0,actual_native_perft=perft,semantic_scope='Closed KRN4/5 learning; independent actor/public tests4/5/8; existing history/promotion/drop/pass/perpetual tests. No full-domain learning or no-progress proof claim.',science='OPEN',publication_boundary='Reviewed project code/data/diagnostics only; sensitive Slack/account originals remain ignored/private.',validator_limit='Session structure/time gate is not scientific-quality proof.')
put(R/'QA_20261015_55.json',quality)
failures=dict(segment=55,failures=[dict(issue='Unsupported runtime prevented supplied normal fallback',before=read('.local_agent/fallback55-before.json'),resolution='Public legality permits remaining-budget normal callback; absent callback explicit legal fallback. Prover still UNKNOWN.77tests pass; old KRN executed snapshots preserved.'),dict(issue='Inherited qualifier printed After study before learning',resolution='Original records preserved with additive notes;1784 inherits identical input qualification, no extra perft claimed.'),dict(issue='Strict price updates do not universally converge',evidence='1780 lowR44>unit42<highR60; low start remains local peak. Pilot1773 selects unit on tie. No unique/human optimum claim.'),dict(issue='Partial-proof retention no actual benefit',evidence='64paid cases24entries0eligible actual-path hits; parent7.3465s vs7.3115s; defer.'),dict(issue='Cheaper trigger loses finite wins',evidence='HighR ALL80/128 vsSMALL76/128, Unknown26->30. No default adoption.'),dict(issue='Native node overshoots',resolution='Actual receipts retained; engine visits are not equal primitive work.'),dict(issue='Statistical/role limits',evidence='All price-gain intervals cross0. Candidate always starts. Balanced-role inputs only, not implemented/executed.'),dict(issue='Packager construction syntax error',resolution='Nested-quote parse failure before any statements executed; corrected source construction. No evidence overwritten or lost.')],old_caps='1766/1768/532 and all prior stopped/partial evidence unchanged; no reset or completion claim.')
put(R/'FAILURES_20261015_55.json',failures)
four=read(R/'task1782/four_board_meta.json');five=read(R/'task1782/five_board_meta.json');trigger=read(R/'task1785/comparison.json')
text=f'''# DEV_AUX segment55 — physical proof tails and conditional learning

Science remains **OPEN**. The finite strategy-completion policy and a real normal-fallback defect are handled. Stable human piece values are not established. Work stays on sidemission; patrol remains PAUSED. Base26fd52997023bf23dc58e8adc0e591ff43fd76d9.

## Implementation and actual objective

At16 half-moves, an ALREADY verified full-history-bound strategy may continue for at most its remaining rank, capped64. Its owner follows the original cursor; each actual public move decreases rank. Defenders use ordinary play; no new proof starts after the horizon. Only an actual Core terminal earns reward. No certificate means UNKNOWN. Both colors/prices share the rule. H16 snapshots, physical moves, costs and unresolved bounds stay separate. A-to-B includes solver+tail; B-to-D compares prices in that fixed complete player. This is a bounded event objective, not infinite WDL or equal actual total compute. No quantity reward or theoretical win adjudication.

A public-valid no-progress state previously raised NotImplementedError before its supplied normal callback. The adapter now obtains public legality and permits that callback under the remaining budget. Without one, it explicitly returns a legal fallback, not internal AB. The prover remains UNKNOWN there. Two real failing-before regressions now pass; **77 focused tests pass**. Supported KRN paths retain their behavior. Earlier executed snapshots bind cohorts separately from this later repair.

## Frozen learning evidence

Four large cohorts each use fresh orbit-separated TRAIN32/DEV32 families, closed KRN stocks on4x4/5x5, one active R price360/720/1440 with N720, modified material-only Fairy-Stockfish, NNUEoff/Threads1/Hash16, aligned leaf/native/capture ACKs, candidate4096 and unit64/unit4096 opponents. Native search is a cold board-snapshot policy; Core repetition3/maxply96 and actual history terminals remain authoritative. There are no pawns, promotions, drops or declarations in the learning cohorts. Separate proof tests cover broader mechanics; these models do not replace the complete GenericChess target.

|Domain|Studies|Global TRAIN choice|DEV B-to-D event gain|Conditional family bootstrap95|
|---|---|---|---|---|
|4x4|1775/1776|R/N=2 in both|{four['summary']['price_solver']['finite_event_difference']:.7f}|{four['summary']['price_solver']['stratified_DEV_family_bootstrap95']}|
|5x5|1780/1781|R/N=2 in both|{five['summary']['price_solver']['finite_event_difference']:.7f}|{five['summary']['price_solver']['stratified_DEV_family_bootstrap95']}|

Each domain has64 independent DEV families, resampled within cohort conditional on its TRAIN-selected candidate. Separate studies remain primary evidence. Every price-gain interval above crosses zero. Solver+tail unit gains are {four['summary']['solver_policy']['finite_event_difference']:.6f}(4x4) and {five['summary']['solver_policy']['finite_event_difference']:.6f}(5x5), with positive pooled conditional intervals. This does not establish universal strength or cost savings. Two budgets are one opponent family, not arbitrary opponent transfer. All individual results and missing/infinite-outcome bounds remain in audits.

Strict adjacent paths share actual grid games, not independent online training runs. In1780 lowR44>unit42<highR60 is a local peak: not all starts converge. Pilot1773 selected unit on a tie:224games/131.860s/2750go;10existing tails physically won through46extra moves/18go. Its H16 prefix would select highR, so truncation changes selection. The1TRAIN/1DEV sized-entry smoke has flat rewards and is an entry test, not successful replication. All pilots and negative cases remain.

Observed DEV proof wins retain a rook; candidates always start, and these DEV sets contain no candidate losses. The zero-go role audit proves only equal-price/equal-budget baseline label symmetry; it does not evaluate learned defense. R/N=2 is a grid endpoint at one absolute scale, not a continuous optimum or full Chess/Shogi value recovery. No human-reference values selected rules, states or prices.

## Cost decisions

Fresh paired32-family1783/1784 fixes prices from earlier TRAIN and changes new-proof triggering:ALL versus board+hand entity count<=4. The count gates computation, never reward; existing verified strategies still continue.256/256 repeated plain reference paths are identical. Independent checks verify actual conduct and all planned slots.

Unit:78/128wins in both, SMALL/ALL hybrid-game cost ratio {trigger['comparisons'][0]['SMALL_to_ALL_game_cost_ratio']:.4f}. HighR:80/128 versus76/128wins, Unknown26 versus30, cost ratio {trigger['comparisons'][1]['SMALL_to_ALL_game_cost_ratio']:.4f}; event delta {trigger['comparisons'][1]['SMALL_minus_ALL_event_difference']:.5f}, interval {trigger['comparisons'][1]['family_bootstrap95']}. About30–34percent cost saving accompanies4fewer finite wins for the highR candidate. No noninferiority margin was declared; equal observations do not establish unseen no-loss. Do not adopt as default or call the ALL-selected price optimal under SMALL. Per-game cost includes public observe/transition, setup separate. Concurrent load and sequential policy order limit timing.

Separate exact-history depth2 partial-proof retention:64paid cases,24candidate entries, **0eligible actual-path hits**; parent7.3465s versus7.3115s. No observed saving: defer integration. This does not refute all caching.

## Validation, cost and continuation

{cost['actual_episode_records']}actual episode records including entry smoke; {cost['actual_new_native_go']}new Nativego; {perft}Nativeperft. {proofs}adopted proof games physically reached the certified rule win. {tails}admitted tails won through{moves}extra actual moves/{tailgo}go. All planned DEV slots are present, with no early incomplete records or unassigned receipts. Independent public replay checks legality, transitions, terminal winner, prices, ACKs, clear commands and actual receipts. Native overshoots remain. No old cap or stopped clock was extended. Generic visits differ from Native nodes; study times are not summed CPU or Agent duration. Full costs/source hashes: COST/QA/FAILURES_20261015_55.json.

Wrong inherited pre-learning qualification timing prose is corrected by additive notes, original records intact. The packager had a pre-execution quoting parse failure, corrected without evidence loss. Dot's full planned-denominator objection is adopted, including unstarted slots and incomplete TRAIN refusal. Dot reviewed54 and the described protocol, not unpublished55 execution. PRIMARY's fixed41e69 backend and13:22 lane-separation message remain read-only context; no primary execution is claimed.

Task1787 starts the next useful role audit and freezes fresh8TRAIN/8DEV inputs for both candidate roles. It has0newgo and is **INPUTS ONLY**: the old entry must reject it until candidate_side and equal-budget baseline role symmetry are implemented and tested. This is not completed training. Improve information per cost before broader learning; do not replace missing wins with piece counts or long games.

Exact project-only evidence and executed sources: segment55 ZIPs in ARCHIVE_MANIFEST_20261015_55.json, independently restored/SHA-checked. Raw Slack/account originals and credentials stay private/ignored. Manual review is separate from the session validator's structure/time gate.
'''
(R/'SEGMENT_20261015_55.md').write_text(text,encoding='utf-8');assert (R/'SEGMENT_20261015_55.md').stat().st_size>5000
print(dict(native_go=cost['actual_new_native_go'],episodes=cost['actual_episode_records'],native_nodes=cost['actual_native_reported_nodes'],perft=perft,proof_games=proofs,tail_wins=tails,tail_moves=moves,tail_go=tailgo))
