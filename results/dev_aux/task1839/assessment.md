# Threshold scheduling assessment

64 frozen calls on the existing 16 complete maxply4 rule games finished. All32 paired target results have identical visited nodes, transitions, frontiers, eager successors, claims and certificate representation hashes. Six target wins per method are actual Session-verified. No new WDL labels or games were generated. This prototype retains the search tree, so neither a linear-space implementation nor a node reduction is established.

The reference literature makes this negative result unsurprising: Nagai/Imai explicitly study equivalence of pn-search and df-pn, while the review describes avoiding recomputation/root traversal as a motivation. Our conservative complete-rule-horizon admission avoids the old depth-UNKNOWN infinity/progress obstacle; it does not solve that general problem.

Sources: https://repository.dl.itc.u-tokyo.ac.jp/records/48966 (2002 paper abstract; PDF fetch429), https://webdocs.cs.ualberta.ca/~mmueller/ps/ICGA2012PNS.pdf (2012 author-hosted review section4). No source text copied.

Decision: do not integrate this scheduler into the learner or fixed opponent. Before more unchanged games, test whether reordering already generated actual terminal successors can reduce visited work. Freeze that changed premise separately, preserve all former results and use the actual Session verifier.
