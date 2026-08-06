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
                            GCEvaluationTables *eval, GCTable *tt,
                            uint32_t max_depth) {
    memset(ctx, 0, sizeof(*ctx));
    ctx->rules = rules;
    ctx->eval = eval;
    ctx->tt = tt;
    ctx->max_depth = max_depth;
    ctx->max_nodes = GC_NODES_UNLIMITED;
    ctx->max_time_ns = GC_TIME_UNLIMITED;
    ctx->deadline_ns = GC_TIME_UNLIMITED;
    if (max_depth > GC_MAX_PLY) {
        return 0;
    }
    size_t depth = 0, bytes = 0;
    if (!gc_checked_size_add((size_t)max_depth, 1, &depth)) {
        return 0;
    }
    if (!gc_checked_size_mul(depth, sizeof(GCMoveList), &bytes)) {
        return 0;
    }
    ctx->pseudo_by_ply = (GCMoveList *)calloc(depth, sizeof(GCMoveList));
    ctx->legal_by_ply = (GCMoveList *)calloc(depth, sizeof(GCMoveList));
    if (!gc_checked_size_mul(depth, depth, &bytes)) {
        gc_search_context_free(ctx);
        return 0;
    }
    ctx->pv_table = (GCPackedAction *)calloc(depth * depth, sizeof(GCPackedAction));
    ctx->pv_length = (uint16_t *)calloc(depth, sizeof(uint16_t));
    ctx->completed_pv = (GCPackedAction *)calloc(depth, sizeof(GCPackedAction));
    if (ctx->pseudo_by_ply == NULL || ctx->legal_by_ply == NULL ||
        ctx->pv_table == NULL || ctx->pv_length == NULL ||
        ctx->completed_pv == NULL) {
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
    free(ctx->completed_pv);
    memset(ctx, 0, sizeof(*ctx));
}

GCSearchControl gc_search_check_budget(GCSearchContext *ctx, int force) {
    if (ctx->cancel != NULL &&
        gc_cancel_flag_is_requested(ctx->cancel)) {
        ctx->control = GC_SEARCH_ABORT_CANCELLED;
        return ctx->control;
    }
    if (ctx->max_nodes != GC_NODES_UNLIMITED && ctx->nodes >= ctx->max_nodes) {
        ctx->control = GC_SEARCH_ABORT_NODE_LIMIT;
        return ctx->control;
    }
    if (ctx->max_time_ns != GC_TIME_UNLIMITED) {
        if (force || ctx->nodes >= ctx->last_time_check_nodes + 128) {
            ctx->last_time_check_nodes = ctx->nodes;
            if (gc_monotonic_ns() >= ctx->deadline_ns) {
                ctx->control = GC_SEARCH_ABORT_TIME_LIMIT;
                return ctx->control;
            }
        }
    }
    ctx->control = GC_SEARCH_CONTINUE;
    return ctx->control;
}

static int32_t gc_negamax(GCSearchContext *ctx, GCPosition *pos, int depth,
                          int32_t alpha, int32_t beta, int ply) {
    /* Node budget is exact: check before visiting this node. */
    if (ctx->max_nodes != GC_NODES_UNLIMITED && ctx->nodes >= ctx->max_nodes) {
        ctx->control = GC_SEARCH_ABORT_NODE_LIMIT;
        return 0;
    }
    ctx->nodes++;
    if (ctx->nodes >= ctx->last_time_check_nodes + 128 &&
        (ctx->max_time_ns != GC_TIME_UNLIMITED || ctx->cancel != NULL)) {
        ctx->last_time_check_nodes = ctx->nodes;
        if (ctx->cancel != NULL &&
            gc_cancel_flag_is_requested(ctx->cancel)) {
            ctx->control = GC_SEARCH_ABORT_CANCELLED;
            return 0;
        }
        if (ctx->max_time_ns != GC_TIME_UNLIMITED &&
            gc_monotonic_ns() >= ctx->deadline_ns) {
            ctx->control = GC_SEARCH_ABORT_TIME_LIMIT;
            return 0;
        }
    }
    if ((uint32_t)ply > ctx->selective_depth) {
        ctx->selective_depth = (uint32_t)ply;
    }
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
        int32_t v = gc_evaluate_material(ctx->rules, ctx->eval, pos);
        if (ctx->tt != NULL) {
            ctx->tt_stores++;
            uint64_t replaced = 0;
            gc_tt_store(ctx->tt, pos, 0, ctx->eval, ply, v,
                        GC_TT_BOUND_EXACT, 0, 0, &replaced);
            ctx->tt_replacements += replaced;
        }
        return v;
    }

    int32_t original_alpha = alpha;
    int32_t original_beta = beta;
    GCPackedAction tt_action = 0;
    int has_tt_action = 0;
    if (ctx->tt != NULL) {
        ctx->tt_probes++;
        int32_t tt_score = 0;
        int has_action = 0;
        int entry_depth = -1;
        uint64_t coll = 0;
        int hit = gc_tt_probe(ctx->tt, pos, depth, ctx->eval, ply, &tt_score,
                              &tt_action, &has_action, &entry_depth, &coll);
        ctx->tt_collisions += coll;
        if (hit) {
            ctx->tt_hits++;
            has_tt_action = has_action;
            if (!ctx->no_tt_score_cutoffs && entry_depth >= depth) {
                if (tt_score > alpha) {
                    alpha = tt_score;
                }
                if (tt_score < beta) {
                    beta = tt_score;
                }
                if (alpha >= beta) {
                    ctx->tt_cutoffs++;
                    return tt_score;
                }
            }
        }
    }

    qsort(legal->data, legal->count, sizeof(GCPackedAction), gc_action_cmp);
    if (has_tt_action && legal->count > 1) {
        size_t found = legal->count;
        size_t si;
        for (si = 0; si < legal->count; si++) {
            if (legal->data[si] == tt_action) {
                found = si;
                break;
            }
        }
        if (found < legal->count) {
            GCPackedAction tmp = legal->data[0];
            legal->data[0] = legal->data[found];
            legal->data[found] = tmp;
        } else {
            ctx->tt_legal_move_misses++;
        }
    }
    int32_t best = -GC_INF32;
    GCPackedAction best_action = 0;
    int has_best = 0;
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
        if (ctx->error || ctx->control != GC_SEARCH_CONTINUE) {
            return 0;
        }
        if (score > best ||
            (score == best && (!has_best || action < best_action))) {
            best = score;
            best_action = action;
            has_best = 1;
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
            ctx->beta_cutoffs++;
            break;
        }
    }
    if (ctx->tt != NULL) {
        ctx->tt_stores++;
        GCTTBound bound = GC_TT_BOUND_EXACT;
        if (best <= original_alpha) {
            bound = GC_TT_BOUND_UPPER;
        } else if (best >= original_beta) {
            bound = GC_TT_BOUND_LOWER;
        }
        uint64_t replaced = 0;
        gc_tt_store(ctx->tt, pos, depth, ctx->eval, ply, best, bound,
                    best_action, has_best, &replaced);
        ctx->tt_replacements += replaced;
    }
    return best;
}

/* One root iteration: search every root child with the shared root alpha and
 * publish the PV into pv_table[0].  Returns 1 on success (check
 * ctx->control/ctx->error for aborts). */
static int gc_root_iteration(GCSearchContext *ctx, GCPosition *pos,
                             uint32_t depth, int32_t *score_out,
                             GCPackedAction *action_out, int *has_action_out) {
    GCMoveList *pseudo = &ctx->pseudo_by_ply[0];
    GCMoveList *legal = &ctx->legal_by_ply[0];
    GCTerminal term = gc_terminal_with_pseudo(ctx->rules, pos, pseudo, legal);
    if (term == (GCTerminal)-1) {
        ctx->error = 1;
        return 0;
    }
    if (term != GC_TERM_ONGOING) {
        *score_out = gc_node_terminal_score(ctx->eval, term, 0);
        *action_out = 0;
        *has_action_out = 0;
        return 1;
    }
    if (depth == 0) {
        *score_out = gc_evaluate_material(ctx->rules, ctx->eval, pos);
        *action_out = 0;
        *has_action_out = 0;
        return 1;
    }

    qsort(legal->data, legal->count, sizeof(GCPackedAction), gc_action_cmp);
    GCPackedAction tt_action = 0;
    int has_tt_action = 0;
    if (ctx->tt != NULL && legal->count > 1) {
        ctx->tt_probes++;
        int32_t tt_score = 0;
        int has_action = 0;
        int entry_depth = -1;
        uint64_t coll = 0;
        if (gc_tt_probe(ctx->tt, pos, depth, ctx->eval, 0, &tt_score,
                        &tt_action, &has_action, &entry_depth, &coll)) {
            ctx->tt_hits++;
            has_tt_action = has_action;
        }
        ctx->tt_collisions += coll;
        if (has_tt_action) {
            size_t found = legal->count;
            size_t si;
            for (si = 0; si < legal->count; si++) {
                if (legal->data[si] == tt_action) {
                    found = si;
                    break;
                }
            }
            if (found < legal->count) {
                GCPackedAction tmp = legal->data[0];
                legal->data[0] = legal->data[found];
                legal->data[found] = tmp;
            } else {
                ctx->tt_legal_move_misses++;
            }
        }
    }
    int32_t best = -GC_INF32;
    GCPackedAction best_action = 0;
    int has_best = 0;
    int32_t alpha = -GC_INF32;
    size_t stride = (size_t)ctx->max_depth + 1;
    size_t k;
    for (k = 0; k < legal->count; k++) {
        if (gc_search_check_budget(ctx, 1) != GC_SEARCH_CONTINUE) {
            return 0;
        }
        GCPackedAction action = legal->data[k];
        GCUndo undo;
        if (gc_make_move(pos, ctx->rules, action, &undo) != GC_STATUS_OK) {
            ctx->error = 1;
            return 0;
        }
        int32_t v = gc_negamax(ctx, pos, depth - 1, -GC_INF32, -alpha, 1);
        gc_unmake_move(pos, ctx->rules, &undo);
        if (ctx->error || ctx->control != GC_SEARCH_CONTINUE) {
            return 0;
        }
        /* A returned value exactly equal to the child's beta (-alpha) is
         * ambiguous: it can be a genuine tie or a TT-bound overestimate of a
         * worse line.  Re-search at the full window so the canonical
         * tie-break only ever sees exact scores (rare; only on ties). */
        if (v >= -alpha && alpha > -GC_INF32) {
            GCUndo undo2;
            if (gc_make_move(pos, ctx->rules, action, &undo2) != GC_STATUS_OK) {
                ctx->error = 1;
                return 0;
            }
            int saved_no_cutoffs = ctx->no_tt_score_cutoffs;
            ctx->no_tt_score_cutoffs = 1;
            v = gc_negamax(ctx, pos, depth - 1, -GC_INF32, GC_INF32, 1);
            ctx->no_tt_score_cutoffs = saved_no_cutoffs;
            gc_unmake_move(pos, ctx->rules, &undo2);
            if (ctx->error || ctx->control != GC_SEARCH_CONTINUE) {
                return 0;
            }
        }
        int32_t score = -v;
        if (score > best || (score == best && (!has_best || action < best_action))) {
            best = score;
            best_action = action;
            has_best = 1;
            ctx->pv_table[0] = action;
            uint16_t child_len = ctx->pv_length[1];
            ctx->pv_length[0] = (uint16_t)(1 + child_len);
            if (child_len > 0) {
                memcpy(&ctx->pv_table[1],
                       &ctx->pv_table[stride],
                       sizeof(GCPackedAction) * child_len);
            }
        }
        if (best > alpha) {
            alpha = best;
        }
    }
    if (ctx->tt != NULL) {
        ctx->tt_stores++;
        uint64_t replaced = 0;
        gc_tt_store(ctx->tt, pos, depth, ctx->eval, 0, best,
                    GC_TT_BOUND_EXACT, best_action, has_best, &replaced);
        ctx->tt_replacements += replaced;
    }
    *score_out = best;
    *action_out = best_action;
    *has_action_out = has_best;
    return 1;
}

int gc_fixed_depth_search(GCSearchContext *ctx, GCPosition *pos,
                          uint32_t depth, GCFixedSearchResult *result) {
    memset(result, 0, sizeof(*result));
    ctx->nodes = 0;
    ctx->error = 0;
    ctx->control = GC_SEARCH_CONTINUE;
    ctx->final_control = GC_SEARCH_CONTINUE;
    size_t i;
    for (i = 0; i <= ctx->max_depth; i++) {
        ctx->pv_length[i] = 0;
    }
    if (depth > ctx->max_depth) {
        result->status = GC_FIXED_SEARCH_ERROR;
        return 0;
    }

    GCMoveList *legal = &ctx->legal_by_ply[0];
    GCTerminal term = gc_terminal_with_pseudo(
        ctx->rules, pos, &ctx->pseudo_by_ply[0], legal);
    if (term == (GCTerminal)-1) {
        result->status = GC_FIXED_SEARCH_ERROR;
        return 0;
    }
    ctx->nodes = 1; /* the root node is visited */
    if (term != GC_TERM_ONGOING) {
        result->score = gc_node_terminal_score(ctx->eval, term, 0);
        result->has_action = 0;
        result->completed_depth = 0;
        result->nodes = ctx->nodes;
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

    int32_t score = 0;
    GCPackedAction best_action = 0;
    int has_action = 0;
    if (!gc_root_iteration(ctx, pos, depth, &score, &best_action,
                           &has_action)) {
        result->status = GC_FIXED_SEARCH_ERROR;
        return 0;
    }
    result->score = score;
    result->best_action = best_action;
    result->has_action = (uint8_t)has_action;
    result->nodes = ctx->nodes;
    result->completed_depth = (uint16_t)depth;
    result->status = GC_FIXED_SEARCH_OK;
    return 1;
}

int gc_iterative_search(GCSearchContext *ctx, GCPosition *pos,
                        uint32_t max_depth, uint64_t max_nodes,
                        uint64_t max_time_ns, GCCancelFlag *cancel,
                        GCFixedSearchResult *result) {
    memset(result, 0, sizeof(*result));
    ctx->max_nodes = max_nodes;
    ctx->max_time_ns = max_time_ns;
    ctx->cancel = cancel;
    ctx->nodes = 0;
    ctx->error = 0;
    ctx->control = GC_SEARCH_CONTINUE;
    ctx->selective_depth = 0;
    ctx->last_time_check_nodes = 0;
    ctx->deadline_ns = (max_time_ns == GC_TIME_UNLIMITED)
                           ? GC_TIME_UNLIMITED
                           : gc_deadline_after(gc_monotonic_ns(), max_time_ns);
    ctx->completed_depth = 0;
    ctx->completed_pv_len = 0;
    ctx->completed_has_action = 0;
    if (ctx->tt != NULL) {
        ctx->tt->generation++;
        if (ctx->tt->generation == 0) {
            gc_tt_clear(ctx->tt);
        }
    }
    size_t i;
    for (i = 0; i <= ctx->max_depth; i++) {
        ctx->pv_length[i] = 0;
    }
    if (max_depth > ctx->max_depth) {
        result->status = GC_FIXED_SEARCH_ERROR;
        return 0;
    }

    GCMoveList *legal = &ctx->legal_by_ply[0];
    GCTerminal term = gc_terminal_with_pseudo(
        ctx->rules, pos, &ctx->pseudo_by_ply[0], legal);
    if (term == (GCTerminal)-1) {
        result->status = GC_FIXED_SEARCH_ERROR;
        return 0;
    }
    ctx->nodes = 1; /* root visited */
    if (term != GC_TERM_ONGOING) {
        result->score = gc_node_terminal_score(ctx->eval, term, 0);
        result->has_action = 0;
        result->completed_depth = 0;
        result->nodes = ctx->nodes;
        result->terminated = 1;
        result->status = GC_FIXED_SEARCH_OK;
        return 1;
    }
    if (max_depth == 0) {
        result->score = gc_evaluate_material(ctx->rules, ctx->eval, pos);
        result->has_action = 0;
        result->completed_depth = 0;
        result->nodes = ctx->nodes;
        result->status = GC_FIXED_SEARCH_OK;
        return 1;
    }

    uint32_t depth;
    int published = 0;
    for (depth = 1; depth <= max_depth; depth++) {
        if (gc_search_check_budget(ctx, 1) != GC_SEARCH_CONTINUE) {
            ctx->final_control = ctx->control;
            break;
        }
        int32_t score = 0;
        GCPackedAction best_action = 0;
        int has_action = 0;
        if (!gc_root_iteration(ctx, pos, depth, &score, &best_action,
                               &has_action)) {
            if (ctx->control != GC_SEARCH_CONTINUE) {
                ctx->final_control = ctx->control;
            }
            break; /* abort or internal error */
        }
        ctx->completed_score = score;
        ctx->completed_best_action = best_action;
        ctx->completed_has_action = (uint8_t)has_action;
        ctx->completed_depth = depth;
        ctx->completed_pv_len = ctx->pv_length[0];
        if (ctx->completed_pv_len > 0) {
            memcpy(ctx->completed_pv, ctx->pv_table,
                   sizeof(GCPackedAction) * ctx->completed_pv_len);
        }
        published = 1;
    }

    if (published) {
        result->score = ctx->completed_score;
        result->best_action = ctx->completed_best_action;
        result->has_action = ctx->completed_has_action;
        result->completed_depth = ctx->completed_depth;
        result->pv_length = ctx->completed_pv_len;
        result->pv = ctx->completed_pv;
        result->nodes = ctx->nodes;
        result->status = GC_FIXED_SEARCH_OK;
        return 1;
    }

    /* No complete iteration: deterministic canonical fallback (min packed). */
    result->score = 0;
    GCPackedAction min_action = 0;
    if (legal->count > 0) {
        min_action = legal->data[0];
        size_t k;
        for (k = 1; k < legal->count; k++) {
            if (legal->data[k] < min_action) {
                min_action = legal->data[k];
            }
        }
    }
    result->best_action = min_action;
    result->has_action = legal->count > 0;
    result->completed_depth = 0;
    result->pv_length = 0;
    result->pv = NULL;
    result->nodes = ctx->nodes;
    result->status = GC_FIXED_SEARCH_OK;
    result->used_fallback = 1;
    return 1;
}
