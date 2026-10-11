# Task040: deferred square references preserve old state

12paired controls pass:8normal and4direct missing-token negatives across global/per_owner and compat/pure. Two distinct (move,set_token) actions actually share the same generated function; every candidate call hits its generated entry. Children and exact callback sequences match original; full parents remain unchanged.

Both slots expire before deferred writes. Reading source_token uses the pre-action position: output_token becomes(1,1) for source square or(2,2) for old token, while source_token resets to None. Foreign per-owner logical instances also expire. Missing-token direct calls reject identically; no public membership claim is made here. Task041 separately tests real S3 rejection/exception provenance.

Initial fixture lookup incorrectly expected CompiledAuxSlot.name; compiled names are erased. The failed source/log remain. Corrected lookup uses the fixed compiler's sorted public-name assignment; conditions and12pair count stay unchanged. Finite semantic pass does not change negative cost or deferred deployment.
