# Local GenericChess workflow

Policy: `AGENTS.md`. Research route: `docs/research/LOCAL_MAINLINE.md`. Agent's short external memory: `.local_agent/NEXT_WORK.md`. Operations: `docs/operations/LOCAL_AGENT.md`.

The local agent works in ordinary task mode. It checks its earlier next-work notes against current evidence, then chooses a bounded research step, implements or analyzes it, tests what changed, records the result, and continues useful work. The notes are revisable memory, not externally assigned orders or a stage limit. It may commit and publish a tested checkpoint to `origin/sandbox`; it may fast-forward a ready checkpoint to `master`. Chat receives one sourced scientific consultation on each active Tokyo weekday, never more than one new request per date. The two-hour scheduled turn checks progress and continues through useful bounded stages while resources allow. Only sufficient evidence that the mainline objective is complete ends the task; a stage or turn boundary leaves it open with updated memory.

Commands: `generic-chess-local.cmd status`, `patrol`, `consult --question-file <path>`, `consult-status`, `publish --tests <target>`, and `promote --candidate <full-sha> --tests <target>`. The old `generic-chess-flow.cmd` entry point is retired.
The two-hour trigger is the Windows scheduled task `GenericChess-Local-Agent-Two-Hour`; its runner queues work to this same Codex thread. See the operations manual for dispatch verification.
