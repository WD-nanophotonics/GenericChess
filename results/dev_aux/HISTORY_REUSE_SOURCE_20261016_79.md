# History-aware strategy reuse: primary-source comparison79

Primary source read: Kishimoto and Müller, *A solution to the GHI problem for
depth-first proof-number search*, Information Sciences175(2005),296–314,
DOI10.1016/j.ins.2004.04.012; author-hosted full paper:
https://webdocs.cs.ualberta.ca/~mmueller/ps/kishimoto-mueller-infsci-ghi.pdf
Sections1.2–1.3 and3.1–3.3 were read. A separate older author-hosted AAAI URL
returned404; no content from that inaccessible paper is claimed.

The paper distinguishes histories that can make cached results unsound. Its
reuse scheme retains path information and verifies an old result in the new
path context instead of blindly accepting a solved position. It discusses
proof-tree simulation and the need to cover every defensive branch. Its
reported Go/super-ko efficiency and guarantees are specific to that method and
rules; they do not establish GenericChess support or our prototype's cost.

Local comparison (inference, not paper validation):2292's six real histories
use an explicitly untrusted rebound candidate, followed by complete current
verification and cursor admission.2296's second loops reach actual repetition
DRAW at unchanged Position and are rejected. This is consistent with the need
for path-sensitive admission, but implements neither the paper's df-pn nor its
base/twin transposition scheme. Our bounded incremental estimates are not
converged proof numbers; strict rank/AND checks supply positive authority.

Next decision: before building any reuse bank, require measured natural
same-Position hits and paid admission costs; preserve fresh actual terminal,
remaining-ply and repetition guards. Do not add a general history-caching
framework based on these six constructed pairs or treat failed positive search
as a disproof. Complete generated-rule support remains OPEN.
