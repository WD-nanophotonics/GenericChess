# DEV_AUX101 handoff from Claude Code (substitute executor)

Who: Claude Code (Anthropic), working in this checkout as DEV_AUX on sidemission
at the user's direct request in its Claude chat on 2026-10-19 ("代替 aux agent 做
material 相关的开发"; "至少每1个小时写一份交接报告"). This is a substitute
executor for the existing DEV_AUX role, not a new worker. The user said Codex
DEV_AUX and Claude will not run at the same time. No PRIMARY/DEEPSEEK/alphasho
state, checkout, stop flag or Slack thread is touched.

Reports are appended below, newest last, at least once per hour of work.
Before resuming, Codex DEV_AUX should read this file, then `git log` on
sidemission for commits whose message says "Claude substitute".

---

## Report 1 — 2026-10-19T06:13Z (segment start)

State found:
- HEAD 0488bc06 = origin/sidemission, clean tree; no DEV_AUX process running.
- rollout/advisor flags: no user stop (user_paused false, advisor enabled);
  90-minute heartbeat remains user-PAUSED, not resumed by me.
- NEXT_WORK Main = task2580/next-dose-proposal.json (PROPOSED_ONLY).

Done so far:
- `session start` -> segment 7cb1af86-0f47-4a9e-87a1-abf7906b0e64,
  started 2026-10-19T06:12:40Z (own clock, segment 100 untouched).
- Added one pointer to this file in the State line of .local_agent/NEXT_WORK.md.
- No code changed yet.

Plan (executes the proposal as written; no change of question):
1. Read task2580 train.py / distribution.py and task2581 EVAL driver.
2. New task dir (task2582 TRAIN, task2583 EVAL): SAME Model/TDLeafEpisode/
   plain D2/eta .05/lambda .95/P1/free NBRQ/all 4 initials; mixed 8,8,64,64
   resets. Arms: Fixednu (theta candidate vs uniform foe) and SelfCandidate
   (same frozen-episode theta for both actors, observe designated candidate
   turns only). 2.5M paid nodes/arm, snapshots at 1.25M and 2.5M.
3. Register new TRAIN families + common NEW 640-slot WLD panel BEFORE fitness.
4. Re-estimate wall time; if >=120 min, stop and ask Dot first (policy).
5. TRAIN, then EVAL, then full audit (histories, reverse TD credits, replay).
6. Segment report + LOCAL_MAINLINE/NEXT_WORK refresh; local commit.
   Push to origin/sidemission only after the user confirms in Claude chat.

Not doing: old cap fills, best-seed/checkpoint choice, human priors,
Xiangqi holdout reads, Core/default/UI changes, Slack sends.

---

## Report 2 — 2026-10-19T06:20Z (registered and running)

New files (all under results/dev_aux, nothing else in the repo changed):
- task2583/train.py — copy of the task2580/train.py TD branch. Only changes:
  methods `Fixednu` / `SelfCandidate`; both use the mixed 8,8,64,64 resets;
  SelfCandidate gives the opponent seat the SAME episode-frozen candidate
  weights; both observe ONLY designated-candidate-colour complete searches.
  Query rows add `self_actor`.
- task2583/audit.py — copy of the task2580/audit.py TD branch. Also checks
  opponent weights per method and that snapshots = last closed episode <= boundary.
- task2583/register.py — writes plan/replay-plan/audit-plan/registration
  (task2583) and eval-plan (task2584). TRAIN families 581k, EVAL roots
  591001-4 (8 plies) / 592001-4 (64 plies). Seeds, foes, eta, lambda, depth,
  nodes/query and seconds/query are the same as in 2580/2581.
- task2584/bind.py — binds initial + every 1.25M/2.5M snapshot (no selection).
- task2584/analyze.py — the registered contrasts (written and pinned BEFORE EVAL).
- Reused unchanged: task2580/replay.py, task2581/evaluate.py, task2581/verify.py.

Smoke test (in ignored .local_agent/smoke2583, 2584; throwaway): 2 arms x 40k
nodes, audit PASS, replay 4/4 MATCH, unpruned 4/4, 12 EVAL games deployment PASS.

One change from the proposal, made BEFORE registration: hard caps are
TRAIN 3600s (proposal 3300) and EVAL 2400s (proposal 1800). The smoke test
measured 7.1k nodes/s and 2.19 s/game while alphasho runs alongside, and a
partial last arm would break the matched budget. The reason is written in
registration.json. Expected total is under 120 min, so no Dot pre-assessment
is needed.

Running: `.local_agent/run101.sh`, log in `.local_agent/run101.log`.
Steps: TRAIN (started 06:18:59Z) -> audit -> replay -> unpruned -> bind
-> EVAL -> deployment audit. Session checkpoint recorded.
If this chat stops mid-run: nothing is lost. Check run101.log; a step that
did not finish leaves its output file missing, and must NOT be refilled
under the same caps.

Next: when the run ends, run `python -m results.dev_aux.task2584.analyze`,
write SEGMENT_20261019_101.md, refresh LOCAL_MAINLINE.md and NEXT_WORK.md,
then commit locally.

---

## Report 3 — 2026-10-19T07:02Z (TRAIN 6/8 arms)

- TRAIN is still running, with no errors or stops so far. 6 of 8 arms closed at
  exactly 2,500,000 paid nodes each: 1977 Fx/SC, 31415 SC/Fx, 27182 Fx, 8173 Fx.
  Total so far 2526.7 s, about 417 s per arm. Projected about 3370 s, against
  the 3600 s hard cap.
- Every closed arm has both 1.25M and 2.5M snapshots. Each snapshot sits a few
  thousand to about 17k nodes below its boundary (last closed episode).
- No fitness has been read. EVAL has not started, and I compare nothing until
  the registered analysis runs. Weight vectors from the training log are
  descriptive only.
- No code has changed since Report 2. Nothing is committed yet.

Next: TRAIN finishes (~07:16Z), then audit, replay, unpruned, bind,
EVAL (~25 min), deployment audit, analyze, then the segment report.

---

## Report 4 — 2026-10-19T07:42Z (segment 101 finished)

- TRAIN COMPLETE: 20M nodes in 3309 s; audit PASS; replay 16/16; unpruned 16/16.
- EVAL COMPLETE: 640/640 actual terminal; deployment audit PASS. The registered
  analysis passed.
- Result: SelfCandidate shows no clear advantage over Fixednu.
  - Pooled SC−Fx is +.03125 at 1.25M and +.0078 at 2.5M.
  - The sign flips by foe, by prefix and by seed.
  - SC produces about 23% fewer TD terms per node.
  - Doubling the dose adds little for either method.
  - Full detail: SEGMENT_20261019_101.md.
- Updated: docs/research/LOCAL_MAINLINE.md (new 101 head; 100 moved to the
  historical section), docs/operations/COLLABORATION_LOG.md (101 entry), and
  .local_agent/NEXT_WORK.md, rewritten. The old memo is kept as
  .local_agent/NEXT_WORK.before101-claude.md.
- `session finish` closed the segment as safe_checkpoint.
- Committed locally on sidemission ("Claude substitute" in the message).
  NOT pushed: publication waits for the user's OK.
- Throwaway smoke dirs .local_agent/smoke2583 and smoke2584 are ignored and
  can be deleted.

For Codex DEV_AUX on return: start from NEXT_WORK Main, which is the full
Generic transfer of the same learner with Fixednu as the control. The
task2583/2584 scripts are plain derivatives of task2580/2581; diff them against
those files to review.
- Following the task2580/2581 convention, the raw query logs
  task2583/queries.jsonl (498 MB) and task2584/eval-queries.jsonl (270 MB) are
  kept locally and NOT committed. I did not build a DELTA_REPRO ZIP or fresh
  reproduction bundle (the task2582-style step); it is left for normal DEV_AUX
  packaging if wanted.

---

## Report 5 — 2026-10-19 (delivery)

- With the user's explicit OK in the Claude chat, d861db87 was pushed to
  origin/sidemission as a fast-forward from 0488bc06.
- Verification: `ls-remote` returns the full SHA
  d861db8767c2c296e21cfe06c6cfa9142d48fdaf. The anonymous GitHub API branch
  endpoint returns the same SHA, and the files are readable at that SHA.
- The first push attempt used a raw SHA refspec. The pre-push hook rejected it
  as designed (it accepts only refs/heads/sidemission), so nothing was sent.
  The retry pushed the branch ref.
- This report is a local follow-up edit made after the push. It is not
  committed; the next DEV_AUX commit can include it.

---

## Report 6 — 2026-10-19 (Slack: AUX_CLAUDE identity, first Dot request)

- User direction: talk to Dot in #generic-chess (C0C6L21UU20) and continue
  development. Slack ID: **AGENT_ID=AUX_CLAUDE** (Claude Code; auxiliary
  material/learning work in this DEV_AUX checkout/sidemission). It is not a
  new checkout or worker, and it is never run at the same time as Codex
  DEV_AUX. Messages are sent with Claude's Slack connector through the same
  shared user account. They do not carry "Sent using ChatGPT".
- Sent AGENT_REQUEST GC-SLACK-20261019-AUXCLAUDE-101a, ts 1792397389.731309.
  It contains the 101 result, a descriptive-only material-order pair count, and
  a request for one interpretation gap and one smallest next step among
  (a) Generic transfer, (b) a matched-terms feedback-density control,
  (c) a changed target. Send record: .local_agent/slack/auxclaude-101a-send.json.
- Descriptive pair count, external P<(N,B)<R<Q, 9 strict pairs per model,
  totals over 4 seeds out of 36: initial 21, Fx 1.25M 26, Fx 2.5M 27,
  SC 1.25M 30, SC 2.5M 30. Not a gate or selection criterion
  (see the CHAT_Comments correction, ts 1792376812.571529).

---

## Report 7 — 2026-10-19 (Dot reply adopted; order-utility check)

- Dot DOT_REPLY ts 1792397818.663009, about 7 min after the request. The
  AUX_CLAUDE route works: messages "Sent using Claude" pass Dot's filter.
  Summary:
  - Keep Fixednu as the control; there is no reason to switch to SC.
  - Gap: closeness to the traditional order is not linked to utility.
  - Smallest next step: an existing-records cross-check.
  - Afterwards: prefer (a), a small full-semantics Generic transfer with a
    Fixednu control. Defer (b). (c) has no priority.
  - Decision: ADOPT.
- Done: task2585/order_utility.py, output task2585/order-utility.json. No new
  games.
  - 32 cells; SC has the higher order score in 20 of them.
  - Of those 20: 9 W−L up, 8 zero, 3 W−L DOWN (seed 1977, uniform foe;
    1.25M p8/p64 −.125 and 2.5M p64 −.375).
  - Initial absolute vs random48821: 24W/7D/1L (p8) and 19W/12D/1L (p64), a
    ceiling.
  - Conclusion: the strong claim "more traditional order ⇒ stronger" is refuted
    on this panel. The order-split is CLOSED as a reason for a dedicated
    experiment; order stays descriptive.
- Next (NEXT_WORK Main): (a) a small Generic transfer of the SAME learner, with
  Fixednu as the control and full promotion/drop/aux/history. First prove it is
  executable and can separate the candidates; scale only after that. Any design
  expected to take >=120 min goes to Dot first.

---

## Report 8 — 2026-10-19T08:28Z (segment 102 started: NEW-rule Generic transfer)

- User direction: start 102 = a small transfer trial of the SAME learner on
  full-semantics Generic rules, with a Fixednu control; keep hourly reports.
  Session b1ad62e2-2eeb-4d9a-be02-ff71eb508b82, started 08:21:03Z.
- Design (task2586, registered before any fitness):
  - NEW rules: generator seeds 351001-351004, 4x4, generated once with no
    retry or outcome filter, 0 failures. Neither checkout's plans had used
    this block. PRIMARY used 291001-4, so I avoided it.
  - TRAIN: the existing audited task2565 Generic code, unchanged. Fixed
    regime (candidate vs fixed uniform nu), 6 free channel coefficients,
    eta .05, lambda .95, D2, H128, prefix 4, all 4 initializations.
    16 arms x 400k nodes, snapshots at 100k/200k/400k. Families 341000+.
  - EVAL: 2560 slots = 4 rules x 4 seeds x 5 models x 8 NEW families
    (345001-8) x 2 roles x 2 foes (DEV_AUX96 uniform/random99031).
  - The 5 models are initial, Fixed@100k/200k/400k and OldRulesMean.
    OldRulesMean is the per-seed mean of the DEV_AUX96 Fixed endpoints trained
    on the OLD rules 271001-4. It tests transfer of learned prices with no
    retraining.
- The only new code is task2586/run.py. It patches task2565.train.compiled()
  to also load task2586/rules-*.json, then calls the unchanged task2565
  train/audit/verify/evaluate. The rest is register.py, bind.py and analyze.py.
- Smoke test in ignored .local_agent/smoke2586: train, audit PASS,
  unpruned 4/4, eval 16 games, deployment PASS.
- Estimate ~65 min total, under 120 min, so no Dot pre-review is needed.
  Running .local_agent/run102.sh, log .local_agent/run102.log.

---

## Report 9 — 2026-10-19T09:05Z (102 TRAIN closed, EVAL running)

- TRAIN COMPLETE: 16/16 arms x 400k = 6.4M nodes in 2154 s.
  - 8115 games: 7933 actual terminal, 182 UNKNOWN.
  - 62,784 TD terms.
  - 16 failed queries (658 nodes); these were paid for and are kept.
- Unchanged task2565 audit PASS on all 124,962 queries (full history,
  reverse credits, cost). Unpruned 32/32 verified.
- Bound initial, Fixed@100k/200k/400k and OldRulesMean. EVAL (2560 slots)
  started 09:04Z, ~26 min. No fitness has been read yet.
- Rule notes (rule files only):
  - All 4 share the same 4x4 initial layout.
  - 351001/351002: P and X promote (forced); P/X drops are partly restricted.
  - 351003: only P promotes (optional); drops are unrestricted.
  - 351004: only P promotes (forced broadly); P drops on one rank only.

---

## Report 10 — 2026-10-19T09:30Z (segment 102 finished)

- EVAL 2560/2560: 2439 actual, 121 U, 0 missing. Deployment audit PASS;
  registered analysis PASS.
- Result: on NEW rules, Fixed TD beats initial at every snapshot.
  - Pooled: 100k [+.174,+.299], 400k [+.133,+.305]; both foes > 0.
  - The curve saturates: 400k-100k is [-.131,+.096].
  - OldRulesMean (no retraining) - initial: [+.084,+.197]. Fixed400k -
    OldRulesMean: [-.029,+.186].
  - Adverse: 351002 vs random99031. U rises with training.
  - 16/32 EVAL roots were also TRAIN roots. A POST-HOC fresh-only check
    (exposure_sensitivity.py) gives the same signs.
- Files: SEGMENT_20261019_102.md, task2586/*, LOCAL_MAINLINE head 102,
  COLLABORATION_LOG entry, NEXT_WORK rewritten (Main = separate H128
  censoring from saturation using existing records).
- Session finish: safe_checkpoint, 63.5 min.
- About the 30-min routine: the user asked for one, but auto mode refused
  CronCreate as unauthorized persistence. I gave the user a /loop command to
  start themselves; none is running unless they started it.
- Raw query logs stay local and uncommitted (convention): task2586/generic/queries.jsonl
  and task2586/eval/eval-queries.jsonl.
- Slack: AGENT_REQUEST GC-SLACK-20261019-AUXCLAUDE-102a ts 1792401964.302919 (102 result + next-step question). Commit 37bce378 pushed, remote verified.

---

## Report 11 — 2026-10-19T09:45Z (Dot 102 reply adopted; censoring decomposition)

- DOT_REPLY ts 1792402091.889509 corrected my use of the both-terminal
  subset. That subset is selected by a model-affected outcome, so it only
  describes itself; I withdraw the "saturation is not censoring" reading. Dot
  asked for a full 512-pair decomposition and a decision threshold before any
  H256 or warm-start run. ADOPTED.
- Done: task2586/censor_decomposition.py, output eval/censor-decomposition.json.
  No new games.
  - Pair counts: TT 464 (+3 known), 400kU/100kT 25 [-38,+12],
    400kT/100kU 13 [-12,+14], UU 10 [-20,+20].
  - Total [-.131,+.096]. All U are HORIZON_UNKNOWN; none are search failures.
  - Decision rule, fixed now: prefer 400k (4x cost) only if gain >= +.0625,
    which needs +29 of the max +46 unresolved.
  - Dot's counterexample 351004/31415 (all 32 terminal, -.0625) shows that not
    all regressions are censoring.
- Decision: keep Fixed@100k as the cheap default checkpoint. No H256 re-EVAL
  or warm-start run now; revisit only if a downstream choice depends on it.

---

## Report 12 — 2026-10-19T10:00Z (segment 103 started: warm vs cold start)

- User direction: 103 = Fixed TD on NEW rules, warm start from OldRulesMean vs
  cold start, at the same paid nodes, with a decision threshold fixed in
  advance; keep hourly reports. Session d0cde1b3-3a07-47e9-bdcc-861840f4d117,
  start 09:55:25Z.
- task2587 (registered before any fitness):
  - NEW rules 348001-4 (unused block, 0 failures). 32 arms = 4 rules x 4 seeds
    x {Fixed cold, FixedWarm}, 100k nodes each, snapshots 25k/50k/100k.
  - EVAL 4096 slots: 8 models (Cold/Warm @0/25k/50k/100k) x NEW families
    347801-8 x 2 roles x 2 foes.
  - Decision rule (margin .0625, full paired bounds, U = [-1,1]):
    - WARM_SAVES_DOSE if lower(Warm@25k-Cold@100k) >= -.0625 AND
      lower(Warm@100k-Cold@100k) >= -.0625.
    - WARM_WORSE if upper(Warm@100k-Cold@100k) < 0.
    - Else UNRESOLVED, which keeps the cold default.
  - Full T/U decomposition for the two decision contrasts.
- Code: task2587/train.py and audit.py are copies of task2565 with exactly two
  edits each (FixedWarm initial taken from plan.initial_weights; FixedWarm
  treated as the Fixed regime). Check with `diff --strip-trailing-cr`.
  The smoke test found a runner bug (the copy's own compiled() was not hooked);
  it was fixed before registration.
- Running .local_agent/run103.sh, log .local_agent/run103.log; ~55 min.

---

## Report 13 — 2026-10-19T10:52Z (segment 103 result)

- Pre-registered DECISION: WARM_WORSE.
  - Warm@100k-Cold@100k [-.088,-.072]; Warm@25k-Cold@100k [-.217,-.197].
  - Only 17 U out of 4096; the decomposition shows U cannot change the
    decision.
- KEY: Warm@0-Cold@0 is [-.033,-.014]. 102's OldRulesMean transfer
  (+.084..+.197) did NOT replicate on rules 348001-4; it is rule-dependent.
  The 102 transfer claim is narrowed to that panel (see SEGMENT_..._103).
- Cold learning replicates: Cold@100k-Cold@0 is [+.174,+.189].
- All audits PASS. Files: SEGMENT_20261019_103.md, task2587/*,
  LOCAL_MAINLINE head 103, COLLABORATION_LOG, NEXT_WORK (Main = descriptive
  rule-capability vs transfer table, existing records only).
- Descriptive table task2587/rule-capability-table.json: per-rule transfer gain vs cold learning gain over 8 NEW rules, Spearman 0.857 (midpoints, n=8). Transfer helps where cold TD gains strongly and hurts where it gains ~0. Hypothesis only. SEGMENT_102 has an appended 'Update after DEV_AUX103' erratum.
- Backup2 descriptive (task2587/warm-credit-description.json): warm/cold update magnitudes are similar; cold drifts hand-P net -0.10/episode vs warm -0.01; weight displacement cold 0.98 vs warm 0.71. Hypothesis only. Slack AGENT_REQUEST 103a ts 1792406894.300239 sent.

---

## Report 14 — 2026-10-19T11:00Z (Dot 103 reply adopted; transfer line closed)

- DOT_REPLY to 103a, read 11:00Z:
  - Transfer = W0-C0 and learning = C100-C0 share the subtrahend C0, so
    Spearman .857 cannot establish learnability->transfer.
  - Price-insensitivity is not the explanation either (348001/348002 react
    strongly).
  - Don't do (a) or (b). Make (c), widening ONE domain factor at a time, the
    next main direction.
  - Smallest step: direct paired W0-C100 plus absolute W/D/L/U per rule/foe.
  - Decision: ADOPTED.
- Done: task2587/direct_w0_c100.py, output direct-w0-c100.json, both panels,
  existing records only.
  - W0-C100 over 16 rule x foe cells: 13 strictly negative, 0 positive,
    3 undetermined (351002/random, 351003 x2; U-heavy).
  - So zero-training OldRulesMean never beats trained cold@100k, and the
    practical choice is unchanged. The transfer diagnosis is CLOSED; no
    simulation for .857.
- NEXT_WORK Main: widen ONE domain factor (board size 5x5, same generator
  config otherwise) with the SAME cold per-rule Fixed TD at 100k, registered
  first. Check channel/type admission first; record the generator outcome as
  is.
- Admission check (in memory, seeds 900001-3, nothing written): board_size 5 yields non-anchor types P/A/B, not P/A/X. The task2565 CHANNELS are hard-coded to P/A/X, so the 5x5 step first needs rule-derived channels (as task2525 did), done as a copy + small diff. Recorded in NEXT_WORK Main. Segment 103 closed after this.
- 5x5 design note: task2565 CHANNELS is a module constant used by environment()/restore()/audit/verify.unpruned (feat). Plan: copy those modules with CHANNELS derived per rule as in task2525 (board P first, then sorted others; hand sorted). For P/A/B that is still 6 dims. Smoke and diff-review before registration.

---

## Report 15 — 2026-10-19T11:35Z (segment 104 started: 5x5 widening)

- User direction (2026-10-19): continue segments without asking each time.
  Session 4c1dc011-80a9-498b-b427-690e92b799c1, start 11:20:05Z.
- task2588 (registered before fitness):
  - ONE widened factor: board_size 5. NEW rules 356001-4; all admitted with
    types P/A/B (0 failures).
  - Same cold Fixed TD; 16 arms x 100k; snapshots 25k/50k/100k.
  - EVAL 2048 slots: Cold@0/25k/50k/100k x NEW families 356801-8 x 2 roles
    x 2 foes.
  - Decision rule: LEARNS_5x5 if lower(Cold@100k-initial) > 0; NO_GAIN if
    upper <= 0; otherwise UNRESOLVED.
- Code: task2588/run.py sets task2565.train.CHANNELS from the rule types
  (board P,A,B; hand A,B,P; same ordering rule as task2525) before importing
  the audited modules. The compiled() hook is reused from task2586. No
  audited file was edited.
- Pre-fitness root note: 8 of 32 EVAL roots are already terminal after <=4
  random plies. They are kept (no filtering) and only lower sensitivity.
- Running .local_agent/run104.sh, ~55 min.

---

## Report 16 — 2026-10-19T12:24Z (104 EVAL near its cap)

- TRAIN COMPLETE: 16 arms, 1.6M nodes, 868 s.
  - Only 471 games and 312 updates. 5x5 games cost about 3.4k nodes each,
    so 100k/arm is a much smaller learning dose than on 4x4 (about 3x
    fewer games).
  - Audit PASS on 11,498 queries; unpruned 32/32.
- EVAL is slower than the smoke estimate: ~1.95 s/game vs 1.27 s.
  - Trained models play longer games, and the smoke sample (16 games) was
    too small.
  - Projection: the 3000 s cap stops EVAL at ~1550/2048 games, i.e.
    PARTIAL_CAP.
  - The cap is NOT extended (policy). Missing slots enter the bounds as
    [-1,1], so the pre-registered decision may come out UNRESOLVED.
- If UNRESOLVED: the follow-up is a separately registered completion of
  exactly the missing slots (same models, roots, foes; existing results
  kept). Under 120 min, and a cost estimate from >= 100 pilot games.

---

## Report 17 — 2026-10-19T12:32Z (segment 104 closed: UNRESOLVED)

- EVAL PARTIAL_CAP at 3000 s: 1521/2048 games, 527 missing. Deployment audit
  PASS.
- Registered decision UNRESOLVED: Cold@100k-Cold@0 [-.543,+.625];
  TT 259 (+13).
- Descriptive both-terminal mean +.05 (vs ~+.18 on 4x4). The effective 5x5
  dose was small (471 games, 312 updates).
- Cost-estimate error: smoke 1.27 s/game vs actual ~1.97 s/game. Next time,
  pilot >= 100 games.
- Next (auto, per user): segment 105 = registered completion of exactly the
  527 missing slots, then re-apply the registered rule to the union.

---

## Report 18 — 2026-10-19T12:35Z (segment 105 started: completion)

- Session d11897fc-2a63-4039-805d-10296a9899e9, started 12:30:11Z.
- task2589 registers the completion of exactly the 527 slots missing from 104.
  The bound models are byte-identical copies; roots, foes, ordering seeds and
  depth are the same.
- union.py (pinned) re-applies the 104 LEARNS_5x5 rule to the union. Estimate
  ~17 min, cap 40 min.
- Slack: AGENT_REQUEST 104a (ts 1792413012.505629) asks Dot whether a
  game-matched or node-matched 5x5 dose is the right currency.

---

## Report 19 — 2026-10-19T12:52Z (105 result: LEARNS_5x5)

- Union of the 104 and 105 games: 0 missing; deployment audit PASS.
  - Registered decision LEARNS_5x5: Cold@100k-Cold@0 [+.041,+.123].
  - The 5x5 curve is still rising at 100k.
- Dot reply 1792413417.828509 (ADOPTED):
  - Paid nodes stay the currency; report actual time; no game-matched dose.
  - Separate compute efficiency from exposure.
  - The widened factor is the generated domain, not board size alone.
  - 104+105 is one logical experiment: total ~83 min, under 120.
- Exposure table (task2589/exposure-table.json): 5x5 vs 4x4 at 100k gives
  0.52x terms and 0.30x updates/games.
- Files: SEGMENT_20261019_105.md, task2589/*, LOCAL_MAINLINE, COLLAB_LOG,
  NEXT_WORK (Main: ask Dot which ONE further generator factor matters).

---

## Report 20 — 2026-10-19T13:00Z (Dot 105a adopted; task2590 hybrid-movement panel running)

- DOT_REPLY 1792414510.091249 (ADOPTED):
  - Next factor: one pre-fixed 4x4 movement-generator change, keeping P/A/X.
  - Gap: pooled gains do not show per-rule learnability; report rules
    individually.
  - Fix held-out roots before fitness.
  - Corrections, applied to SEGMENT_105 and LOCAL_MAINLINE: union U = 52
    (not 41); 4x4 "no gain shown after 100k" (not "saturated"); 103
    OldRulesMean-initial is strictly negative; Chess SC advantage "not
    established on this panel".
- task2590 runs inside session 105 (d11897fc) as its second research stage;
  report name SEGMENT_20261019_106.md.
  - NEW rules 363001-4 with allow_hybrid=True, 4x4, P/A/X; 0 failures.
  - 16 cold arms x 100k.
  - EVAL: 1024 slots, Cold@0 vs Cold@100k, held-out families per rule (root
    not among TRAIN families 363100..363599). 0 terminal roots.
  - Decision: LEARNS_HYBRID if lower > 0, plus per-rule counts.
- Running .local_agent/run106.sh, ~20 min.
- 106 RESULT: LEARNS_HYBRID pooled [+.010,+.084]; per rule 3 positive, 363001 strictly negative [-.328,-.156]; seeds 2+/2-; 0 held-out overlap. Report SEGMENT_20261019_106.md. Next: describe the 363001 failure from existing records, then Dot.
- 363001 failure description (task2590/failure-description.json): TRAIN candidate reward +.048 (others +.17..+.28); weights drift board X -.77, board P -.38, hand A +.33, hand P +.50; EVAL wins 67->51; length is not the separator. Slack AGENT_REQUEST 106a sent.
- credit-by-outcome (task2590/credit-by-outcome.json): positive rules have strongly opposed W/L credits; 363001 has small credits and weak W/L contrast. Hypothesis: weak outcome signal plus bootstrap drift. Descriptive only.

---

## Report 21 — 2026-10-19T13:30Z (363001 diagnosis per Dot)

- Dot 106a reply (ADOPTED): narrowed to option (a), a raw-record ledger and
  credit split for 363001. Corrections: a near-0 mean reward is not "no
  signal"; "3 positive" means merged foes.
- task2590/credit_split.py reconciles exactly (2.2e-16).
- The terminal TD error is identically 0 on all rules, because the last
  observed D2 search already sees the terminal.
- Heuristic vs outcome-seen bootstrap conflicts occur on all rules.
- 363001 is distinct:
  - The heuristic share is 0.78-1.41 on all seeds (positive rules
    0.17-0.46).
  - Heuristic drift pushes board X down on all 4 seeds.
- Next: propose to Dot a minimal targeted check (363001 only: lambda=1, or a
  heuristic-step down-weight, vs the original). Registered first, small.

---

## Report 22 — 2026-10-19T13:50Z (segment 107: lambda probe)

- Dot did not answer follow-up split1 within 10 min. Per Dot's earlier rule
  (strong mechanism found -> ONE minimal check) and the <120-min policy, I
  registered and ran the probe: 363001 only, lambda .95 -> 1.0, everything
  else identical. Audits PASS.
- Decision NO_FLIP: Lam1-C0 [-.164,-.070]. But Lam1-C100(.95) is
  [+.055,+.195]: the degradation is halved without a flip.
- Line stopped (partly explained). Next: a synthesis doc, then ask Dot for
  one next main direction.
- Synthesis doc: results/dev_aux/AUX_CLAUDE_SYNTHESIS_20261019.md (101-107 in one page, with Dot's wording corrections).

---

## Report 23 — 2026-10-19T14:00Z (segment 108: leap-only panel)

- Dot was silent >12 min twice on 107a (next-direction question), a soft
  block per policy. I chose candidate (1), the cheapest decision-relevant
  option: how common are per-rule failures?
- task2592 is a sed-derived copy of task2590 with only the constants changed:
  - leap_probability=1.0, ray_probability=0.0.
  - NEW rules 364001-4, P/A/X, 0 failures.
  - TRAIN families 364100+; held-out EVAL families from 364600 (outside the
    TRAIN check range this time).
  - 1 of 32 held-out roots is terminal (kept).
- Same decision form: pooled LEARNS_LEAP plus per-rule counts. Running
  run108.sh within session 107 (a6ffbcc4).
- 108 RESULT: LEARNS_LEAP [+.125,+.188]; 364003 negative; held-out FAILED for 364004 (TRAIN family 364651 > 500-span assumption), post-hoc fresh-only same sign. Cross-panel 20 NEW rules 13+/4-/3?. Synthesis updated.

---

## Report 24 — 2026-10-19T14:15Z (Dot 107a adopted; ROUND CLOSED)

- Dot recommends (3): pause new Generic learning experiments and close the
  round with a correct synthesis. 108 had already run before the reply
  arrived; it is kept as counts only.
- Corrections applied:
  - SEGMENT_107 per-seed results: not "all negative". 1977 undetermined,
    8173 +, 27182 strongly -, 31415 [-.125,0]. 27182 is worse under lambda=1.
  - Mechanism wording: "compatible, not isolated".
  - Credit-split conclusions are limited to the 106 records.
  - The 20 rules are now a dev/regression set; no failure-rate claim.
  - Updated: synthesis, LOCAL_MAINLINE, SEGMENT_108, NEXT_WORK.
- STATUS FOR CODEX DEV_AUX: start from results/dev_aux/AUX_CLAUDE_SYNTHESIS_20261019.md
  and NEXT_WORK Main. AUX_CLAUDE starts no new experiments in this round.
- Draft (no runs): docs/research/GENERATED_RULE_SAMPLING_SPEC.md defines the sampling population, estimand, sample size and a corrected held-out rule for any future failure-rate claim. Each cell is likely >=120 min, so Dot review first.

---

## Report 25 — 2026-10-19T14:20Z (pause point)

- The round is closed per Dot 107a. Session a6ffbcc4 (segment 107) is
  intentionally left ACTIVE: the validator refuses finish before 60 min, and
  the remaining step is a user/advisor decision, not more work.
  - The next executor should resume it (do not reset the clock) and finish it
    with evidence SEGMENT_20261019_107.md and 108.md, or continue under it.
- Options for the user or next executor:
  1. A sampling-population study per docs/research/GENERATED_RULE_SAMPLING_SPEC.md
     (>=120 min per cell, so Dot review first).
  2. Hand back to Codex DEV_AUX, using the synthesis and NEXT_WORK.
- All work is pushed; origin/sidemission is at the latest SHA in git log.

---

## Report 26 — 2026-10-19 (FINAL: handed back to Codex DEV_AUX)

- User decision (2026-10-19): stop here and hand back to Codex DEV_AUX,
  which continues from results/dev_aux/AUX_CLAUDE_SYNTHESIS_20261019.md and
  .local_agent/NEXT_WORK.md.
- AUX_CLAUDE is stopping. No background runs or monitors are active, and no
  uncommitted project files are left, except the raw queries.jsonl /
  eval-queries.jsonl, which stay local by convention.
- Session a6ffbcc4 (segment 107) is still ACTIVE. Resume it and finish it
  (evidence: SEGMENT_20261019_107.md, 108.md); do not reset its clock.
- Throwaway smoke folders .local_agent/smoke25xx and the .local_agent/run10x.sh
  scripts and logs are ignored and can be deleted.
- Things worth reviewing first:
  - task2586/run.py: the rule-file hook.
  - task2587/{train,audit}.py: diff them against task2565.
  - task2588/run.py: the channel hook.
  - task2590/credit_split.py.
  - The Dot threads 101a-107a in #generic-chess.
