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
