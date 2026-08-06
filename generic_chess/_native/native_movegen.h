#ifndef GENERIC_CHESS_NATIVE_MOVEGEN_H
#define GENERIC_CHESS_NATIVE_MOVEGEN_H

#include "native_types.h"

/* Growable move-list helpers.  All functions return 1 on success; on
 * allocation/overflow failure they return 0 and record a GC_MOVE_ERROR_*
 * code in ``list->error`` so callers can distinguish "overflow" from a
 * normal empty list. */
void gc_move_list_init(GCMoveList *list);
void gc_move_list_clear(GCMoveList *list);
void gc_move_list_destroy(GCMoveList *list);
int gc_move_list_reserve(GCMoveList *list, size_t required);
int gc_move_list_append(GCMoveList *list, GCPackedAction action);

/* Fill ``out`` with pseudo actions (no legality filter).  Returns 0 and sets
 * ``out->error`` when the list could not grow. */
int gc_pseudo_actions(const GCRules *rules, GCPosition *pos, GCMoveList *out);

/* Fill ``out`` with legal actions.  ``out`` must be initialized; its contents
 * are cleared before generation.  Returns 0 on allocation failure. */
int gc_legal_actions(const GCRules *rules, GCPosition *pos, GCMoveList *out);

/* Legality filter over an existing pseudo list (search hot path reuses the
 * per-ply pseudo and legal lists, so no per-node allocation happens). */
int gc_legal_filter(const GCRules *rules, GCPosition *pos,
                    const GCMoveList *pseudo, GCMoveList *legal);

#endif /* GENERIC_CHESS_NATIVE_MOVEGEN_H */
