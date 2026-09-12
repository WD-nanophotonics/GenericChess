# GenericChess F93 release-candidate promotion gate

## Immutable candidate binding

- Master SHA: `44fce4f9dfeee0ef9480597c7ab34195db984100`
- Tested product SHA: `fd14151f4f489e24252dd440de0b38f0a77bf127`
- Final sandbox SHA: `fd14151f4f489e24252dd440de0b38f0a77bf127`
- Direct `origin` verification: `origin/master` is `44fce4f...` and
  `origin/sandbox` is `fd14151f...`.
- `git merge-base origin/master HEAD` equals master; comparison is
  `ahead=464, behind=0`; master is an ancestor of the candidate
  (`FAST_FORWARD_ANCESTOR=TRUE`).

## Final verification

Command executed once at the candidate SHA:

`.venv\\Scripts\\python.exe -m pytest -q -p no:cacheprovider`

Result: 1,950 passed, 14 failed, and 3 skipped out of 1,967 collected tests.
The failures were confined to the existing F24F semantic perft expectation,
frozen historical-source/manifest checks (F40/F41/F48/H48/H49), environment-
bound H50B1 ABI helper compilation, and an external AlphaSho configuration
path used by the round-five corrective harness. No F87A-F92 product gate
regression was observed; F87A playability, F88 desktop semantic human
acceptance, F89 real desktop semantic AI acceptance, F90 built-in record
reopen, F91 release-version authority, and F92 non-editable wheel acceptance
were previously accepted at their immutable checkpoints, with F92’s final
code checkpoint being this candidate.

## Decision

`PROMOTION_NOT_READY`.

The candidate is fast-forwardable and the release/product gates are complete,
but the required full-suite result is not green. This F93 gate made no runtime
or product-code changes; the only intended final-phase artifact is this
durable report. Promotion remains blocked by the repository’s explicit
sandbox-to-master approval contract, in addition to the failing full-suite
evidence above.
