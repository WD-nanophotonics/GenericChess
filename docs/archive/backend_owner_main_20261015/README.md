# Owned backend and main-frontier evidence

Report: docs/research/OWNED_BACKENDS_AND_MAIN_FRONTIER.md. Member hashes and
publication-copy sanitization are explicit in manifest.json. Failed/superseded
scripts and results are intentional; they are not all runnable success cases.

For the self-contained semantic replay, extract evidence.zip into
`.local_agent/backend-owner-20261015` in this repository with its normalPython3.12
environment, dependencies and Zig installed. Build the normal product Native
module using scripts/build_native_zig.py if absent, then run build_replay.py and
verify_coexist.py from that directory using the repository Python. The replay
rejects reads of older private folders, uses frozen supplied rules/walks and
writes unique verification outputs. Actual local replay checked37roots/56contexts,
5860legal identities/292checkedchildren;18V1capacitydeclines remain. It does not
rerun resource curves or certify a pristine dependency installation. Private V2
binaries are not shipped/activated. Timed sources and final scoped sources are
separate; final source's matching-work overhead control is in the report.

src_v2_baseline is the prior qualified payload5/1024/64target source. src_main_binary
is the unrestricted experimental main hint; final src_scoped_v1/v2 confines it to
exact-root replay and adds an observable counter. src_empty_run is rejected on
cost despite77824 byte comparisons. src_scan_profile is instrumentation only.
Original C-key byte harness failed due unallocated auxiliary pointer; the initial
stack-overflow inference was withdrawn. Corrected harness uses SHA-update byte
interception, not a production replacement for SHA. No original failure is erased.
