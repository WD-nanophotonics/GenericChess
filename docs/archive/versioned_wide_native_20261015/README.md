# Versioned wide Native evidence, 2026-10-15

The report is docs/research/VERSIONED_WIDE_NATIVE_AND_PROMOTION_CLOSURE.md.
Archive member hashes and any publication sanitization are in manifest.json.
Exact private originals remain under ignored .local_agent. This archive contains
failed preparation scripts and superseded scope judgments, explicitly corrected
in the report; it is not a claim that every historical script passes today.

To replay the final semantic qualification, extract evidence.zip into
`.local_agent/wide-interface-20261015` in a normal project checkout with its
Python 3.12 environment, project dependencies and Zig installed. Run
`.venv\Scripts\python.exe .local_agent/wide-interface-20261015/build.py`, then
`.venv\Scripts\python.exe .local_agent/wide-interface-20261015/verify_replay.py`.
The replay uses qualification-inputs.json and the final clean wide_common.py;
it rejects access to other private evidence folders and writes uniquely named
verification results. Historical prepare/qualify scripts can depend on older
private inputs; use verify_replay.py for the supplied self-contained qualifier.
The actual dependency-audited local replay passed17roots/1301edges. A pristine
machine installation was not tested. The resource curves are NOT rerun by replay.
No private binary is shipped or automatically activated in the product.
