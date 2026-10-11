# Clock and count interpretation

This is a source audit of the frozen producer `physical_profile.py`, not another caller measurement. The existing `physical-profile.json` remains unchanged.

| Recorded quantity | Included scope | Excluded or overlapping scope |
|---|---|---|
| `session_seconds` | GameSession construction and replacement of declared state/history witnesses | Compilation, CoreBoard construction and weighted evaluator setup before the arm |
| `wall` | Fresh AlphaBetaPlayer construction and choose_action | Session setup, later restoration assertions and record conversion |
| `copy` | Saved WorkingPosition constructor plus its finally counter increment before the clock is stopped | Auxiliary dict built by the caller; later addition to the observer context |
| `freeze` | Saved to_position plus its finally counter increment before the clock is stopped | Caller-evaluated auxiliary tuple/sort argument; later observer-context addition |
| `trans` | Saved transition and nested copy/freeze wrappers, their observer-context additions, checkpoints and auxiliary work | Transition wrapper setup before its clock and final counter/row bookkeeping after its clock stops |

The narrow methods are nested inside transition. Their elapsed values are not disjoint additive categories alongside transition. Subtracting them yields an instrumented residual, not a pure rule-IR execution measure. Instrumentation itself is charged differently by the clocks: copy/freeze counter increments precede their end timestamps, while the transition count increment follows its end timestamp.

Components aggregate both session and choose stages; the choose wall cannot be the denominator for an unqualified sum that includes the initial session trial. Finally counters identify entered attempts. Task029 demonstrates that an attempted freeze need not return a published child. Task031 separately shows that pass publication does not enter these three instrumented methods. Task032 separates visible Python Native payload copies from these working-position methods and from opaque C internals.

Ordinary execution precedes observed execution in this producer. The two supplied wall values describe those arms; they do not isolate a causal instrumentation cost from order or warm-state effects. The producer already labels them observer-overhead context rather than a speed claim. Task030's shared-candidate cost producer has a different timer boundary and opposite-order comparisons; keep those records separate.

Decision remains scoped DEFER. These observations repair attribution vocabulary and prevent an unjustified savings calculation. They neither identify an undisclosed large cost nor justify changing defaults, search budgets or the frozen caller.
