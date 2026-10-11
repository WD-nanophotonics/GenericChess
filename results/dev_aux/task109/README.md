# Qualified mature short-game entry

This is an auxiliary integration entry for the frozen Task099 experiment, using
the unchanged Task104 Chess reward and Task108 evolution schedule. It has not
executed a mature engine. Task110 mocks test orchestration only.

Run from the independent DEV_AUX clone, after an actual permitted Fairy material
entry has passed the twenty Task091-style legal/leaf probes:

```powershell
.venv/Scripts/python.exe results/dev_aux/task109/run.py --binary <qualified-entry> --qualification <new-qualified-record> --output results/dev_aux/<fresh-run-directory>
```

The default old qualification fails before process creation. Preserve the original
4551 record; this entry does not retry, rebuild, rename or bypass it. A future
runtime/source version needs its own honest qualification evidence. Synthetic
test probe records are temporary nonexecutable fixtures and are never runtime
qualification. No YaneuraOu/USI integration is claimed.

Each game has a fresh owned process,1thread,16MiB hash,NNUE/tablebases disabled.
Five single-type leaf probes verify the actual candidate values after configuring
the auxiliary Chess variant. The original declared1024node setting remains; final
reported nodes are recorded separately. Full initial-board move history accompanies
each search. PythonChess owns legal moves and standard automatic outcomes.

The4game pilot pairs two profiles by color/opening/random seed. A profile difference
must occur within a paired color. All paired ties stop before training. Pilot cost
includes configuration, leaf probes, gameplay, journal writes and process cleanup;
a480game projection above900seconds also stops before training. This projection
is a cost warning from four games, not a reliable upper bound on later games.

Training retains432train+48heldout calls with its own900second fuse. Pilot cost
is additional and reported separately. One global deadline is propagated through
each move/configuration wait; each UCI response has at most10seconds. Waiting polls
stop flags at100ms intervals. Completed callbacks returned after cleanup beyond
the deadline are retained as physical completions but rejected for selection.
There is no immediate cancellation or hard OS wall-clock guarantee: synchronous
process startup/pipe writes and bounded owned-process cleanup can add latency.

Append-only event records retain game start, each pending board/move and completed
game reward decomposition; interruption also saves the controller's accepted
calls and unfinished generation. Flush is not power-loss durability. A fresh output
directory is required; no automatic resume/retry or merging partial generations.
An interrupted final heldout stage cannot justify a completed learning claim.

Human-reference ratios never enter this reward/controller. Mature SEE/order/
pruning priors remain, so eventual recovery would establish conditional leaf
learning with this mature searcher. Report heldout reward components and all three
starts, including failures, before describing human-value agreement.
