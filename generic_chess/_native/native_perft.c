#include "native_perft.h"

#include <stdlib.h>

#include "native_attack.h"
#include "native_hash.h"
#include "native_movegen.h"
#include "native_state.h"

void gc_perft_scratch_init(GCPerftScratch *scratch) {
    scratch->pseudo = NULL;
    scratch->legal = NULL;
    scratch->capacity = 0;
}

void gc_perft_scratch_destroy(GCPerftScratch *scratch) {
    if (scratch->pseudo != NULL) {
        size_t i;
        for (i = 0; i < scratch->capacity; i++) {
            gc_move_list_destroy(&scratch->pseudo[i]);
            gc_move_list_destroy(&scratch->legal[i]);
        }
        free(scratch->pseudo);
        free(scratch->legal);
    }
    scratch->pseudo = NULL;
    scratch->legal = NULL;
    scratch->capacity = 0;
}

int gc_perft_scratch_ensure(GCPerftScratch *scratch, size_t levels) {
    if (levels <= scratch->capacity) {
        return 1;
    }
    GCMoveList *pseudo =
        (GCMoveList *)realloc(scratch->pseudo, levels * sizeof(GCMoveList));
    GCMoveList *legal =
        (GCMoveList *)realloc(scratch->legal, levels * sizeof(GCMoveList));
    if (pseudo == NULL || legal == NULL) {
        free(pseudo);
        free(legal);
        return 0;
    }
    scratch->pseudo = pseudo;
    scratch->legal = legal;
    size_t i;
    for (i = scratch->capacity; i < levels; i++) {
        gc_move_list_init(&scratch->pseudo[i]);
        gc_move_list_init(&scratch->legal[i]);
    }
    scratch->capacity = levels;
    return 1;
}

GCTerminal gc_terminal_with_pseudo(const GCRules *rules, GCPosition *pos,
                                   GCMoveList *pseudo, GCMoveList *legal) {
    if (!gc_pseudo_actions(rules, pos, pseudo)) {
        return (GCTerminal)-1; /* allocation failure; caller must check */
    }
    if (!gc_legal_filter(rules, pos, pseudo, legal)) {
        return (GCTerminal)-1; /* allocation failure; caller must check */
    }
    if (legal->count == 0) {
        GCSquare anchor = gc_find_anchor(rules, pos, pos->side_to_move);
        if (anchor != GC_NO_SQUARE &&
            gc_is_square_attacked(rules, pos, anchor,
                                  1 - pos->side_to_move)) {
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

GCTerminal gc_terminal(const GCRules *rules, GCPosition *pos,
                       GCMoveList *legal) {
    GCMoveList pseudo;
    gc_move_list_init(&pseudo);
    GCTerminal term = gc_terminal_with_pseudo(rules, pos, &pseudo, legal);
    gc_move_list_destroy(&pseudo);
    return term;
}

static int gc_perft_inner(const GCRules *rules, GCPosition *pos, int depth,
                          GCPerftScratch *scratch, uint64_t *total) {
    if (depth <= 0) {
        *total = 1;
        return 1;
    }
    GCMoveList *pseudo = &scratch->pseudo[depth];
    GCMoveList *legal = &scratch->legal[depth];
    GCTerminal term = gc_terminal_with_pseudo(rules, pos, pseudo, legal);
    if (term == (GCTerminal)-1) {
        return 0;
    }
    if (term != GC_TERM_ONGOING) {
        *total = 0;
        return 1;
    }
    uint64_t sum = 0;
    size_t i;
    for (i = 0; i < legal->count; i++) {
        GCUndo undo;
        if (gc_make_move(pos, rules, legal->data[i], &undo) != GC_STATUS_OK) {
            return 0;
        }
        uint64_t child = 0;
        int ok = gc_perft_inner(rules, pos, depth - 1, scratch, &child);
        gc_unmake_move(pos, rules, &undo);
        if (!ok) {
            return 0;
        }
        sum += child;
    }
    *total = sum;
    return 1;
}

int gc_perft(const GCRules *rules, GCPosition *pos, int depth,
             GCPerftScratch *scratch, uint64_t *total) {
    if (!gc_perft_scratch_ensure(scratch, (size_t)depth + 1)) {
        return 0;
    }
    return gc_perft_inner(rules, pos, depth, scratch, total);
}

int gc_perft_divide(const GCRules *rules, GCPosition *pos, int depth,
                    GCPerftScratch *scratch, GCMoveList *root_moves,
                    uint64_t *counts, uint64_t *total) {
    if (!gc_perft_scratch_ensure(scratch, (size_t)depth + 1)) {
        return 0;
    }
    GCMoveList *pseudo = &scratch->pseudo[depth];
    GCMoveList *legal = &scratch->legal[depth];
    GCTerminal term = gc_terminal_with_pseudo(rules, pos, pseudo, legal);
    if (term == (GCTerminal)-1) {
        return 0;
    }
    if (term != GC_TERM_ONGOING) {
        *total = 0;
        gc_move_list_clear(root_moves);
        return 1;
    }
    size_t n = legal->count;
    if (!gc_move_list_reserve(root_moves, n)) {
        return 0;
    }
    gc_move_list_clear(root_moves);
    size_t i;
    for (i = 0; i < n; i++) {
        root_moves->data[i] = legal->data[i];
    }
    root_moves->count = n;
    uint64_t sum = 0;
    for (i = 0; i < n; i++) {
        GCUndo undo;
        if (gc_make_move(pos, rules, legal->data[i], &undo) != GC_STATUS_OK) {
            return 0;
        }
        uint64_t child = 0;
        int ok = gc_perft_inner(rules, pos, depth - 1, scratch, &child);
        gc_unmake_move(pos, rules, &undo);
        if (!ok) {
            return 0;
        }
        counts[i] = child;
        sum += child;
    }
    *total = sum;
    return 1;
}
