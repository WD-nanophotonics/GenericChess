# Minimal source acquisition and first-probe boundary

2026-10-04. New task AFTER metadata-only audit and request encoding. Acquire
only author-provided kbk/krk cp4 and the pinned chess1.11.2 source package. No
blanket endgame set, install, generation, credentials or other-project access.

Fetch the Gaviota author repository's full current master commit via GitHub API,
then those TWO file metadata records at that commit. Verify total table bytes
<=64KiB before requesting either blob. Read each from its immutable commit URL,
verify exact metadata size and Git blob SHA1, record SHA256; preserve originals
in ignored .local_agent/certificate_source. Fetch PyPI chess1.11.2 release JSON,
only its source archive<=256KiB, verify the advertised SHA256/size. Extract only
regular members chess/__init__.py, chess/gaviota.py and the archive's license,
by exact member names into this ignored source directory; no tar extractall or
package/environment install. Use explicit source sys.path only in later audits.
Network acquisition wall budget15 seconds total; individual timeout uses the
remaining time. Any missing metadata, size/hash conflict or cap -> incomplete
manifest and no probe. No automatic retry or overwrite of original evidence.
Preflight destination and manifest BEFORE any observations.

This source step has ZERO public game transitions, coefficient values or
tablebase probes. Package/repo hashes establish integrity/association, not a
proof of table-generation correctness or local move/goal equivalence. A future
frozen first-probe test must check those semantic assumptions separately with
fresh local terminal-first handling and exact state request hashes.

No reserved candidate-use root is chosen by a tablebase result. The possible
four-piece capture-root comparison is a later separate protocol. Existing
experiment transition/enumeration/time limits are not expanded by this task.
