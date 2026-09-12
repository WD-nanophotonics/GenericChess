# GenericChess F93 release-candidate promotion gate

## Immutable candidate binding

- Master SHA: `44fce4f9dfeee0ef9480597c7ab34195db984100`
- Tested product SHA: `4405b62af21033c6a1374086d051d0caaf0de29a`
- Final sandbox SHA: recorded below after this durable report commit.
- Direct `origin` verification: `origin/master` is `44fce4f...` and
  final `origin/sandbox` SHA is recorded after this durable report commit.
- `git merge-base origin/master HEAD` equals master; comparison is
  `ahead=466, behind=0` after the code and report commits; master is an ancestor of the candidate
  (`FAST_FORWARD_ANCESTOR=TRUE`).

## Final verification

Command executed once after the R1 repairs at tested product SHA
`4405b62af21033c6a1374086d051d0caaf0de29a`:

`.venv\\Scripts\\python.exe -m pytest -q -p no:cacheprovider`

Result: 1,963 passed, 0 failed, and 4 skipped out of 1,967 collected tests.
The four skips are environment/optional-suite skips; the optional AlphaSho
evaluation suite is not present on this machine. The R1 repairs were limited
to historical-authority assertions, synthetic H49B test doubles, the
historical F24F evidence fixture, a writable Zig cache location, and the
optional external-suite skip. No F87A-F92 product gate regression was
observed; F87A playability, F88 desktop semantic human acceptance, F89 real
desktop semantic AI acceptance, F90 built-in record reopen, F91 release-
version authority, and F92 non-editable wheel acceptance remain accepted at
their immutable checkpoints.

## Decision

`PROMOTION_READY`.

The candidate is fast-forwardable and the release/product gates are complete.
The F93-R1 gate made no runtime or product-code changes. The final sandbox SHA
must be bound to an explicit Chat promotion approval before any master update.
