# Repository layout and recovery

| Location | Retained purpose |
|---|---|
| `generic_chess/` | Rules, complete state/history, search, learning, CLI, UI and Native sources |
| `scripts/` | Supported development entries and their tested imports |
| `tests/` | Product, development, workflow and semantic contracts plus fixtures |
| `tools/local_agent/` | Current role, session, Slack and publication operations |
| `docs/architecture/ADR-*` | Implemented architecture decisions |
| `docs/research/LOCAL_MAINLINE.md` | Current scientific decisions; active research owns this file |
| `docs/research/data/` | Inputs required by retained callers and regression tests |
| `results/dev_aux/` | Auxiliary learner sources, frozen current inputs and their dependencies |
| `.local_agent/` | Ignored role state, current private work and unique recovery material |

The 2026-10-21 cleanup removes closed experiments and archives from the current
tree while retaining Git history. See [the cleanup record](CLEANUP_20261021.md)
and its exact path manifest. Do not regenerate closed audit chains merely to
restore the former directory layout. A demonstrated current caller or new
decision-changing question is required before restoring an old tool or dataset.

Recover a selected file using the full base SHA in the cleanup record, for example
`git show <base-sha>:<path>`. Inspect it in a private investigation directory;
do not overwrite current research or its frozen inputs. Uncommitted unique
payloads removed by this cleanup have a verified ignored recovery ZIP.

The user chose to keep existing researchers running. Their active mainline,
collaboration log, task2633–2636 files, session state, stops, pilots and recurrence
are preserved. Some mainline-linked reports consequently remain until their
owner can compact that file safely. This cleanup does not change search or
learning algorithms, default budgets, models, or repository visibility.
