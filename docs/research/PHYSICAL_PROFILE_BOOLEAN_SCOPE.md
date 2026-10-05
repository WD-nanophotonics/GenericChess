# Strict physical promotion flag at the constructor boundary

Review found a distinct input-validation gap: Profile annotates promoted as
bool, but Python dataclasses do not enforce it. The old _profile predicate
tests truthiness; promoted=1 compares/hashes equal to True, and promoted=0 to
False. Thus declared bool identity cannot be inferred from type annotations
or the otherwise valid8064 bool-profile observations. Preserve their producer
and all pins unchanged; no population/census rerun or result correction.

A narrow new constructor entry rejects non-Profile inputs or non-bool flags
before invoking the frozen physical dispatcher. All legitimate bool profiles
use that exact dispatcher; ordinary origin/current/closure and grammar checks
are delegated unchanged. This is an input-domain correction, not a new movement
model, metadata-chain or price admission. Canonical ordering/identity need not
accept false-like integers as physical promotion status.

Tests demonstrate the old truthiness predicate on1/0 without geometry, then
require the new boundary to reject both before any constructor work. A single
fresh3x3 bool-input construction checks retained physical inheritance/NONE
scope at at most128 canonical candidates/15sec; no game events or distance
worlds. Do not append controls to the closed8064/R-TR studies.
