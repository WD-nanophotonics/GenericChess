# ChatGPT review intake: GitHub and Slack

Latest direct user instruction, 2026-10-26: autonomous ChatGPT reviews may be
written directly into the project GitHub repository, including a dedicated
ChatGPT Patrol file/directory. Slack is still a review source, but is no longer
the only source. Both existing roles check both sources before choosing a new
round's research action. This is an intake change, not a research-scope change.

## Opening a work round

1. Recover the own memo, role/branch, session and scoped stops first. Preserve
   the same active/interrupted segment and confirmed work; do not credit gaps.
2. Inspect the current remote refs, not just the local checkout. Use the existing
   origin for WD-nanophotonics/GenericChess. Resolve the remote default branch
   with `git ls-remote --symref origin HEAD`, and list current heads with
   `git ls-remote --heads origin`. Compare with the last actually covered refs.
3. Locate the user-designated ChatGPT Patrol directory/file in the default,
   own-role and previously identified review branches. On first discovery or
   a missing/moved location, inspect remote tree path names for ChatGPT/Patrol
   and relevant review refs; check a relevant PR/review branch if present.
   GitHub default-branch code search alone does not cover all branches.
   The exact path/ref must come from observed remote data, not a guessed name.
4. Pin each read to its full remote commit SHA and path. For a selected branch,
   explicitly fetch its tracking ref if necessary:
   `git fetch origin refs/heads/<branch>:refs/remotes/origin/<branch>`.
   Read with `git ls-tree` and `git show <full-sha>:<path>`, or the supported
   GitHub file API at that SHA. No pull, merge, checkout, code execution or
   other-role infrastructure import is needed merely to read a review.
5. Compare file/blob hashes and diffs against the previous covered revision.
   Read new AND modified comments in full, including the index/current summary,
   linked context and supersession/correction relevant to this role. A changed
   branch tip alone is not a new review, and an old timestamp does not exclude
   an edited file. Retain deletion/rename observations and previous evidence.
6. Also check new Slack autonomous ChatGPT comments and complete relevant
   threads using SLACK_WORKFLOW.md. Existing Dot requests and the single delayed
   five-minute reply check remain in force; GitHub intake does not replace them.
7. Before research, record read/adopt/defer/reject with reasons and the actual
   next action. Update the own current Main/memo where a review changes the
   decision; do not automatically append all suggestions as an experiment queue.

## Evidence, authority and incomplete coverage

Preserve exact remote file bytes and lookup/read errors privately in the own
Git-ignored state before assessment, using an exclusive original capture and
existing atomic helpers for mutable notes. In existing review notes record the
repository, branch/ref, full commit SHA, path, blob/content hash, observed time,
previous covered revision, author/source context and coverage gaps. Do not edit
another role's memo, research state or evidence to record this check. Publication
copies still exclude personal information, passwords and credentials.

The hierarchy is: latest direct user instructions > independently initiated
ChatGPT reviews, whether on GitHub or Slack > solicited Dot replies/messages >
local proposals. Transport does not change authority. A filename, commit author,
account or TYPE marker alone cannot prove autonomous origin. Preserve context;
unresolved provenance stays unclassified. For conflicting reviews inspect their
scope, source versions, correction relationship and evidence; surface unresolved
conflicts rather than treating the newest commit timestamp as automatic truth.
No review silently expands role/scope/fees, clears a stop or replaces a separately
required user confirmation for a >=120-minute logical experiment.

If the directory is absent, access fails, a ref is stale or a thread is partial,
record exactly what was covered and what is UNKNOWN. Do not mark all GitHub
reviews checked, invent a path, overwrite a prior covered boundary, or declare
no advice exists. Use one bounded discovery attempt at the existing work start;
continue independent authorized work without empty polling or a new timer.

## Located review channel — 2026-10-26

The actual directory is `docs/reviews/chatgpt_patrol/` on remote `sandbox`.
Always resolve/fetch its CURRENT full SHA at work opening; the observation SHA
below is provenance, not a pin that may hide later reviews. DEV_AUX's own-branch
fetch alone is insufficient: explicitly fetch/read remote sandbox for this intake.

The directory appeared during this update after the initial tree/file/PR lookup
had no match. A subsequent publish fetch found remote commit
`07875ca38f44d5086a0fa394c21583e3c829bfd2` adding
`docs/reviews/chatgpt_patrol/2026-10-26_002651_JST_GITHUB_WRITE_TEST.md`.
Its exact bytes were privately preserved before full reading. It contains actual
autonomous direction review, not just a write-test receipt: prioritize checking
pure-Leaper compilation/full-search hot paths; retain p49/p53 as diagnostics.
The review states source-only inspection and no new local benchmark execution.
Each role assesses applicability independently; a read is not implementation.

Initial absence and the later discovery are both retained. Future discovery
still checks new/modified files, related refs and incomplete coverage; no guessed
path, placeholder directory, automatic merge or research-state takeover.

Historical rollout observation, before the later2026-10-26 restore: cadence was
180minutes, PRIMARY ACTIVE and DEV_AUX PAUSED. This is superseded, not current
status. See [DEV_AUX current status](DEV_AUX_CURRENT_STATUS.md) for the latest
user-authorized ACTIVE/hourly state and waiting assignment. Existing ID/chat
bindings and ordinary60–90effective-minute accounting remain. Each role publishes
only its own changes; reading a review never grants review-branch ownership.
