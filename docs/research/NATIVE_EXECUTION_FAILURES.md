# Native child-identity failure propagation

The observed defect was a false completed search, not a real machine OOM:
forcing serializer failure during sorting caused completedD2/score0/actionNone.
The old Boolean transition result conflated rule rejection and identity failure.
A retry through the existing no-history probe catches an outer failure but
misses persistent nested-reply failures: both transitions reject, losing cause.
Ten paired fixture checks establish that counterexample.

The product repair is a small explicit-status change across the Native
module/runtime and header. The internal transition returns1(success),0(rule/input/capacity
rejection),-1(child identity failure). Nested S3 reply and postcondition handling
propagate negative status. Material/policy sorting and recursive iterative AB
stop with existing internal_error; they preserve the last completed iteration.
Existing Boolean wrappers explicitly clamp >0, preventing negative truthiness.
No global product error flag, new error enum, optimizer, model, UI or default
parameter is added. Capacity refusal retains its old rejection classification.

## Actual verification

- Ten paired status checks: outer/nested failure=-1, normal=1,
  malformed/capacity=0, input unchanged.
- Twelve actual fault/retry/cold engine queries on saved gen2/Shogi and a nested
  fixture: injected error retains legalD1, retry matches coldD3 full tuple.
- Three checks on a genuinely played two-action prefix (three canonical history
  records and witnesses) retain required nested failure and parent immutability.
  The problem-start RuleSet variant is explicit, not a builtin population claim.
- Four persistent development regressions build current source with an
  ordering-scoped private serializer fault, crossing root-window and cache
  switches. Retained action/score/PV equals independentD1; retry matches coldD3.
  Compiling old7af59066 source with the same regression fails: completed rather
  than internal_error. No fault hook is shipped in the product.
- Private clean full active layers pass. Installed production full active layers:
  2270tests,0failures,0errors,0skipped,245.48seconds. Four strengthened regressions
  plus focused dependencies pass48tests. These runs/repeated publisher checks
  are not independent scientific samples.

The optional fault-build regression requires Windows Native and Zig; other
environments report its explicit skip. Normal-layer tests remain portable.
This repair does not claim every Native API or arbitrary memory-corruption/OOM
path has been classified. Standalone Boolean probes preserve Boolean failure
behavior; the specific repaired consumer is persistent iterative search.
A serializer false is classified as internal identity failure, not proven OOM.
Private injection is evidence of control flow, not a report of current machine
Application Control or allocation failure. No user intervention is needed.

## Following cost decision

The static material view remains a PRIVATE candidate at this checkpoint.
Dot agrees that unused allocation need not be retained to mimic old OOM traces.
Its concrete Boolean-adaptation objection exposed another real consumer:
terminal availability calls a no-history Boolean probe whose nested reply still
computes a digest. A private injection scoped to the second root availability
check (D2, after D1 finishes) yields completedD3/actionNone through this chain.
The input is a declared immobile-anchor A/B problem, with two actual legal moves
and three exact history witnesses. Six digest failures were counted; sorting and
ordinary recursion were not injected.

The follow-on repair preserves raw probe status in the visitor, stops enumeration
on success OR error, and sets the existing ok error channel on failure. Terminal
assessment already turns that channel into internal_error. Runtime Boolean wrappers remain compatible rather than serving as an internal
status source; public availability uses its existing failed-query exception channel. Actual repaired query retains
the independent fullD1 tuple; same-TT retry matches coldD3. Two additional
persistent fault regressions cover this terminal path with both root-window
modes. No global product fault flag or new error framework is introduced.
The earlier12 ordering-fault queries did not cover this path; the old claim is
not retroactively expanded. The initial2270 normal suite is before this follow-on
repair; final full-suite results are recorded separately.


Under an explicitly stated valid-input contract it removes an unused outer
digest allocation; it does not promise the same artificial allocation-failure
trajectory as old checked sorting. Necessary nested computations still execute
and must retain negative status. Search/canonical nodes keep full histories.
New combined status/view paired tests distinguish these two failure surfaces;
six profile guard controls and two fixedD5 roots are independently scoped.
Old16s and64s resource planes remain immutable. No global/default/strength claim.

Dot's source objection directly yielded a falsifiable nested counterexample and
a smaller explicit-status repair. Its new technical request is not a publication
gate. Existing speed-range evidence is separately classified in
SEARCH_SPEED_EVIDENCE.md. Agent-only source/results are hash-bound by
data/ordering_status_20261012.json; raw Slack/account, user inputs, compiler logs,
binaries and local session/stop/memo are excluded.

A refreshed PRIVATE status/view build includes the final availability repair.
Four actualprefix3 calls trigger the required terminal nested failure, retain
the fullD1 tuple and match same-TT/coldD3. Raw branch counters confirm the view
really executes on the normal retry. Its older cleanD5 combined controls match
79801/174824visits and full tuples, with gen2about6.0–6.19→4.62s and
Shogi9.20–9.23→7.76s; twelve profile cells preserve fallback and compact-leaf
scope. These are finite private cost/consumer checks, not a current published
speed interval, production view enablement or independent strength evidence.


Final installed-production active suite after the availability repair:2272tests,
0failures/errors/skips in253.38seconds. The extra final run is
justified by the newly observed terminal-path defect; initial2270 results remain
unchanged and are not relabelled as final-source coverage.
