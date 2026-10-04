# Targeted source acquisition after an oversized release archive

2026-10-04. Original protocol and both incomplete manifests preserved. First
sandbox attempt denied sockets before any bytes; explicit escalation fetched
and independently checked author kbk2021bytes/krk10824bytes, then refused the
PyPI source archive under the original256KiB cap. No source extracted or probe.
Second tool wall1.685s, measured source work1.563s. Do not expand the archive cap
or repeat fetched table downloads to conceal this failure.

Changed acquisition premise: fetch ONLY the three official maintainer files
chess/__init__.py,chess/gaviota.py,LICENSE.txt from the resolved v1.11.2 GitHub
tag commit. Metadata must establish combined<=256KiB before any file content.
Verify each exact size/Git blob SHA1 and record SHA256. Preserve them in the same
ignored explicit source directory. A correction manifest binds already verified
table hashes and original failed manifest; no global package/environment install.
Remaining conservative network work cap12seconds; combined prior tool walls and
correction source work stay below15seconds. No automatic retry or overwrite.
If the narrow source also exceeds cap/is unavailable, stop acquisition rather
than enlarge budget. ZERO game transitions/probes during this step.
New source integrity does not prove library correctness, table generation,
local move equivalence or finite-horizon applicability. Actual first-probe controls
need a separately frozen semantic/state protocol and may still be inconclusive.
