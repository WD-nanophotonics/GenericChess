# Role-local identity and environment recovery

## Concrete repaired defects

Repeated reports inferred PRIMARY ownership from the app's default cwd even
though the user assigned this existing chat to DEV_AUX. Real local sandbox
permission denials were mixed with unsupported heartbeat/remote diagnoses.
The own status helper also queried origin/sandbox and the old consultation
ledger; the batch entry silently returned2 for inherited publish/promote.
Those are repaired in this auxiliary checkout. No PRIMARY code/state, app
binding, filesystem security or schedule was changed by this repair.

## Supported entry and outcomes

- Use the absolute own dev-aux-local.cmd entry. It anchors cwd to its own
  checkout; module ROOT is derived from its own source, never the app cwd.
- doctor verifies expected DEV_AUX and sidemission against own role record,
  actual Git root/branch and configured checkout. MATCH, MISMATCH and UNKNOWN
  are separate. Missing/unreadable records never assign the PRIMARY role.
- session start requires a matching identity before creating/resuming state.
  Stops retain priority. The default cwd cannot override a verified role.
- doctor --check-heartbeat compares only the existing auxiliary automation's
  target with the own chat record. Read failure is UNKNOWN and does not become
  a target mismatch. It does not update/rebind/pause any schedule. An unset
  CODEX_HOME uses the exact user .codex path; it never starts a root search.
- doctor --check-remote checks only origin refs/heads/sidemission. DIFFERENT
  heads are transport facts, not an identity failure. An unpublished local
  commit can legitimately differ from the remote. MATCH requires full SHAs.
- status uses origin/sidemission and current mailbox state, without consulting
  the legacy Dot ledger or querying the PRIMARY branch.
- inherited publish/promote are rejected explicitly: review/test, then commit
  and git push origin sidemission in separate checked calls. Never force or
  substitute sandbox/master. Direct Python CLI dispatch also blocks the old
  PRIMARY publisher for this role.

## Error handling and evidence

For a denial, preserve the actual command, phase, error/exit and scoped effect.
A local index permission error is not a remote-push error. Remote authentication,
network and history failures have separate labels. Use supported escalation for
this own checkout when ordinary access is denied; a local permission error does
not establish broken Windows ACLs, wrong heartbeat target or missing user consent.
Do not call a live executor allowlist stale without evidence of the cause.

Try the supported correction and recheck the actual operation. A successful
correction supersedes the current error state while preserving historical raw
evidence. Report a continuing blocker only with current diagnosis, recovery
attempts and exact necessary user action; do not repeat old failures or request
new authorization already granted. The CLI cannot prevent false natural-language
claims if a caller bypasses it: recovery must use this tested entry and reports
must reference its actual results.

## Verification

131 workflow tests pass, including PRIMARY default cwd with valid AUX identity,
actual role/branch/checkout mismatch, unreadable/missing records, access recovery,
separate heartbeat mismatch/unknown, remote failure and explicit inherited-route
rejection. Live doctor verifies own identity, existing heartbeat target and full
remote SHA. Tests do not write PRIMARY files or contact another Agent.

Configuration repair is not a60-minute research sample. After publication,
start a genuine owned session/work interval, obey existing experiment caps,
perform useful scientific work and accumulate3600 confirmed seconds before a
normal finish. A heartbeat that only plans/inspects under Plan Mode does not
meet that research obligation and must not claim it did. Plan Mode is a developer
constraint; a scheduler prompt cannot override it or switch modes. Once execution
is enabled, proceed without another permission queue.
