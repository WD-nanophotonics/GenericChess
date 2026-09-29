# Chess arrival deadline crossing

## Question and observation

The frozen first-action service prior fails Chess and barely changes
V2C outside the bishop's permanent color class. Does merely replacing
unlimited access with a finite move deadline give a stable rule-only
ordering of bishop and knight target access?

`scripts/audit_chess_arrival_profile.py` uses only the already-frozen
positive directed Chess board topology in
`.generic_chess_flow/static-material-domain-fragmentation-topology.json`
(SHA-256 `4e72d518bebcf398f077b2ed587562b7529df10f53e1ce5f4cea9ab5b4d99c3d`).
For each of two owners and 64 possible sources, breadth-first search
finds the minimum number of *own-piece moves* to every target. The
table counts the source itself at zero moves, weights all source-target
pairs equally, and gives exact fractions. Occupancy merely established
positive topology edges; this calculation has no sequential blocker,
enemy reply, survival, or target-selection model. It reads no human
material reference.

| Own-piece move deadline | Bishop reachable pairs | Knight reachable pairs |
| ---: | ---: | ---: |
| 0 | 1/64 | 1/64 |
| 1 | 39/256 | 25/256 |
| 2 | 1/2 | 185/512 |
| 3 | 1/2 | 377/512 |
| 4 | 1/2 | 979/1024 |
| 5 | 1/2 | 1023/1024 |
| 6 or more | 1/2 | 1 |

The bishop leads through two own moves; the knight leads from three.
The bishop reaches every square of its starting color within two moves
and never crosses color. The knight's full-board reach takes up to six.
This exact reversal shows why a finite deadline is consequential, but
the RuleSet does not specify which deadline, how many opponent moves
intervene, or the utility of arrival. Selecting two or three moves to
repair a material ratio would be another fitted context assumption.
This check is a temporal diagnostic, not a new material prior.

## Decision

The existing `SEARCH_DEPLOYMENT_CONTRACT_AUDIT.md` has already checked
the engine boundary: iterative deepening, time/node stops, and Python
quiescence do not provide a universal fixed arrival deadline. Repeating
that audit would add no evidence. A defensible replacement needs an
independently specified task or deployment distribution, including the
cost and survival of successive moves. Until then, preserve the
conditional ordering instead of converting this curve into a scalar.
