# Task 2601 scope correction

The initial script audit_train_root_concentration.py called json.loads on the whole manifest before selecting its TRAIN array. It did not compute any EVAL metric or inspect outcomes, but the parser decoded EVAL rows into memory, contrary to the intended strict TRAIN-only handling. That parser version and its result are preserved as v1 historical evidence.

The corrected v2 parser reads the JSON text envelope, structurally skips non-target values without JSON-decoding their rows, and only decodes the TRAIN array. Its result is stored separately as root-concentration-v2.json. The corrected metrics are checked against v1; no EVAL data were used in the comparison. This is an implementation-scope correction, not a changed scientific conclusion.
