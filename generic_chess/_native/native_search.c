#include "native_search.h"

#include <stdlib.h>
#include <string.h>

#include "native_movegen.h"
#include "native_perft.h"
#include "native_state.h"

#define GC_INF32 2000000000

static int gc_action_cmp(const void *a, const void *b) {
    uint64_t x = *(const uint64_t *)a;
    uint64_t y = *(const uint64_t *)b;
    return (x > y) - (x < y);
}

/* Terminal score from the current node's side-to-move perspective using the
 * evaluation config's mate score (never a second hard-coded constant). */
static int32_t gc_node_terminal_score(const GCEvaluationTables *eval,
                                      GCTerminal term, int ply) {
    switch (term) {
        case GC_TERM_CHECKMATE:
            return -(eval->mate_score - ply);
        default:
            return 0;
    }
}

int gc_search_context_alloc(GCSearchContext *ctx, const GCRules *rules,
                            GCEvaluationTables *eval, uint32_t max_depth) {
    memset(ctx, 0, sizeof(*ctx));
    ctx->rules = rules;
    ctx->eval = eval;
    ctx->max_depth = max_depth;
    size_t depth = (size_t)max_depth + 1;
    ctx->pseudo_by_ply = (GCMoveList *)calloc(depth, sizeof(GCMoveList));
    ctx->legal_by_ply = (GCMoveList *)calloc(depth, sizeof(GCMoveList));
    ctx->pv_table = (GCPackedAction *)calloc(depth * depth, sizeof(GCPackedAction));
    ctx->pv_length = (uint16_t *)calloc(depth, sizeof(uint16_t));
    if (ctx->pseudo_by_ply == NULL || ctx->legal_by_ply == NULL ||
        ctx->pv_table == NULL || ctx->pv_length == NULL) {
        gc_search_context_free(ctx);
        return 0;
    }
    size_t i;
    for (i = 0; i < depth; i++) {
        gc_move_list_init(&ctx->pseudo_by_ply[i]);
        gc_move_list_init(&ctx->legal_by_ply[i]);
    }
    return 1;
}

void gc_search_context_free(GCSearchContext *ctx) {
    if (ctx->pseudo_by_ply != NULL) {
        size_t depth = (size_t)ctx->max_depth + 1;
        size_t i;
        for (i = 0; i < depth; i++) {
            gc_move_list_destroy(&ctx->pseudo_by_ply[i]);
            gc_move_list_destroy(&ctx->legal_by_ply[i]);
        }
    }
    free(ctx->pseudo_by_ply);
    free(ctx->legal_by_ply);
    free(ctx->pv_table);
    free(ctx->pv_length);
    memset(ctx, 0, sizeof(*ctx));
}

static int32_t gc_negamax(GCSearchContext *ctx, GCPosition *pos, int depth,
                          int32_t alpha, int32_t beta, int ply) {
    ctx->nodes++;
    /* Reset this node's PV row so a terminal node (or a node whose best line
     * ends here) never inherits stale tail moves from a sibling search. */
    ctx->pv_length[ply] = 0;
    GCMoveList *pseudo = &ctx->pseudo_by_ply[ply];
    GCMoveList *legal = &ctx->legal_by_ply[ply];
    GCTerminal term = gc_terminal_with_pseudo(ctx->rules, pos, pseudo, legal);
    if (term == (GCTerminal)-1) {
        ctx->error = 1;
        return 0;
    }
    if (term != GC_TERM_ONGOING) {
        return gc_node_terminal_score(ctx->eval, term, ply);
    }
    if (depth <= 0) {
        return gc_evaluate_material(ctx->rules, ctx->eval, pos);
    }

    qsort(legal->data, legal->count, sizeof(GCPackedAction), gc_action_cmp);
    int32_t best = -GC_INF32;
    size_t stride = (size_t)ctx->max_depth + 1;
    size_t i;
    for (i = 0; i < legal->count; i++) {
        GCPackedAction action = legal->data[i];
        GCUndo undo;
        if (gc_make_move(pos, ctx->rules, action, &undo) != GC_STATUS_OK) {
            ctx->error = 1;
            return 0;
        }
        int32_t score = -gc_negamax(ctx, pos, depth - 1, -beta, -alpha,
                                    ply + 1);
        gc_unmake_move(pos, ctx->rules, &undo);
        if (ctx->error) {
            return 0;
        }
        if (score > best) {
            best = score;
            ctx->pv_table[(size_t)ply * stride] = action;
            uint16_t child_len = ctx->pv_length[ply + 1];
            ctx->pv_length[ply] = (uint16_t)(1 + child_len);
            if (child_len > 0) {
                memcpy(&ctx->pv_table[(size_t)ply * stride + 1],
                       &ctx->pv_table[(size_t)(ply + 1) * stride],
                       sizeof(GCPackedAction) * child_len);
            }
        }
        if (best > alpha) {
            alpha = best;
        }
        if (alpha >= beta) {
            break;
        }
    }
    return best;
}

int gc_fixed_depth_search(GCSearchContext *ctx, GCPosition *pos,
                          uint32_t depth, GCFixedSearchResult *result) {
    memset(result, 0, sizeof(*result));
    ctx->nodes = 0;
    ctx->error = 0;
    size_t i;
    for (i = 0; i <= ctx->max_depth; i++) {
        ctx->pv_length[i] = 0;
    }
    if (depth > ctx->max_depth) {
        result->status = GC_FIXED_SEARCH_ERROR;
        return 0;
    }

    GCMoveList *pseudo = &ctx->pseudo_by_ply[0];
    GCMoveList *legal = &ctx->legal_by_ply[0];
    GCTerminal term = gc_terminal_with_pseudo(ctx->rules, pos, pseudo, legal);
    if (term == (GCTerminal)-1) {
        result->status = GC_FIXED_SEARCH_ERROR;
        return 0;
    }
    ctx->nodes = 1; /* the root node is visited */
    if (term != GC_TERM_ONGOING) {
        result->score = gc_node_terminal_score(ctx->eval, term, 0);
        result->has_action = 0;
        result->completed_depth = 0;
        result->terminated = 1;
        result->status = GC_FIXED_SEARCH_OK;
        return 1;
    }
    if (depth == 0) {
        result->score = gc_evaluate_material(ctx->rules, ctx->eval, pos);
        result->has_action = 0;
        result->completed_depth = 0;
        result->nodes = ctx->nodes;
        result->status = GC_FIXED_SEARCH_OK;
        return 1;
    }

    qsort(legal->data, legal->count, sizeof(GCPackedAction), gc_action_cmp);
    int32_t best = -GC_INF32;
    GCPackedAction best_action = 0;
    size_t stride = (size_t)ctx->max_depth + 1;
    size_t k;
    for (k = 0; k < legal->count; k++) {
        GCPackedAction action = legal->data[k];
        GCUndo undo;
        if (gc_make_move(pos, ctx->rules, action, &undo) != GC_STATUS_OK) {
            result->status = GC_FIXED_SEARCH_ERROR;
            return 0;
        }
        int32_t score = -gc_negamax(ctx, pos, depth - 1, -GC_INF32,
                                    GC_INF32, 1);
        gc_unmake_move(pos, ctx->rules, &undo);
        if (ctx->error) {
            result->status = GC_FIXED_SEARCH_ERROR;
            return 0;
        }
        if (score > best) {
            best = score;
            best_action = action;
            ctx->pv_table[0] = action;
            uint16_t child_len = ctx->pv_length[1];
            ctx->pv_length[0] = (uint16_t)(1 + child_len);
            if (child_len > 0) {
                memcpy(&ctx->pv_table[1],
                       &ctx->pv_table[stride],
                       sizeof(GCPackedAction) * child_len);
            }
        }
    }
    result->score = best;
    result->best_action = best_action;
    result->has_action = legal->count > 0;
    result->nodes = ctx->nodes;
    result->completed_depth = (uint16_t)depth;
    result->status = GC_FIXED_SEARCH_OK;
    return 1;
}
