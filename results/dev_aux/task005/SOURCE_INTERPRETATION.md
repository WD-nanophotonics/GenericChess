## Source-derived interpretation before execution

For the concrete provider, each uncached successful provider call invokes exactly
one transient C-generation function. Runtime counters advance after provider
return plus pair validation. Cancellation at later checkpoints can therefore
separate C return from accepted count. The completedD2 controls with no abort/
fallback retain their existing scope; do not retroactively reinterpret them
as a failed route. Core-neutral counters do not authenticate a provider backend:
always record the actual callable/class, supported binary and fallback route.

The per-provider last_call_metrics record is published near provider return;
it may be absent before publication or present even if subsequent Runtime
validation aborts. It is not an exception-inclusive total. These are source
hypotheses until the declared C-entry controls run, not measured outcomes.
