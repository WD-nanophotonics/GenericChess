# Local GenericChess workflow

Policy: `AGENTS.md`. Research route: `docs/research/LOCAL_MAINLINE.md`. Operations: `docs/operations/LOCAL_AGENT.md`.

The local agent chooses a bounded research step, implements or analyzes it, tests what changed, and records the result. It may commit and publish a tested checkpoint to `origin/sandbox`; it may fast-forward a ready checkpoint to `master`. Chat receives one sourced scientific consultation on each active Tokyo weekday, never more than one new request per date. The two-hour scheduled check observes health and verifies this task's Goal when available.

Commands: `generic-chess-local.cmd status`, `patrol`, `consult --question-file <path>`, `consult-status`, `publish --tests <target>`, and `promote --candidate <full-sha> --tests <target>`. The old `generic-chess-flow.cmd` entry point is retired.
