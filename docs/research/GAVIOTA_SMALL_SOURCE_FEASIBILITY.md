# Small independent goal-source footprint, before downloads or probes

2026-10-04. Primary-source/code metadata audit only. No tablebase or package
download/install, generation, file opening or submitted/probed position. No
goal labels or prior coefficients were admitted.

## Actual small source, not a complete five-piece dependency set

The author's repository includes a test set with three physical pieces, in
four compression schemes; its README recommends supporting cp4. Its `gtb/gtb4`
directory lists kbk,knk,kpk,kqk,krk `.gtb.cp4` files. The directory name denotes
compression scheme4, NOT four-piece coverage. This is a concrete small-source
lead rather than requiring a blanket five-piece download.
[Author README](https://github.com/michiguel/Gaviota-Tablebases/blob/master/readme.txt),
[author directory](https://github.com/michiguel/Gaviota-Tablebases/tree/master/gtb/gtb4).

GitHub's rendered metadata reports about1.97KB for
[kbk](https://github.com/michiguel/Gaviota-Tablebases/blob/master/gtb/gtb4/kbk.gtb.cp4)
and9.22KB for
[kqk](https://github.com/michiguel/Gaviota-Tablebases/blob/master/gtb/gtb4/kqk.gtb.cp4).
These are rounded page sizes, not verified byte counts or checksums. The knk/kpk/
krk blob metadata requests returned cache-miss/internal errors. Their sizes,
the five-file total, pinned repository commit, exact bytes/checksums and current
download integrity remain unverified. Do not substitute forum totals or infer
four/five-piece availability from the API library's capability.

## Probe implementation observations and association obligation

In tagged python-chess v1.11.2 source, the pure-Python probe rejects castling
and more than5pieces, returns KvK draw, and resolves legal en-passant alternatives
by probing their successors. Its material lookup can reverse colours/ranks;
the requested side and signed DTM are converted accordingly. It opens tables
lazily with `rb+`, uses LZMA blocks and a bounded128-block cache. Missing files
raise an error; corrupted data has undefined behaviour per the documentation.
The native path can shortcut insufficient material and shares global library
state. These are source observations, NOT measured memory/runtime or an
implemented local adapter.
[Tagged maintainer implementation](https://github.com/niklasf/python-chess/blob/v1.11.2/chess/gaviota.py),
[maintainer API](https://python-chess.readthedocs.io/en/latest/gaviota.html).

Consequences for our proposed small scope (our inference): choose no-castling,
no-EP states first, avoiding a dependency surprise from EP successor material.
For a pawn-containing root, source semantics/needed promoted-type coverage must
be checked separately; having only kpk is not a general conversion certificate.
Use an isolated verified file copy if rb+ is required, preserving original hash;
do not promise a read-only file open merely because the algorithm is a probe.
Explicit side/board mapping, legal state status, authoritative terminal-first
handling, full local history/absolute ply and remaining-horizon bridge remain
mandatory. A returned DTM number or file name cannot authenticate state identity.
CONDITIONAL_DTM_BRIDGE_RESULTS.md's boolean premise flags are assumptions, not
proof that this source/state conversion has been done.

## A narrower useful-choice possibility

Our prospective structural inference: a four-piece root with two Kings and TWO
ordinary enemy types can give the defending King two different captures. Both
capture children contain only three pieces, so the two selected-child labels
could use three-piece files even though the root itself is outside that test
set. Remaining enemy types differ, hence positive relative material weights can
reverse that pair. Complete legal choices and GLOBAL selection still matter;
the pair is not sufficient to prove either is selected or a good goal choice.

Candidate and unit may both select captures; then paired-regret cancellation
needs only those selected child values, not the root optimum or every quiet
child's label. Zero may instead select a quiet four-piece child by canonical
tie; keep that label unknown without the corresponding certificate. This can
support a narrow falsifier versus unit, not the earlier full two-baseline
admission requirement, Shogi control, natural-play generalization or positive
complete prior coverage. No root was generated/selected/probed here.

Next: qualify exact no-EP/no-rights local-to-standard current-state conversion
and legal-choice correspondence on a small predeclared structural scope,
then preflight a pinned minimal file manifest. Download/probe decisions need
their own frozen evidence/cost contract; this audit does not activate a source
or waive compatible finite-horizon semantics. The scientific objective stays OPEN.
