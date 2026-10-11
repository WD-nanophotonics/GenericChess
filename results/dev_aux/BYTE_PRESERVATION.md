# Scientific byte preservation

The pre-publication staged-byte audit failed on 2026-10-11 around 06:29 UTC: 23 staged paths differed from their working-file bytes because Git newline filtering normalized Windows text. The whitespace check passed separately; that did not make the byte audit pass. Publication was held.

New task027 through task037 directories now have narrow `-text` attributes. Existing product and older scientific records retain their attributes. Restaging and exact byte comparison are pending until the agreed 06:30–06:40 UTC source/document-only resource window ends. No success or remote publication is claimed by this note.

Input hashes in the audit reports bind raw captured bytes. Preserve those bytes rather than replacing hashes with a normalized-text hash. Task033's `candidate_function_sha256` instead binds the generated logical LF source string before Windows text writing; it is not the physical file-byte hash. A separate delivery manifest will name actual byte hashes, so both meanings remain visible. Do not rewrite historical fields to hide the distinction.

The retained Task034 scope correction and Task037 initial anchor diagnostic are part of the evidence. They must be delivered along with the final controls. Raw Slack/account records remain ignored under `.local_agent` and are excluded from publication.


Delivery update after the resource window: the first repaired audit verified69new science files exactly; Task033 logical-source hash also matched. Subsequent Tasks039–041 will extend the manifest before final publication. Raw CRLF records intentionally trigger plain Git diff --check's trailing-CR diagnostics. The relevant whitespace verification uses `git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --cached --check`, preserving ordinary blank/tab checks while recognizing CRLF. That check passed; neither it nor the byte audit reruns engines. Final exact count is in delivery_20261011_3/byte_manifest.json.
