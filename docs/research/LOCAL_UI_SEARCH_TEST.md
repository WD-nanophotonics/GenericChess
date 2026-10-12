# Historical work-machine UI consumer test

This is a historical work-machine experiment, not the current user integration
route or a delivery to another computer. UI Test is maintained on the user
computer; PRIMARY supplies reviewed backend changes through sandbox, and
DEV_AUX supplies its own sidemission validation. Existing copies remain as
evidence. See [backend handoff](../operations/BACKEND_HANDOFF.md) for actual
public entry points, parameters and limits. No UI-copy maintenance is selected.

The historical local test copy kept the user frontend at
99c97bb87474c44af94c76571f326ef8a41eb898 and overlays the reviewed current
sandbox backend in an ignored directory. It does not overwrite ui-test,
a user's checkout, historical exports or game saves. This is a local manual
verification build, not a remote UI-branch update.

Start from the project root:

    .venv\Scripts\python.exe .local_agent/ui-native-q0-test-20261012/run_native_q0_ui_test.py --port 8785

Or double-click .local_agent/ui-native-q0-test-20261012/start.cmd.
The launcher opens the loopback page; Ctrl+C stops it. The test service used
for verification has been stopped. Its next normal launch is ready.

The visible banner states that Chess uses Native q0/material-only evaluation,
exact-root pruning, current canonical reconstruction/threshold confirmation,
1MiB TT and min-depth2 ordering. The controller explicitly sets q0/hard0 and
maxdepth12 for this named test; the selected 0.5/1/3-second budget remains.
These choices differ from the Core q4 dynamic evaluator and are not a promise
of improved play. Shogi declarations and generated legacy rules currently use
the complete Core q4/hard8 UI player. Actual backend is also exposed in the
API state ai.backend. No hidden unsupported-q4 Native fallback is asserted.

The frontend was built from its fixed dependencies. Actual worker submission,
pause/restart cancellation and same current-state commit checks passed on
Chess/Shogi/hybrid. Real HTTP page/banner/health and all three first moves
passed; the declared 4x4 hybrid seed42 checkmated on its first move, a genuine
terminal outcome with no next actions. Subsequent actual in-app browser observation and screenshots verify Chess setup,\nAI b1-c3, reload/continue, human e7-e5 and Native reply g1-h3 with three-step\nhistory. An old CoreAI label was observed and corrected only in this local\ntest copy to follow ai.backend; the setup text now declares the profile.\nThis does not extend the rendered check to all Shogi/generated interactions.

Manual checks:
1. Play Chess PVE as either color; confirm legal AI replies and the explicit
   test banner. Export and reopen a continuation bundle.
2. Pause AI during thinking, restart, then resume; an old move must not appear
   on the restarted game.
3. Try Shogi and a generated game; confirm Core backend and promotion/hand
   interactions. Report the exported rules/record and steps for any defect.

The default frozen UI branch remains separate. No private immediate-win stop,
root-only ordering prototype, q4 refresh or unfinished Native declaration
adapter is enabled. Rollback is simply to launch the user's original ui-test
checkout normally; no engine changes or local saves must be deleted.

Only Agent-written bridge fragments, hashes and synthetic verification summary
are published to sandbox. User UI source/dependencies/full copies, private game
saves, raw Slack/account data and native binaries remain local. The local paths
do not give Dot filesystem access; it receives fixed-revision report links.
