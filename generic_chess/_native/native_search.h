#ifndef GENERIC_CHESS_NATIVE_SEARCH_H
#define GENERIC_CHESS_NATIVE_SEARCH_H

#include "native_types.h"
#include "native_eval.h"
#include "native_tt.h"
#include "native_cancel.h"
#include "native_clock.h"

#define GC_FIXED_SEARCH_OK 0
#define GC_FIXED_SEARCH_ERROR 1

typedef enum {
    GC_SEARCH_CONTINUE = 0,
    GC_SEARCH_ABORT_NODE_LIMIT,
    GC_SEARCH_ABORT_TIME_LIMIT,
    GC_SEARCH_ABORT_CANCELLED,
    GC_SEARCH_INTERNAL_ERROR
} GCSearchControl;

#define GC_NODES_UNLIMITED UINT64_MAX
#define GC_TIME_UNLIMITED UINT64_MAX

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
    int no_tt_score_cutoffs; /* re-search mode: TT only orders, never cuts */
    uint64_t max_nodes;
    uint64_t max_time_ns;
    uint64_t deadline_ns;
    uint64_t last_time_check_nodes;
    GCCancelFlag *cancel;
    GCSearchControl control;
    GCSearchControl final_control; /* abort reason of the last incomplete depth */
    GCPackedAction *completed_pv;
    uint16_t completed_pv_len;
    int32_t completed_score;
    GCPackedAction completed_best_action;
    uint16_t completed_depth;
    uint8_t completed_has_action;
    int error;
} GCSearchContext;

typedef struct {
    int32_t score;
    GCPackedAction best_action;
    uint8_t has_action;
    GCPackedAction *pv; /* caller-owned buffer for iterative results */
    uint16_t pv_length;
    uint64_t nodes;
    uint16_t completed_depth;
    uint8_t terminated; /* root position was terminal */
    uint8_t used_fallback;
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

/* Unified budget check: ``force`` skips the 128-node time/cancel interval.
 * Priority: cancelled > node_limit > time_limit. */
GCSearchControl gc_search_check_budget(GCSearchContext *ctx, int force);

/* Iterative deepening search with node/time budgets and an atomic cancel
 * flag.  Only fully completed iterations are published; on an early abort
 * ``result`` keeps the last completed depth (or fallback semantics set by
 * the caller).  ``max_nodes``/``max_time_ns`` use the *_UNLIMITED sentinels. */
int gc_iterative_search(GCSearchContext *ctx, GCPosition *pos,
                        uint32_t max_depth, uint64_t max_nodes,
                        uint64_t max_time_ns, GCCancelFlag *cancel,
                        GCFixedSearchResult *result);

#endif /* GENERIC_CHESS_NATIVE_SEARCH_H */
