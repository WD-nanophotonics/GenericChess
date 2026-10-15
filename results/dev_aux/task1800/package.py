"""Build segment56 review artifacts only after all actual studies close."""
import json,hashlib
from pathlib import Path
R=Path("results/dev_aux")
def read(p):return json.loads(Path(p).read_text(encoding="utf-8-sig"))
def put(p,x):Path(p).write_text(json.dumps(x,indent=2),encoding="utf-8")
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
ids=[1788,1789,1791,1792,1796,1797,1798];studies=[];proofs=tails=moves=tailgo=0
for task in ids:
    p=R/f"task{task}";r=read(p/"result.json");a=read(p/"audit.json");t=read(p/"tail_audit.json")
    assert r["status"]=="COMPLETE" and a["status"]=="PASS_PUBLIC_REPLAY_AND_RECEIPTS"
    assert r["games"]==a["games"] and a["unassigned_native_receipts"]==a["early_unknown_before_H"]==0
    assert not any(x["missing_games"] or x["early_incomplete"] for x in a["cells_DEV_only"].values())
    assert t["counts"].get("incomplete_tail_unknown",0)==0
    proofs+=a["proof_calls"];tails+=t["counts"].get("actual_tail_wins",0);moves+=t["counts"].get("tail_steps",0);tailgo+=t["counts"].get("tail_native_go",0)
    studies.append(dict(task=task,**{k:r[k] for k in ("status","games","actual_native_go","actual_native_reported_nodes","seconds")},plan_sha256=sha(p/"plan.json"),game_sha256=a["raw_games_sha256"],proof_conversion=a["proof_conversion"],native_node_overruns=a["native_node_overruns"],step_time_overruns=a["step_time_overruns"],max_step_seconds=a["max_step_seconds"]))
perft=sum(read(R/f"task{i}/native_qualification.json")["actual_perft"] for i in (1788,1791,1792,1797,1798))
public=read(R/"task1793/result.json");work=read(R/"task1795/result.json")
assert public["status"]=="COMPLETE_FINITE_REFERENCE_PASS" and work["status"]=="COMPLETE_FIXED_WORK_CONTROL"
cost=dict(segment=56,studies=studies,actual_new_native_go=sum(x["actual_native_go"] for x in studies),actual_native_reported_nodes=sum(x["actual_native_reported_nodes"] for x in studies),actual_episode_records=sum(x["games"] for x in studies),actual_native_perft=perft,adopted_proof_games_physically_redeemed=proofs,admitted_tails_physically_won=tails,physical_tail_moves=moves,physical_tail_native_go=tailgo,caller_cost_attribution=read(R/"task1802/decision.json"),public_finite_validation=public,public_vs_runtime_fixed_work={k:v for k,v in work.items() if k!="paired"},measurement_limits="Actual study walls overlap Agent engineering; do not sum as CPU/Agent duration. Separate qualification cost in own records. Public proof visits differ from Native nodes; all Native overshoots retained. Ordinary concurrent work allowed; no exclusive timing or model-token attribution.")
put(R/"COST_20261015_56.json",cost)
subjects=sorted({str(x) for x in Path("scripts").glob("generic*proof*.py")})
qa=dict(segment=56,status="ACTUAL_AUDITS_AND_MANUAL_REVIEW_REQUIRED",all_studies_closed=True,all_planned_DEV_slots_present=True,unassigned_native_receipts=0,all_actual_tails_completed=True,proof_games=proofs,tail_wins=tails,subject_sha256={x:sha(x) for x in subjects},semantic_scope="KRN4x4 two-role finite learning. Generic no-progress public proof separately validated, no learning claims there. Declaration choices still unsupported. Core/product/default/UI not modified.",science="OPEN",publication="Actual outgoing project-only source/data/evidence checked; exact sensitive Slack/account originals private/ignored.",workflow="Session validator tests structure/time, not scientific quality. New source after1792loaded binds only future studies; exact old executed source archived.")
put(R/"QA_20261015_56.json",qa)
failures=dict(segment=56,records=[
    dict(issue="Legacy A-to-B did not hold opponent fixed",cause="proof_enabled=enabled applied to both sides",impact="Legacy solver contrast is joint policy change; B-to-D price contrast still same opponent",resolution="Explicit opponent_proof=True in new1796/1797/1798; actual per-actor proof, price, budget and tail audit. Old trajectories/rewards/caps untouched."),
    dict(issue="Timed baseline role paths sometimes differ",evidence="1791 family59 bothcolors: UNKNOWN versus repetitiondraw, first divergence from different residual Native node budgets after time-cut PN",impact="No finite W-L event change in these two cases, but no deterministic replay or timing-noise-free inference",resolution="Preserve actual logs, separate configured resources and actual work; no automatic rerun."),
    dict(issue="Public history proof cost",evidence="96 matched-work/tree calls public1.62-1.67x runtime on tested roots",resolution="Opt-in fallback, not default/speedup claim. No synthesized halfmove/history reset; atomic transition time charged."),
    dict(issue="Initial resource symmetry assertion too strict",evidence="1789 same actual paths but differing timed proof nodes",resolution="Reported actual node differences and all-draw scope; later paid nonzero opposite payoff controls also checked."),
    dict(issue="New no-progress test assumed a single draw kind",evidence="Eight no-progress draws and one actual stalemate at threshold",resolution="Preserve real terminal priority; test corrected, no rule or output altered."),
    dict(issue="Handwritten history test illegal black king step",evidence="Public legality rejected d4c4 when rookc3 attacked it",resolution="Use legal rookb2 cycle; same-board/sameply histories now produce distinct actual terminals."),
    dict(issue="Paid caller attribution expected64states but60available",resolution="1801pre-timingfailure preserved;1802usesactual60states/300pairs.0.49ms saved percallback despite0.309microcostratio, deferclosedloop optimization andno newenginebatch."),
    dict(issue="Offline diagnostic syntax error",resolution="Closed missing list bracket; no game executed or data changed by failed analysis."),
    dict(issue="Live PowerShell tail inspection raced append",evidence="Extra data JSON parsing on two appended lines",resolution="Read a completed stable JSONL line with Python; producer and saved records unaffected."),
    dict(issue="Inherited qualifier false After-study label",resolution="Old exact outputs retained with additive timing notes. Future qualifier accepts explicit invocation phase; actual fixed-opponent records say BEFORE_STUDY."),
],old_caps="No old capped/stopped run reset or extension. Guarded1787 and1794 input plans remain unchanged; executed successors reference their exact hashes.",limitations="Small rootlaws/one absolute scale/finite horizon; grid endpoint not unique continuous optimum or full human price recovery. Actual price-result vector/cost, not action/terminal density alone, governs next choice.")
put(R/"FAILURES_20261015_56.json",failures)
print(dict(go=cost["actual_new_native_go"],episodes=cost["actual_episode_records"],perft=perft,proofs=proofs,tails=tails,moves=moves,tailgo=tailgo))
