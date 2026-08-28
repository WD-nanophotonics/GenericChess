# Historical material index

The live branches retain product code, architecture decisions, regression tests,
and compact conclusions. Large generated evidence, old inbox deliveries, and
one-off review packages were removed from current trees without rewriting Git
history.

## Recovery points

- Retired Chat/Gmail coordination history:
  `archive/chat-legacy-20260829` at
  `84423c27fee5827f1d2e54a8d1a63365d0f51d54`.
- Formal baseline immediately before workflow cleanup:
  `4f1d03a308f5fd04a01bbd980c7411888ea1ed9d`.
- Sandbox F22 audit baseline:
  `3281b3cfd0a495b0fe75ce8a3c0a28cc20343b38`.

Use `git show <commit>:<path>` or a temporary detached worktree to inspect old
material. Do not restore legacy Gmail transport or generated artifact trees to
an active branch.

The removed local `chat` worktree also contained an uncommitted partial migration
from `gc-bridge` to `gmail-courier ensure/once`. That intermediate interface was
already superseded by ChatCourier's typed request lifecycle and was intentionally
not committed.
