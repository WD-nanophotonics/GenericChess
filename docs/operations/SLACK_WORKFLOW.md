# GenericChess Slack collaboration workflow â€”2026-10-24

## Review sources and current authority

The2026-10-26 user correction adds GitHub ChatGPT Patrol reviews at every work
opening. Follow [CHATGPT_REVIEW_WORKFLOW.md](CHATGPT_REVIEW_WORKFLOW.md) for
remote discovery, full-SHA reads, changed-file coverage and adoption. This file
continues to govern Slack transport; Slack is not the sole review source.

## Restored Dot contact

The user lifted the Dot pause on2026-10-24. Direct two-way Dot consultation,
including bounded real-time exchange, is restored in existing NanoMelon
`#generic-chess` (`C0C6L21UU20`). Outbound collaboration addresses Dot directly;
a separate asynchronous comment-style report is no longer mandatory. The old
Oct20 pause and Oct23 asynchronous-only/no-mention/single-message rules are
superseded, not alternative live policies. No new channel/chat/worker/scheduler.

Priority: latest direct user instructions > independently initiated ChatGPT
GitHub or Slack review comments > Dot's solicited replies/messages > local proposals.
Continue reading ChatGPT's autonomous reviews; an immediate answer to a local
question is not that higher-priority autonomous review. Shared account IDs and
TYPE=CHAT_REPLY/DOT_REPLY markers are transport/provenance clues, not proof of
independent authorship or authority. Save origin, timestamp, full thread, context
and uncertainty. Unknown origin stays unclassified. Record adopt/defer/reject,
reasons and execution effects. If evidence challenges advice, surface the conflict
instead of silently treating speculation as fact. Neither advisor expands user
scope, budgets, AUX authority or platform permissions. Dot cannot override the
pure-Leaper-first direction or authorize >=120minute runs on the user's behalf.

## Reading and actual Slack interactions

At each existing60minute patrol/manual work start, read new autonomous ChatGPT
project comments and complete relevant threads once; retain coverage boundaries
and any gaps. A direct request for latest messages permits a fresh bounded read.
User correction2026-10-25: every NEW work round must initiate a fresh mailbox
`TYPE=AGENT_REQUEST` root addressed to Dot. Old-thread reads and AGENT_FOLLOWUP
messages do not substitute for the request trigger. Prepare the actual next-step
plan, evidence, own judgment and any real decision question; publish referenced
work and verify the full remote SHA BEFORE sending. Record session UUID, request
ID and verified root in local evidence/memo. Resume the same active round without
duplicating a verified request. If send is uncertain reconcile it, never blindly
resend; record a real failure and continue independent work. This requirement
replaces optional-only start consultation. Send at the start, not after doing
the research or at round end: the already reviewed/published checkpoint plus
the current executable plan suffices; no new result is required first. No
response is a work gate. During
later reads/sends consider a concrete question, especially doubts about
correctness, interpretation or method; do not fabricate a scientific question. Relevant active Dot thread replies and bounded substantive
follow-ups may be read/sent within the work segment; the ordinary patrol cadence
is not a ban on real-time dialogue. Do not add empty repeated polls, chasing,
self-reply loops or idle waiting. If no reply, continue independent useful work;
contact permission does not prove current Dot availability or local push delivery.

Use the existing Slack plugin/channel/mailbox, identity binding and supported
thread transport. Mentions are allowed when an existing verified Dot routing ID
requires them; never invent an ID or mention a different account to wake it.
Current shared-account channel routing remains unchanged. Request TYPE=DOT_REPLY
and the immutable REQUEST_ID for solicited Dot replies. Existing CHAT_REPLY and
old DOT_REPLY remain compatible; they do not determine scientific authority.
Keep meaningful progress/negative results/UNKNOWN/cost/next action in substantive
conversation, with fixed published source/full verified remote SHA. Each send,
including follow-ups, requires reviewed content and push/SHA verification first.
A real refusal is reported and diagnosed, never bypassed or retried blindly.


User correction2026-10-25: at the opening of EVERY logical Slack interaction,
check newly available Chat comments and complete relevant threads, not only at
the scheduled patrol. A send/readback/five-minute follow-up belonging to that
interaction does not recursively open another interaction or require an endless
channel-read loop. Preserve raw originals first; record newest covered root and
thread boundaries, including replies on relevant existing comments.
After each Dot send, record sent UTC and due UTC (+5minutes), continue useful
independent work, then perform ONE bounded reply check at about five minutes.
The immediate delivery/payload readback does not replace this delayed reply check.
If that check opens a fresh Slack interaction, check new Chat comments there too.
Record checked UTC/result; no repeated polling, waiting for a reply, new worker
or timer. On a real interruption, preserve the due check for same-round resume;
do not claim it was executed. Replies retain their solicited Dot authority.

User clarification2026-10-25: TYPE=AGENT_REQUEST requires a Dot reply. Other
message types, including AGENT_FOLLOWUP, allow a discretionary reply: neither
mandatory response nor mandatory silence. This is the requested collaboration
contract, not proof of delivery or a guaranteed local enforcement mechanism.
Five minutes is the single delayed-check target, NOT a response expiry: retain
late replies and read them at the next meaningful interaction. No missing reply
creates a research/publication gate or permission to poll repeatedly.

## Exact originals before evaluation

Save the exact raw, project-related read in Git-ignored `.local_agent` BEFORE
parsing, reconciling or adopting advice. Keep timestamps as exact strings. For a
long thread request small pages (limit 20) and follow the returned cursor chain;
validate actual reply counts using the existing strict parser. Preserve partial,
refused and failed reads as evidence. If the connected read path is unavailable,
report the visibility limit and do not claim that the Chat is clear or healthy.

Preflight the save/serialization path with synthetic Unicode and quoted text
before making the patrol read. In functions.exec, immediately `store` the exact
returned object under a project-specific key BEFORE any encoding, shell call or
assessment, then save its lossless JSON privately. Do not rely on an unavailable
global such as `btoa`, or interpolate untrusted message text as shell code.
For chunked capture, check each native save exit code before continuing and
verify the assembled byte count against the retained serialization before
saving the final original. Refuse an empty or incomplete assembly. Exercise the
same chunk-save expression in the synthetic preflight: a separate simpler call
does not detect a syntax error in the real capture command. If
disk capture fails, retry saving the SAME retained return after diagnosing the
serializer; do not make another channel read. Only assess after the private save
succeeds. If the returned object was lost, preserve the failure and leave that
coverage boundary open; do not advance the last-complete boundary or claim the
messages were reviewed. Read again at the next permitted patrol, not in a loop.

Use the active session UUID plus a FRESH read UUID for every logical patrol
capture, with distinct channel/thread/page names. A time-only suffix such as
1935 repeats on another day; a session UUID alone can repeat after resumption.
Before a read, preflight a separate synthetic path through
`tools.local_agent.slack_transport.save_plugin_original(path, payload_bytes)`.
Use that helper for the final lossless raw bytes as well: it requires an ignored
path under this checkout .local_agent, creates exclusively, and refuses different
bytes at an existing path. An identical retry confirms bytes without rewriting.
Do not use WriteAllBytes/WriteAllText/Path.write_bytes or mutable write_json to
replace an original. Mutable assessments still use write_json.
If a collision is refused, keep the SAME retained tool return and save it under
a fresh read UUID; do not reread Slack. A partial failed write is also preserved.
Never reconstruct a lost wrapper and call it the exact original. The observed
2026-10-22 collision lost the preceding day's channel-wrapper original while
its complete thread original remained; the provenance amendment records that
limit. This is a data-preservation rule, not a send/approval/worker mechanism.

## Delivery and pending requests

The repository remains PUBLIC. Inspect outgoing actual content and exclude
personal information/passwords/credentials; sanitize publication copies only.
Preserve exact private originals in ignored .local_agent. Publish reviewed role
work with generic-chess-local.cmd publish --tests <relevant targets>; verify the
FULL origin/sandbox SHA before a send. No force-push or cross-checkout delivery.

Use the existing mailbox: prepare immutable request, begin-send once, store the
exact plugin result before encoding, bind a successful receipt and verify parent
payload by bounded thread readback. Preserve old request bodies, content hashes,
roots and revisions. Never rewrite historical requests to address Dot or reinterpret
old advice as autonomous review. A verified-delivered PENDING request can coexist
with a distinct substantive request via existing asynchronous_progress_enabled;
that legacy-named flag is transport concurrency, not an asynchronous-only policy.
PREPARED/SEND_UNCERTAIN/unverified sends require reconciliation, no automatic
resend. Reply in the known thread for a genuine follow-up after content/push/SHA
checks and preserve its exact receipt; never silently change the parent payload.
Follow unresolved questions during relevant dialogue or the next original patrol;
reading, adopting and executing are distinct. No reply is a research/publication
gate. >=120minute runs still need the user's confirmation, not Dot approval.
