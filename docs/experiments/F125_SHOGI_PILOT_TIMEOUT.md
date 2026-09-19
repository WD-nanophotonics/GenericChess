# F125 Standard Shogi pilot: bounded timeout

## Outcome

The Supervisor-authorized Standard Shogi 64-decision-root pilot did not produce a scientific classification. Both bounded invocations reached the declared 60-minute hard wall without a result artifact. No Shogi expansion is authorized from this evidence.

## Scope and implementation

- Work order: split F125 by family, run Standard Shogi alone with at most 64 fresh decision roots.
- Implementation checkpoint: `021a578eec0dffd943c1cbd40af838fa957f274b`
- Family: `standard_shogi`
- Requested roots: `64`
- Decision-root seed: `1250221`
- Resource envelope: `f125-known-oracle-one-ply-search-compression-shogi-pilot-v1`
- Limits: 45 expected wall minutes, 60 hard wall minutes, 3 expected CPU hours, 4 hard CPU hours, one lane, 1,000,000 nodes, 1,500,000 plies.
- Command digest: `4d1c4f89321377229f063d58b2c0b622961bdf223a7617c5441a19c1ae68dd5c`

## Attempts

### Attempt 1: original calculation path

- Run: `f125-shogi-pilot-v1-7c1541fb36e6`
- Result: hard-wall timeout; no result artifact.
- The invocation was not retained as a scientific result because it did not emit structured output.

### Attempt 2: bounded child-state reuse optimization

- Run: `f125-shogi-pilot-v2-d1afdbe4c640`
- Start epoch: `1789786966.4017081`
- Finished epoch: `1789790567.7774537`
- Terminal status: `timed_out`
- Timeout reason: `hard_wall_minutes_exceeded`
- Exit code: none
- Structured result: absent
- `stdout.log`: empty
- `stderr.log`: empty

The second invocation used the smallest calculation-preserving optimization: root child states were reused for the existing one-ply teacher and compressed prediction calculations, while depth-2 calculations and all gates remained unchanged. It therefore constitutes a distinct reasonable technical attempt, not an altered scientific procedure.

## Decision

There is no valid Standard Shogi classification, informative-root count, or retained raw result. Under the signed Supervisor direction, the next action cannot be another self-directed Heavy retry. Report both bounded timeouts to Supervisor/Chat and await a new decision.

