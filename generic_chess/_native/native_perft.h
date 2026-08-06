#ifndef GENERIC_CHESS_NATIVE_PERFT_H
#define GENERIC_CHESS_NATIVE_PERFT_H

#include "native_types.h"

/* Terminal classification matching Core _terminal_from_parts:
 * legal moves empty -> checkmate/stalemate (check wins over repetition and
 * max-ply); otherwise repetition draw, then max-ply draw.
 *
 * ``legal`` receives the generated legal move list (cleared first) so the
 * caller can reuse it instead of generating moves twice. */
GCTerminal gc_terminal(const GCRules *rules, GCPosition *pos,
                       GCMoveList *legal);

/* Variant that generates pseudo moves into the caller-provided ``pseudo``
 * list (no per-node allocation inside the hot path). */
GCTerminal gc_terminal_with_pseudo(const GCRules *rules, GCPosition *pos,
                                   GCMoveList *pseudo, GCMoveList *legal);

/* Per-depth scratch lists avoid per-node allocation while keeping each
 * active node's move list intact during child recursion. */
typedef struct {
    GCMoveList *pseudo;
    GCMoveList *legal;
    size_t capacity; /* number of depth levels allocated */
} GCPerftScratch;

void gc_perft_scratch_init(GCPerftScratch *scratch);
void gc_perft_scratch_destroy(GCPerftScratch *scratch);
int gc_perft_scratch_ensure(GCPerftScratch *scratch, size_t levels);

/* Perft matching the Python correctness-corpus definition:
 * depth 0 -> 1; a terminal node at depth > 0 contributes 0.
 * Returns 1 on success (total written to ``*total``), 0 on allocation error. */
int gc_perft(const GCRules *rules, GCPosition *pos, int depth,
             GCPerftScratch *scratch, uint64_t *total);

/* divide=True: per-root-action node counts.  ``root_moves`` receives the
 * root legal actions, ``counts`` one entry per action. */
int gc_perft_divide(const GCRules *rules, GCPosition *pos, int depth,
                    GCPerftScratch *scratch, GCMoveList *root_moves,
                    uint64_t *counts, uint64_t *total);

#endif /* GENERIC_CHESS_NATIVE_PERFT_H */
