# Reproduction and exact evidence

REPRO_DATA_20261020.zip and REPRO_MANIFEST.json deliver the exact project
training/evaluation/cost journals, frozen inputs,24 registered source files,
source-verification receipts and finite Generic contract data. Every archive
member has its uncompressed size and SHA256 in the manifest. Large originals
stay at their original ignored paths locally; the capsule carries their exact
bytes. Do not launch any training/evaluator against existing receipts.

Two pre-existing Git blobs (`task2153/stop_evidence.py` and
`tools/local_agent/environment.py`) have line-ending projections relative to
the registered executed bytes. The capsule contains the exact registered
sources; its raw-byte hashes are authoritative. In a dedicated owned validation
checkout, use those verified source bytes before running the pinned auditor.
Do not silently substitute a Git text projection or overwrite another role's
normal working checkout. The exact eight Generic smoke dependencies are also
provided in task2621/REGISTERED_SOURCE_SNAPSHOT.zip with their own manifest.

Two launcher receipt command fields use the portable executable token `python`
instead of the original user-specific absolute executable path. The module,
arguments, UTC timestamps and PID are retained. Both original and publication
hashes and the projection reason are explicit in the manifest. Exact originals
remain ignored/private. No game/query/outcome, source pin, budget or exit receipt
was projected. This is declared publication sanitation, not an original command
receipt or cryptographic actor authentication.

Extract into a separate evidence directory inside an owned DEV_AUX checkout;
verify all member hashes before reading/replaying it. Do not overwrite an
existing dataset or source checkout. The registered source bytes and original
execution baseline are identified in the manifest. The additive NO_CONTEST
record reader fix was made after the original Chess evaluator closed; it changes
no Chess rule or registered source fingerprint.

The independent closed-run auditor can read the extracted run by setting its
RUN path before calling audit(). Keep ROOT and role identity anchored to the
actual owning checkout; no role/branch check should be bypassed. The write-once
independent-audit.json must be absent from a new replay output directory, while
the published original remains intact. Compare the regenerated audit result
byte-for-byte with the original published audit. No search, training, new game,
cap extension or strength sample is needed for this action/accounting replay.

Relevant targeted checks:

```text
python -m pytest results/dev_aux/task2620/test_audit.py results/dev_aux/task2620/test_execution.py results/dev_aux/task2620/test_panel_description.py
python -m pytest results/dev_aux/task2621/test_fixed_scale.py tests/product/test_session_serialization.py tests/product/test_session_record.py tests/product/test_session.py tests/product/test_initial_setup_options.py tests/product/test_generic_declaration_semantics.py
```

Use an owned writable temporary directory for pytest. A pre-existing local-Git
transport fixture needed supported escalation in the sandbox; it passed there.
This is separate from scientific test correctness and from the actual reviewed
origin/sidemission publication.
