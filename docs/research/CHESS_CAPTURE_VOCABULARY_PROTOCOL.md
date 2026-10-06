# Diagnose strict metadata admission, without retrying constructors

Both global effect constructors are closed failures before any action checks;
their generic error messages do not identify the first offending pattern.
One independent structural pass compiles native IR and records ALL effect
vocabulary and per-pattern ownership/disposition, without calling either
constructor or materializing a state. Compare their literal allowed sets
with each pattern; report all unsupported effect kinds in actual IR order.
Do not infer whether a rejected pattern is reachable/legal from metadata.
One compile,5000 effect terms/15sec,zero transitions/runtime/source pushes.
This identifies admission scope, not a new controller or production fix.
