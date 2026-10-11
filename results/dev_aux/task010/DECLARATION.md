# Task010 persistent-key versus mutable-count consistency

New decision-changing premise from Task006: the restored search key uses a
persistent snapshot while terminal counts use the mutable table. Can a corrupted
Runtime report the same root key as a clean runtime, and after a genuine retry
does its stored snapshot digest agree with a rebuilt snapshot of actual counts?
This tests integrity diagnostic needs, not an observed TT wrong-cutoff.

Two arms original/private one-conjunct candidate, ordinary Chess initial state
with builtin high repetition limit so retry remains ONGOING. One injected
snapshot RuntimeError per arm, then one real same legal push/pop. At root before/
after fault compare search_key and actual multiset; after retry compare snapshot
items AND digest against _snapshot_from_occurrences and a clean same-action
Runtime. Keep Task007 limit2 witness untouched. No search/TT probe or timing;
under60seconds, source unchanged. Failure data is output, not assumed acceptance.
