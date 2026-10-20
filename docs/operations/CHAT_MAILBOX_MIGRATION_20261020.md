# Chat mailbox migration verification — 2026-10-20

## Decision and implementation
The user's all-role communication decision replaces realtime Dot with periodic
Chat mailbox exchange. Shared implementation/policy revision:
a2faee270efce9cdf9b5204a67e09a8efbb98ac3 on origin/sidemission.
Default unmigrated configs cannot dispatch new Dot requests. Legacy protocol
regressions use an explicit historical mode; old ledgers/manual remain intact.
The new mailbox preserves exact raw data before coverage/adoption, saves
version-bound adopt/defer/reject decisions, and carries deferred comments into
later probes. Plain-language supplements under Chat-origin threads are reviewed
without requiring DOT_REPLY, a Dot identity or immediate response.
One logical read permits channel/thread pagination. One prepared report can
dispatch once; uncertain delivery reconciles only at the next probe.

## Validation
The complete tests/workflow suite passes 99 tests, including empty/late/edited
comments, thread pagination, duplicate probe calls, incomplete coverage,
raw-before-cursor persistence, uncertain-send readback, wrong receipt, role stops,
migration idempotence and legacy pending preservation. The private-fixture
Windows path-length failure was fixed by using content-hash raw artifact names.
No product/default/UI or scientific frozen artifact was changed.

## Real DEV_AUX probe
- Probe: GC-MAIL-6776a15223e84c92b819a5874326055e.
- Prior verified channel boundary: 1792442676.061439; new root coverage:
  1792463224.074019. The fetched channel page crossed the prior boundary.
- Read the complete relevant current research thread and the Chat-comment
  thread including its plain-language correcting supplement. Channel pagination
  stopped at the prior verified coverage, rather than traversing old history.
- Exact originals, config backup, coverage and decisions remain Git-ignored
  in DEV_AUX's local state; no raw Slack/account data is included here.
- Seven comments/supplements were reviewed: 3 adopted, 4 deferred with reasons.
  The tight one-sided UNKNOWN-bound audit is accepted as a future independent
  check; no old conclusion was changed just by reading the suggestion.
  The correcting supplement keeps traditional Chess prices descriptive only,
  never a training target, success gate or seed selection rule.
- One report was sent to the sole authorized project channel, addressed CHAT:
  [successful send](https://nanomelon.slack.com/archives/C0C6L21UU20/p1792471421105239).
  Its successful tool receipt verifies route and timestamp; state is SENT.
  No post-send read was performed. Chat reading/adoption/execution is unverified.

## Runtime and rollout
DEV_AUX's own config now uses chat_mailbox with Dot disabled. Its existing
heartbeat remains ACTIVE, every 90 minutes, targeting the same chat; only its
communication instructions changed. Original configuration/prompt are preserved
privately. Existing stop scopes, research clocks and frozen caps are retained.
This user-requested configuration/validation is not a research-duration sample.
PRIMARY_SANDBOX and DEEPSEEK_AUX owners apply the published shared protocol and
run mailbox migrate in their own checkouts, then update their own existing
probe prompts. Their private state and schedules were not changed by DEV_AUX.
Expected runs below 120 minutes retain autonomous authority. Runs at/above
120 minutes await explicit Chat mailbox assessment addressing scope and budget;
shorter independent work continues while waiting. No new worker or schedule.
