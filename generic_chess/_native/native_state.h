#ifndef GENERIC_CHESS_NATIVE_STATE_H
#define GENERIC_CHESS_NATIVE_STATE_H

#include "native_types.h"

/* Plain board payload filled by the Python module from a pack dict. */
typedef struct {
    uint8_t side_to_move;
    uint16_t ply;
    uint16_t root_hash_count;
    GCPiece board[GC_MAX_SQUARES];     /* occupied flag set for real pieces */
    uint16_t hand_counts[2][GC_MAX_TYPES];
} GCBoardPayload;

/* Initialize a position from a payload and compute the full hash/history. */
int gc_position_pack(GCPosition *pos, const GCRules *rules,
                     const GCBoardPayload *payload);

/* Trusted make: the action is assumed to come from the native legal move
 * generator.  Only cheap memory-safety guards (bounds, hand range, history
 * capacity) run here; returns a GC_STATUS_* code (0 == OK). */
int gc_make_move(GCPosition *pos, const GCRules *rules, GCPackedAction action,
                 GCUndo *undo);

/* Checked make: validates the packed action (fields + exact membership in the
 * native legal move list) before applying it.  Returns a GC_STATUS_* code. */
int gc_make_move_checked(GCPosition *pos, const GCRules *rules,
                         GCPackedAction action, GCUndo *undo);

/* Field-level validation only (no move application).  Returns GC_STATUS_OK
 * when the action passes cheap structural checks. */
int gc_validate_action(const GCRules *rules, const GCPosition *pos,
                       GCPackedAction action);

void gc_unmake_move(GCPosition *pos, const GCRules *rules, const GCUndo *undo);

int gc_make_move_verify(GCPosition *pos, const GCRules *rules,
                        GCPackedAction action, GCUndo *undo);

#endif /* GENERIC_CHESS_NATIVE_STATE_H */
