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

/* Make one packed action; fills undo. Returns 0 on internal error
 * (e.g. no piece at from, drop on occupied square). */
int gc_make_move(GCPosition *pos, const GCRules *rules, GCPackedAction action,
                 GCUndo *undo);

void gc_unmake_move(GCPosition *pos, const GCRules *rules, const GCUndo *undo);

int gc_make_move_verify(GCPosition *pos, const GCRules *rules,
                        GCPackedAction action, GCUndo *undo);

#endif /* GENERIC_CHESS_NATIVE_STATE_H */
