#ifndef GENERIC_CHESS_NATIVE_SEARCH_H
#define GENERIC_CHESS_NATIVE_SEARCH_H

#include "native_types.h"
#include "native_eval.h"
#include "native_tt.h"

#define GC_FIXED_SEARCH_OK 0
#define GC_FIXED_SEARCH_ERROR 1

/* Fixed-depth negamax/alpha-beta context.
 *
 * No TT / qsearch / ordering / time / node / cancellation support in this
 * phase; the per-ply move lists and the triangular PV table are the only
 * reusable scratch, so the search hot path never allocates. */
typedef struct {
    const GCRules *rules;
    GCEvaluationTables *eval;
    GCTable *tt; /* NULL disables the transposition table */
    uint64_t nodes;
    uint32_t max_depth;
    GCMoveList *pseudo_by_ply;
    GCMoveList *legal_by_ply;
    GCPackedAction *pv_table; /* (max_depth+1) x (max_depth+1) */
    uint16_t *pv_length;      /* [max_depth+1] */
    uint32_t selective_depth; /* deepest main-search ply reached */
    uint64_t tt_probes;
    uint64_t tt_hits;
    uint64_t tt_cutoffs;
    uint64_t tt_stores;
    uint64_t tt_replacements;
    uint64_t tt_collisions;
    uint64_t tt_legal_move_misses;
    uint64_t beta_cutoffs;
    int error;
} GCSearchContext;

typedef struct {
    int32_t score;
    GCPackedAction best_action;
    uint8_t has_action;
    uint64_t nodes;
    uint16_t completed_depth;
    uint8_t terminated; /* root position was terminal */
    int status;
} GCFixedSearchResult;

/* Allocate a search context for a fixed max depth.  Returns 1 on success. */
int gc_search_context_alloc(GCSearchContext *ctx, const GCRules *rules,
                            GCEvaluationTables *eval, GCTable *tt,
                            uint32_t max_depth);

void gc_search_context_free(GCSearchContext *ctx);

/* Run a fixed-depth search.  The position is restored on return.  Fills
 * ``result``; returns 1 on success (result->status == GC_FIXED_SEARCH_OK),
 * 0 on internal/allocation failure. */
int gc_fixed_depth_search(GCSearchContext *ctx, GCPosition *pos,
                          uint32_t depth, GCFixedSearchResult *result);

#endif /* GENERIC_CHESS_NATIVE_SEARCH_H */
