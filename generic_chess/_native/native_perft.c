#include "native_perft.h"

#include "native_attack.h"
#include "native_hash.h"
#include "native_movegen.h"
#include "native_state.h"

GCTerminal gc_terminal(GCRules *rules, GCPosition *pos) {
    GCPackedAction moves[GC_MAX_ACTIONS];
    int n = gc_legal_actions(rules, pos, moves, GC_MAX_ACTIONS);
    if (n == 0) {
        GCSquare anchor = gc_find_anchor(rules, pos, pos->side_to_move);
        if (anchor != GC_NO_SQUARE &&
            gc_is_square_attacked(rules, pos, anchor, 1 - pos->side_to_move)) {
            return GC_TERM_CHECKMATE;
        }
        return GC_TERM_STALEMATE;
    }
    if (gc_repetition_count(rules, pos) >= rules->repetition_limit) {
        return GC_TERM_REPETITION;
    }
    if (pos->ply >= rules->max_ply) {
        return GC_TERM_MAX_PLY;
    }
    return GC_TERM_ONGOING;
}

uint64_t gc_perft(GCRules *rules, GCPosition *pos, int depth) {
    if (depth <= 0) {
        return 1;
    }
    GCPackedAction moves[GC_MAX_ACTIONS];
    int n = gc_legal_actions(rules, pos, moves, GC_MAX_ACTIONS);
    if (n == 0) {
        return 0;
    }
    if (gc_repetition_count(rules, pos) >= rules->repetition_limit) {
        return 0;
    }
    if (pos->ply >= rules->max_ply) {
        return 0;
    }
    uint64_t total = 0;
    int i;
    for (i = 0; i < n; i++) {
        GCUndo undo;
        gc_make_move(pos, rules, moves[i], &undo);
        total += gc_perft(rules, pos, depth - 1);
        gc_unmake_move(pos, rules, &undo);
    }
    return total;
}

void gc_perft_divide(GCRules *rules, GCPosition *pos, int depth,
                     GCPackedAction *actions, uint64_t *counts, int *n,
                     uint64_t *total) {
    int count = gc_legal_actions(rules, pos, actions, GC_MAX_ACTIONS);
    *n = count;
    *total = 0;
    int i;
    for (i = 0; i < count; i++) {
        GCUndo undo;
        gc_make_move(pos, rules, actions[i], &undo);
        counts[i] = gc_perft(rules, pos, depth - 1);
        gc_unmake_move(pos, rules, &undo);
        *total += counts[i];
    }
}
