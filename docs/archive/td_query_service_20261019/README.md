# TD query service evidence capsule

This capsule preserves the inputs and source needed to inspect the bounded
TDLeaf query-consumer comparison documented in
[`TD_QUERY_CONSUMER_COMPOSITION_20261019.md`](../../research/TD_QUERY_CONSUMER_COMPOSITION_20261019.md).

- `evidence.zip` contains 60 project payloads; `manifest.json` lists each
  member's byte count and SHA-256 and records the archive SHA-256.
- `qualification.json` records a saved four-output captured-source replay.
  It used Python `-S`, verified source origins, and ran without Native, games,
  training, optimizer updates, or UNKNOWN refill.
- `reproduce.py` runs from the repository root and writes its temporary
  extraction/results only under the ignored `.local_agent` directory. It
  checks the pinned captured sources and saved outputs; it does not rerun the
  original Native queries or training experiment.

The qualification is retained as saved provenance. Reading this capsule does
not establish an independent rerun by a later reviewer, an end-to-end learning
speedup, policy equivalence, playing strength, or all-rule coverage.
