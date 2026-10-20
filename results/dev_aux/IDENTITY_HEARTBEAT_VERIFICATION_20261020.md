# GC auxiliary identity and heartbeat verification — 2026-10-20

The existing heartbeat is correctly bound to the existing gc辅助 chat.
No corrupt metadata or heartbeat-routing defect was established.

- The official automation record has ID dev-aux, ACTIVE status, a 90-minute interval and target chat 01a128cf-ae2d-7352-a456-06bd38367221.
- The task API resolves that same ID to gc辅助; the current user turn and earlier delivered heartbeat turns are in that chat.
- DEV_AUX's existing role configuration selects its independent checkout and sidemission. Its active session records that same chat ID.
- The task API's initial project cwd names the primary project directory. This is an observed context field, not evidence that this auxiliary has become PRIMARY or that the heartbeat was misrouted. The earlier assertion of a routing fault was an Agent interpretation error.
- Ordinary sandbox Git status/access and remote DNS failed. Repeating the bounded checks through supported escalation succeeded: sidemission is a valid worktree and local/remote refs both resolved to 4e3c614a30fdf78eb0ead6489d17bdfb6a545dab. These failures therefore do not establish broken repository metadata or unavailable credentials/network outside the sandbox.
- No automation, role assignment, repository visibility, primary state, ACL or security control was changed by this correction.

Recovery rules now require comparing the actual target ID, configured state/interval, explicit user role assignment and own checkout role/branch before reporting a mismatch. Default cwd alone is insufficient. Use an explicit own-checkout workdir and supported escalation for enforced sandbox restrictions. Future actual contradictions must be diagnosed from their concrete evidence.

This is a bounded operational correction, not new training, a research-duration sample or a claim that all future dispatches are guaranteed.
