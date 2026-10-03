# GenericChess local research policy

This is the sole active policy. User instructions take precedence. The old
Supervisor–Worker, work-order, Goal, ownership-capsule and Chat approval
strategies have been removed from active use. Historical records are evidence.

One local Agent works in this checkout on `sandbox`, in ordinary task mode.
Read `.local_agent/NEXT_WORK.md` and `docs/research/LOCAL_MAINLINE.md` at the
start of every turn. Preserve research results, unrelated changes, and the
Chess/Shogi/Xiangqi scientific boundaries. Select the smallest observation
that resolves a concrete uncertainty; give long computations resource and
abort limits. Do not start concurrent heavy jobs or additional Agents.

The Agent and ordinary Chat advisor are research partners of nearly equal
authority. Chat may supply sources, criticism, concrete directions or advice;
neither party wins a disagreement by role alone. Record evidence and why a
suggestion is adopted, deferred or rejected. Chat is not a work-order issuer
or a publication gate. Continue independent research when Chat is unavailable.

Consult daily at 10:00 Asia/Tokyo when there is a substantive new question,
and additionally when needed. Consolidate identical questions, reconcile an
uncertain request before sending another, and do not catch up missed days.
Use `consult`, `consult-status` and `reconcile` through the calling Agent's
native app tools. Read-only local code access is unavailable in the qualified
Chat; provide bounded code content with its hash. Git is version control and
final delivery, never a prerequisite to asking a question.

Ordinary Chat and mechanical transport must not launch extra Work/worker
execution. Consult dispatch stays disabled until quota qualification is
recorded in `.local_agent/advisor.json`; do not silently relax this gate,
switch channels, resend an uncertain request or revive the archived Courier.

One native heartbeat may continue this same chat every two hours after
acceptance. It must not overlap an active turn. No Windows scheduler, old Goal,
parallel writer or restored automation runs alongside it. An explicit user
stop suspends continuation and consultation; a phase, commit or turn boundary
does not prove the scientific objective complete. Notify only meaningful
results, failures or required user decisions.

Before publication, inspect the exact outgoing diff for sensitive or unrelated
content and run relevant tests. Publish to `origin/sandbox` and verify the full
remote SHA. Promotion is a tested fast-forward of published sandbox to master
in this single repository. Never force-push. State local and published status
accurately. Never touch alphasho, its audits or other projects under this task.

Operations and capability evidence: `docs/operations/LOCAL_AGENT.md` and
`docs/operations/REBUILD_20261003.md`.
