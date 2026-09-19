F129 closeout: Standard Shogi known-oracle T1 scalar compression

- Work order: GENERICCHESS_F129_SHOGI_KNOWN_ORACLE_T1_SCALAR_COMPRESSION
- Existing Courier request: GENERICCHESS-20260919-070904-f90afa76
- Heavy run: f129-shogi-known-oracle-t1-r3-b570a07cce9c
- Heavy envelope: f129-shogi-known-oracle-t1-compression-v1
- Runtime: 3471.86 seconds
- Retained roots: train 1995, dev 252, holdout 254
- T1 shards: 20; child states evaluated: 108502
- Classification: SHOGI_HANDCRAFTED_T1_SEARCH_TARGET_COMPRESSION_LIMIT_SUPPORTED
- Numerical gate: pass
- Representation gate: fail
- Holdout compressed T1 RMSE: 8476.16832054588
- Holdout direct-oracle static baseline RMSE: 6088.17472319246

The exact T1 labels were generated and the reproducible direct-control stage matched
the frozen baseline. The scalar compression representation did not pass: its holdout
RMSE exceeded the static direct-oracle baseline. No candidate or promotion was
authorized. Transient result, stage, and shard files remain under the local flow
runtime and are intentionally excluded from Git.

Validation: tests/test_f129_shogi_known_oracle_t1_scalar_compression.py passed.
