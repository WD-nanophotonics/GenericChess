#ifndef GENERIC_CHESS_NATIVE_PERFT_H
#define GENERIC_CHESS_NATIVE_PERFT_H

#include "native_types.h"

/* Terminal classification matching Core _terminal_from_parts:
 * legal moves empty -> checkmate/stalemate (check wins over repetition and
 * max-ply); otherwise repetition draw, then max-ply draw. */
GCTerminal gc_terminal(GCRules *rules, GCPosition *pos);

/* Perft matching the Python correctness-corpus definition:
 * depth 0 -> 1; a terminal node at depth > 0 contributes 0. */
uint64_t gc_perft(GCRules *rules, GCPosition *pos, int depth);

/* divide=True: per-root-action node counts. */
void gc_perft_divide(GCRules *rules, GCPosition *pos, int depth,
                     GCPackedAction *actions, uint64_t *counts, int *n,
                     uint64_t *total);

#endif /* GENERIC_CHESS_NATIVE_PERFT_H */
