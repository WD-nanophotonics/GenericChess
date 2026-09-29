# Type-preserving intrinsic board-event coverage

## Bounded question and method

Can the destination-aware physical-event composer cover representative
current-type board actions in Chess, Standard Shogi, and Xiangqi without
silently relaxing their local constraints? Enumerate compiled leap/ray
candidates for both owners and all board sources, apply deterministic
zones and exact local occupancy guards, then union occupancy cubes under
the canonical key `(owner, type, source, destination, target state,
resolved removals, resulting type)`. Stop above 100,000 candidates per
type. This is a semantic coverage audit; it computes no material score,
human-value metric, or Xiangqi reference.

| RuleSet | Current type | Geometry candidates | Physical event keys |
| --- | --- | ---: | ---: |
| Chess | B | 2,240 | 2,240 |
| Chess | N | 1,344 | 1,344 |
| Chess | Q | 5,824 | 5,824 |
| Chess | R | 3,584 | 3,584 |
| Shogi | G | 1,664 | 1,664 |
| Xiangqi | A | 1,152 | 64 |
| Xiangqi | C | 6,120 | 5,476 |
| Xiangqi | E | 896 | 336 |
| Xiangqi | H | 2,032 | 2,032 |
| Xiangqi | R | 6,120 | 6,120 |
| Xiangqi | S | 964 | 644 |

All listed types had zero unsupported *intrinsic* candidates and stayed
below the candidate budget. Event-key counts are after rule/occupancy
filtering and canonical union; they are neither legal move counts in
actual positions nor material values. The type list is deliberate: it
tests type-preserving board modes, not promotion-bearing base types or
promoted/held modes.

The audit records dynamic `own_anchor_safe` invariants separately and
does not model their positional truth. It excludes Shogi G's allowed
held-token drops from the board-mode ledger. Compiler-emitted legacy
drop patterns for these Chess and Xiangqi types have zero allowed drop
squares and are recorded as disabled, rather than treated as legal
options. Duplicate physical descriptions are unioned; a focused test
checks that equivalent removal references yield one event key, while
two distinct destinations sharing one removed square remain distinct.

Next gates are to cover transition-bearing and held modes with the same
event identity and explicit cost/coverage limits, then decide whether a
declared random-target first-action service quantity is a defensible
relative material prior. This coverage result alone does not establish
that service quantity as a proxy for winning utility.
