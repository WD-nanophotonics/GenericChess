# GenericChess F86J controlled partial-reversibility mobility design

Status: static-only controlled design checkpoint. This is a zero-dynamic-compute
follow-on to the accepted F86I evidence. The F86J prep manifest was published
at `1c00612b44ee5fee3a050afa0dd6b4d2f79239cf`; the result checkpoint is the
subsequent commit containing this report and `results.json`.

## Design authority

F86J keeps the eight F86I/F86C source samples, material, source rulesets, and
Anchor transform. The candidate profile is
`ORTHO4_PLUS_FIRST_ATOM_REVERSE_ORDINARY`:

- Anchor movement is exactly ORTHO4: `(1,0),(-1,0),(0,1),(0,-1)`.
- For each ordinary type, the first atom in the frozen source order is selected.
- Only that atom's exact reverse counterpart is appended, if absent.
- Source atoms remain an unchanged prefix; the appended atoms are deduplicated
  and deterministically ordered.
- No promotion, drops, HOME rules, FULL8 Anchor moves, material changes, or
  production/default generator changes are introduced.

This is deliberately between the F86H directional ordinary graph and F86I's
full reverse closure. The F86I full-closure cohort produced one checkmate and
15 censored `ongoing@32` games, so the cheapest sufficient next decision is a
static mechanism and mate-geometry gate before authorizing any new games.

| sample | candidate fingerprint | source ordinary atoms | candidate ordinary atoms | reverse atoms added |
|---|---|---:|---:|---:|
| V4-2 | `86581cc73bc9c2146eb5117384be4a717fa3bd8a87c2e123c6470434bbe47b01` | 1 | 2 | 1 |
| V4-3 | `1c9b0970746e87b3b134d187428496013076c16223cfbf3093fdf2724488fd76` | 5 | 8 | 3 |
| V4-4 | `ed6784e034a0bd625be4d69bace6a459c9d16d590abf93066025115603ed0fde` | 1 | 2 | 1 |
| V4-5 | `effc9905d3b3afd3d67d4696ec0c259531f05feb380479f590179fb9fac063b1` | 1 | 2 | 1 |
| V5-2 | `0c6aa8afa8b571c4cad8bead2962367a73abc4c94c6aef9e227b05fd81a6422e` | 2 | 3 | 1 |
| V5-3 | `74db9dbacc5234524b844062609f5aa4e273a8cef2627bd6d137be07be45ae35` | 5 | 7 | 2 |
| V5-4 | `9e4c3f8a9bc5279ad5d8464d6bdadaac1e6f138f4e90812dcfc2cb71660dfd07` | 2 | 3 | 1 |
| V5-5 | `19e70cb043da1f4b04501a565b3ea5c0330dce92f61bf8b09dd73030290e17e5` | 4 | 6 | 2 |

## Static mechanism result

The empty-board ordinary mobility graph was evaluated for all eight frozen
candidate rulesets. Partial reversal removes the monotone-DAG property in all
eight samples, but unlike F86I it does not produce direct reverse coverage of
every ordinary edge.

| sample | ordinary sink fraction | direct reverse-edge fraction | nontrivial SCC fraction | monotone DAG |
|---|---:|---:|---:|---|
| V4-2 | 0.000 | 1.000 | 1.000 | false |
| V4-3 | 0.0625 | 0.675 | 0.875 | false |
| V4-4 | 0.125 | 1.000 | 0.875 | false |
| V4-5 | 0.125 | 1.000 | 0.875 | false |
| V5-2 | 0.080 | 0.7804878049 | 0.920 | false |
| V5-3 | 0.040 | 0.6095238095 | 0.920 | false |
| V5-4 | 0.040 | 0.3902439024 | 0.920 | false |
| V5-5 | 0.040 | 0.5871559633 | 0.960 | false |

The rows with direct reverse fraction `1.0` are small source cases where the
selected reverse atom happens to close the only ordinary atom. The V4-3 and
V5-3 multi-atom cases demonstrate the intended partial regime: the directional
DAG obstruction is removed while several ordinary edges remain one-way.

## Targeted static mate-capacity gate

The existing F86F/F86H predicate and F86H optimistic kinematic analysis were
reused only for V4-3 and V5-3. The per-cell cap was 2,048 and the total cap
was 4,096; no dynamic games or tactical probes were run.

| sample | candidate checks | validated positions | templates | truncated | ordinary assignment reachable | joint kinematic |
|---|---:|---:|---:|---|---:|---:|
| V4-3 | 288 | 233 | 23 | no | 0 | 0 |
| V5-3 | 2,048 | 1,871 | 98 | yes | 0 | 0 |

Both targeted cells route to
`PARTIAL_REVERSIBILITY_INSUFFICIENT_KINEMATICALLY`. The partial design
therefore removes the graph-level directional obstruction without recovering a
known static mate-template route from the frozen opening. V5-3 remains a
cap-truncated census and is not interpreted as a complete negative over all
possible templates.

## Scope and evidence boundary

This checkpoint used zero new games, policy trajectories, tactical nodes, BFS,
teacher/search compute, training, or F85 compute. The default generator is
unchanged. Dynamic evaluation is intentionally deferred because the static
first gate did not show targeted kinematic rescue and F86I already established
that full reverse closure creates censored nontermination risk.

Durable evidence:

- Manifest: `artifacts/f86j_partial_reversibility_design/manifest.json`
- Static summary: `artifacts/f86j_partial_reversibility_design/results.json`
- Runner: `scripts/f86j_partial_reversibility_design.py`
- Contracts: `tests/test_f86j_partial_reversibility_design.py`

Overall F86J routing:

```text
mechanism: PARTIAL_REVERSIBILITY_REMOVES_DAG_WITHOUT_FULL_REVERSE_CLOSURE
V4-3: PARTIAL_REVERSIBILITY_INSUFFICIENT_KINEMATICALLY
V5-3: PARTIAL_REVERSIBILITY_INSUFFICIENT_KINEMATICALLY (census truncated)
dynamic: NOT_RUN_BY_CHEAP_STATIC_FIRST_GATE
```
