# Runtime ownership and exception consequence scope

Static pinned source inspection after Task006.

AlphaBetaPlayer.choose_action calls run_root_search and stores its result as a
PlayerDecision. It retains TT and Native provider, not a SearchPathRuntime.
run_root_search creates a fresh local Runtime on each invocation. Its catches
are SearchAborted, not MemoryError or general RuntimeError. The GUI worker
catches Exception, emits an error and None, and returns. These inspected normal
caller paths do not reuse a leaked Runtime after a snapshot MemoryError.
This does not establish that every script/library caller discards it.

The direct push/pop API and context-manager lifecycle are nevertheless useful
restoration contracts to verify. A local caller explicitly catching an injected
MemoryError and reusing that object is a scoped behavioral witness, not evidence
that the ordinary UI returns a false repetition after a real memory failure.

No standard cancellation checkpoint is present between child occurrence
addition and successful history append in the inspected source. A deliberate
snapshot failure therefore does not show a natural timeout/cancellation trigger.
MemoryError recovery itself can fail during cleanup under genuine exhaustion;
the injected exception is controllable and does not simulate global exhaustion.

The rollback restores _snapshot but leaks a private entry at Task006's seam.
search_key uses the persistent snapshot, while terminal repetition uses
occurrence_count. This inconsistency warrants preserving actual private-table
evidence rather than trusting restored search-key equality. Task007 tests only
the declared retry terminal consequence. Candidate lifecycle checks retain both
pre-history and post-history cases to avoid double-removal.
