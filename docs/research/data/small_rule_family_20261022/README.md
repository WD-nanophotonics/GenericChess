# Small rule families, exposure and resources

`observations.json.gz` is a compact technical publication copy (about2.1MB,
about40.7MB decoded), not an additional fitness run. `manifest.json` fixes its
hash. It contains complete canonical rules and game records, exact full-state
hashes, slim observed search returns with literal PVs/cost/source, natural-root
measurements, finite references and nine producer source snapshots. Exact raw
returns, setup tracebacks, Chat/account data and session logs remain private.
The snapshots record their original relative layout; they are not automatically
executed by this reader. All currently claimed inputs and observations are here.

From the repository root, in the existing project environment:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m docs.research.data.small_rule_family_20261022.verify
```

The reader replays complete histories, checks full GameState hashes and PVs,
reproduces RNG/FLOOR choices, evaluates every measured D1 child with actual
Evaluator objects, and independently recomputes finite references using scalar
negamax. It never invokes Player fitness or training. Shared Core verification
is not an independent game engine or a WDL oracle. `qualification.json` records
one successful run on these exact bytes; current-tree publication copies have
matching hashes. This is evidence for these claims, not a universal training gate.

Counts distinguish413 new retained trajectories (281 from initial states and132
conditional continuations),12 old self-source records, and46 extra cold calls.
Forty-seven planned high-budget games were not attempted. A cooperative time
cap does not imply complete coverage or preemption. All raw UNKNOWN remains.
The16 reused discard-D1 games are already inside the192-game new family batch;
they are not16 additional games. Opposite self roles share a single tail;
other policy tails remain independent even with common prefixes or RNG seeds.
Preparation annotations inside frozen registrations are historical snapshots;
actual batch statuses, query arrays and missing slots determine execution.

The separately named `next_*` files describe a24-physical-game/32-role-frame
leaf control that is **NOT RUN**. `next_inputs.json.gz` decompresses to the exact
input hash in `next_protocol.json`; `next_runner.py` matches its preflight hash.
It expects the recorded project-root `.local_agent` layout. Both actors use a
common Static ordering adapter; Unit changes only candidate leaf values. The
code has been compiled and its24 slots/profiles/method contracts checked, with
zero Player queries. Do not confuse this future plan with executed observations.
