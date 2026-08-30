# ADR-056: Chat authority over local artifact publication defaults

- Status: Accepted
- Date: 2026-08-30
- Scope: Courier review, artifact publication, and repository control policy

## Decision

For a Courier task, authority is ordered as: explicit user instruction, the
receipt-bound Chat work order, the local Agent, then repository hygiene
defaults. This resolves the specific case where Chat requires a generated full
report or other audit artifact to be uploaded and pushed while an older local
rule classifies that file type as raw or transient.

The local exclusion remains the default for unrequested output. A user or Chat
work order that names an exact path overrides it for that path only. The Agent
must preserve the exact artifact, force-add it when an ignore rule hides it,
run the required tests, publish `origin/sandbox`, verify the full SHA, and
close out that SHA. It must not expand the exception to neighboring files,
whole generated directories, unrelated Courier state, or a substitute
transport.

## Review control

The review chain is machine-checkable at the workflow level:

1. The work order names the exact artifact and scope.
2. The artifact is generated or preserved without hand-editing its reported
   results.
3. Required tests and path-level inspection run before staging.
4. The named path is staged even if local ignore policy requires force-add.
5. Commit, publish, exact local/remote SHA verification, and closeout follow.

This policy does not authorize production evaluator/search/Native changes,
promotion without exact Chat approval, broad directory uploads, or mode
switches. It changes only which authority decides whether a specifically
named review artifact is publishable.
