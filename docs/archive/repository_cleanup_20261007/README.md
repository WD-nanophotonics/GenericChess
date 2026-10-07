# Repository cleanup snapshot:20261007

History only. No archived rule, cap, approval gate or old experiment is an active
requirement. The current policies and mainline live outside this directory.

Exact pre-cleanup source/test/research/output snapshot:
E:/CodexArchive/20261007-structure/GenericChess/snapshot.zip
SHA256:6b7af1ee7fd0c8167527896435d8b11d01cd0b5f6dfc194c6b476e5ef0ff0944
5123files,142902777uncompressed bytes; ZIP17429538bytes. Original path/file hashes
are in the neighboring index.json. The ignored local duplicate is
.local_agent/layout-backup-20261007/snapshot.zip. Every member was extracted into
an isolated local verification directory and compared byte/hash before retirement;
the durable E copy was separately hash/size verified. No App credentials, Slack
inbox or other project's files are included. Opaque copying is not holdout exposure.

- retired-sources.json: old runners, receipt tests and obsolete workflow tools.
- retired-research.json: superseded notes/data; live exceptions reflect actual callers/current evidence.
- retired-outputs.json: old generated artifacts/checkpoints.
- retired-local-history.json: old private one-off producers/reviews and root test output,
  backed by E:/CodexArchive/20261007-structure/GenericChess/local-history.zip
  SHA256:e3c28538a4a79a2c66f872ce1cc521aaaf57c3f40359f0389061d780e4354ce6.
- retired-operations.json: same-byte dated Slack cutover receipt, stored here as text.
- ../continuation_20261007/index.json: exact previous941-line mainline snapshot.

Git base before cleanup:04b411d2a6bc4c6c96ab193bee2ee400251eb433.
Unchanged product modules are recoverable there; the ZIP also covers local outputs.

Recovery: verify the ZIP SHA, extract into a fresh temporary directory, check the
selected file against index.json, and inspect it there. When reproducing an old
experiment, recover its same-era dependencies/inputs and conditions together.
Do not copy old policies or restore all tests to default collection. Restore live
files only as a deliberate reviewed change; cleanup did not rewrite Git history.

Validation receipts and current collection outcomes are recorded in acceptance.json
once complete. Source hashes prove preservation; tests and entry smoke checks
prove the selected live route, not all possible historical runners.
