#include "native_state.h"

#include <string.h>

#include "native_hash.h"
#include "native_movegen.h"

int gc_position_pack(GCPosition *pos, const GCRules *rules,
                     const GCBoardPayload *payload) {
    memset(pos, 0, sizeof(GCPosition));
    pos->side_to_move = payload->side_to_move;
    pos->ply = payload->ply;
    pos->root_hash_count = payload->root_hash_count;
    memcpy(pos->board, payload->board, sizeof(GCPiece) * rules->squares);
    memcpy(pos->hand_counts, payload->hand_counts, sizeof(pos->hand_counts));
    gc_hash_full(rules, pos);
    pos->history_lo[0] = pos->hash_lo;
    pos->history_hi[0] = pos->hash_hi;
    pos->history_len = 1;
    pos->history_complete = (payload->root_hash_count == 0);
    gc_repetition_context_rebuild(pos);
    return 1;
}

int gc_make_move(GCPosition *pos, const GCRules *rules, GCPackedAction action,
                 GCUndo *undo) {
    GCSquare to = (GCSquare)GC_ACTION_TO(action);
    GCSquare from = (GCSquare)GC_ACTION_FROM(action);
    GCTypeIndex promo = (GCTypeIndex)GC_ACTION_PROMO(action);
    GCTypeIndex base = (GCTypeIndex)GC_ACTION_BASE(action);
    uint8_t kind = (uint8_t)GC_ACTION_KIND(action);
    uint8_t side = pos->side_to_move;

    if (pos->history_len >= (uint16_t)(GC_MAX_PLY + 1)) {
        return GC_STATUS_HISTORY_FULL;
    }
    memset(undo, 0, sizeof(GCUndo));
    undo->to = to;
    undo->old_side = side;
    undo->old_ply = pos->ply;
    undo->old_history_len = pos->history_len;
    undo->old_hash_lo = pos->hash_lo;
    undo->old_hash_hi = pos->hash_hi;
    undo->old_repetition_context_lo = pos->repetition_context_lo;
    undo->old_repetition_context_hi = pos->repetition_context_hi;

    if (kind == GC_ACTION_KIND_DROP) {
        if (to >= rules->squares || pos->board[to].occupied) {
            return to >= rules->squares ? GC_STATUS_ACTION_TO_OUT_OF_RANGE
                                        : GC_STATUS_ACTION_DROP_OCCUPIED;
        }
        if (pos->hand_counts[side][base] == 0) {
            return GC_STATUS_ACTION_DROP_NO_HAND;
        }
        undo->from = GC_NO_SQUARE;
        undo->was_drop = 1;
        GCPiece piece;
        piece.base_type = base;
        piece.current_type = base;
        piece.owner = side;
        piece.promoted = 0;
        piece.occupied = 1;
        if (!gc_hash_remove_hand((GCRules *)rules, pos, side, base)) {
            return GC_STATUS_HAND_OVERFLOW;
        }
        pos->hand_counts[side][base]--;
        pos->board[to] = piece;
        gc_hash_xor_piece((GCRules *)rules, pos, &piece, to);
    } else {
        if (from >= rules->squares || to >= rules->squares) {
            return GC_STATUS_ACTION_FROM_OUT_OF_RANGE;
        }
        GCPiece moved = pos->board[from];
        GCPiece captured = pos->board[to];
        if (!moved.occupied) {
            return GC_STATUS_ACTION_NO_MOVER;
        }
        if (moved.owner != side) {
            return GC_STATUS_ACTION_WRONG_OWNER;
        }
        if (captured.occupied && captured.owner == side) {
            return GC_STATUS_ACTION_TARGET_FRIENDLY;
        }
        undo->from = from;
        undo->moved = moved;
        undo->captured = captured;
        /* The action's promo field is 8-bit: 0xFF is the "no promotion"
         * sentinel (GC_NO_TYPE is the 16-bit sentinel). */
        undo->was_promotion = (promo != 0xFF);

        GCPiece placed = moved;
        if (undo->was_promotion) {
            placed.current_type = promo;
            placed.promoted = 1;
        }

        gc_hash_xor_piece((GCRules *)rules, pos, &moved, from);
        if (captured.occupied) {
            if (pos->hand_counts[side][captured.base_type] >= GC_MAX_HAND) {
                gc_hash_xor_piece((GCRules *)rules, pos, &moved, from);
                return GC_STATUS_HAND_OVERFLOW;
            }
            gc_hash_xor_piece((GCRules *)rules, pos, &captured, to);
            if (!gc_hash_add_hand((GCRules *)rules, pos, side,
                                  captured.base_type)) {
                gc_hash_xor_piece((GCRules *)rules, pos, &moved, from);
                return GC_STATUS_HAND_OVERFLOW;
            }
            pos->hand_counts[side][captured.base_type]++;
        }
        memset(&pos->board[from], 0, sizeof(GCPiece));
        pos->board[to] = placed;
        gc_hash_xor_piece((GCRules *)rules, pos, &placed, to);
    }

    gc_hash_xor_side((GCRules *)rules, pos, side); /* remove old side */
    pos->side_to_move = 1 - side;
    gc_hash_xor_side((GCRules *)rules, pos, 1 - side); /* add new side */
    pos->ply++;
    /* Incrementally update the repetition-context fingerprint for the child
     * position before appending it to the history stack. */
    {
        uint16_t old_count = gc_hash_occurrences(rules, pos, pos->hash_lo,
                                                 pos->hash_hi);
        uint64_t token_lo, token_hi;
        if (old_count > 0) {
            gc_repetition_count_token(pos->hash_lo, pos->hash_hi, old_count,
                                      &token_lo, &token_hi);
            pos->repetition_context_lo ^= token_lo;
            pos->repetition_context_hi ^= token_hi;
        }
        gc_repetition_count_token(pos->hash_lo, pos->hash_hi,
                                  (uint16_t)(old_count + 1),
                                  &token_lo, &token_hi);
        pos->repetition_context_lo ^= token_lo;
        pos->repetition_context_hi ^= token_hi;
    }
    pos->history_lo[pos->history_len] = pos->hash_lo;
    pos->history_hi[pos->history_len] = pos->hash_hi;
    pos->history_len++;
    return GC_STATUS_OK;
}

int gc_validate_action(const GCRules *rules, const GCPosition *pos,
                       GCPackedAction action) {
    GCSquare to = (GCSquare)GC_ACTION_TO(action);
    GCSquare from = (GCSquare)GC_ACTION_FROM(action);
    GCTypeIndex promo = (GCTypeIndex)GC_ACTION_PROMO(action);
    GCTypeIndex base = (GCTypeIndex)GC_ACTION_BASE(action);
    uint8_t kind = (uint8_t)GC_ACTION_KIND(action);

    if ((action & ~(uint64_t)0xFFFFFFFFFull) != 0) {
        return GC_STATUS_ACTION_RESERVED_BITS;
    }
    if (kind != GC_ACTION_KIND_BOARD && kind != GC_ACTION_KIND_DROP) {
        return GC_STATUS_ACTION_INVALID_KIND;
    }
    if (to >= rules->squares) {
        return GC_STATUS_ACTION_TO_OUT_OF_RANGE;
    }
    if (base >= rules->type_count) {
        return GC_STATUS_ACTION_BASE_OUT_OF_RANGE;
    }
    if (promo != 0xFF) {
        if (promo >= rules->type_count) {
            return GC_STATUS_ACTION_PROMO_OUT_OF_RANGE;
        }
    }
    if (kind == GC_ACTION_KIND_BOARD) {
        if (from >= rules->squares) {
            return GC_STATUS_ACTION_FROM_OUT_OF_RANGE;
        }
    } else {
        if (from != 0xFF) {
            return GC_STATUS_ACTION_FROM_NOT_SENTINEL;
        }
    }
    return GC_STATUS_OK;
}

int gc_make_move_checked(GCPosition *pos, const GCRules *rules,
                         GCPackedAction action, GCUndo *undo) {
    int status = gc_validate_action(rules, pos, action);
    if (status != GC_STATUS_OK) {
        return status;
    }
    /* Exact membership in the native legal move list: the same truth source
     * the search uses, so a forged packed action cannot bypass legality. */
    GCMoveList legal;
    gc_move_list_init(&legal);
    if (!gc_legal_actions(rules, pos, &legal)) {
        gc_move_list_destroy(&legal);
        return GC_STATUS_MEMORY;
    }
    int found = 0;
    size_t i;
    for (i = 0; i < legal.count; i++) {
        if (legal.data[i] == action) {
            found = 1;
            break;
        }
    }
    gc_move_list_destroy(&legal);
    if (!found) {
        return GC_STATUS_ACTION_NOT_LEGAL;
    }
    return gc_make_move(pos, rules, action, undo);
}

void gc_unmake_move(GCPosition *pos, const GCRules *rules, const GCUndo *undo) {
    (void)rules;
    uint8_t side = undo->old_side;
    if (undo->was_drop) {
        GCPiece dropped = pos->board[undo->to];
        gc_hash_xor_piece((GCRules *)rules, pos, &dropped, undo->to);
        memset(&pos->board[undo->to], 0, sizeof(GCPiece));
        gc_hash_add_hand((GCRules *)rules, pos, side, dropped.base_type);
        pos->hand_counts[side][dropped.base_type]++;
    } else {
        GCPiece placed = pos->board[undo->to];
        gc_hash_xor_piece((GCRules *)rules, pos, &placed, undo->to);
        pos->board[undo->from] = undo->moved;
        if (undo->captured.occupied) {
            pos->board[undo->to] = undo->captured;
            gc_hash_xor_piece((GCRules *)rules, pos, &undo->captured, undo->to);
            gc_hash_remove_hand((GCRules *)rules, pos, side,
                                undo->captured.base_type);
            pos->hand_counts[side][undo->captured.base_type]--;
        } else {
            memset(&pos->board[undo->to], 0, sizeof(GCPiece));
        }
    }
    pos->side_to_move = side;
    pos->ply = undo->old_ply;
    pos->history_len = undo->old_history_len;
    pos->hash_lo = undo->old_hash_lo;
    pos->hash_hi = undo->old_hash_hi;
    pos->repetition_context_lo = undo->old_repetition_context_lo;
    pos->repetition_context_hi = undo->old_repetition_context_hi;
}

int gc_make_move_verify(GCPosition *pos, const GCRules *rules,
                        GCPackedAction action, GCUndo *undo) {
    if (gc_make_move(pos, rules, action, undo) != GC_STATUS_OK) {
        return 0;
    }
    return gc_hash_verify(rules, pos);
}
